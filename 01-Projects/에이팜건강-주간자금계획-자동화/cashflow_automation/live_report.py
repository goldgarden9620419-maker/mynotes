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
_SUMIFS = ("=SUMIFS('4주일별계획'!${col}$6:${col}$33,"
           "'4주일별계획'!$A$6:$A$33,\">=\"&DATE({y1},{m1},{d1}),"
           "'4주일별계획'!$A$6:$A$33,\"<=\"&DATE({y2},{m2},{d2}))")


class LiveTemplateError(RuntimeError):
    pass


def fill_live_workbook(template_path: Path, report: dict,
                       out_path: Path) -> Path:
    """템플릿의 수식·서식을 유지한 채 최신 값으로 채워 저장한다."""
    template_path = Path(template_path)
    if not template_path.exists():
        raise LiveTemplateError(f"라이브 템플릿이 없습니다: {template_path}")
    wb = load_workbook(template_path)
    required = {"요약", "4주일별계획", "13주주별계획", "정기지출분석",
                "계좌내역통합_RAW", "설정및분류"}
    missing = required - set(wb.sheetnames)
    if missing:
        wb.close()
        raise LiveTemplateError(f"템플릿에 시트가 없습니다: {missing}")

    meta = report["meta"]
    forecast = report["forecast"]
    base_date: date = meta["base_date"]
    stats = report.get("history_stats", {})

    _fill_config(wb["설정및분류"], forecast)
    _fill_summary(wb["요약"], report, base_date, stats)
    _fill_daily(wb["4주일별계획"], forecast, base_date,
                meta.get("run_date"))
    _fill_weekly(wb["13주주별계획"], forecast, base_date)
    _fill_account_scenario(wb, report.get("account_scenario"))
    _fill_expense(wb, report.get("integrated_masked", []))
    _fill_apalm_expense(wb, report.get("apalm_expenses", []))
    _fill_recurring(wb["정기지출분석"], report.get("recurring", []))
    _fill_raw(wb["계좌내역통합_RAW"], report.get("bank_rows", []))

    # 은행 파일을 폴더에서 자동으로 읽으므로 수동 붙여넣기 시트는 제거한다
    if "주간계좌_붙여넣기" in wb.sheetnames:
        wb.remove(wb["주간계좌_붙여넣기"])

    # 정기지출분석은 사용자가 분류·성격을 편집하는 시트라 맨 끝에 둔다
    idx = wb.sheetnames.index("정기지출분석")
    wb.move_sheet("정기지출분석", offset=len(wb.sheetnames) - 1 - idx)

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
        # 실적으로 채워진 지난 날짜는 값이므로, 미래 행 중 하나라도
        # 반영률 수식(INDEX×$B$13)이 살아 있으면 수식 보존으로 본다
        formula_ok = any(
            "INDEX" in str(daily.cell(row=r, column=3).value or "")
            and "$B$13" in str(daily.cell(row=r, column=3).value or "")
            for r in range(6, 34))
        a6 = daily["A6"].value
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


def _fill_summary(ws, report: dict, base_date: date, stats: dict) -> None:
    ws["A3"] = (f"기준일 {base_date} | 농협·우리은행·국민은행 계좌 "
                "거래내역 통합 (자동 갱신)")
    ws["B6"] = round(report.get("total_balance") or 0)
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


