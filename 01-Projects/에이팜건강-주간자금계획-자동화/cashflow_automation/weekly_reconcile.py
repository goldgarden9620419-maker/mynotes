# -*- coding: utf-8 -*-
"""금요일 주간 대조: 이번 주 계획 vs 실제 계좌별 입출금.

월요일 자금계획의 지급예정과 은행 3사 실제 입출금을 주말 전에 대조해,
차이(미집행·계획없는출금·금액차이)를 사용자에게 먼저 확인받는 보고서
(06_확인필요/주간대조_일시.xlsx)를 만든다 (2026-09-21 사용자 요청:
"원래 계획과 실 지출을 비교해 한번 더 확인").

기본 일정은 금요일 17:00 자동 생성 + 트레이 메뉴 수동 실행.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Optional

from common import (
    BANK_REFLECT_OK, MATCH_AMOUNT_DIFF, MATCH_DATE_DIFF, MATCH_MANUAL,
    MATCH_NOT_FOUND, MATCH_PAID, MATCH_PARTIAL, MATCH_UNPLANNED,
    REFLECT_PAID, now_local, save_workbook, week_monday,
)
from excel_report import account_label

_NAVY = "1F4E79"
_DIFF_ORDER = [MATCH_NOT_FOUND, MATCH_UNPLANNED, MATCH_AMOUNT_DIFF,
               MATCH_DATE_DIFF, MATCH_PARTIAL, MATCH_MANUAL]


def _d(value):
    return value.date() if isinstance(value, datetime) else value


def build_reconcile_data(plans: list[dict], bank_rows: list[dict],
                         balances: dict, run_date: date,
                         date_window_days: int = 3,
                         name_threshold: float = 70,
                         aliases: Optional[list[list[str]]] = None,
                         amount_tolerance: float = 0.01) -> dict:
    """이번 주 계획 vs 실제 대조 자료를 만든다.

    기간은 직전 토요일~run_date(금요일 상한): 자금계획이 주말(토·일)
    지급분부터 계획하므로 토요일 시작이라야 계획 파일 기간과 맞는다
    (2026-11-06 사용자 문의: "왜 10/31~11/6 기간과 다른가").
    plans: 통합 지출계획 행(정상반영·지급완료), bank_rows: 표준 은행 행.
    balances: (은행, 계좌)별 현재 잔액. 반환 dict는 write_reconcile_workbook
    입력으로 쓴다.
    """
    import payment_matcher

    monday = week_monday(run_date)
    week_start = monday - timedelta(days=2)                # 직전 토요일부터
    week_end = min(run_date, monday + timedelta(days=4))   # 이번 주 금요일까지

    week_plans = []
    for p in plans:
        pd = _d(p.get("자금계획 반영일") or p.get("지급예정일"))
        if pd is not None and week_start <= pd <= week_end:
            week_plans.append(p)

    matched = payment_matcher.match_payments(
        week_plans, bank_rows, run_date,
        window_days=date_window_days, name_threshold=name_threshold,
        unplanned_days=max(0, (run_date - week_start).days),
        aliases=aliases, amount_tolerance=amount_tolerance)

    diffs = [r for r in matched["results"]
             if r.get("대조결과") != MATCH_PAID]
    diffs += matched["unplanned"]
    diffs.sort(key=lambda r: (_DIFF_ORDER.index(r.get("대조결과"))
                              if r.get("대조결과") in _DIFF_ORDER else 9,
                              _d(r.get("지급예정일")
                                 or r.get("실제출금일")) or date.max))
    ok_rows = [r for r in matched["results"]
               if r.get("대조결과") == MATCH_PAID]
    ok_rows.sort(key=lambda r: _d(r.get("실제출금일")
                                  or r.get("지급예정일")) or date.max)

    # 계좌별: 주간 실제 흐름과 주초(토요일 시작) 잔액 (내부이체 포함 되돌림)
    accounts: dict = {}
    last_bank_date: Optional[date] = None
    for tx in bank_rows:
        if tx.get("반영상태") != BANK_REFLECT_OK:
            continue
        td = _d(tx.get("거래일"))
        if td is not None and (last_bank_date is None or td > last_bank_date):
            last_bank_date = td
        key = (tx.get("은행"), tx.get("계좌") or "")
        acct = accounts.setdefault(key, {
            "입금": 0.0, "출금": 0.0, "내부이체": 0.0, "마지막거래일": None})
        if td is None or td < week_start or td > run_date:
            continue
        amt_in = tx.get("입금액") or 0.0
        amt_out = tx.get("출금액") or 0.0
        if tx.get("내부이체"):
            acct["내부이체"] += amt_in - amt_out
        else:
            acct["입금"] += amt_in
            acct["출금"] += amt_out
        if acct["마지막거래일"] is None or td > acct["마지막거래일"]:
            acct["마지막거래일"] = td

    rows = []
    for key in sorted(set(balances) | set(accounts)):
        acct = accounts.get(key) or {"입금": 0.0, "출금": 0.0,
                                     "내부이체": 0.0, "마지막거래일": None}
        current = float(balances.get(key) or 0.0)
        opening = current - acct["입금"] + acct["출금"] - acct["내부이체"]
        rows.append({
            "계좌": account_label(*key),
            "주초잔액": opening, "입금": acct["입금"], "출금": acct["출금"],
            "내부이체": acct["내부이체"], "현재잔액": current,
            "마지막거래일": acct["마지막거래일"],
        })

    # 은행 파일이 아직 없는 날짜의 미집행은 판정 보류 안내를 덧붙인다
    for rw in diffs:
        if rw.get("대조결과") == MATCH_NOT_FOUND:
            pdd = _d(rw.get("지급예정일"))
            if pdd is not None and (last_bank_date is None
                                    or pdd > last_bank_date):
                rw["비고"] = ((rw.get("비고") or "") +
                            " 은행 내역이 아직 없는 날짜 — 파일 갱신 후 "
                            "재확인").strip()

    plan_out = sum(p.get("예상금액") or 0 for p in week_plans)
    actual_out = sum(a["출금"] for a in rows)
    counts = {k: sum(1 for r in diffs if r.get("대조결과") == k)
              for k in _DIFF_ORDER}
    return {
        "기간": (week_start, week_end), "실행일": run_date,
        "은행기준일": last_bank_date,
        "계좌": rows,
        "계획지출": plan_out, "실제출금": actual_out,
        "일치": len(ok_rows), "완료내역": ok_rows,
        "차이내역": diffs, "차이건수": counts,
    }


def write_reconcile_workbook(data: dict, out_path: Path) -> Path:
    """대조 자료를 주간대조 워크북(안내·대조결과·계좌별대조)으로 저장한다.

    2026-11-06 사용자 요청으로 단순화: '대조결과' 한 시트에서
    ① 나간 돈(완료) ② 안 나간 돈(확인 ▼) ③ 계획에 없는 지출(확인 ▼)
    세 칸만 보면 되게 한다.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    def _head(ws, row, headers, widths):
        for c, (h, w) in enumerate(zip(headers, widths), start=1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.fill = PatternFill("solid", start_color=_NAVY)
            cell.font = Font(name="맑은 고딕", color="FFFFFF", bold=True,
                             size=10)
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[get_column_letter(c)].width = w

    def _put(ws, row, col, value, *, bold=False, size=10, color="000000",
             fmt=None, fill=None):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = Font(name="맑은 고딕", bold=bold, size=size, color=color)
        if fmt:
            cell.number_format = fmt
        if fill:
            cell.fill = PatternFill("solid", start_color=fill)
        return cell

    monday, week_end = data["기간"]
    n_diff = len(data["차이내역"])

    # ── 안내 ────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "안내"
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 90
    _put(ws, 1, 1, f"주간 대조 — 계획 vs 실제 입출금 ({monday} ~ {week_end})",
         bold=True, size=13, color=_NAVY)
    _put(ws, 2, 1, "확인 완료", bold=True)
    _put(ws, 2, 2, "아니오", fill="FFF2CC")
    # '확인 완료'는 드롭다운으로 고른다 (2026-10-11 사용자 요청:
    # 타이핑 대신 선택식 + 셀 선택 시 안내 말풍선)
    from openpyxl.worksheet.datavalidation import DataValidation
    done_dv = DataValidation(type="list", formula1='"아니오,예"',
                             allow_blank=True)
    done_dv.error = "'예' 또는 '아니오'만 입력할 수 있습니다."
    done_dv.showErrorMessage = True
    done_dv.promptTitle = "검토 완료 표시"
    done_dv.prompt = ("'대조결과' 시트 검토가 끝나면 ▼에서 '예'를 골라 "
                      "저장하세요. 검토 완료로 기록됩니다.")
    done_dv.showInputMessage = True
    ws.add_data_validation(done_dv)
    done_dv.add("B2")
    msg = (f"'대조결과' 시트만 보면 됩니다 — 확인할 것 {n_diff}건: "
           "초록(나간 돈)은 그냥 훑어보고, 주황(안 나간 돈)과 "
           "붉은(계획에 없는 지출)만 ▼에서 골라 표시한 뒤 "
           "위 B2를 '예'로 바꿔 저장하세요."
           if n_diff else
           "이번 주 계획과 실제 입출금이 모두 일치합니다. "
           "B2를 '예'로 바꿔 저장하면 검토 완료로 기록됩니다.")
    _put(ws, 3, 1, msg, color="C00000" if n_diff else "2E7D32")
    last = data.get("은행기준일")
    if last is None or last < data["실행일"]:
        _put(ws, 4, 1,
             f"⚠ 은행 파일이 {last or '없음'}까지만 있어 오늘 거래가 빠져 "
             "있을 수 있습니다 — 은행 3사 파일을 새로 받아 넣고 "
             "'주간 대조 확인'을 다시 실행하면 정확해집니다.",
             color="C00000")

    # ── 대조결과 (2026-11-06 사용자 요청: 직관적인 3칸 체크 화면) ──
    ws = wb.create_sheet("대조결과")
    for col, w in (("A", 12), ("B", 10), ("C", 42), ("D", 14), ("E", 22),
                   ("F", 36)):
        ws.column_dimensions[col].width = w
    diffs = data["차이내역"]
    paid = list(data.get("완료내역") or [])
    paid += [r for r in diffs if r.get("대조결과") in
             (MATCH_AMOUNT_DIFF, MATCH_DATE_DIFF, MATCH_PARTIAL)]
    paid.sort(key=lambda r: _d(r.get("실제출금일")
                               or r.get("지급예정일")) or date.max)
    unpaid = [r for r in diffs if r.get("대조결과") in
              (MATCH_NOT_FOUND, MATCH_MANUAL)]
    unplanned = [r for r in diffs
                 if r.get("대조결과") == MATCH_UNPLANNED]

    _put(ws, 1, 1, f"이번 주 돈 흐름 확인 ({monday} ~ {week_end})",
         bold=True, size=13, color=_NAVY)
    _put(ws, 2, 1, "초록 = 계획대로 나감(훑어보기만) · 주황 = 안 나감(▼ 선택) · "
                   "붉은 = 계획에 없던 지출(▼ 선택) — 끝나면 '안내' 시트 "
                   "B2를 '예'로 저장")

    def _amt(row, *keys):
        for k in keys:
            v = row.get(k)
            if v is not None:
                return v
        return 0

    def _section(r, mark, title, rows, total, fill):
        _put(ws, r, 1, f"{mark} {title} — {len(rows)}건 · 합계 "
                       f"{round(total):,}원", bold=True, size=11, fill=fill)
        return r + 1

    # ① 계획대로 나간 돈 (금액·지급일 차이, 일부지급 포함 — 비고로 표시)
    r = _section(4, "①", "계획대로 나간 돈",
                 paid, sum(_amt(x, "실제금액", "예정금액") for x in paid),
                 "C6EFCE")
    _head(ws, r, ["나간 날짜", "팀", "내용", "금액", "확인", "비고"],
          [12, 10, 42, 14, 22, 36])
    r += 1
    if not paid:
        _put(ws, r, 1, "이번 주에 나간 계획 지출이 없습니다.")
        r += 1
    for row in paid:
        kind = row.get("대조결과")
        d = _d(row.get("실제출금일") or row.get("지급예정일"))
        if d is not None:
            _put(ws, r, 1, datetime.combine(d, dtime()), fmt="yyyy-mm-dd")
        _put(ws, r, 2, row.get("팀명") or "")
        _put(ws, r, 3, row.get("거래처") or "")
        _put(ws, r, 4, round(_amt(row, "실제금액", "예정금액")), fmt="#,##0")
        note = row.get("비고") or ""
        if kind == MATCH_PARTIAL:
            rest = (row.get("예정금액") or 0) - (row.get("실제금액") or 0)
            note = (f"일부만 나감 — 남은 {round(rest):,}원은 다음 주 "
                    f"이월 검토. {note}").strip()
        elif kind == MATCH_AMOUNT_DIFF:
            note = (f"계획 {round(row.get('예정금액') or 0):,}원과 "
                    f"금액이 다름. {note}").strip()
        elif kind == MATCH_DATE_DIFF:
            pdd = _d(row.get("지급예정일"))
            note = (f"예정일({pdd})과 다른 날 나감. {note}").strip()
        if note:
            _put(ws, r, 6, note, fill="FFF2CC")
        r += 1
    r += 1

    # ② 계획했는데 안 나간 돈 — 확인 드롭다운
    from openpyxl.worksheet.datavalidation import DataValidation
    r = _section(r, "②", "계획했는데 안 나간 돈",
                 unpaid, sum(_amt(x, "예정금액") for x in unpaid), "FFE699")
    _head(ws, r, ["예정 날짜", "팀", "내용", "금액", "확인 (▼ 선택)", "비고"],
          [12, 10, 42, 14, 22, 36])
    r += 1
    if not unpaid:
        _put(ws, r, 1, "계획한 돈이 모두 나갔습니다.")
        r += 1
    else:
        unpaid_dv = DataValidation(
            type="list",
            formula1='"다음 주 지급(이월),취소됨(안 나감),이미 지급됨(통장 확인)"',
            allow_blank=True)
        unpaid_dv.showErrorMessage = False
        unpaid_dv.promptTitle = "안 나간 돈 확인"
        unpaid_dv.prompt = ("왜 안 나갔는지 ▼에서 골라 주세요. "
                            "'다음 주 지급'이면 취합 지출계획에 이월해 "
                            "반영하세요. 모르면 비워 둬도 됩니다.")
        unpaid_dv.showInputMessage = True
        ws.add_data_validation(unpaid_dv)
        for row in unpaid:
            d = _d(row.get("지급예정일"))
            if d is not None:
                _put(ws, r, 1, datetime.combine(d, dtime()),
                     fmt="yyyy-mm-dd")
            _put(ws, r, 2, row.get("팀명") or "")
            _put(ws, r, 3, row.get("거래처") or "")
            _put(ws, r, 4, round(_amt(row, "예정금액")), fmt="#,##0")
            _put(ws, r, 5, "", fill="FFE699")
            unpaid_dv.add(f"E{r}")
            _put(ws, r, 6, row.get("비고") or "")
            r += 1
    r += 1

    # ③ 계획에 없는 지출 — 확인 드롭다운
    r = _section(r, "③", "계획에 없는 지출",
                 unplanned, sum(_amt(x, "실제금액") for x in unplanned),
                 "FFC7CE")
    _head(ws, r, ["나간 날짜", "은행", "내용", "금액", "확인 (▼ 선택)", "비고"],
          [12, 10, 42, 14, 22, 36])
    r += 1
    if not unplanned:
        _put(ws, r, 1, "계획에 없는 지출이 없습니다.")
        r += 1
    else:
        unpl_dv = DataValidation(
            type="list",
            formula1='"아는 지출(문제 없음),모르는 지출(알아보기)"',
            allow_blank=True)
        unpl_dv.showErrorMessage = False
        unpl_dv.promptTitle = "계획에 없는 지출 확인"
        unpl_dv.prompt = ("아는 지출인지 ▼에서 골라 주세요. 분류는 월요일 "
                          "확인필요 파일의 '처리' 칸에서 고르면 다음부터 "
                          "자동 인식됩니다.")
        unpl_dv.showInputMessage = True
        ws.add_data_validation(unpl_dv)
        for row in unplanned:
            d = _d(row.get("실제출금일"))
            if d is not None:
                _put(ws, r, 1, datetime.combine(d, dtime()),
                     fmt="yyyy-mm-dd")
            _put(ws, r, 2, row.get("은행") or "")
            _put(ws, r, 3, row.get("거래처") or "")
            _put(ws, r, 4, round(_amt(row, "실제금액")), fmt="#,##0")
            _put(ws, r, 5, "", fill="FFC7CE")
            unpl_dv.add(f"E{r}")
            note = row.get("비고") or ""
            if note.endswith((".xlsx", ".xls")):   # 원본 파일명은 노이즈
                note = ""
            _put(ws, r, 6, note)
            r += 1
    ws.freeze_panes = "A3"

    # ── 계좌별대조 ──────────────────────────────────────────────────
    ws = wb.create_sheet("계좌별대조")
    _put(ws, 1, 1, f"계좌별 입출금 대조 ({monday} ~ {week_end})",
         bold=True, size=12, color=_NAVY)
    _head(ws, 3, ["계좌", "주초 잔액", "이번 주 입금", "이번 주 출금",
                  "내부이체(순)", "현재 잔액", "마지막 거래일"],
          [26, 15, 15, 15, 14, 15, 13])
    r = 4
    for a in data["계좌"]:
        _put(ws, r, 1, a["계좌"])
        for c, k in ((2, "주초잔액"), (3, "입금"), (4, "출금"),
                     (5, "내부이체"), (6, "현재잔액")):
            _put(ws, r, c, round(a[k]), fmt="#,##0;[Red]-#,##0")
        d = a["마지막거래일"]
        if d is not None:
            _put(ws, r, 7, datetime.combine(d, dtime()),
                 fmt="yyyy-mm-dd")
        r += 1
    _put(ws, r, 1, "합계", bold=True)
    for c, k in ((2, "주초잔액"), (3, "입금"), (4, "출금"),
                 (5, "내부이체"), (6, "현재잔액")):
        _put(ws, r, c, round(sum(a[k] for a in data["계좌"])),
             bold=True, fmt="#,##0;[Red]-#,##0")
    r += 2
    _put(ws, r, 1, "계획 대비 요약", bold=True, color=_NAVY)
    _put(ws, r + 1, 1, "이번 주 계획 지출")
    _put(ws, r + 1, 2, round(data["계획지출"]), fmt="#,##0")
    _put(ws, r + 2, 1, "실제 외부 출금")
    _put(ws, r + 2, 2, round(data["실제출금"]), fmt="#,##0")
    _put(ws, r + 3, 1, "차이 (계획-실제)", bold=True)
    _put(ws, r + 3, 2, round(data["계획지출"] - data["실제출금"]),
         bold=True, fmt="#,##0;[Red]-#,##0")
    _put(ws, r + 4, 1, "대조 결과")
    cnt = data["차이건수"]
    _put(ws, r + 4, 2,
         f"일치 {data['일치']}건 · 미집행 {cnt.get(MATCH_NOT_FOUND, 0)}건 · "
         f"계획없는출금 {cnt.get(MATCH_UNPLANNED, 0)}건 · 금액·기타 차이 "
         f"{n_diff - cnt.get(MATCH_NOT_FOUND, 0) - cnt.get(MATCH_UNPLANNED, 0)}건")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_workbook(wb, out_path)
    wb.close()
    return out_path


def run_weekly_reconcile(cfg, log, now=None, open_file: bool = True) -> Path:
    """입력을 읽어 주간대조 파일을 만들고 (기본) 자동으로 연다."""
    import bank_classifier
    import bank_loader
    import duplicate_checker
    import forecast_engine
    import team_loader
    from card_payment import CardPaymentCalculator

    now = now or now_local(cfg.timezone_name)
    run_date = now.date()

    card_calc = CardPaymentCalculator.from_workbook(cfg.base_workbook_path())
    team_data = team_loader.load_all_teams(cfg)
    plan = team_loader.build_integrated_plan(
        team_data["rows"], card_calc.settlement_date,
        include_unconfirmed=cfg.get("forecast", "include_unconfirmed",
                                    default=True))
    forecast_engine.split_apalm_marked(plan)   # 에이팜 별도관리 건 제외

    bank_data = bank_loader.load_all_banks(cfg)
    kept, _dups = duplicate_checker.remove_duplicates(bank_data["rows"])
    rules = bank_classifier.load_rules(
        cfg.state_dir / cfg.get("bank", "classify_rules_file",
                                default="classify_rules.json"))
    bank_classifier.classify_rows(kept, rules)
    balances, _total = bank_loader.summarize_balances(kept)

    match_targets = plan["countable"] + [
        r for r in plan["integrated"] if r.get("반영상태") == REFLECT_PAID]
    data = build_reconcile_data(
        match_targets, kept, balances, run_date,
        date_window_days=cfg.get("matching", "date_window_days", default=3),
        name_threshold=cfg.get("matching", "name_similarity_threshold",
                               default=70),
        aliases=rules.get("매칭별칭"),
        amount_tolerance=cfg.get("matching", "amount_tolerance",
                                 default=0.01))

    out = cfg.folder("review") / f"주간대조_{now:%Y%m%d_%H%M}.xlsx"
    write_reconcile_workbook(data, out)
    log.info("주간 대조(%s~%s): 일치 %d건, 차이 %d건 — %s",
             data["기간"][0], data["기간"][1], data["일치"],
             len(data["차이내역"]), out.name)
    if open_file:
        from app import _open_file
        _open_file(out)
    return out
