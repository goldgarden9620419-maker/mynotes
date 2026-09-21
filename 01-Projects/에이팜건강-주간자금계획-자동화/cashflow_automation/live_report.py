# -*- coding: utf-8 -*-
"""라이브 자금계획 워크북 채우기.

사용자의 기존 자금계획 워크북(수식 내장형)을 템플릿으로 삼아
값만 갱신한 결과물을 만든다. 반영률 셀(요약!B13)에 걸린 수식은
전부 보존되므로, 엑셀에서 반영률을 바꾸면 즉시 재계산된다.

템플릿 위치: 04_기준파일/자금계획_라이브템플릿.xlsx
매주 갱신되는 것:
  - 4주일별계획 A열 날짜를 새 주차(월요일~+27일)로 재고정
  - 13주주별계획 1~4주차 SUMIFS 수식의 날짜 리터럴 재작성, 기간 텍스트
  - 요약 통계·계좌 잔액, 설정및분류 요일평균, 정기지출, RAW 전체 교체
  - 4주 D~G(확정입금·송금·카드·기타지출)와 13주 5~13주차 D~G 값
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

from common import WEEKDAY_KO
from excel_report import account_label


def _set(ws, row: int, col: int, value):
    """병합 셀은 건너뛰는 안전 쓰기. 성공한 셀을 돌려준다."""
    cell = ws.cell(row=row, column=col)
    if isinstance(cell, MergedCell):
        return None
    cell.value = value
    return cell

LIVE_TEMPLATE_NAME = "자금계획_라이브템플릿.xlsx"
EXPENSE_SHEET = "지출계획_취합"

_EXPENSE_COLUMNS = [
    ("요청ID", "요청ID", 18), ("팀명", "팀명", 12), ("신청자", "신청자", 9),
    ("품의승인", "품의승인", 10), ("지급예정일", "지급예정일", 12),
    ("자금계획 반영일", "자금계획 반영일", 13), ("거래처", "거래처", 16),
    ("지출내용", "지출내용", 24), ("예상금액", "예상금액", 13),
    ("지급방법", "지급방법", 10), ("카드구분", "카드구분", 10),
    ("확정여부", "확정여부", 9), ("진행상태", "진행상태", 9),
    ("최종수정일", "최종수정일", 12), ("원본파일", "원본파일", 24),
    ("반영상태", "반영상태", 12), ("확인사항", "확인사항", 28),
]

_CONF_LABEL = {"상": "높음", "중": "중간", "하": "낮음"}
_MONEY_WON = '#,##0"원"'

# 13주 1~4주차 SUMIFS: 일별계획의 해당 열을 주 단위로 합산
# (6행 전일 마감·7행 오늘 실잔고 출발 행 다음의 계획 행 8~35 기준)
_SUMIFS = ("=SUMIFS('4주일별계획'!${col}$8:${col}$35,"
           "'4주일별계획'!$A$8:$A$35,\">=\"&DATE({y1},{m1},{d1}),"
           "'4주일별계획'!$A$8:$A$35,\"<=\"&DATE({y2},{m2},{d2}))")


class LiveTemplateError(RuntimeError):
    pass


def fill_live_workbook(template_path: Path, report: dict,
                       out_path: Path) -> Path:
    """템플릿의 수식·서식을 유지한 채 최신 값으로 채워 저장한다."""
    template_path = Path(template_path)
    if not template_path.exists():
        raise LiveTemplateError(f"라이브 템플릿이 없습니다: {template_path}")
    wb = load_workbook(template_path)
    # 정기지출분석은 별도 검토 파일로 옮겨져 템플릿에 없어도 된다
    required = {"요약", "4주일별계획", "13주주별계획",
                "계좌내역통합_RAW", "설정및분류"}
    missing = required - set(wb.sheetnames)
    if missing:
        wb.close()
        raise LiveTemplateError(f"템플릿에 시트가 없습니다: {missing}")

    meta = report["meta"]
    forecast = report["forecast"]
    base_date: date = meta["base_date"]
    stats = report.get("history_stats", {})

    holidays = report.get("holidays") or {}
    scen = report.get("account_scenario") or {}
    n_acc = len(scen.get("accounts") or [])
    _fill_config(wb["설정및분류"], forecast)
    _fill_summary(wb["요약"], report, base_date, stats, n_acc)
    _fill_daily(wb, forecast, base_date,
                meta.get("run_date"), holidays=holidays,
                scenario=scen, balances=report.get("balances"),
                last_dates=report.get("account_last_dates"))
    _fill_weekly(wb["13주주별계획"], forecast, base_date, n_acc)
    _fill_account_scenario(wb, report.get("account_scenario"),
                           holidays=holidays,
                           run_date=meta.get("run_date"))
    _fill_expense(wb, report.get("integrated_masked", []), holidays=holidays,
                  run_date=meta.get("run_date"))
    _fill_apalm_expense(wb, report.get("apalm_expenses", []),
                        holidays=holidays)
    _fill_raw(wb["계좌내역통합_RAW"], report.get("bank_rows", []),
              holidays=holidays)

    # 은행 파일을 폴더에서 자동으로 읽으므로 수동 붙여넣기 시트는 제거한다
    if "주간계좌_붙여넣기" in wb.sheetnames:
        wb.remove(wb["주간계좌_붙여넣기"])

    # 분류·성격 검토는 확인 단계의 별도 정기지출분석 파일에서만 한다
    # (2026-09-20 사용자 요청) — 라이브에는 시트를 담지 않는다
    if "정기지출분석" in wb.sheetnames:
        wb.remove(wb["정기지출분석"])

    # 13주 주별계획은 매주 확인할 필요가 없어 숨긴다 (2026-09-20 사용자
    # 요청). 자료·수식은 그대로라 필요하면 시트 숨기기 해제로 볼 수 있다
    wb["13주주별계획"].sheet_state = "hidden"

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


def verify_live_workbook(path: Path, base_date: date) -> bool:
    """수식 보존과 날짜 재고정을 재열기로 검증한다."""
    try:
        wb = load_workbook(path)
    except Exception:
        return False
    try:
        daily = wb["4주일별계획"]
        # 온라인 예상입금 열은 계좌 열 수에 따라 위치가 다르다
        online_col = 3
        for c in range(1, 30):
            if str(daily.cell(row=5, column=c).value or "").strip() \
                    == "온라인 예상입금":
                online_col = c
                break
        # 실적으로 채워진 지난 날짜는 값이므로, 미래 행 중 하나라도
        # 반영률 수식(INDEX×$B$13)이 살아 있으면 수식 보존으로 본다
        formula_ok = any(
            "INDEX" in str(daily.cell(row=r, column=online_col).value or "")
            and "$B$13" in str(daily.cell(row=r,
                                          column=online_col).value or "")
            for r in range(8, 36))
        a6 = daily["A8"].value       # 6~7행은 전일·오늘 실잔고 출발 행
        a6_date = a6.date() if isinstance(a6, datetime) else a6
        weekly = wb["13주주별계획"]
        c6w = str(weekly["C6"].value or "")
        summary = wb["요약"]
        return (formula_ok
                and a6_date == base_date
                and f"DATE({base_date.year},{base_date.month},{base_date.day})"
                in c6w
                and "SUMIFS" in c6w
                and str(summary["B14"].value or "").startswith("="))
    except Exception:
        return False
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# 시트별 채우기
# ---------------------------------------------------------------------------

def _fill_config(ws, forecast: dict) -> None:
    weekday_avg = forecast.get("weekday_avg", {})
    for i in range(7):
        _set(ws, 6 + i, 3, round(weekday_avg.get(i, 0)))


def _fill_summary(ws, report: dict, base_date: date, stats: dict,
                  n_acc: int = 0) -> None:
    from openpyxl.utils import get_column_letter as col_l
    ws["A3"] = (f"기준일 {base_date} | 농협·우리은행·국민은행 계좌 "
                "거래내역 통합 (자동 갱신)")
    ws["B6"] = round(report.get("total_balance") or 0)
    # 4주 기말·최저 잔액 수식을 일별계획의 기말잔액 열 위치로 재작성
    # (계좌 열 수에 따라 열이 이동한다)
    close = col_l(daily_layout(n_acc)["close"])
    ws["B14"] = f"='4주일별계획'!{close}35"
    ws["B15"] = f"=MIN('4주일별계획'!{close}8:{close}35)"
    if stats.get("외부입금") is not None:
        ws["B7"] = round(stats["외부입금"])
        ws["B8"] = round(stats.get("외부출금") or 0)
        ws["B9"] = round(stats.get("온라인입금") or 0)
        ws["B10"] = round(stats.get("주평균온라인") or 0)
    last_dates = report.get("account_last_dates", {})
    labels = report.get("account_labels", {})
    balances = sorted(report.get("balances", {}).items())
    for i in range(max(len(balances), 6)):  # 계좌 수 변동 대비 여유분 정리
        r = 6 + i
        if i < len(balances):
            key, amount = balances[i]
            _set(ws, r, 4, labels.get(key) or account_label(*key))
            last = last_dates.get(key)
            dcell = _set(ws, r, 5,
                         datetime.combine(last, dtime()) if last else None)
            if dcell is not None:
                dcell.number_format = "yyyy-mm-dd"
            fcell = _set(ws, r, 6, round(amount))
            if fcell is not None:
                fcell.number_format = _MONEY_WON
        else:
            for c in (4, 5, 6):
                _set(ws, r, c, None)


ETC_HEADER = "조정·추정 지출"   # 자동이체 + 주간조정·자동추정·확인지시 합


DAILY_SHEET = "4주일별계획"
_DAILY_ONLINE = ("=INDEX('설정및분류'!$C$6:$C$12,WEEKDAY(A{r},2))"
                 "*'요약'!$B$13")


def daily_layout(n: int) -> dict:
    """4주일별계획 열 배치 (2026-09-21 사용자 지정 순서).

    일자·요일 | 계좌별 예상잔고 | 온라인 예상입금 | 계좌별 입금 배분 |
    확정·기타입금 | 송금예정 | 카드결제 | 조정·추정 지출 | 순현금흐름 |
    기초잔액 | 기말잔액 | 비고. 계좌가 없으면(n=0) 예전 배치와 같다.
    """
    return {
        "bal": list(range(3, 3 + n)),
        "online": 3 + n,
        "alloc": list(range(4 + n, 4 + 2 * n)),
        "conf": 4 + 2 * n, "transfer": 5 + 2 * n, "card": 6 + 2 * n,
        "etc": 7 + 2 * n, "net": 8 + 2 * n, "open": 9 + 2 * n,
        "close": 10 + 2 * n, "note": 11 + 2 * n,
    }


def _fill_daily(wb, forecast: dict, base_date: date,
                run_date: Optional[date] = None,
                holidays: Optional[dict] = None,
                scenario: Optional[dict] = None,
                balances: Optional[dict] = None,
                last_dates: Optional[dict] = None) -> None:
    """4주일별계획 시트를 처음부터 다시 그린다 (자동 생성).

    계좌별 예상잔고·입금 배분 열은 계좌별시나리오(행 1:1) 셀을 참조하는
    수식이라 반영률(요약 B13)과 함께 즉시 재계산된다. 실잔고(은행에서
    확인된 계좌별 최근 잔고)는 상단 안내 줄에 표시한다 — 예상잔고는
    실잔고에 예상입금·지출·이체를 반영한 값이며, 당일 이미 입금·출금된
    실적은 중복 계산하지 않는다 (2026-09-21 사용자 요청 배치).
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as col_l

    holidays = holidays or {}
    balances = balances or {}
    last_dates = last_dates or {}
    accounts = (scenario or {}).get("accounts") or []
    opening_map = (scenario or {}).get("opening") or {}
    n = len(accounts)
    lay = daily_layout(n)
    note_col = lay["note"]
    daily_by_date = {r["일자"]: r for r in forecast.get("daily", [])}

    index = wb.sheetnames.index(DAILY_SHEET)
    wb.remove(wb[DAILY_SHEET])
    ws = wb.create_sheet(DAILY_SHEET, index)

    navy, green, gray = "1F4E79", "548235", "808080"
    money = '#,##0"원"'
    num_bal = "#,##0;[Red]-#,##0"
    num_flow = "#,##0;[Red]-#,##0;"          # 0은 빈칸으로
    bal_fill = PatternFill("solid", start_color="D9E2F1")
    alloc_fill = PatternFill("solid", start_color="E2EFDA")
    edit_fill = PatternFill("solid", start_color="FFF2CC")
    calc_fill = PatternFill("solid", start_color="EBF1DE")
    online_fill = PatternFill("solid", start_color="F2F2F2")
    thin = Side(style="thin", color="D9D9D9")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    white_bold = dict(name="맑은 고딕", bold=True, size=9, color="FFFFFF")

    title = _set(ws, 2, 1, "향후 4주 일별 자금계획")
    if title is not None:
        title.font = Font(name="맑은 고딕", bold=True, size=13, color=navy)
    note_txt = ("온라인 예상입금은 최근 12주 요일별 평균 × 입금 반영률"
                "(요약 B13)로 계산됩니다. 노란색 칸만 입력하세요.")
    if accounts:
        def _real(k):
            v = balances.get(k)
            if v is None:
                v = opening_map.get(k)
            return round(float(v or 0))
        real_txt = " · ".join(
            f"{account_label(b, a)} {_real((b, a)):,}"
            + (f"({last_dates[(b, a)]:%m-%d})"
               if last_dates.get((b, a)) else "")
            for b, a in accounts)
        note_txt += (f"  |  실잔고(은행 최근 확인): {real_txt} — 계획은 6행 "
                     "전일 마감 실잔고에서 출발해 지출예정(취합)·확정입금·"
                     "온라인 예상입금만 반영합니다. 7행은 오늘 실잔고와 오늘 "
                     "실제 입금·출금(참고)이며, 당일 실제 순증감은 출발 "
                     "잔액 계산에서 이미 상쇄되어 이중계산되지 않습니다")
    a3 = _set(ws, 3, 1, note_txt)
    if a3 is not None:
        a3.font = Font(name="맑은 고딕", size=9, color=gray)

    # 4행 그룹 띠 + 5행 머리글
    def _band(c1, c2, text, color):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=4, column=c)
            cell.fill = PatternFill("solid", start_color=color)
            cell.border = box
        head = _set(ws, 4, c1, text)
        if head is not None:
            head.font = Font(**white_bold)
            head.alignment = Alignment(horizontal="left",
                                       vertical="center")
        if c2 > c1:
            ws.merge_cells(start_row=4, start_column=c1,
                           end_row=4, end_column=c2)

    if accounts:
        _band(lay["bal"][0], lay["bal"][-1], "계좌별 예상잔고", navy)
        _band(lay["alloc"][0], lay["alloc"][-1],
              "계좌별 입금 배분(예상)", green)

    heads = [(1, "일자", navy, 11), (2, "요일", navy, 5)]
    heads += [(c, account_label(b, a), navy, 13)
              for c, (b, a) in zip(lay["bal"], accounts)]
    heads += [(lay["online"], "온라인 예상입금", navy, 14)]
    heads += [(c, account_label(b, a), green, 13)
              for c, (b, a) in zip(lay["alloc"], accounts)]
    heads += [(lay["conf"], "확정·기타입금", navy, 13),
              (lay["transfer"], "송금예정", navy, 13),
              (lay["card"], "카드결제", navy, 12),
              (lay["etc"], ETC_HEADER, navy, 13),
              (lay["net"], "순현금흐름", navy, 13),
              (lay["open"], "기초잔액", navy, 14),
              (lay["close"], "기말잔액", navy, 14),
              (note_col, "비고", navy, 34)]
    for c, text, color, width in heads:
        cell = _set(ws, 5, c, text)
        if cell is not None:
            cell.font = Font(**white_bold)
            cell.alignment = Alignment(horizontal="center",
                                       vertical="center")
            cell.fill = PatternFill("solid", start_color=color)
            cell.border = box
        ws.column_dimensions[col_l(c)].width = width
    # 계좌 열 2개 그룹은 개요(+/-)로 접었다 펼 수 있다. group() 호출은
    # 너비 설정과 겹치면 한 열만 남는 문제가 있어 열별로 직접 지정한다
    for c in lay["bal"] + lay["alloc"]:
        ws.column_dimensions[col_l(c)].outline_level = 1
        ws.column_dimensions[col_l(c)].hidden = False
    if accounts:
        ws.sheet_format.outlineLevelCol = 1

    # 실적 구간이 있으면 시작잔액을 '기준일 시작' 잔액 값으로 고정한다
    # (현재잔액에는 이미 이번 주 실적이 반영돼 있어 이중계산 방지).
    # 실행일 당일 거래만 은행에 찍힌 경우(당일은 실적으로 확정하지 않아
    # actual_until이 비어 있어도 시작잔액≠현재잔액)도 같은 이유로 고정한다
    start = forecast.get("start_balance")
    opening = forecast.get("opening_balance")
    fix_start = start is not None and (
        forecast.get("actual_until") is not None
        or (opening is not None and round(start) != round(opening)))

    def _put(row, c, value, fmt=None, fill=None, font=None):
        cell = _set(ws, row, c, value)
        if cell is not None:
            if fmt:
                cell.number_format = fmt
            if fill is not None:
                cell.fill = fill
            cell.font = font or Font(name="맑은 고딕", size=10)
            cell.border = box
        return cell

    red_font = Font(name="맑은 고딕", size=10, color="C00000")
    bold_font = Font(name="맑은 고딕", size=10, bold=True)
    start_fill = PatternFill("solid", start_color="EDEDED")

    # 출발 행 2개 (2026-09-21 사용자 요청):
    #  6행 = 전일 마감 계좌별 실잔고 — 계획은 여기서 출발
    #  7행 = 오늘 은행 확인 계좌별 실잔고 + 오늘 실제 입금·출금 (참고
    #        표시 — 당일 실제 순증감은 출발 잔액 계산에서 이미 상쇄됨)
    today_actual = forecast.get("today_actual") or {}
    today_d = run_date or base_date
    prev_d = today_d - timedelta(days=1)
    gray_font = Font(name="맑은 고딕", size=10, color="808080")
    for rr in (6, 7):
        for c in range(1, note_col + 1):
            cell = ws.cell(row=rr, column=c)
            if not isinstance(cell, MergedCell):
                cell.fill = start_fill
                cell.border = box
    # 6행: 전일 마감 실잔고 (계획 출발점)
    _put(6, 1, datetime.combine(prev_d, dtime()), fmt="yyyy-mm-dd",
         fill=start_fill, font=bold_font)
    _put(6, 2, WEEKDAY_KO[prev_d.weekday()], fill=start_fill,
         font=bold_font)
    for idx, c in enumerate(lay["bal"]):
        _put(6, c, f"='{ACCOUNT_SCENARIO_SHEET}'!{col_l(4 + idx)}6",
             fmt=num_bal, fill=bal_fill, font=bold_font)
    _put(6, lay["close"],
         (f"='{ACCOUNT_SCENARIO_SHEET}'!{col_l(3)}6" if accounts
          else (round(start) if fix_start else "='요약'!$B$6")),
         fmt="#,##0", fill=start_fill, font=bold_font)
    _put(6, note_col, "전일 마감 실잔고 — 여기서 계획 시작",
         fill=start_fill, font=bold_font)
    # 7행: 오늘 실잔고 + 오늘 실제 입금·출금 (참고)
    _put(7, 1, datetime.combine(today_d, dtime()), fmt="yyyy-mm-dd",
         fill=start_fill, font=gray_font)
    _put(7, 2, WEEKDAY_KO[today_d.weekday()], fill=start_fill,
         font=gray_font)
    for idx, c in enumerate(lay["bal"]):
        _put(7, c, f"='{ACCOUNT_SCENARIO_SHEET}'!{col_l(4 + idx)}7",
             fmt=num_bal, fill=bal_fill, font=gray_font)
    if accounts:
        _put(7, lay["close"], "='요약'!$B$6", fmt="#,##0",
             fill=start_fill, font=gray_font)
    if today_actual:
        for c, v in ((lay["online"], today_actual.get("온라인")),
                     (lay["conf"], today_actual.get("기타입금")),
                     (lay["etc"], today_actual.get("출금")),
                     (lay["net"], today_actual.get("순증감"))):
            _put(7, c, round(v) if v else None, fmt=num_flow,
                 fill=start_fill, font=gray_font)
    _put(7, note_col,
         "오늘 실잔고(은행 확인)·실제 입금·출금 — 참고 (이중계산 안 됨)",
         fill=start_fill, font=gray_font)

    for i in range(28):
        row = 8 + i
        d = base_date + timedelta(days=i)
        off = d.weekday() >= 5 or d in holidays
        acell = _put(row, 1, datetime.combine(d, dtime()),
                     fmt="yyyy-mm-dd", font=red_font if off else None)
        _put(row, 2, WEEKDAY_KO[d.weekday()],
             font=red_font if off else None)
        src = daily_by_date.get(d)
        # 계좌별 예상잔고·입금 배분 — 계좌별시나리오 참조 (행 1:1)
        for idx, c in enumerate(lay["bal"]):
            _put(row, c, f"='{ACCOUNT_SCENARIO_SHEET}'!"
                         f"{col_l(4 + idx)}{row}",
                 fmt=num_bal, fill=bal_fill)
        for idx, c in enumerate(lay["alloc"]):
            _put(row, c, f"='{ACCOUNT_SCENARIO_SHEET}'!"
                         f"{col_l(5 + n + idx)}{row}",
                 fmt=num_flow, fill=alloc_fill)
        # 온라인 예상입금: 지난 실적일·공휴일은 값, 그 밖엔 반영률 수식
        if src and src.get("실적"):
            _put(row, lay["online"],
                 round(src.get("온라인 예상입금") or 0),
                 fmt="#,##0", fill=online_fill)
        elif d in holidays:
            _put(row, lay["online"], 0, fmt="#,##0", fill=online_fill)
        else:
            _put(row, lay["online"], _DAILY_ONLINE.format(r=row),
                 fmt=money, fill=online_fill)
        vals = [None, None, None, None]
        if src:
            etc = (src.get("자동이체") or 0) + (src.get("기타지출") or 0)
            vals = [src.get("확정·기타입금") or None,
                    src.get("팀별 송금예정") or None,
                    src.get("카드결제") or None,
                    etc or None]
        for key, v in zip(("conf", "transfer", "card", "etc"), vals):
            _put(row, lay[key], round(v) if v else None,
                 fmt=money, fill=edit_fill)
        ol, cl = col_l(lay["online"]), col_l(lay["conf"])
        el, fl, gl = (col_l(lay["transfer"]), col_l(lay["card"]),
                      col_l(lay["etc"]))
        _put(row, lay["net"],
             f"={ol}{row}+{cl}{row}-{el}{row}-{fl}{row}-{gl}{row}",
             fmt=money, fill=calc_fill)
        # 기초잔액은 앞 행의 기말을 잇는다. 첫 계획 행은 6행(전일 마감
        # 실잔고)에서 출발한다 — 7행(오늘 실잔고)은 참고 표시일 뿐
        # 체인에 넣지 않는다 (당일 실제가 이중계산되지 않게).
        # 기준일<실행일이면 첫 행은 숨김 실적 체인의 시작잔액 값
        if row == 8 and run_date is not None and run_date > base_date:
            _put(row, lay["open"], round(start or 0), fmt="#,##0",
                 fill=calc_fill)
        elif row == 8:
            _put(row, lay["open"], f"={col_l(lay['close'])}6",
                 fmt="#,##0", fill=calc_fill)
        else:
            _put(row, lay["open"], f"={col_l(lay['close'])}{row - 1}",
                 fmt="#,##0", fill=calc_fill)
        _put(row, lay["close"],
             f"={col_l(lay['open'])}{row}+{col_l(lay['net'])}{row}",
             fmt=money, fill=calc_fill)
        # 그날 반영된 지출 내역 요약
        ncell = _put(row, note_col, (src or {}).get("비고") or None)
        if ncell is not None:
            ncell.alignment = Alignment(horizontal="left", vertical="top",
                                        wrap_text=True)
            rd = ws.row_dimensions.get(row)
            if rd is not None:
                rd.height = None    # 높이 자동(customHeight 해제)
    ws.freeze_panes = "C8"
    # 은행 내역으로 확인이 끝난 지난 일자(실적 구간)는 행을 숨긴다 —
    # 조회일 이후의 자금계획에 집중 (2026-09-20 사용자 요청).
    # 단, 실행일 행은 당일 실적이 있어도 항상 보인다 (2026-09-21 사용자
    # 요청: 실행일 포함 표시). 자료·수식은 그대로라 필요하면 행 숨기기
    # 해제로 볼 수 있다
    actual_until = forecast.get("actual_until")
    show_from = run_date or actual_until
    for i in range(28):
        d = base_date + timedelta(days=i)
        ws.row_dimensions[8 + i].hidden = bool(
            actual_until is not None and d <= actual_until
            and (show_from is None or d < show_from))
    # 붉은 상자는 그 일자 행 전체(모든 열)를 묶는다 (2026-09-21 사용자 요청)
    _outline_exec_window(ws, note_col, base_date, run_date)