def _fill_daily(ws, forecast: dict, base_date: date,
                run_date: Optional[date] = None) -> None:
    daily_by_date = {r["일자"]: r for r in forecast.get("daily", [])}
    # 비고 열 위치는 머리글(5행)에서 찾는다 (기본 K열)
    note_col = 11
    for c in range(1, 21):
        if str(ws.cell(row=5, column=c).value or "").strip() == "비고":
            note_col = c
            break
    # 실적 구간이 있으면 시작잔액을 '기준일 시작' 잔액 값으로 고정한다
    # (현재잔액에는 이미 이번 주 실적이 반영돼 있어 이중계산 방지)
    if forecast.get("actual_until") is not None \
            and forecast.get("start_balance") is not None:
        i6 = _set(ws, 6, 9, round(forecast["start_balance"]))
        if i6 is not None:
            i6.number_format = "#,##0"
    for i in range(28):
        row = 6 + i
        d = base_date + timedelta(days=i)
        acell = _set(ws, row, 1, datetime.combine(d, dtime()))
        if acell is not None:
            acell.number_format = "yyyy-mm-dd"
        _set(ws, row, 2, WEEKDAY_KO[d.weekday()])
        src = daily_by_date.get(d)
        vals = [None, None, None, None]
        if src:
            etc = (src.get("자동이체") or 0) + (src.get("기타지출") or 0)
            vals = [src.get("확정·기타입금") or None,
                    src.get("팀별 송금예정") or None,
                    src.get("카드결제") or None,
                    etc or None]
        # 지난 날짜(실적)는 온라인입금도 실제 값으로 고정한다
        if src and src.get("실적"):
            c3 = _set(ws, row, 3, round(src.get("온라인 예상입금") or 0))
            if c3 is not None:
                c3.number_format = "#,##0"
        for c, v in zip((4, 5, 6, 7), vals):
            _set(ws, row, c, round(v) if v else None)
        # 그날 반영된 지출 내역 요약 (없으면 이전 실행 잔여값 정리)
        ncell = _set(ws, row, note_col, (src or {}).get("비고") or None)
        if ncell is not None:
            # 긴 내역은 셀 안에서 자동 줄바꿈 + 행 높이 자동 조정
            from openpyxl.styles import Alignment
            ncell.alignment = Alignment(horizontal="left", vertical="top",
                                        wrap_text=True)
            rd = ws.row_dimensions.get(row)
            if rd is not None:
                rd.height = None
                rd.customHeight = False
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
    for r in range(6, 34):
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
    first = 6 + max(0, min((start - base_date).days, 27))
    last = 6 + max(0, min((end - base_date).days, 27))
    outline_week_box(ws, first, last, 1, last_col)


def _fill_weekly(ws, forecast: dict, base_date: date) -> None:
    weekly = forecast.get("weekly", [])
    for w in range(13):
        r = 6 + w
        w_start = base_date + timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        _set(ws, r, 2, f"{w_start} ~ {w_end}")
        if w < 4:
            # 1~4주차: SUMIFS 수식의 날짜 리터럴을 새 주차로 재작성
            for col in ("C", "D", "E", "F", "G"):
                ws[f"{col}{r}"] = _SUMIFS.format(
                    col=col, y1=w_start.year, m1=w_start.month,
                    d1=w_start.day, y2=w_end.year, m2=w_end.month,
                    d2=w_end.day)
        else:
            wr = weekly[w] if w < len(weekly) else {}
            etc = (wr.get("자동이체") or 0) + (wr.get("기타지출") or 0)
            for c, v in ((4, wr.get("확정기타입금")), (5, wr.get("송금예정")),
                         (6, wr.get("카드결제")), (7, etc)):
                _set(ws, r, c, round(v) if v else None)


ACCOUNT_SCENARIO_SHEET = "계좌별시나리오"


