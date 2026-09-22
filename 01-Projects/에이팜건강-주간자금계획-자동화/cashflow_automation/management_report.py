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

from common import WEEKDAY_KO
from excel_report import account_label
from live_report import exec_window, outline_week_box

SHEET_NAME = "주간보고"
CHECK_SHEET = "정기지출 체크"

_NAVY = "1F4E79"
_EDIT_FILL = PatternFill("solid", start_color="FFF2CC")   # 수정 가능 칸
_HEAD_FILL = PatternFill("solid", start_color=_NAVY)
_ACT_FILL = PatternFill("solid", start_color="EFEFEF")    # 실적 구간
_RED_FILL = PatternFill("solid", start_color="FFC7CE")
_DIFF_FILL = PatternFill("solid", start_color="FFE699")   # 계획·실제 차이
_THIN = Border(*(Side(style="thin", color="BBBBBB"),) * 4)

# 일별 흐름 표: 기준일부터 4주(28일)
_DAY_FIRST, _DAY_COUNT = 14, 28
_DAY_LAST = _DAY_FIRST + _DAY_COUNT - 1          # 41
_SUM_ROW = _DAY_LAST + 1                         # 42: 최저·기말
_VERDICT_ROW = _SUM_ROW + 1                      # 43: 판정문

# 입금 예정 표(③): 실행일~차주 금요일 창의 온라인 예상·확정입금 항목과
# 실입금(은행 확인) 대조 (2026-09-22 사용자 요청)
_INC_HEAD = _VERDICT_ROW + 2                     # 45: 섹션 띠
_INC_COLS = _INC_HEAD + 1                        # 46: 열 머리글
_INC_FIRST, _INC_LAST = _INC_COLS + 1, 68        # 47..68
_INC_TOTAL = _INC_LAST + 1                       # 69

# 지출 예정 표의 데이터 행 범위 (SUMIFS가 참조하는 고정 구간)
_EXP_HEAD = _INC_TOTAL + 2                       # 71: 섹션 띠
_EXP_COLS = _EXP_HEAD + 1                        # 72: 열 머리글
_EXP_FIRST, _EXP_LAST = _EXP_COLS + 1, 166       # 73..166
_EXP_TOTAL = _EXP_LAST + 1                       # 167

_TARGET_HEAD = _EXP_TOTAL + 2                    # 169
_TARGET_ROW = _TARGET_HEAD + 1                   # 170: 목표 최저잔액
_SC_COLS = _TARGET_ROW + 1                       # 171
_SC_FIRST = _SC_COLS + 1                         # 172..174

_RATE_CELL = "$F$12"
# 목표 최저잔액 입력칸 — B열(요일용, 좁음)을 피해 C열에 둔다
_TARGET_CELL = f"$C${_TARGET_ROW}"
# 시작잔액·②용 숨김 도우미는 J·K열 (G·H는 ④ 실지출·차이 열로 사용)
_START_CELL = "$K$13"


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