def outline_week_box(ws, first_row: int, last_row: int,
                     first_col: int, last_col: int) -> None:
    """지정 구역을 하나의 붉은 외곽 테두리 상자로 묶는다 (격자 아님)."""
    from copy import copy
    from openpyxl.styles import Side

    red = Side(style="medium", color="C00000")

    def _edge(row, col, **sides):
        cell = ws.cell(row=row, column=col)
        b = copy(cell.border)
        for name in sides:
            setattr(b, name, red)
        cell.border = b

    for c in range(first_col, last_col + 1):
        _edge(first_row, c, top=True)
        _edge(last_row, c, bottom=True)
    for r in range(first_row, last_row + 1):
        _edge(r, first_col, left=True)
        _edge(r, last_col, right=True)


def exec_window(run_date: date) -> tuple[date, date]:
    """붉은 상자 구간: 실행일부터 차주(다음 주) 금요일까지."""
    from common import week_monday
    end = week_monday(run_date) + timedelta(days=7 + 4)
    return run_date, end


def _outline_exec_window(ws, note_col: int, base_date: date,
                         run_date: Optional[date]) -> None:
    """실행일~차주 금요일 구간을 붉은 상자로 표시.

    예: 목요일(9/18) 실행이면 9/18~다음 주 금요일(9/25)을 묶는다.
    예전 버전이 넣어둔 TODAY() 조건부서식(셀별 격자)은 제거한다.
    """
    from copy import copy

    stale = [cf for cf in list(ws.conditional_formatting)
             if any(r.formula and "WEEKDAY(TODAY()" in r.formula[0]
                    for r in cf.rules)]
    for cf in stale:
        try:
            del ws.conditional_formatting._cf_rules[cf]
        except KeyError:
            pass
    last_col = max(note_col, 11)
    # 이전 실행이 남긴 붉은 테두리를 먼저 지운다 (재실행 대비)
    for r in range(8, 36):
        for c in range(1, last_col + 1):
            cell = ws.cell(row=r, column=c)
            b = cell.border
            dirty = False
            for name in ("top", "bottom", "left", "right"):
                s = getattr(b, name, None)
                if s is not None and s.style == "medium" \
                        and s.color is not None \
                        and str(s.color.rgb or "").endswith("C00000"):
                    if not dirty:
                        b = copy(b)
                        dirty = True
                    setattr(b, name, None)
            if dirty:
                cell.border = b
    start, end = exec_window(run_date or base_date)
    first = 8 + max(0, min((start - base_date).days, 27))
    last = 8 + max(0, min((end - base_date).days, 27))
    outline_week_box(ws, first, last, 1, last_col)