def _fill_account_scenario(wb, scenario: Optional[dict]) -> None:
    """계좌별 일별 잔액 시나리오 시트 (우리→농협→국민 인출 우선순위)."""
    if not scenario or not scenario.get("accounts"):
        return
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    if ACCOUNT_SCENARIO_SHEET in wb.sheetnames:
        ws = wb[ACCOUNT_SCENARIO_SHEET]
    else:
        try:
            index = wb.sheetnames.index("4주일별계획") + 1
        except ValueError:
            index = len(wb.sheetnames)
        ws = wb.create_sheet(ACCOUNT_SCENARIO_SHEET, index)

    accounts = scenario["accounts"]
    title = _set(ws, 2, 1, "계좌별 일별 잔액 시나리오 (자동 반영)")
    if title is not None:
        title.font = Font(name="맑은 고딕", bold=True, size=13,
                          color="1F4E79")
    note = _set(ws, 3, 1,
                "인출 우선순위: 우리은행 → 농협 → 국민은행. 부족분은 이체 열의 "
                "금액만큼 우리은행으로 옮겨 집행하는 가정입니다 "
                "(입금은 계좌별 최근 비중대로 배분, 기본 반영률 기준).")
    if note is not None:
        note.font = Font(name="맑은 고딕", size=9, color="808080")

    headers = (["일자", "요일"]
               + [account_label(b, a) + " 잔액" for b, a in accounts]
               + ["총잔액", "농협→우리 이체", "국민→우리 이체", "비고"])
    widths = [11, 6] + [15] * len(accounts) + [15, 14, 14, 22]
    for c, header in enumerate(headers, start=1):
        cell = _set(ws, 5, c, header)
        if cell is not None:
            cell.fill = PatternFill("solid", start_color="1F4E79")
            cell.font = Font(name="맑은 고딕", color="FFFFFF", bold=True,
                             size=10)
            cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = widths[c - 1]

    r = 6
    for row in scenario["rows"]:
        d = row["일자"]
        acell = _set(ws, r, 1, datetime.combine(d, dtime()))
        if acell is not None:
            acell.number_format = "yyyy-mm-dd"
        _set(ws, r, 2, row.get("요일"))
        balances = row.get("잔액")
        values = []
        if balances is None:
            values = [None] * (len(accounts) + 1)
        else:
            values = [round(balances.get(k, 0)) for k in accounts]
            values.append(round(sum(balances.get(k, 0) for k in accounts)))
        nh = sum(v for k, v in (row.get("이체") or {}).items()
                 if k[0] == "농협")
        kb = sum(v for k, v in (row.get("이체") or {}).items()
                 if k[0] == "국민은행")
        values += [round(nh) or None, round(kb) or None]
        for i, v in enumerate(values, start=3):
            cell = _set(ws, r, i, v)
            if cell is not None:
                cell.number_format = "#,##0"
                cell.font = Font(name="맑은 고딕", size=10)
        ncell = _set(ws, r, 3 + len(values), row.get("비고") or None)
        if ncell is not None:
            ncell.font = Font(name="맑은 고딕", size=9,
                              color="C00000" if row.get("비고") else "808080")
        r += 1
    # 잔여 행 정리
    for rr in range(r, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            if ws.cell(row=rr, column=c).value is not None:
                _set(ws, rr, c, None)
    ws.freeze_panes = "A6"


def _fill_expense(wb, rows: list[dict]) -> None:
    """팀 지출계획 취합을 별도 시트로 자동 반영 (매주 전체 갱신).

    대외비 행은 분류·총액 집계로만 표시된다(상세 미노출).
    """
    from openpyxl.styles import Alignment, Font, PatternFill

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
                "대외비는 분류·총액만 표시됩니다.")
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

    r = 6
    for row in rows:
        for c, (_header, key, _width) in enumerate(_EXPENSE_COLUMNS, start=1):
            value = row.get(key)
            if isinstance(value, datetime):
                value = value.date()
            cell = _set(ws, r, c, value)
            if cell is None:
                continue
            cell.font = Font(name="맑은 고딕", size=10)
            if key == "예상금액":
                cell.number_format = "#,##0"
            elif isinstance(value, date):
                cell.number_format = "yyyy-mm-dd"
        r += 1
    # 머리글 자동 필터 — 반영일·팀명·반영상태 등으로 골라 볼 수 있다
    ws.auto_filter.ref = (f"A5:{get_column_letter(len(_EXPENSE_COLUMNS))}"
                          f"{max(r - 1, 6)}")
    # 이전 실행의 잔여 행 정리
    end = max(ws.max_row, r)
    for rr in range(r, end + 1):
        row_empty = True
        for c in range(1, len(_EXPENSE_COLUMNS) + 1):
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


def _fill_apalm_expense(wb, rows: list[dict]) -> None:
    """에이팜 지출계획 전용 시트.

    비고에 '에이팜'이 적힌 팀 지출계획은 자금계획에서 뺀 별도관리
    건(미반영)으로, 이름으로 인식된 자동 추정 등은 자금계획에 포함된
    참고 건(반영)으로 함께 보여준다.
    """
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

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


def _fill_recurring(ws, recurring: list[dict]) -> None:
    _set(ws, 5, 11, "성격")  # 기준파일 '정기지출분류' 시트에서 수정 가능
    for i in range(6, max(len(recurring) + 20, 90)):
        for c in range(1, 12):
            _set(ws, i, c, None)
    for i, it in enumerate(recurring, start=6):
        values = [it.get("은행"), it.get("정기지출명"),
                  it.get("분류") or "성격확인필요",
                  it.get("발생개월수"), it.get("거래건수"),
                  round(it.get("평균 월지출") or 0),
                  round(it.get("최소 월지출") or 0),
                  round(it.get("최대 월지출") or 0),
                  f"매월 {it.get('대표 지급일')}일 전후",
                  _CONF_LABEL.get(it.get("신뢰도"), it.get("신뢰도")),
                  it.get("성격") or "정기"]
        for c, v in enumerate(values, start=1):
            cell = _set(ws, i, c, v)
            if cell is not None and c in (6, 7, 8):
                cell.number_format = _MONEY_WON


def _fill_raw(ws, bank_rows: list[dict]) -> None:
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
        r += 1
    # 이전 실행의 잔여 행·템플릿의 옛 붙여넣기용 수식을 끝까지 정리한다
    # (중간 빈 구간에서 멈추면 아래쪽 잔여 수식이 살아남아 #REF! 위험)
    for rr in range(r, ws.max_row + 1):
        for c in range(1, 15):
            if ws.cell(row=rr, column=c).value is not None:
                _set(ws, rr, c, None)