def _fill_recurring_check(wb, report: dict) -> None:
    """'정기지출 체크' 시트: 금주 도래 정기지출의 팀 제출 여부 대조표.

    자동추정을 '제외'로 두고 팀 지출예정 파일 기준으로 운영할 때,
    팀이 빠뜨린 매월 정기지출(누락 의심)을 한눈에 보고 재제출을
    요청할 수 있게 한다.
    """
    meta = report["meta"]
    checks = report.get("recurring_check") or []
    run_date = meta.get("run_date") or meta["base_date"]
    win_start, win_end = exec_window(run_date)

    ws = wb.create_sheet(CHECK_SHEET)
    for c, w in zip(range(1, 8), (12, 6, 28, 14, 12, 27, 30)):
        ws.column_dimensions[get_column_letter(c)].width = w
    _put(ws, 1, 1, "금주 정기지출 체크 — 팀 지출예정 제출 확인",
         bold=True, size=13, color=_NAVY)
    _put(ws, 2, 1, f"확인 구간 {win_start} ~ {win_end} (실행일~차주 금요일) · "
                   "매월 나가던 정기지출이 팀 지출예정 파일에 들어왔는지 "
                   "자동 대조한 결과입니다.", size=9, color="555555")
    missing = [c for c in checks if c.get("누락")]
    if missing:
        _put(ws, 3, 1, f"⚠ 누락 의심 {len(missing)}건 — 해당 팀에 지출예정 "
                       "파일 재제출을 요청하세요.", bold=True, color="C00000")
    elif checks:
        _put(ws, 3, 1, "누락 의심 없음 — 구간 내 정기지출이 모두 팀 계획에 "
                       "반영되어 있거나 자동 반영 중입니다.",
             bold=True, color="1E7145")
    else:
        _put(ws, 3, 1, "이번 구간에 도래하는 정기지출이 없습니다.",
             color="555555")

    head_row = 5
    for c, head in enumerate(("예정일", "요일", "항목", "예상금액(평균)",
                              "관리상태", "팀 지출예정", "확인 결과"),
                             start=1):
        _put(ws, head_row, c, head, bold=True, color="FFFFFF",
             fill=_HEAD_FILL, align="center", border=True)
    holidays = report.get("holidays") or {}
    r = head_row + 1
    for chk in checks:
        d = chk.get("예정일")
        off = d is not None and (d.weekday() >= 5 or d in holidays)
        day_color = "C00000" if off else "000000"
        _put(ws, r, 1, d, fmt="yyyy-mm-dd", border=True, color=day_color)
        _put(ws, r, 2, WEEKDAY_KO[d.weekday()] if d else "",
             align="center", border=True, color=day_color)
        _put(ws, r, 3, chk.get("항목") or "", border=True)
        _put(ws, r, 4, round(chk.get("예상금액") or 0), fmt="#,##0",
             border=True)
        _put(ws, r, 5, chk.get("관리상태") or "", align="center", border=True)
        t_amt, t_date = chk.get("팀제출금액"), chk.get("팀제출일")
        team = (f"있음 · {t_amt:,.0f}원 ({t_date.month}/{t_date.day})"
                if t_amt is not None else "없음")
        _put(ws, r, 6, team, border=True)
        verdict = _put(ws, r, 7, chk.get("판정") or "", border=True,
                       bold=bool(chk.get("누락")))
        if chk.get("누락"):
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = _RED_FILL
            verdict.font = _font(bold=True, color="C00000")
        r += 1
    ws.auto_filter.ref = f"A{head_row}:G{max(r - 1, head_row + 1)}"
    ws.freeze_panes = f"A{head_row + 1}"
    _setup_print(ws, max(r - 1, head_row + 1), last_col=7)