def _fill_weekly(ws, forecast: dict, base_date: date,
                 n_acc: int = 0) -> None:
    from openpyxl.utils import get_column_letter as col_l
    weekly = forecast.get("weekly", [])
    if str(ws.cell(row=5, column=7).value or "").strip() in ("기타지출",
                                                             ETC_HEADER):
        _set(ws, 5, 7, ETC_HEADER)
    # 13주 시트의 C~G가 합산할 4주일별계획 열 (계좌 열 수에 따라 이동)
    lay = daily_layout(n_acc)
    src = {"C": col_l(lay["online"]), "D": col_l(lay["conf"]),
           "E": col_l(lay["transfer"]), "F": col_l(lay["card"]),
           "G": col_l(lay["etc"])}
    for w in range(13):
        r = 6 + w
        w_start = base_date + timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        _set(ws, r, 2, f"{w_start} ~ {w_end}")
        if w < 4:
            # 1~4주차: SUMIFS 수식의 날짜 리터럴을 새 주차로 재작성
            for col in ("C", "D", "E", "F", "G"):
                ws[f"{col}{r}"] = _SUMIFS.format(
                    col=src[col], y1=w_start.year, m1=w_start.month,
                    d1=w_start.day, y2=w_end.year, m2=w_end.month,
                    d2=w_end.day)
        else:
            wr = weekly[w] if w < len(weekly) else {}
            etc = (wr.get("자동이체") or 0) + (wr.get("기타지출") or 0)
            for c, v in ((4, wr.get("확정기타입금")), (5, wr.get("송금예정")),
                         (6, wr.get("카드결제")), (7, etc)):
                _set(ws, r, c, round(v) if v else None)


