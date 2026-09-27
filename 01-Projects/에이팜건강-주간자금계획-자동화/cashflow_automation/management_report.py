# -*- coding: utf-8 -*-
"""주간 자금 경영보고 워크북 (대화형).

기존 고정서식 주간자금계획 파일을 대신하는 보고용 엑셀.
현재 자금 현황 → 향후 4주 일별 흐름(부족 여부) → 반영된 입금예정
(온라인 예상·확정입금 vs 실입금) → 반영된 지출예정 전체 표(실지출
대조·확인란 포함) → 안정을 위한 필요 추가 입금 → 건강사업팀 전달
메모 순서로 한 시트에 담고, 노란 칸(반영률·목표잔액·지출 지급일·
금액)을 고치면 수식으로 즉시 재계산되게 만든다. 첫 주(취합 지출예정
파일 기준주)는 붉은 외곽 상자로 표시한다.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from common import WEEKDAY_KO, save_workbook
from excel_report import account_label
from live_report import exec_window, outline_week_box

# 통합 파일(주간자금계획_일시.xlsx)의 첫 시트 이름 (2026-09-23 사용자
# 요청: 경영보고·대표보고·라이브를 한 파일로 합치고 경영보고가 입력 기준)
SHEET_NAME = "경영보고"
CEO_SHEET = "대표보고"
# ② 지출예정 확인(I열) 선택지 (2026-09-23 사용자 요청): '보류' 행은
# 계획(④·라이브)에서 제외, '적용'·빈칸은 반영
EXP_APPLY = "적용"
EXP_HOLD = "보류"
# ④·라이브·대표보고 SUMIFS 공통 조건: 보류 행 제외
_NOT_HOLD = f'"<>{EXP_HOLD}"'

_NAVY = "1F4E79"
_EDIT_FILL = PatternFill("solid", start_color="FFF2CC")   # 수정 가능 칸
_HEAD_FILL = PatternFill("solid", start_color=_NAVY)
_ACT_FILL = PatternFill("solid", start_color="EFEFEF")    # 실적 구간
_RED_FILL = PatternFill("solid", start_color="FFC7CE")
_DIFF_FILL = PatternFill("solid", start_color="FFE699")   # 계획·실제 차이
_THIN = Border(*(Side(style="thin", color="BBBBBB"),) * 4)

# 섹션 순서 (2026-09-23 사용자 요청: 지출예정 표를 현황 바로 다음으로
# 올려 지급일·금액을 위에서 바로 고치게 한다):
# ① 현재 자금 현황(계좌 6~11, 총잔액 12행 고정 + 반영률 F12)
# ② 반영된 지출예정  ③ 반영된 입금예정  ④ 4주 일별 흐름
# ⑤ 필요 추가 입금  ⑥ 메모
_ACC_FIRST, _ACC_MAX = 6, 6                      # 계좌 행 6..11 (고정 폭)
_TOTAL_ROW = 12                                  # 총잔액 (고정)
_RATE_CELL = "$F$12"                             # 입금 반영률 (총잔액 행)

# ② 지출 예정 표의 데이터 행 범위 (SUMIFS가 참조하는 고정 구간)
_EXP_HEAD = 14                                   # 섹션 띠
_EXP_COLS = _EXP_HEAD + 1                        # 15: 열 머리글
_EXP_FIRST, _EXP_LAST = _EXP_COLS + 1, 109       # 16..109
_EXP_TOTAL = _EXP_LAST + 1                       # 110

# ③ 입금 예정 표: 온라인 예상·확정입금 항목과 실입금(은행 확인) 대조
_INC_HEAD = _EXP_TOTAL + 2                       # 112: 섹션 띠
_INC_COLS = _INC_HEAD + 1                        # 113: 열 머리글
_INC_FIRST, _INC_LAST = _INC_COLS + 1, 135       # 114..135
_INC_TOTAL = _INC_LAST + 1                       # 136

# ④ 일별 흐름 표: 기준일부터 4주(28일)
_DAY_HEAD = _INC_TOTAL + 2                       # 138: 섹션 띠
_DAY_COLS = _DAY_HEAD + 1                        # 139: 열 머리글
_DAY_FIRST, _DAY_COUNT = _DAY_COLS + 1, 28       # 140..167
_DAY_LAST = _DAY_FIRST + _DAY_COUNT - 1          # 167
_SUM_ROW = _DAY_LAST + 1                         # 168: 최저·기말
_VERDICT_ROW = _SUM_ROW + 1                      # 169: 판정문

_TARGET_HEAD = _VERDICT_ROW + 2                  # 171
_TARGET_ROW = _TARGET_HEAD + 1                   # 172: 목표 최저잔액
_SC_COLS = _TARGET_ROW + 1                       # 173
_SC_FIRST = _SC_COLS + 1                         # 174..176

# 목표 최저잔액 입력칸 — B열(요일용, 좁음)을 피해 C열에 둔다
_TARGET_CELL = f"$C${_TARGET_ROW}"
# 시작잔액·④용 숨김 도우미는 J·K열 (G·H는 ② 실지출·차이 열로 사용)
_START_CELL = f"$K${_DAY_COLS}"


def _font(bold=False, size=10, color="000000"):
    return Font(name="맑은 고딕", bold=bold, size=size, color=color)


def _put(ws, row, col, value, *, bold=False, size=10, color="000000",
         fill=None, fmt=None, align=None, border=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = _font(bold, size, color)
    if fill is not None:
        cell.fill = fill
    if fmt:
        cell.number_format = fmt
    if align:
        cell.alignment = Alignment(horizontal=align, vertical="center",
                                   wrap_text=(align == "left"))
    if border:
        cell.border = _THIN
    return cell


def _setup_print(ws, last_row: int, last_col: int = 9) -> None:
    """A4 세로 한 장 폭에 맞는 인쇄 설정 (프린트 시 빈칸 없이 깔끔하게)."""
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.worksheet.properties import PageSetupProperties
    ws.print_area = f"A1:{get_column_letter(last_col)}{last_row}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = 9          # A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins = PageMargins(left=0.35, right=0.35, top=0.5, bottom=0.5)


def _section(ws, row, text):
    for c in range(1, 10):
        cell = ws.cell(row=row, column=c)
        cell.fill = _HEAD_FILL
        cell.border = _THIN
    _put(ws, row, 1, text, bold=True, color="FFFFFF", size=11)


def create_management_workbook(report: dict, out_path: Path) -> Path:
    """경영보고 시트만 담은 워크북 (라이브 템플릿이 없을 때의 대체용)."""
    wb = Workbook()
    wb.remove(wb.active)
    build_management_sheet(wb, report)
    build_ceo_sheet(wb, report)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_workbook(wb, out_path)
    wb.close()
    return out_path


def build_management_sheet(wb, report: dict):
    """'경영보고' 시트를 주어진 워크북의 맨 앞에 만든다.

    섹션 순서(2026-09-23 사용자 요청): ① 현황 → ② 지출예정(수정) →
    ③ 입금예정(수정) → ④ 4주 일별 흐름 → ⑤ 필요 추가 입금 → ⑥ 메모.
    노란 칸(반영률 F12·② 지급일·금액·③ 확정입금 일자·금액·목표잔액)을
    고치면 ④와 라이브 시트(SUMIFS 연동)까지 즉시 재계산된다.
    """
    meta = report["meta"]
    forecast = report["forecast"]
    base_date: date = meta["base_date"]
    daily_by_date = {r["일자"]: r for r in forecast.get("daily", [])}
    weekday_avg = forecast.get("weekday_avg", {})
    rate = forecast.get("rate", 0.8)
    actual_until = forecast.get("actual_until")
    start_balance = forecast.get("start_balance")
    if start_balance is None:
        start_balance = report.get("total_balance") or 0

    if SHEET_NAME in wb.sheetnames:
        wb.remove(wb[SHEET_NAME])
    ws = wb.create_sheet(SHEET_NAME, 0)
    for c, w in zip(range(1, 12), (13, 6, 15, 40, 16, 14, 14, 12, 9,
                                   12, 12)):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.column_dimensions["J"].hidden = True
    ws.column_dimensions["K"].hidden = True

    week_end = base_date + timedelta(days=6)
    _put(ws, 1, 1, f"주간 자금 경영보고 — {meta.get('company', '')}",
         bold=True, size=14, color=_NAVY)
    _put(ws, 2, 1, f"기준주 {base_date} (월) ~ {week_end} (일) · "
                   f"작성 {meta.get('run_at', '')} · "
                   f"실행일~차주 금요일만 표시 (그 밖의 일자 행은 숨김 — "
                   f"행 숨기기 해제로 열람 가능)",
         size=9, color="555555")
    _put(ws, 3, 1, "노란 칸(입금 반영률 F12·② 지출 지급일·금액·③ 확정입금·"
                   "목표 최저잔액)을 고치면 이 시트의 ④ 일별 흐름과 라이브 "
                   "시트 전체가 즉시 다시 계산됩니다. ② 지출예정에서 "
                   "실지출과 차이 나는 행(주황)은 확인(I열) 드롭다운으로 "
                   "표시하세요.",
         size=9, color="B36B00")

    # ① 현재 자금 현황 -----------------------------------------------------
    _section(ws, 5, "① 현재 자금 현황")
    labels = report.get("account_labels", {})
    last_dates = report.get("account_last_dates", {})
    balances = sorted(report.get("balances", {}).items())
    # 계좌 행은 6~11로 고정하고 총잔액은 항상 12행 — 아래 표들의 행
    # 위치(수식 참조 구간)가 계좌 수와 무관하게 일정해진다 (2026-09-23)
    for i, (key, amount) in enumerate(balances[:_ACC_MAX]):
        r = _ACC_FIRST + i
        _put(ws, r, 1, labels.get(key) or account_label(*key), border=True)
        _put(ws, r, 3, round(amount or 0), fmt="#,##0", border=True)
        last = last_dates.get(key)
        _put(ws, r, 4, f"최종 거래일 {last}" if last else "", size=9,
             color="808080")
    _put(ws, _TOTAL_ROW, 1, "총잔액", bold=True, border=True)
    _put(ws, _TOTAL_ROW, 3, f"=SUM(C{_ACC_FIRST}:C{_TOTAL_ROW - 1})",
         bold=True, fmt="#,##0", border=True)
    # 입금 반영률은 총잔액 행 옆(F12) — 라이브·수식이 모두 이 칸을 본다
    _put(ws, _TOTAL_ROW, 5, "입금 반영률", bold=True)
    _put(ws, _TOTAL_ROW, 6, rate, fill=_EDIT_FILL, fmt="0%", align="center",
         border=True)
    from openpyxl.worksheet.datavalidation import DataValidation
    rate_options = sorted(report.get("receipt_rates")
                          or [0.6, 0.7, 0.8, 0.9, 1.0])
    rate_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(f"{int(round(r * 100))}%"
                                for r in rate_options) + '"',
        allow_blank=True)
    rate_dv.error = "목록에 있는 반영률만 선택할 수 있습니다."
    rate_dv.showErrorMessage = True
    ws.add_data_validation(rate_dv)
    rate_dv.add(_RATE_CELL.replace("$", ""))

    holidays = report.get("holidays") or {}
    intraday = forecast.get("intraday") or {}
    # 실행일~차주 금요일 밖의 일자 행은 숨긴다 (2026-09-19 사용자 요청).
    # 값·수식은 그대로 두므로 4주 합계·시나리오는 전체 기간으로 계산된다.
    w_start, w_end = exec_window(meta.get("run_date") or base_date)
    table_end = base_date + timedelta(days=_DAY_COUNT - 1)
    hide_window = w_start <= table_end and w_end >= base_date

    # ② 반영된 지출예정 전체 (수정 가능 + 실지출 대조·확인란).
    # 2026-09-23 사용자 요청으로 현황 바로 다음에 둔다 — 여기서
    # 지급일·금액을 고치면 ④ 일별 흐름과 라이브 전 시트가 재계산
    _section(ws, _EXP_HEAD, "② 반영된 지출예정 (실행일~차주 금요일 표시) — "
                            "지급일·금액(노란 칸)을 고치면 아래 ④ 일별 "
                            "흐름과 라이브 시트 전체가 다시 계산됩니다 · "
                            "실지출(G)을 적으면 차이(H) 자동 계산 · "
                            "확인(I)에서 '보류'를 고른 행은 계획에서 제외")
    for c, head in enumerate(("지급일", "요일", "구분", "내용", "금액",
                              "지급방법", "실지출(은행 확인)", "차이(잔여)",
                              "확인"), start=1):
        _put(ws, _EXP_COLS, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    intraday_chk = (report.get("intraday_check")
                    or forecast.get("intraday") or {})
    check_by_id = {det.get("요청ID"): det
                   for det in (intraday_chk.get("대조내역") or [])
                   if det.get("요청ID")}
    # 확인(I) 드롭다운: '적용'(기본 — 빈칸도 적용) / '보류'(계획 제외).
    # 2026-09-23 사용자 요청 — '보류' 행은 ④와 라이브의 SUMIFS 조건
    # ("<>보류")에서 빠져 그 금액이 계획에 반영되지 않는다
    confirm_dv = DataValidation(type="list",
                                formula1=f'"{EXP_APPLY},{EXP_HOLD}"',
                                allow_blank=True)
    confirm_dv.error = f"'{EXP_APPLY}' 또는 '{EXP_HOLD}'만 " \
                       "선택할 수 있습니다."
    confirm_dv.showErrorMessage = True
    ws.add_data_validation(confirm_dv)
    row = _EXP_FIRST
    for item in report.get("week_expenses", []):
        if row > _EXP_LAST:
            break
        d = item.get("일자")
        # 창 밖 지급일 행도 숨긴다 — 값은 남아 ②·합계 계산에는 그대로 반영
        if hide_window and isinstance(d, date):
            dd = d.date() if isinstance(d, datetime) else d
            ws.row_dimensions[row].hidden = not (w_start <= dd <= w_end)
        # 주말·공휴일 지급일은 붉은 글자 (직접 고친 날짜는 색 유지)
        off = isinstance(d, date) and (d.weekday() >= 5 or d in holidays)
        day_color = "C00000" if off else "000000"
        _put(ws, row, 1,
             datetime.combine(d, dtime()) if isinstance(d, date) else d,
             fmt="yyyy-mm-dd", fill=_EDIT_FILL, border=True, color=day_color)
        _put(ws, row, 2, f'=IF(A{row}="","",MID("월화수목금토일",'
                         f'WEEKDAY(A{row},2),1))', align="center", border=True,
             color=day_color)
        _put(ws, row, 3, item.get("구분") or "", border=True)
        _put(ws, row, 4, item.get("내용") or "", border=True, align="left")
        _put(ws, row, 5, round(item.get("금액") or 0), fmt="#,##0",
             fill=_EDIT_FILL, border=True)
        _put(ws, row, 6, item.get("지급방법") or "", align="center",
             border=True)
        # 실지출(G): 당일 대조(intraday) 결과가 있으면 미리 채우고, 없는
        # 행도 은행 확인 후 수기로 적을 수 있는 노란 입력칸 (2026-09-23
        # 사용자 요청). G를 적으면 차이(H)가 자동 계산되고, 차이 나는
        # 행은 주황 강조. 확인(I)은 모든 행에서 적용/보류 선택 가능
        det = check_by_id.get(item.get("요청ID"))
        mismatch = det is not None and det.get("상태") != "집행 확인"
        _put(ws, row, 7,
             round(det.get("집행액") or 0) if det is not None else "",
             fmt="#,##0", border=True,
             fill=_DIFF_FILL if mismatch else _EDIT_FILL)
        _put(ws, row, 8, f'=IF(OR(G{row}="",E{row}=""),"",E{row}-G{row})',
             fmt="#,##0", border=True,
             fill=_DIFF_FILL if mismatch else None)
        _put(ws, row, 9, "", border=True, fill=_EDIT_FILL, align="center")
        confirm_dv.add(f"I{row}")
        row += 1
    exp_next_row = row
    # 예비 행(숨김)도 바로 쓸 수 있게 입력칸·수식·드롭다운을 깔아 둔다 —
    # 행 숨기기 해제 후 지급일·내용·금액을 적으면 곧바로 계획에 반영된다
    for r in range(exp_next_row, _EXP_LAST + 1):
        _put(ws, r, 1, "", fmt="yyyy-mm-dd", fill=_EDIT_FILL, border=True)
        _put(ws, r, 2, f'=IF(A{r}="","",MID("월화수목금토일",'
                       f'WEEKDAY(A{r},2),1))', align="center", border=True)
        for c in (3, 4, 6):
            _put(ws, r, c, "", border=True)
        _put(ws, r, 5, "", fmt="#,##0", fill=_EDIT_FILL, border=True)
        _put(ws, r, 7, "", fmt="#,##0", fill=_EDIT_FILL, border=True)
        _put(ws, r, 8, f'=IF(OR(G{r}="",E{r}=""),"",E{r}-G{r})',
             fmt="#,##0", border=True)
        _put(ws, r, 9, "", border=True, fill=_EDIT_FILL, align="center")
        confirm_dv.add(f"I{r}")
    _put(ws, _EXP_TOTAL, 4, "합계(숨긴 행 포함 4주 전체 · 보류 제외)",
         bold=True, align="center")
    _put(ws, _EXP_TOTAL, 5,
         f"=SUMIFS(E{_EXP_FIRST}:E{_EXP_LAST},"
         f"I{_EXP_FIRST}:I{_EXP_LAST},{_NOT_HOLD})",
         bold=True, fmt="#,##0")
    # 머리글에 자동 필터 — 지급일·구분별로 골라 볼 수 있다
    ws.auto_filter.ref = f"A{_EXP_COLS}:I{_EXP_LAST}"

    # ③ 반영된 입금예정 (표시·대조용, 2026-09-22 사용자 요청) --------------
    _section(ws, _INC_HEAD, "③ 반영된 입금예정 (실행일~차주 금요일) — "
                            "예상은 반영률(F12) 연동 · 실입금은 은행 확인 값")
    for c, head in enumerate(("입금일", "요일", "구분", "내용", "예상금액",
                              "실입금(은행 확인)", "차이"), start=1):
        _put(ws, _INC_COLS, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    run_date = meta.get("run_date") or base_date
    today_actual = forecast.get("today_actual") or {}
    adj_in_by_date: dict = {}
    for adj in report.get("adjustments") or []:
        if (adj.get("조정입금") or 0) > 0:
            adj_in_by_date.setdefault(adj.get("일자"), []).append(adj)

    def _inc_row(r, d, gubun, naeyong, expect, actual, editable=False):
        off = d is not None and (d.weekday() >= 5 or d in holidays)
        color = "C00000" if off else "000000"
        edit = _EDIT_FILL if editable else None
        if d is not None:
            _put(ws, r, 1, datetime.combine(d, dtime()), fmt="yyyy-mm-dd",
                 border=True, color=color, fill=edit)
            _put(ws, r, 2, WEEKDAY_KO[d.weekday()], align="center",
                 border=True, color=color)
        _put(ws, r, 3, gubun, border=True)
        _put(ws, r, 4, naeyong, border=True, align="left")
        if expect is not None:
            _put(ws, r, 5, expect, fmt="#,##0", border=True, fill=edit)
        else:
            _put(ws, r, 5, "", border=True)
        if actual is not None:
            _put(ws, r, 6, round(actual), fmt="#,##0", border=True,
                 fill=_ACT_FILL)
        else:
            _put(ws, r, 6, "", border=True)
        _put(ws, r, 7, f'=IF(OR(F{r}="",E{r}=""),"",F{r}-E{r})',
             fmt="#,##0", border=True)

    inc_row = _INC_FIRST
    d = w_start
    while d <= w_end and inc_row <= _INC_LAST:
        offset = (d - base_date).days
        day_row = _DAY_FIRST + offset if 0 <= offset < _DAY_COUNT else None
        expect = (f"=ROUND(J{day_row}*{_RATE_CELL},0)"
                  if day_row is not None else 0)
        actual = (today_actual.get("온라인")
                  if d == run_date and today_actual else None)
        _inc_row(inc_row, d, "온라인 예상", "12주 요일평균 × 반영률",
                 expect, actual)
        inc_row += 1
        for adj in adj_in_by_date.get(d, []):
            if inc_row > _INC_LAST:
                break
            _inc_row(inc_row, d, "확정입금", adj.get("내용") or "",
                     round(adj.get("조정입금") or 0), None, editable=True)
            inc_row += 1
        if (d == run_date and today_actual
                and (today_actual.get("기타입금") or 0) > 0
                and inc_row <= _INC_LAST):
            _inc_row(inc_row, d, "기타 실입금", "계획 외 입금(은행 확인)",
                     None, today_actual.get("기타입금"))
            inc_row += 1
        d += timedelta(days=1)
    # 창 밖(차주 금요일 이후~4주 끝) 확정입금도 표에 담는다(행 숨김) —
    # ②의 K열과 라이브가 이 표 전체를 SUMIFS로 참조하므로, 여기 있어야
    # 그 날짜의 확정입금이 계획에 반영되고 일자·금액 수정도 이어진다
    horizon = base_date + timedelta(days=_DAY_COUNT - 1)
    for adj_d in sorted(k for k in adj_in_by_date
                        if k is not None and w_end < k <= horizon):
        for adj in adj_in_by_date.get(adj_d, []):
            if inc_row > _INC_LAST:
                break
            _inc_row(inc_row, adj_d, "확정입금", adj.get("내용") or "",
                     round(adj.get("조정입금") or 0), None, editable=True)
            ws.row_dimensions[inc_row].hidden = True
            inc_row += 1
    for hr in range(inc_row, _INC_LAST + 1):
        ws.row_dimensions[hr].hidden = True
    _put(ws, _INC_TOTAL, 4, "합계(표시 구간)", bold=True, align="center")
    _put(ws, _INC_TOTAL, 5, f"=SUM(E{_INC_FIRST}:E{_INC_LAST})",
         bold=True, fmt="#,##0")
    _put(ws, _INC_TOTAL, 6, f"=SUM(F{_INC_FIRST}:F{_INC_LAST})",
         bold=True, fmt="#,##0")

    # ④ 향후 4주 일별 자금 흐름 --------------------------------------------
    _section(ws, _DAY_HEAD, "④ 향후 4주 일별 자금 흐름 — ② 지출·③ 입금 "
                            "수정과 반영률(F12)에 즉시 연동 "
                            "(실행일~차주 금요일만 표시 · 계산은 4주 전체)")
    for c, head in enumerate(("일자", "요일", "입금", "지출", "예상잔액",
                              "지출 내역"), start=1):
        _put(ws, _DAY_COLS, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    for c in (7, 8, 9):     # '지출 내역' 머리글을 F~I 폭으로 병합
        _put(ws, _DAY_COLS, c, "", fill=_HEAD_FILL, border=True)
    ws.merge_cells(start_row=_DAY_COLS, start_column=6,
                   end_row=_DAY_COLS, end_column=9)
    _put(ws, _DAY_COLS, 11, round(start_balance), fmt="#,##0")  # 시작잔액

    def _detail_formula(row, prefix=""):
        """그 일자에 반영된 ② 지출 항목을 '내용 금액' 형태로 나열한다
        (2026-09-23 사용자 요청 — '상태' 대신 내역·금액 확인).
        ②의 지급일·금액 수정을 그대로 따라오고, 보류 행은 뺀다.
        잔액이 음수면 '⚠ 잔액 부족'을 붙인다. TEXTJOIN이 없는 구형
        엑셀에서는 IFERROR로 부족 표시만 남긴다(배열 수식으로 저장)."""
        a = f"$A${_EXP_FIRST}:$A${_EXP_LAST}"
        dd = f"$D${_EXP_FIRST}:$D${_EXP_LAST}"
        e = f"$E${_EXP_FIRST}:$E${_EXP_LAST}"
        ii = f"$I${_EXP_FIRST}:$I${_EXP_LAST}"
        head = f'"{prefix}"&IF(E{row}<0,"⚠ 잔액 부족 · ","")'
        core = (f'{head}&_xlfn.TEXTJOIN(" · ",TRUE,IF(({a}=$A{row})*({e}<>0)'
                f'*({ii}<>"{EXP_HOLD}"),{dd}&" "&TEXT({e},"#,##0"),""))')
        return (f'=IFERROR({core},'
                f'"{prefix}"&IF(E{row}<0,"⚠ 잔액 부족",""))')

    def _detail_cell(row, value, **kw):
        if isinstance(value, str) and value.startswith("=IFERROR"):
            # TEXTJOIN(IF(배열)) — 배열 수식으로 저장해야 엑셀·LibreOffice
            # 모두 항목 나열을 계산한다 (일반 수식이면 #VALUE!)
            from openpyxl.worksheet.formula import ArrayFormula
            value = ArrayFormula(f"F{row}", value)
        cell = _put(ws, row, 6, value, border=True, **kw)
        for c in (7, 8, 9):
            _put(ws, row, c, "", border=True)
        ws.merge_cells(start_row=row, start_column=6,
                       end_row=row, end_column=9)
        if cell is not None:
            cell.alignment = Alignment(horizontal="left",
                                       vertical="center", wrap_text=True)
        return cell

    for i in range(_DAY_COUNT):
        row = _DAY_FIRST + i
        d = base_date + timedelta(days=i)
        if hide_window:
            ws.row_dimensions[row].hidden = not (w_start <= d <= w_end)
        src = daily_by_date.get(d, {})
        is_actual = (actual_until is not None and d <= actual_until) \
            or bool(src.get("당일실적"))
        # 주말·공휴일은 일자·요일을 붉은 글자로 (2026-09-20 사용자 요청)
        day_color = "C00000" if (d.weekday() >= 5 or d in holidays) \
            else "000000"
        _put(ws, row, 1, datetime.combine(d, dtime()), fmt="yyyy-mm-dd",
             border=True, color=day_color)
        _put(ws, row, 2, WEEKDAY_KO[d.weekday()], align="center", border=True,
             color=day_color)
        # 숨김 도우미: J=요일별 온라인 평균, K=확정·기타입금(수식 참조용)
        # 공휴일은 은행·정산이 쉬므로 예상입금 0 (2026-09-20 사용자 결정)
        _put(ws, row, 10,
             0 if d in holidays else round(weekday_avg.get(d.weekday(), 0)),
             fmt="#,##0")
        # K: 계획 행은 ③ 확정입금 표를 SUMIFS로 참조 — ③의 일자·금액을
        # 고치면 ②와 (연동된) 라이브까지 즉시 재계산된다 (2026-09-23).
        # 실적 행은 실제 값, 이월일은 전일 미도착 확정입금을 더한다
        _k_sumifs = (f"=SUMIFS($E${_INC_FIRST}:$E${_INC_LAST},"
                     f"$A${_INC_FIRST}:$A${_INC_LAST},A{row},"
                     f"$C${_INC_FIRST}:$C${_INC_LAST},\"확정입금\")")
        if is_actual:
            _put(ws, row, 11, round(src.get("확정·기타입금") or 0),
                 fmt="#,##0")
        elif intraday and d == intraday.get("이월일"):
            _put(ws, row, 11,
                 _k_sumifs + f"+{round(intraday.get('_이월확정') or 0)}",
                 fmt="#,##0")
        else:
            _put(ws, row, 11, _k_sumifs, fmt="#,##0")
        if is_actual:
            inflow = (src.get("온라인 예상입금") or 0) \
                + (src.get("확정·기타입금") or 0)
            outflow = (src.get("팀별 송금예정") or 0) \
                + (src.get("카드결제") or 0) + (src.get("자동이체") or 0) \
                + (src.get("기타지출") or 0)
            _put(ws, row, 3, round(inflow), fmt="#,##0", fill=_ACT_FILL,
                 border=True)
            _put(ws, row, 4, round(outflow), fmt="#,##0", fill=_ACT_FILL,
                 border=True)
            _detail_cell(row, "실적(은행 확인)", size=9, color="808080")
        elif intraday and d == intraday.get("이월일"):
            # 익일: 전일 미집행 이월분을 SUMIFS에 더한다 (③ 표의 전일
            # 항목은 실적 마감으로 닫혀 이 값으로만 반영된다)
            carried = round(sum((intraday.get("남은계획") or {}).values())
                            + (intraday.get("_이월확정") or 0) * 0
                            + (intraday.get("_이월조정지출") or 0))
            _put(ws, row, 3, f"=ROUND(J{row}*{_RATE_CELL},0)+K{row}",
                 fmt="#,##0", border=True)
            _put(ws, row, 4,
                 f"=SUMIFS($E${_EXP_FIRST}:$E${_EXP_LAST},"
                 f"$A${_EXP_FIRST}:$A${_EXP_LAST},A{row},"
                 f"$I${_EXP_FIRST}:$I${_EXP_LAST},{_NOT_HOLD})+{carried}",
                 fmt="#,##0", border=True)
            _detail_cell(row, _detail_formula(
                row, prefix="전일 미집행 이월 포함 · "), size=9)
        else:
            _put(ws, row, 3, f"=ROUND(J{row}*{_RATE_CELL},0)+K{row}",
                 fmt="#,##0", border=True)
            _put(ws, row, 4, f"=SUMIFS($E${_EXP_FIRST}:$E${_EXP_LAST},"
                             f"$A${_EXP_FIRST}:$A${_EXP_LAST},A{row},"
                             f"$I${_EXP_FIRST}:$I${_EXP_LAST},{_NOT_HOLD})",
                 fmt="#,##0", border=True)
            _detail_cell(row, _detail_formula(row), size=9)
        prev = _START_CELL if i == 0 else f"E{row - 1}"
        _put(ws, row, 5, f"={prev}+C{row}-D{row}", fmt="#,##0", border=True)
    ws.conditional_formatting.add(
        f"E{_DAY_FIRST}:E{_DAY_LAST}",
        CellIsRule(operator="lessThan", formula=["0"], fill=_RED_FILL))
    # 실행일~차주 금요일 구간을 하나의 붉은 상자로 묶는다. 내역 칸은
    # F:I 병합이라 저장 시 openpyxl이 앵커(F) 테두리를 병합 범위의
    # 바깥 모서리로 재구성한다 — 오른쪽·위·아래 모서리를 앵커에 건다
    first = _DAY_FIRST + max(0, min((w_start - base_date).days,
                                    _DAY_COUNT - 1))
    last = _DAY_FIRST + max(0, min((w_end - base_date).days, _DAY_COUNT - 1))
    outline_week_box(ws, first, last, 1, 5)
    from copy import copy as _copy
    _red_side = Side(style="medium", color="C00000")
    for r in range(first, last + 1):
        anchor = ws.cell(row=r, column=6)
        b = _copy(anchor.border)
        b.right = _red_side
        if r == first:
            b.top = _red_side
        if r == last:
            b.bottom = _red_side
        anchor.border = b
        # col5 오른쪽에 생긴 상자 안쪽 선은 지운다
        e = ws.cell(row=r, column=5)
        eb = _copy(e.border)
        eb.right = Side(style="thin", color="BBBBBB")
        e.border = eb
    _put(ws, _SUM_ROW, 1, "4주 최저 잔액", bold=True)
    _put(ws, _SUM_ROW, 3, f"=MIN(E{_DAY_FIRST}:E{_DAY_LAST})", bold=True,
         fmt="#,##0")
    _put(ws, _SUM_ROW, 4, "4주 예상 기말잔액", bold=True, align="left")
    _put(ws, _SUM_ROW, 5, f"=E{_DAY_LAST}", bold=True, fmt="#,##0")
    _put(ws, _VERDICT_ROW, 1,
         f'=IF(C{_SUM_ROW}>=0,"향후 4주 부족분 없음 — 계획대로 집행 '
         f'가능합니다.","향후 4주 최대 부족 "&TEXT(-C{_SUM_ROW},"#,##0")'
         f'&"원 — 지출 일정 조정 또는 자금 조치가 필요합니다.")', bold=True)

    # ⑤ 안정을 위한 필요 추가 입금 (향후 4주) ------------------------------
    _section(ws, _TARGET_HEAD, "⑤ 안정을 위한 필요 추가 입금 (향후 4주)")
    _put(ws, _TARGET_ROW, 1, "목표 최저잔액", bold=True)
    # 금액 칸은 좁은 B열(요일용)을 피해 C열부터 쓴다 — B열에 두면
    # 8자리 금액이 #####로 가려진다 (2026-09-20 사용자 보고)
    _put(ws, _TARGET_ROW, 3, report.get("stability_target") or 0,
         fill=_EDIT_FILL, fmt="#,##0", border=True)
    _put(ws, _TARGET_ROW, 4, "예: 0원(적자 없음) 또는 안전하게 유지하고 "
                             "싶은 잔액을 입력하세요.", size=9,
         color="808080", align="left")
    for c, head in ((1, "반영률"), (2, None), (3, "4주 기말잔액"),
                    (4, "4주 최저잔액"), (5, "자금부족 예상일"),
                    (6, "필요 추가 입금")):
        _put(ws, _SC_COLS, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    scenarios = forecast.get("rate_scenarios", {})
    r = _SC_FIRST
    base_need_row = None
    for sc_rate in (0.8, 0.9, 1.0):
        sc = scenarios.get(sc_rate)
        if not sc:
            continue
        if base_need_row is None:
            base_need_row = r
        _put(ws, r, 1, sc_rate, fmt="0%", align="center", border=True)
        _put(ws, r, 3, round(sc.get("4주 기말잔액") or 0), fmt="#,##0",
             border=True)
        _put(ws, r, 4, round(sc.get("4주 최저잔액") or 0), fmt="#,##0",
             border=True)
        shortage = sc.get("자금부족 예상일")
        _put(ws, r, 5, str(shortage) if shortage else "없음", align="center",
             border=True)
        _put(ws, r, 6, f"=MAX(0,{_TARGET_CELL}-D{r})", fmt="#,##0",
             border=True, bold=True)
        r += 1
    need = f"F{base_need_row}" if base_need_row else "0"
    _put(ws, r, 1, "주당 추가 입금 목표", bold=True)
    _put(ws, r, 3, f"=ROUND({need}/4,0)", bold=True, fmt="#,##0")
    _put(ws, r, 4, "영업일당(주 5일 기준)", bold=True, align="left")
    _put(ws, r, 5, f"=ROUND({need}/20,0)", bold=True, fmt="#,##0")

    # ⑥ 건강사업팀 전달 메모 -----------------------------------------------
    memo_row = r + 2
    _section(ws, memo_row, "⑥ 건강사업팀 전달 메모 (자동 작성)")
    ws.merge_cells(start_row=memo_row + 1, start_column=1,
                   end_row=memo_row + 3, end_column=6)
    memo = _put(
        ws, memo_row + 1, 1,
        f'=IF({need}<=0,'
        f'"현재 반영률 기준 향후 4주 자금은 목표 최저잔액("'
        f'&TEXT({_TARGET_CELL},"#,##0")&"원)을 유지합니다. '
        f'추가 입금 목표 없이 계획대로 진행 가능합니다.",'
        f'"향후 4주 최저 예상잔액이 목표("&TEXT({_TARGET_CELL},"#,##0")'
        f'&"원) 대비 "&TEXT({need},"#,##0")&"원 부족합니다. '
        f'4주간 총 "&TEXT({need},"#,##0")&"원, 주당 약 "'
        f'&TEXT(ROUND({need}/4,0),"#,##0")&"원의 추가 입금(매출 회수)이 '
        f'필요합니다. 건강사업팀에 목표 공유를 권장합니다.")')
    memo.alignment = Alignment(horizontal="left", vertical="top",
                               wrap_text=True)
    ws.freeze_panes = "A4"

    # 인쇄 최적화: 지출표의 빈 예비행은 3행만 남기고 숨긴다 (수식 구간
    # $47:$140은 유지 — 필요하면 행 숨기기 해제 후 추가 입력 가능)
    for hr in range(exp_next_row + 3, _EXP_LAST + 1):
        ws.row_dimensions[hr].hidden = True
    _setup_print(ws, memo_row + 4)

    # '정기지출 체크' 시트는 만들지 않는다 (2026-09-23 사용자 확정:
    # 정기지출 관련은 결과파일에 넣지 않고, 누락 의심만 확인필요
    # 파일의 '정기지출누락' 시트에서 확인받는다)
    return ws


def build_ceo_sheet(wb, report: dict):
    """'대표보고' 시트 — 경영보고 셀을 수식으로 참조하는 한 장 요약.

    2026-09-23 사용자 요청: PDF 대신 같은 파일 안의 시트로 만들고,
    경영보고에서 일자·금액·반영률을 고치면 여기도 즉시 따라오게 하며,
    그대로 인쇄하면 A4 한 장에 맞게 나온다.
    """
    from common import week_monday

    meta = report["meta"]
    forecast = report["forecast"]
    base_date: date = meta["base_date"]
    run_date = meta.get("run_date") or base_date
    holidays = report.get("holidays") or {}
    M = f"'{SHEET_NAME}'!"

    if CEO_SHEET in wb.sheetnames:
        wb.remove(wb[CEO_SHEET])
    pos = 1 if SHEET_NAME in wb.sheetnames else 0
    ws = wb.create_sheet(CEO_SHEET, pos)
    for c, w in zip(range(1, 6), (24, 9, 17, 17, 17)):
        ws.column_dimensions[get_column_letter(c)].width = w

    def _sec(row, text):
        for c in range(1, 6):
            cell = ws.cell(row=row, column=c)
            cell.fill = _HEAD_FILL
            cell.border = _THIN
        _put(ws, row, 1, text, bold=True, color="FFFFFF", size=11)

    _put(ws, 1, 1, f"{meta.get('company', '')} 주간 자금계획 보고",
         bold=True, size=15, color=_NAVY)
    _put(ws, 2, 1,
         f'="기준일 {base_date} · 작성 {meta.get("run_at", "")} · '
         f'입금 반영률 "&TEXT({M}{_RATE_CELL},"0%")'
         f'&" (경영보고 시트와 실시간 연동)"',
         size=9, color="555555")

    _sec(4, "핵심 요약")
    day_a = f"{M}$A${_DAY_FIRST}:$A${_DAY_LAST}"
    day_e = f"{M}$E${_DAY_FIRST}:$E${_DAY_LAST}"
    labels = [
        ("현재 전체 계좌잔액", f"={M}C{_TOTAL_ROW}", None),
        ("4주 예상 기말잔액", f"={M}E{_DAY_LAST}", None),
        ("4주 최저 예상잔액", f"={M}C{_SUM_ROW}",
         f'=TEXT(INDEX({day_a},MATCH({M}C{_SUM_ROW},'
         f'{day_e},0)),"m/d 예상")'),
        ("향후 4주 확정지출", f"={M}E{_EXP_TOTAL}", None),
        ("카드 결제 예정액(4주)",
         f'=SUMIFS({M}$E${_EXP_FIRST}:$E${_EXP_LAST},'
         f'{M}$F${_EXP_FIRST}:$F${_EXP_LAST},"법인카드",'
         f'{M}$I${_EXP_FIRST}:$I${_EXP_LAST},{_NOT_HOLD})', None),
        ("자금부족 예상일",
         f'=IFERROR(TEXT(INDEX({day_a},MATCH(TRUE,'
         f'INDEX({day_e}<0,0),0)),"yyyy-mm-dd"),"없음")', "text"),
        ("확인필요 건수", f"{len(report.get('issues', []))}건", "text"),
        ("자료 미제출 팀",
         ", ".join(report.get("missing_teams", [])) or "없음", "text"),
    ]
    r = 5
    for label, value, extra in labels:
        _put(ws, r, 1, label, bold=True, border=True)
        _put(ws, r, 3, value, border=True,
             fmt=None if extra == "text" else "#,##0")
        if extra and extra != "text":
            _put(ws, r, 4, extra, size=9, color="808080", border=True)
        r += 1
    verdict_row = r + 1
    ws.merge_cells(start_row=verdict_row, start_column=1,
                   end_row=verdict_row, end_column=5)
    v = _put(ws, verdict_row, 1, f"={M}A{_VERDICT_ROW}", bold=True,
             color=_NAVY)
    v.alignment = Alignment(horizontal="left", vertical="center",
                            wrap_text=True)

    # 금주(주말 실행이면 차주) 월~금 일별 전망 — 경영보고 ② 행을 참조
    display_monday = week_monday(run_date)
    if run_date.weekday() >= 5:
        display_monday += timedelta(days=7)
    word = "차주" if display_monday > week_monday(run_date) else "금주"
    day_head = verdict_row + 2
    _sec(day_head, f"{word} 일별 잔액 전망 (월~금) — 반영률·지출 수정과 "
                   "실시간 연동")
    for c, head in enumerate(("일자", "요일", "예상 기말잔액", "상태"),
                             start=1):
        _put(ws, day_head + 1, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    off0 = (display_monday - base_date).days
    for i in range(5):
        rr = day_head + 2 + i
        src_row = _DAY_FIRST + off0 + i
        d = display_monday + timedelta(days=i)
        in_table = 0 <= off0 + i < _DAY_COUNT
        color = "C00000" if (d.weekday() >= 5 or d in holidays) else "000000"
        _put(ws, rr, 1, f"={M}A{src_row}" if in_table else
             datetime.combine(d, dtime()), fmt="yyyy-mm-dd", border=True,
             color=color)
        _put(ws, rr, 2, WEEKDAY_KO[d.weekday()], align="center",
             border=True, color=color)
        _put(ws, rr, 3, f"={M}E{src_row}" if in_table else "",
             fmt="#,##0", border=True)
        _put(ws, rr, 4, f'=IF(C{rr}<0,"부족","")', align="center",
             border=True, color="C00000")
    ws.conditional_formatting.add(
        f"C{day_head + 2}:C{day_head + 6}",
        CellIsRule(operator="lessThan", formula=["0"], fill=_RED_FILL))

    # 반영률 시나리오 — 경영보고 ⑤ 표(80·90·100%)를 그대로 참조
    sc_head = day_head + 8
    _sec(sc_head, "입금 반영률 시나리오 (80·90·100%) — 필요 추가 입금")
    for c, head in enumerate(("반영률", "", "4주 기말잔액", "4주 최저잔액",
                              "필요 추가 입금"), start=1):
        if head:
            _put(ws, sc_head + 1, c, head, bold=True, color="FFFFFF",
                 fill=_HEAD_FILL, align="center", border=True)
    for i in range(3):
        rr = sc_head + 2 + i
        sr = _SC_FIRST + i
        _put(ws, rr, 1, f"={M}A{sr}", fmt="0%", align="center", border=True)
        _put(ws, rr, 3, f"={M}C{sr}", fmt="#,##0", border=True)
        _put(ws, rr, 4, f"={M}D{sr}", fmt="#,##0", border=True)
        _put(ws, rr, 5, f"={M}F{sr}", fmt="#,##0", border=True, bold=True)
    note_row = sc_head + 6
    _put(ws, note_row, 1,
         f'="· 목표 최저잔액 "&TEXT({M}{_TARGET_CELL},"#,##0")&"원 기준. '
         f'시나리오 값은 실행 시점 계산이며, 반영률·지출 수정은 위 표와 '
         f'경영보고에 즉시 반영됩니다."', size=9, color="808080")
    _put(ws, note_row + 1, 1,
         "· 대외비 항목은 분류·총액으로만 표시됩니다. 상세 내역은 같은 "
         "파일의 경영보고·지출계획_취합 시트를 확인하십시오.",
         size=9, color="808080")

    # A4 세로 한 장에 맞춤 — 그대로 인쇄하면 바로 보고용
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.worksheet.properties import PageSetupProperties
    ws.print_area = f"A1:E{note_row + 1}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = 9              # A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.6, bottom=0.6)
    return ws


def create_combined_workbook(report: dict, template_path: Path,
                             out_path: Path) -> Path:
    """통합 결과 파일 하나를 만든다 (2026-09-23 사용자 요청).

    시트 순서(2026-09-23 사용자 요청: 요약·업데이트운영을 맨 앞으로):
    요약(수정 안내 표 포함) → 업데이트운영(운영 방법) → 경영보고(입력
    기준) → 대표보고(A4 인쇄) → 라이브 시트들. 라이브의 일별
    지출·확정입금 칸은 경영보고 ③·④ 표를 SUMIFS로 참조하므로,
    경영보고에서 일자·금액·반영률(F12)을 고치면 라이브의
    4주일별계획·계좌별시나리오·13주·요약까지 전부 즉시 재계산된다.
    """
    import live_report

    live_report.fill_live_workbook(template_path, report, out_path,
                                   link_sheet=SHEET_NAME)
    wb = load_workbook(out_path)
    try:
        build_management_sheet(wb, report)
        build_ceo_sheet(wb, report)
        front = ["요약", live_report.UPDATE_GUIDE_SHEET,
                 SHEET_NAME, CEO_SHEET]
        wb._sheets.sort(key=lambda sh: (front.index(sh.title)
                                        if sh.title in front
                                        else len(front)))
        wb.active = 0
        save_workbook(wb, out_path)
    finally:
        wb.close()
    return out_path


def verify_combined_workbook(path: Path, base_date: date) -> bool:
    """통합 파일 재열기 검증: 경영보고 수식 + 대표보고 연동 + 라이브."""
    import live_report

    if not verify_management_workbook(path):
        return False
    try:
        wb = load_workbook(path)
    except Exception:
        return False
    try:
        if CEO_SHEET not in wb.sheetnames:
            return False
        ceo = wb[CEO_SHEET]
        if not str(ceo["C5"].value or "").startswith(f"='{SHEET_NAME}'!"):
            return False
        summary = wb["요약"]
        if str(summary["B13"].value or "") != f"='{SHEET_NAME}'!$F$12":
            return False
        # 요약·업데이트운영이 맨 앞 (2026-09-23 사용자 요청)
        if wb.sheetnames[:2] != ["요약", "업데이트운영"]:
            return False
    except Exception:
        return False
    finally:
        wb.close()
    return live_report.verify_live_workbook(path, base_date)


def verify_management_workbook(path: Path) -> bool:
    """재열기 + 핵심 수식 보존 검증."""
    try:
        wb = load_workbook(path)
    except Exception:
        return False
    try:
        if SHEET_NAME not in wb.sheetnames:
            return False
        ws = wb[SHEET_NAME]
        return (str(ws[f"C{_SUM_ROW}"].value or "").startswith("=MIN")
                and str(ws[f"E{_EXP_TOTAL}"].value or "")
                .startswith("=SUM")     # SUMIFS(보류 제외) 합계
                and str(ws[f"E{_DAY_FIRST}"].value or "").startswith("="))
    except Exception:
        return False
    finally:
        wb.close()