def create_management_workbook(report: dict, out_path: Path) -> Path:
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

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
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
    _put(ws, 3, 1, "노란 칸(입금 반영률·목표 최저잔액·지출 지급일·금액)을 "
                   "고치면 아래 모든 수치가 즉시 다시 계산됩니다. "
                   "④ 지출예정에서 실지출과 차이 나는 행(주황)은 확인(I열) "
                   "드롭다운으로 확인 표시하세요.",
         size=9, color="B36B00")

    # ① 현재 자금 현황 -----------------------------------------------------
    _section(ws, 5, "① 현재 자금 현황")
    labels = report.get("account_labels", {})
    last_dates = report.get("account_last_dates", {})
    balances = sorted(report.get("balances", {}).items())
    r = 6
    for key, amount in balances:
        _put(ws, r, 1, labels.get(key) or account_label(*key), border=True)
        _put(ws, r, 3, round(amount or 0), fmt="#,##0", border=True)
        last = last_dates.get(key)
        _put(ws, r, 4, f"최종 거래일 {last}" if last else "", size=9,
             color="808080")
        r += 1
    total_row = r
    _put(ws, total_row, 1, "총잔액", bold=True, border=True)
    _put(ws, total_row, 3, f"=SUM(C6:C{total_row - 1})", bold=True,
         fmt="#,##0", border=True)

    # ② 향후 4주 일별 자금 흐름 --------------------------------------------
    _section(ws, 12, "② 향후 4주 일별 자금 흐름 "
                     "(실행일~차주 금요일만 표시 · 계산은 4주 전체)")
    _put(ws, 12, 5, "입금 반영률", bold=True, color="FFFFFF")
    _put(ws, 12, 6, rate, fill=_EDIT_FILL, fmt="0%", align="center",
         border=True)
    # 라이브 파일처럼 드롭다운으로 반영률을 고른다 (고르면 즉시 재계산)
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
    for c, head in enumerate(("일자", "요일", "입금", "지출", "예상잔액",
                              "상태"), start=1):
        _put(ws, 13, c, head, bold=True, color="FFFFFF", fill=_HEAD_FILL,
             align="center", border=True)
    _put(ws, 13, 11, round(start_balance), fmt="#,##0")  # K13: 시작잔액(숨김)

    holidays = report.get("holidays") or {}
    intraday = forecast.get("intraday") or {}
    # 실행일~차주 금요일 밖의 일자 행은 숨긴다 (2026-09-19 사용자 요청).
    # 값·수식은 그대로 두므로 4주 합계·시나리오는 전체 기간으로 계산된다.
    w_start, w_end = exec_window(meta.get("run_date") or base_date)
    table_end = base_date + timedelta(days=_DAY_COUNT - 1)
    hide_window = w_start <= table_end and w_end >= base_date

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
        _put(ws, row, 11, round(src.get("확정·기타입금") or 0), fmt="#,##0")
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
            _put(ws, row, 6, "실적", size=9, color="808080", align="center",
                 border=True)
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
                 f"$A${_EXP_FIRST}:$A${_EXP_LAST},A{row})+{carried}",
                 fmt="#,##0", border=True)
            _put(ws, row, 6, f'=IF(E{row}<0,"부족","")', color="C00000",
                 align="center", border=True)
        else:
            _put(ws, row, 3, f"=ROUND(J{row}*{_RATE_CELL},0)+K{row}",
                 fmt="#,##0", border=True)
            _put(ws, row, 4, f"=SUMIFS($E${_EXP_FIRST}:$E${_EXP_LAST},"
                             f"$A${_EXP_FIRST}:$A${_EXP_LAST},A{row})",
                 fmt="#,##0", border=True)
            _put(ws, row, 6, f'=IF(E{row}<0,"부족","")', color="C00000",
                 align="center", border=True)
        prev = _START_CELL if i == 0 else f"E{row - 1}"
        _put(ws, row, 5, f"={prev}+C{row}-D{row}", fmt="#,##0", border=True)
    ws.conditional_formatting.add(
        f"E{_DAY_FIRST}:E{_DAY_LAST}",
        CellIsRule(operator="lessThan", formula=["0"], fill=_RED_FILL))
    # 실행일~차주 금요일 구간을 하나의 붉은 상자로 묶는다
    first = _DAY_FIRST + max(0, min((w_start - base_date).days,
                                    _DAY_COUNT - 1))
    last = _DAY_FIRST + max(0, min((w_end - base_date).days, _DAY_COUNT - 1))
    outline_week_box(ws, first, last, 1, 6)
    _put(ws, _SUM_ROW, 1, "4주 최저 잔액", bold=True)
    _put(ws, _SUM_ROW, 3, f"=MIN(E{_DAY_FIRST}:E{_DAY_LAST})", bold=True,
         fmt="#,##0")
    _put(ws, _SUM_ROW, 4, "4주 예상 기말잔액", bold=True, align="left")
    _put(ws, _SUM_ROW, 5, f"=E{_DAY_LAST}", bold=True, fmt="#,##0")
    _put(ws, _VERDICT_ROW, 1,
         f'=IF(C{_SUM_ROW}>=0,"향후 4주 부족분 없음 — 계획대로 집행 '
         f'가능합니다.","향후 4주 최대 부족 "&TEXT(-C{_SUM_ROW},"#,##0")'
         f'&"원 — 지출 일정 조정 또는 자금 조치가 필요합니다.")', bold=True)

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

    def _inc_row(r, d, gubun, naeyong, expect, actual):
        off = d is not None and (d.weekday() >= 5 or d in holidays)
        color = "C00000" if off else "000000"
        if d is not None:
            _put(ws, r, 1, datetime.combine(d, dtime()), fmt="yyyy-mm-dd",
                 border=True, color=color)
            _put(ws, r, 2, WEEKDAY_KO[d.weekday()], align="center",
                 border=True, color=color)
        _put(ws, r, 3, gubun, border=True)
        _put(ws, r, 4, naeyong, border=True, align="left")
        if expect is not None:
            _put(ws, r, 5, expect, fmt="#,##0", border=True)
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
                     round(adj.get("조정입금") or 0), None)
            inc_row += 1
        if (d == run_date and today_actual
                and (today_actual.get("기타입금") or 0) > 0
                and inc_row <= _INC_LAST):
            _inc_row(inc_row, d, "기타 실입금", "계획 외 입금(은행 확인)",
                     None, today_actual.get("기타입금"))
            inc_row += 1
        d += timedelta(days=1)
    for hr in range(inc_row, _INC_LAST + 1):
        ws.row_dimensions[hr].hidden = True
    _put(ws, _INC_TOTAL, 4, "합계(표시 구간)", bold=True, align="center")
    _put(ws, _INC_TOTAL, 5, f"=SUM(E{_INC_FIRST}:E{_INC_LAST})",
         bold=True, fmt="#,##0")
    _put(ws, _INC_TOTAL, 6, f"=SUM(F{_INC_FIRST}:F{_INC_LAST})",
         bold=True, fmt="#,##0")

    # ④ 반영된 지출예정 전체 (수정 가능 + 실지출 대조·확인란) --------------
    _section(ws, _EXP_HEAD, "④ 반영된 지출예정 (실행일~차주 금요일 표시) — "
                            "지급일·금액을 고치면 ②가 다시 계산됩니다 · "
                            "실지출과 차이 나는 행(주황)은 확인(I열) 선택")
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
    confirm_dv = DataValidation(type="list", formula1='"확인"',
                                allow_blank=True)
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
        # 실지출 대조: 당일 대조(intraday) 결과를 요청ID로 연결한다.
        # 차이 나는 행은 주황으로 강조하고 확인란(I) 드롭다운을 단다
        det = check_by_id.get(item.get("요청ID"))
        if det is not None:
            mismatch = det.get("상태") != "집행 확인"
            fill = _DIFF_FILL if mismatch else None
            _put(ws, row, 7, round(det.get("집행액") or 0), fmt="#,##0",
                 border=True, fill=fill)
            _put(ws, row, 8, f'=IF(G{row}="","",E{row}-G{row})',
                 fmt="#,##0", border=True, fill=fill)
            _put(ws, row, 9, "", border=True,
                 fill=_EDIT_FILL if mismatch else None, align="center")
            if mismatch:
                confirm_dv.add(f"I{row}")
        else:
            for c in (7, 8, 9):
                _put(ws, row, c, "", border=True)
        row += 1
    _put(ws, _EXP_TOTAL, 4, "합계(숨긴 행 포함 4주 전체)", bold=True,
         align="center")
    _put(ws, _EXP_TOTAL, 5, f"=SUM(E{_EXP_FIRST}:E{_EXP_LAST})",
         bold=True, fmt="#,##0")
    # 머리글에 자동 필터 — 지급일·구분별로 골라 볼 수 있다
    ws.auto_filter.ref = f"A{_EXP_COLS}:I{_EXP_LAST}"

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
    for hr in range(row + 3, _EXP_LAST + 1):
        ws.row_dimensions[hr].hidden = True
    _setup_print(ws, memo_row + 4)

    _fill_recurring_check(wb, report)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


def verify_management_workbook(path: Path) -> bool:
    """재열기 + 핵심 수식 보존 검증."""
    try:
        wb = load_workbook(path)
    except Exception:
        return False
    try:
        if SHEET_NAME not in wb.sheetnames \
                or CHECK_SHEET not in wb.sheetnames:
            return False
        ws = wb[SHEET_NAME]
        return (str(ws[f"C{_SUM_ROW}"].value or "").startswith("=MIN")
                and "SUM(" in str(ws[f"E{_EXP_TOTAL}"].value or "")
                and str(ws[f"E{_DAY_FIRST}"].value or "").startswith("="))
    except Exception:
        return False
    finally:
        wb.close()