ACCOUNT_SCENARIO_SHEET = "계좌별시나리오"


def _fill_account_scenario(wb, scenario: Optional[dict],
                           holidays: Optional[dict] = None,
                           run_date: Optional[date] = None) -> None:
    """계좌별 일별 잔액 시나리오 시트 (우리→농협→국민 인출 우선순위).

    ① 잔액 → ② 당일 예상입금 배분 → ③ 지출 → ④ 부족분 이체 블록을
    색으로 구분해 '전날 잔액 + ② − ③ − ④ = 오늘 잔액'이 왼쪽부터
    그대로 읽히게 한다. 지난 실적 일자는 숨기고 마지막 실적일(출발
    잔액)만 남긴다. 자동 생성 시트이므로 매번 새로 그린다.

    예측 행은 값이 아니라 수식으로 쓴다: ②·③이 4주일별계획의 입금
    (요약!B13 반영률 수식)·지출 셀을 참조하고, 이체·잔액은 MIN/MAX
    수식으로 연쇄 계산되므로 요약 시트에서 반영률을 바꾸면 이 표도
    즉시 다시 계산된다. 수식 훼손 방지를 위해 시트를 암호 없이
    보호한다(행·열 숨기기 해제는 허용).
    """
    if not scenario or not scenario.get("accounts"):
        return
    from excel_report import is_offday
    from openpyxl.styles import (Alignment, Border, Font, PatternFill,
                                 Side)
    from openpyxl.utils import get_column_letter

    if ACCOUNT_SCENARIO_SHEET in wb.sheetnames:
        index = wb.sheetnames.index(ACCOUNT_SCENARIO_SHEET)
        wb.remove(wb[ACCOUNT_SCENARIO_SHEET])
    else:
        try:
            index = wb.sheetnames.index("4주일별계획") + 1
        except ValueError:
            index = len(wb.sheetnames)
    ws = wb.create_sheet(ACCOUNT_SCENARIO_SHEET, index)

    accounts = scenario["accounts"]
    shares = scenario.get("shares") or {}
    n = len(accounts)
    # 열 배치: 일자·요일 | ① 총잔액+계좌별 잔액 | ② 입금 합계+계좌별
    # 배분 | ③ 지출 | ④ 이체 2열 | 비고
    col_total = 3
    col_in_sum = col_total + 1 + n
    col_out = col_in_sum + 1 + n
    col_tr = col_out + 1
    col_note = col_tr + 2

    navy, green = "1F4E79", "548235"
    orange, d_orange, gray = "ED7D31", "C55A11", "808080"
    thin = Side(style="thin", color="D9D9D9")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    white_bold = dict(name="맑은 고딕", bold=True, size=9, color="FFFFFF")

    share_txt = " · ".join(f"{account_label(b, a)} "
                           f"{shares.get((b, a), 0):.0%}"
                           for b, a in accounts) if shares else ""
    title = _set(ws, 2, 1, "계좌별 일별 잔액 시나리오 (자동 반영)")
    if title is not None:
        title.font = Font(name="맑은 고딕", bold=True, size=13, color=navy)
    note = _set(ws, 3, 1,
                "읽는 법: 오늘 총잔액 = 전날 총잔액 + ② 입금 합계 − ③ 지출. "
                "지출은 전액 우리은행에서 집행하고, 모자라면 ④처럼 농협 → "
                "국민 순으로 우리은행에 이체해 채웁니다. '요약' 시트의 입금 "
                "반영률(B13)을 바꾸면 이 표도 즉시 다시 계산됩니다. 지난 "
                "실적 일자 행은 숨김(마지막 실적일 잔액에서 출발), 실수 "
                "방지를 위해 시트 보호(암호 없음)."
                + (f" ② 배분 비중(최근 입금 실적): {share_txt}"
                   if share_txt else ""))
    if note is not None:
        note.font = Font(name="맑은 고딕", size=9, color=gray)

    def _band(c1, c2, text, color):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=4, column=c)
            cell.fill = PatternFill("solid", start_color=color)
            cell.border = box
        head = _set(ws, 4, c1, text)
        if head is not None:
            head.font = Font(**white_bold)
            head.alignment = Alignment(horizontal="left", vertical="center")
        if c2 > c1:
            ws.merge_cells(start_row=4, start_column=c1,
                           end_row=4, end_column=c2)

    _band(col_total, col_total + n, "① 잔액 (총잔액 · 계좌별)", navy)
    _band(col_in_sum, col_in_sum + n,
          "② 오늘 들어오는 돈 — 예상입금 배분", green)
    _band(col_out, col_out, "③ 지출", orange)
    _band(col_tr, col_tr + 1, "④ 부족분 이체", d_orange)

    # 머리글 2행: 일자·요일·비고는 4~5행 세로 병합
    heads = ([(1, "일자", navy), (2, "요일", navy)]
             + [(col_total, "총잔액", navy)]
             + [(col_total + 1 + i, account_label(b, a), navy)
                for i, (b, a) in enumerate(accounts)]
             + [(col_in_sum, "합계", green)]
             + [(col_in_sum + 1 + i, account_label(b, a), green)
                for i, (b, a) in enumerate(accounts)]
             + [(col_out, "우리은행 집행", orange)]
             + [(col_tr, "농협→우리", d_orange),
                (col_tr + 1, "국민→우리", d_orange)]
             + [(col_note, "비고", gray)])
    widths = {1: 11, 2: 5, col_total: 15, col_in_sum: 13, col_out: 13,
              col_tr: 12, col_tr + 1: 12, col_note: 22}
    for c, text, color in heads:
        row0 = 4 if c in (1, 2, col_note) else 5
        cell = _set(ws, row0, c, text)
        if cell is not None:
            cell.font = Font(**white_bold)
            cell.alignment = Alignment(horizontal="center",
                                       vertical="center")
        for rr in (4, 5):
            hc = ws.cell(row=rr, column=c)
            if rr >= row0:
                hc.fill = PatternFill("solid", start_color=color)
            hc.border = box
        if row0 == 4:
            ws.merge_cells(start_row=4, start_column=c,
                           end_row=5, end_column=c)
        ws.column_dimensions[get_column_letter(c)].width = \
            widths.get(c, 14)

    total_fill = PatternFill("solid", start_color="D9E2F1")
    in_fill = PatternFill("solid", start_color="E2EFDA")
    out_fill = PatternFill("solid", start_color="FCE4D6")
    tr_fill = PatternFill("solid", start_color="F8CBAD")
    red = Font(name="맑은 고딕", size=10, color="C00000")
    num_bal = "#,##0;[Red]-#,##0"
    num_flow = "#,##0;[Red]-#,##0;"          # 0은 빈칸으로
    rows = scenario["rows"]
    last_act = max((i for i, rw in enumerate(rows) if rw.get("실적")),
                   default=None)
    opening = scenario.get("opening") or {}
    daily = "'4주일별계획'!"                 # 행 번호가 이 시트와 같다
    col_l = get_column_letter
    # 4주일별계획의 입금·지출 열 위치 (계좌 열 수에 따라 이동)
    dlay = daily_layout(n)
    d_in = f"{daily}{col_l(dlay['online'])}{{r}}+{daily}{col_l(dlay['conf'])}{{r}}"
    d_out = (f"{daily}{col_l(dlay['transfer'])}{{r}}"
             f"+{daily}{col_l(dlay['card'])}{{r}}"
             f"+{daily}{col_l(dlay['etc'])}{{r}}")

    def _num(rr, cc, value, fmt, bold=False):
        cell = _set(ws, rr, cc, value)
        if cell is not None:
            cell.number_format = fmt
            cell.font = Font(name="맑은 고딕", size=10, bold=bold)
        return cell

    # 이체 계산용 숨김 열(비고 오른쪽): 인출 우선순위 순 계좌별 이체액
    helper_cols = {k: col_note + j for j, k in enumerate(accounts[1:], 1)}
    for c in helper_cols.values():
        ws.column_dimensions[col_l(c)].hidden = True
    nh_cols = [c for (b, _a), c in helper_cols.items() if b == "농협"]
    kb_cols = [c for (b, _a), c in helper_cols.items() if b == "국민은행"]

    # 출발 행 2개 (2026-09-21 사용자 요청):
    #  6행 = 전일 마감 계좌별 실잔고 — 시나리오는 여기서 출발
    #  7행 = 오늘 은행 확인 계좌별 실잔고 (참고 — 당일 실제 순증감은
    #        출발 잔액 계산에서 이미 상쇄됨)
    today_d = run_date or (rows[0]["일자"] if rows else date.today())
    prev_d = today_d - timedelta(days=1)
    current = scenario.get("current") or opening
    for rr in (6, 7):
        for c in range(1, col_note + 1):
            cell = ws.cell(row=rr, column=c)
            cell.border = box
            if col_total <= c <= col_total + n:
                cell.fill = total_fill
    for rr, dd, vals, bold, label in (
            (6, prev_d, opening, True, "전일 마감 실잔고 — 여기서 출발"),
            (7, today_d, current, False,
             "오늘 실잔고(은행 확인) — 참고")):
        acell = _set(ws, rr, 1, datetime.combine(dd, dtime()))
        if acell is not None:
            acell.number_format = "yyyy-mm-dd"
            acell.font = Font(name="맑은 고딕", size=10, bold=bold,
                              color=None if bold else gray)
        wcell = _set(ws, rr, 2, WEEKDAY_KO[dd.weekday()])
        if wcell is not None:
            wcell.font = Font(name="맑은 고딕", size=10, bold=bold,
                              color=None if bold else gray)
        _num(rr, col_total, f"=SUM({col_l(4)}{rr}:{col_l(3 + n)}{rr})",
             num_bal, bold=True)
        for idx, k in enumerate(accounts):
            _num(rr, 4 + idx, round(float(vals.get(k) or 0)), num_bal,
                 bold=bold)
        ncell = _set(ws, rr, col_note, label)
        if ncell is not None:
            ncell.font = Font(name="맑은 고딕", size=9, bold=bold,
                              color=gray)

    r = 8
    for i, row in enumerate(rows):
        d = row["일자"]
        # 지난 실적 일자는 숨긴다 (출발 행이 실잔고를 보여준다)
        ws.row_dimensions[r].hidden = last_act is not None and i <= last_act
        acell = _set(ws, r, 1, datetime.combine(d, dtime()))
        if acell is not None:
            acell.number_format = "yyyy-mm-dd"
        wcell = _set(ws, r, 2, row.get("요일"))
        if is_offday(d, holidays):
            for cell in (acell, wcell):
                if cell is not None:
                    cell.font = red

        if row.get("실적"):
            balances = row.get("잔액")
            if balances is not None:
                _num(r, col_total,
                     round(sum(balances.get(k, 0) for k in accounts)),
                     num_bal, bold=True)
                for idx, k in enumerate(accounts):
                    _num(r, 4 + idx, round(balances.get(k, 0)), num_bal)
            ncell = _set(ws, r, col_note, "실적 구간")
            if ncell is not None:
                ncell.font = Font(name="맑은 고딕", size=9, color=gray)
        else:
            # 예측 행은 전부 수식: 요약!B13(반영률)을 바꾸면 4주일별계획
            # 입금 수식을 거쳐 이 표의 입금·이체·잔액이 즉시 재계산된다
            # 전날 잔액: 바로 윗 행 참조. 첫 데이터 행(8행)은 6행(전일
            # 마감 실잔고)에서 출발한다 — 7행(오늘 실잔고)은 참고 표시
            prev_r = 6 if r == 8 else r - 1
            prev = {k: f"{col_l(4 + idx)}{prev_r}"
                    for idx, k in enumerate(accounts)}
            in_cell = {k: f"{col_l(col_in_sum + 1 + idx)}{r}"
                       for idx, k in enumerate(accounts)}
            out_ref = f"{col_l(col_out)}{r}"
            w = accounts[0]
            need = f"MAX(0,{out_ref}-{prev[w]}-{in_cell[w]})"
            _num(r, col_in_sum, "=" + d_in.format(r=r), num_flow)
            for idx, k in enumerate(accounts):
                _num(r, col_in_sum + 1 + idx,
                     f"={col_l(col_in_sum)}{r}*{shares.get(k, 0):.6f}",
                     num_flow)
            _num(r, col_out, "=" + d_out.format(r=r), num_flow)
            done = []
            for k in accounts[1:]:
                minus = "".join(f"-{col_l(c)}{r}" for c in done)
                _num(r, helper_cols[k],
                     f"=MIN(MAX(0,{prev[k]}+{in_cell[k]}),{need}{minus})",
                     num_flow)
                done.append(helper_cols[k])
            for cc, cols in ((col_tr, nh_cols), (col_tr + 1, kb_cols)):
                _num(r, cc,
                     ("=" + "+".join(f"{col_l(c)}{r}" for c in cols))
                     if cols else None, num_flow)
            plus = "".join(f"+{col_l(c)}{r}"
                           for c in helper_cols.values())
            _num(r, 4, f"={prev[w]}+{in_cell[w]}-{out_ref}{plus}", num_bal)
            for idx, k in enumerate(accounts):
                if idx:
                    _num(r, 4 + idx,
                         f"={prev[k]}+{in_cell[k]}"
                         f"-{col_l(helper_cols[k])}{r}", num_bal)
            _num(r, col_total, f"=SUM({col_l(4)}{r}:{col_l(3 + n)}{r})",
                 num_bal, bold=True)
            wl = col_l(4)
            ncell = _set(ws, r, col_note,
                         f'=IF({wl}{r}<-0.5,"전 계좌 소진 — 부족 "'
                         f'&TEXT(-{wl}{r},"#,##0")&"원","")')
            if ncell is not None:
                ncell.font = Font(name="맑은 고딕", size=9, color="C00000")

        # 블록별 배경색·테두리로 구간을 구분
        for c in range(1, col_note + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = box
            if c == col_total:
                cell.fill = total_fill
            elif col_in_sum <= c <= col_in_sum + n:
                cell.fill = in_fill
            elif c == col_out:
                cell.fill = out_fill
            elif c in (col_tr, col_tr + 1):
                cell.fill = tr_fill
        r += 1
    ws.freeze_panes = "D8"   # 일자·요일·총잔액·출발 행 2개 고정
    # 실수로 수식을 지우지 않게 암호 없는 시트 보호 (행·열 숨기기
    # 해제와 셀 선택은 그대로 가능)
    from openpyxl.worksheet.protection import SheetProtection
    ws.protection = SheetProtection(sheet=True, formatRows=False,
                                    formatColumns=False)


def _fill_expense(wb, rows: list[dict],
                  holidays: Optional[dict] = None,
                  run_date: Optional[date] = None) -> None:
    """팀 지출계획 취합을 별도 시트로 자동 반영 (매주 전체 갱신).

    대외비 행은 분류·총액 집계로만 표시된다(상세 미노출).
    경영보고 지출예정 표와 같은 기간(실행일~차주 금요일)만 표시하고
    그 밖의 반영일 행은 숨긴다 (2026-09-21 사용자 요청) — 값은 남아
    있어 행 숨기기 해제로 전체를 볼 수 있다.
    """
    from openpyxl.styles import Alignment, Font, PatternFill
    from excel_report import is_offday

    if EXPENSE_SHEET in wb.sheetnames:
        ws = wb[EXPENSE_SHEET]
    else:
        try:
            index = wb.sheetnames.index("13주주별계획") + 1
        except ValueError:
            index = len(wb.sheetnames)
        ws = wb.create_sheet(EXPENSE_SHEET, index)

    title = _set(ws, 2, 1, "팀 지출계획 취합 (자동 반영)")
    if title is not None:
        title.font = Font(name="맑은 고딕", bold=True, size=13,
                          color="1F4E79")
    note = _set(ws, 3, 1,
                "매 실행마다 팀 제출 파일에서 자동 갱신됩니다. "
                "대외비는 분류·총액만 표시됩니다. 경영보고와 같은 "
                "실행일~차주 금요일 기간만 표시합니다 (그 밖의 반영일 "
                "행은 숨김 — 행 숨기기 해제로 전체 확인).")
    if note is not None:
        note.font = Font(name="맑은 고딕", size=9, color="808080")

    from openpyxl.utils import get_column_letter
    for c, (header, _key, width) in enumerate(_EXPENSE_COLUMNS, start=1):
        cell = _set(ws, 5, c, header)
        if cell is not None:
            cell.fill = PatternFill("solid", start_color="1F4E79")
            cell.font = Font(name="맑은 고딕", color="FFFFFF", bold=True,
                             size=10)
            cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = width
    # 예전 버전이 만든 대조·확인완료·숨김 헬퍼 열(R~U)은 정리한다
    for c in range(len(_EXPENSE_COLUMNS) + 1, len(_EXPENSE_COLUMNS) + 5):
        _set(ws, 5, c, None)
        ws.column_dimensions[get_column_letter(c)].hidden = False

    window = exec_window(run_date) if run_date is not None else None
    r = 6
    for row in rows:
        reflect_d = None
        for c, (_header, key, _width) in enumerate(_EXPENSE_COLUMNS, start=1):
            value = row.get(key)
            if isinstance(value, datetime):
                value = value.date()
            if key == "자금계획 반영일" and isinstance(value, date):
                reflect_d = value
            cell = _set(ws, r, c, value)
            if cell is None:
                continue
            cell.font = Font(name="맑은 고딕", size=10)
            if key == "예상금액":
                cell.number_format = "#,##0"
            elif isinstance(value, date):
                cell.number_format = "yyyy-mm-dd"
                if is_offday(value, holidays):
                    cell.font = Font(name="맑은 고딕", size=10,
                                     color="C00000")
        # 경영보고 지출예정 표와 같은 기간 밖의 반영일 행은 숨긴다
        ws.row_dimensions[r].hidden = bool(
            window is not None and reflect_d is not None
            and not (window[0] <= reflect_d <= window[1]))
        r += 1
    # 머리글 자동 필터 — 반영일·팀명·반영상태 등으로 골라 볼 수 있다
    ws.auto_filter.ref = (f"A5:{get_column_letter(len(_EXPENSE_COLUMNS))}"
                          f"{max(r - 1, 6)}")
    # 이전 실행의 잔여 행 정리 (숨김 상태도 되돌린다)
    end = max(ws.max_row, r)
    for rr in range(r, end + 1):
        ws.row_dimensions[rr].hidden = False
        row_empty = True
        for c in range(1, len(_EXPENSE_COLUMNS) + 5):
            if ws.cell(row=rr, column=c).value is not None:
                _set(ws, rr, c, None)
                row_empty = False
        if row_empty and rr > r + 5:
            break
    ws.freeze_panes = "A6"


APALM_SHEET = "에이팜 지출계획"

_APALM_COLUMNS = [
    ("일자", "일자", 12), ("요일", "요일", 6), ("출처", "출처", 12),
    ("자금계획 반영", "반영", 15), ("팀명", "팀명", 12),
    ("거래처", "거래처", 18), ("지출내용", "지출내용", 28),
    ("예상금액", "예상금액", 14), ("지급방법", "지급방법", 10),
    ("비고", "비고", 14),
]


def _fill_apalm_expense(wb, rows: list[dict],
                        holidays: Optional[dict] = None) -> None:
    """에이팜 지출계획 전용 시트.

    비고에 '에이팜'이 적힌 팀 지출계획은 자금계획에서 뺀 별도관리
    건(미반영)으로, 이름으로 인식된 자동 추정 등은 자금계획에 포함된
    참고 건(반영)으로 함께 보여준다.
    """
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from excel_report import is_offday

    if APALM_SHEET in wb.sheetnames:
        ws = wb[APALM_SHEET]
    else:
        try:
            index = wb.sheetnames.index(EXPENSE_SHEET) + 1
        except ValueError:
            index = len(wb.sheetnames)
        ws = wb.create_sheet(APALM_SHEET, index)

    title = _set(ws, 2, 1, "에이팜 지출계획 (자동 반영)")
    if title is not None:
        title.font = Font(name="맑은 고딕", bold=True, size=13,
                          color="1F4E79")
    note = _set(ws, 3, 1,
                "지출계획 비고에 '에이팜'으로 표시한 건은 자금계획(4주·13주)에 "
                "반영하지 않고 여기서만 관리합니다. '반영' 표시 건은 자금계획에 "
                "포함된 에이팜 관련 참고 항목입니다.")
    if note is not None:
        note.font = Font(name="맑은 고딕", size=9, color="808080")

    for c, (header, _key, width) in enumerate(_APALM_COLUMNS, start=1):
        cell = _set(ws, 5, c, header)
        if cell is not None:
            cell.fill = PatternFill("solid", start_color="1F4E79")
            cell.font = Font(name="맑은 고딕", color="FFFFFF", bold=True,
                             size=10)
            cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = width

    excluded_fill = PatternFill("solid", start_color="FFF2CC")
    r = 6
    for row in rows:
        excluded = str(row.get("반영") or "").startswith("미반영")
        row_d = row.get("일자")
        row_off = isinstance(row_d, date) and is_offday(row_d, holidays)
        for c, (_header, key, _width) in enumerate(_APALM_COLUMNS, start=1):
            if key == "요일":
                d = row.get("일자")
                value = WEEKDAY_KO[d.weekday()] if isinstance(d, date) else ""
            else:
                value = row.get(key)
            if isinstance(value, datetime):
                value = value.date()
            cell = _set(ws, r, c, value)
            if cell is None:
                continue
            if row_off and key in ("일자", "요일"):
                cell.font = Font(name="맑은 고딕", size=10, color="C00000")
            else:
                cell.font = Font(name="맑은 고딕", size=10)
            if excluded:
                cell.fill = excluded_fill
            if key == "예상금액":
                cell.number_format = "#,##0"
            elif isinstance(value, date):
                cell.number_format = "yyyy-mm-dd"
        r += 1
    if rows:
        sums = [("합계(자금계획 미반영)",
                 sum(x.get("예상금액") or 0 for x in rows
                     if str(x.get("반영") or "").startswith("미반영"))),
                ("합계(자금계획 반영)",
                 sum(x.get("예상금액") or 0 for x in rows
                     if not str(x.get("반영") or "").startswith("미반영")))]
        for label, amount in sums:
            if not amount:
                continue
            _set(ws, r, 7, label)
            total = _set(ws, r, 8, round(amount))
            for c in (7, 8):
                cell = ws.cell(row=r, column=c)
                if not isinstance(cell, MergedCell):
                    cell.font = Font(name="맑은 고딕", size=10, bold=True)
            if total is not None:
                total.number_format = "#,##0"
            r += 1
    else:
        empty = _set(ws, r, 1, "이번 실행에 정리할 에이팜 지출계획이 없습니다.")
        if empty is not None:
            empty.font = Font(name="맑은 고딕", size=10, color="808080")
        r += 1
    # 이전 실행의 잔여 행 정리
    end = max(ws.max_row, r)
    for rr in range(r, end + 1):
        row_empty = True
        for c in range(1, len(_APALM_COLUMNS) + 1):
            if ws.cell(row=rr, column=c).value is not None:
                _set(ws, rr, c, None)
                row_empty = False
        if row_empty and rr > r + 5:
            break
    ws.freeze_panes = "A6"


def _fill_raw(ws, bank_rows: list[dict],
              holidays: Optional[dict] = None) -> None:
    from openpyxl.styles import Font
    from excel_report import is_offday
    red = Font(name="맑은 고딕", size=10, color="C00000")
    rows = [r for r in bank_rows if r.get("반영상태") != "중복제외"]
    rows.sort(key=lambda r: (r.get("거래일") or date.min,
                             r.get("거래일시") or datetime.min))
    r = 2
    for t in rows:
        tx_date = t.get("거래일")
        dt = t.get("거래일시") or (datetime.combine(tx_date, dtime())
                               if tx_date else None)
        cls = t.get("자동분류") or ""
        if t.get("내부이체"):
            cls = "계좌간이체"
        elif not cls:
            cls = "기타입금" if (t.get("입금액") or 0) > 0 else "기타지출"
        values = [
            dt, datetime.combine(tx_date, dtime()) if tx_date else None,
            t.get("은행"), account_label(t.get("은행", ""),
                                       t.get("계좌") or ""),
            round(t.get("출금액") or 0), round(t.get("입금액") or 0),
            None if t.get("거래후잔액") is None else round(t["거래후잔액"]),
            t.get("적요"), t.get("기재내용·상대방"), t.get("취급점"), cls,
            "Y" if t.get("내부이체") else "N",
            "Y" if t.get("정기지출후보") else "N",
            round(t.get("현금유출입") or 0),
        ]
        off = tx_date is not None and is_offday(tx_date, holidays)
        for c, v in enumerate(values, start=1):
            cell = _set(ws, r, c, v)
            if cell is None:
                continue
            if c == 1:
                cell.number_format = "yyyy-mm-dd hh:mm:ss"
            elif c == 2:
                cell.number_format = "yyyy-mm-dd"
            elif c in (5, 6, 7, 14):
                cell.number_format = "#,##0"
            if off and c in (1, 2):
                cell.font = red
        r += 1
    # 이전 실행의 잔여 행·템플릿의 옛 붙여넣기용 수식을 끝까지 정리한다
    # (중간 빈 구간에서 멈추면 아래쪽 잔여 수식이 살아남아 #REF! 위험)
    for rr in range(r, ws.max_row + 1):
        for c in range(1, 15):
            if ws.cell(row=rr, column=c).value is not None:
                _set(ws, rr, c, None)
