# -*- coding: utf-8 -*-
"""주간 자금 경영보고 워크북 (대화형).

기존 고정서식 주간자금계획 파일을 대신하는 보고용 엑셀.
현재 자금 현황 → 이번 주 일별 흐름(부족 여부) → 지출 예정 표 →
안정을 위한 필요 추가 입금 → 건강사업팀 전달 메모 순서로 한 시트에
담고, 노란 칸(반영률·목표잔액·지출 지급일·금액)을 고치면 수식으로
즉시 재계산되게 만든다.
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

SHEET_NAME = "주간보고"

_NAVY = "1F4E79"
_EDIT_FILL = PatternFill("solid", start_color="FFF2CC")   # 수정 가능 칸
_HEAD_FILL = PatternFill("solid", start_color=_NAVY)
_ACT_FILL = PatternFill("solid", start_color="EFEFEF")    # 실적 구간
_RED_FILL = PatternFill("solid", start_color="FFC7CE")
_THIN = Border(*(Side(style="thin", color="BBBBBB"),) * 4)

# 지출 예정 표의 데이터 행 범위 (SUMIFS가 참조하는 고정 구간)
_EXP_FIRST, _EXP_LAST = 26, 88
_DAY_FIRST = 14  # 일별 흐름 표 첫 데이터 행 (7일)
_RATE_CELL = "$F$12"
_TARGET_CELL = "$B$92"


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


def _section(ws, row, text):
    for c in range(1, 7):
        cell = ws.cell(row=row, column=c)
        cell.fill = _HEAD_FILL
        cell.border = _THIN
    _put(ws, row, 1, text, bold=True, color="FFFFFF", size=11)


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
    for c, w in zip(range(1, 9), (13, 6, 15, 40, 15, 12, 12, 12)):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.column_dimensions["G"].hidden = True
    ws.column_dimensions["H"].hidden = True

    week_end = base_date + timedelta(days=6)
    _put(ws, 1, 1, f"주간 자금 경영보고 — {meta.get('company', '')}",
         bold=True, size=14, color=_NAVY)
    _put(ws, 2, 1, f"기준주 {base_date} (월) ~ {week_end} (일) · "
                   f"작성 {meta.get('run_at', '')}", size=9, color="555555")
    _put(ws, 3, 1, "노란 칸(입금 반영률·목표 최저잔액·지출 지급일·금액)을 "
                   "고치면 아래 모든 수치가 즉시 다시 계산됩니다.",
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

    # ② 이번 주 일별 자금 흐름 ---------------------------------------------
    _section(ws, 12, "② 이번 주 일별 자금 흐름")
    _put(ws, 12, 5, "입금 반영률", bold=True, color="FFFFFF")
    _put(ws, 12, 6, rate, fill=_EDIT_FILL, fmt="0%", align="center",
         border=True)
    for c, head in enumerate(("일자", "요일", "입금", "지출", "예상잔액",
                              "상태"), start=1):
        _put(ws, 13, c, head, bold=True, color="FFFFFF", fill=_HEAD_FILL,
             align="center", border=True)
    _put(ws, 13, 8, round(start_balance), fmt="#,##0")  # H13: 시작잔액(숨김)

    for i in range(7):
        row = _DAY_FIRST + i
        d = base_date + timedelta(days=i)
        src = daily_by_date.get(d, {})
        is_actual = actual_until is not None and d <= actual_until
        _put(ws, row, 1, datetime.combine(d, dtime()), fmt="yyyy-mm-dd",
             border=True)
        _put(ws, row, 2, WEEKDAY_KO[d.weekday()], align="center", border=True)
        # 숨김 도우미: G=요일별 온라인 평균, H=확정·기타입금(수식 참조용)
        _put(ws, row, 7, round(weekday_avg.get(d.weekday(), 0)), fmt="#,##0")
        _put(ws, row, 8, round(src.get("확정·기타입금") or 0), fmt="#,##0")
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
        else:
            _put(ws, row, 3, f"=ROUND(G{row}*{_RATE_CELL},0)+H{row}",
                 fmt="#,##0", border=True)
            _put(ws, row, 4, f"=SUMIFS($E${_EXP_FIRST}:$E${_EXP_LAST},"
                             f"$A${_EXP_FIRST}:$A${_EXP_LAST},A{row})",
                 fmt="#,##0", border=True)
            _put(ws, row, 6, f'=IF(E{row}<0,"부족","")', color="C00000",
                 align="center", border=True)
        prev = "$H$13" if i == 0 else f"E{row - 1}"
        _put(ws, row, 5, f"={prev}+C{row}-D{row}", fmt="#,##0", border=True)
    day_last = _DAY_FIRST + 6
    ws.conditional_formatting.add(
        f"E{_DAY_FIRST}:E{day_last}",
        CellIsRule(operator="lessThan", formula=["0"], fill=_RED_FILL))
    _put(ws, 21, 1, "주중 최저 잔액", bold=True)
    _put(ws, 21, 3, f"=MIN(E{_DAY_FIRST}:E{day_last})", bold=True,
         fmt="#,##0")
    _put(ws, 21, 4, "주말(일) 예상 기말잔액", bold=True, align="left")
    _put(ws, 21, 5, f"=E{day_last}", bold=True, fmt="#,##0")
    _put(ws, 22, 1,
         f'=IF(C21>=0,"이번 주 부족분 없음 — 계획대로 집행 가능합니다.",'
         f'"이번 주 최대 부족 "&TEXT(-C21,"#,##0")&"원 — '
         f'지출 일정 조정 또는 자금 조치가 필요합니다.")', bold=True)

    # ③ 이번 주 지출 예정 (수정 가능) --------------------------------------
    _section(ws, 24, "③ 이번 주 지출 예정 — 지급일·금액을 고치면 ②가 "
                     "다시 계산됩니다")
    for c, head in enumerate(("지급일", "요일", "구분", "내용", "금액",
                              "지급방법"), start=1):
        _put(ws, 25, c, head, bold=True, color="FFFFFF", fill=_HEAD_FILL,
             align="center", border=True)
    row = _EXP_FIRST
    for item in report.get("week_expenses", []):
        if row > _EXP_LAST:
            break
        d = item.get("일자")
        _put(ws, row, 1,
             datetime.combine(d, dtime()) if isinstance(d, date) else d,
             fmt="yyyy-mm-dd", fill=_EDIT_FILL, border=True)
        _put(ws, row, 2, f'=IF(A{row}="","",MID("월화수목금토일",'
                         f'WEEKDAY(A{row},2),1))', align="center", border=True)
        _put(ws, row, 3, item.get("구분") or "", border=True)
        _put(ws, row, 4, item.get("내용") or "", border=True, align="left")
        _put(ws, row, 5, round(item.get("금액") or 0), fmt="#,##0",
             fill=_EDIT_FILL, border=True)
        _put(ws, row, 6, item.get("지급방법") or "", align="center",
             border=True)
        row += 1
    _put(ws, _EXP_LAST + 1, 4, "합계", bold=True, align="center")
    _put(ws, _EXP_LAST + 1, 5, f"=SUM(E{_EXP_FIRST}:E{_EXP_LAST})",
         bold=True, fmt="#,##0")

    # ④ 안정을 위한 필요 추가 입금 (향후 4주) ------------------------------
    _section(ws, 91, "④ 안정을 위한 필요 추가 입금 (향후 4주)")
    _put(ws, 92, 1, "목표 최저잔액", bold=True)
    _put(ws, 92, 2, report.get("stability_target") or 0, fill=_EDIT_FILL,
         fmt="#,##0", border=True)
    _put(ws, 92, 4, "예: 0원(적자 없음) 또는 안전하게 유지하고 싶은 잔액을 "
                    "입력하세요.", size=9, color="808080", align="left")
    for c, head in enumerate(("반영률", "4주 기말잔액", "4주 최저잔액",
                              "자금부족 예상일", "필요 추가 입금"), start=1):
        _put(ws, 93, c, head, bold=True, color="FFFFFF", fill=_HEAD_FILL,
             align="center", border=True)
    scenarios = forecast.get("rate_scenarios", {})
    r = 94
    base_need_row = None
    for sc_rate in (0.8, 0.9, 1.0):
        sc = scenarios.get(sc_rate)
        if not sc:
            continue
        if base_need_row is None:
            base_need_row = r
        _put(ws, r, 1, sc_rate, fmt="0%", align="center", border=True)
        _put(ws, r, 2, round(sc.get("4주 기말잔액") or 0), fmt="#,##0",
             border=True)
        _put(ws, r, 3, round(sc.get("4주 최저잔액") or 0), fmt="#,##0",
             border=True)
        shortage = sc.get("자금부족 예상일")
        _put(ws, r, 4, str(shortage) if shortage else "없음", align="center",
             border=True)
        _put(ws, r, 5, f"=MAX(0,{_TARGET_CELL}-C{r})", fmt="#,##0",
             border=True, bold=True)
        r += 1
    need = f"E{base_need_row}" if base_need_row else "0"
    _put(ws, r, 1, "주당 추가 입금 목표", bold=True)
    _put(ws, r, 2, f"=ROUND({need}/4,0)", bold=True, fmt="#,##0")
    _put(ws, r, 4, "영업일당(주 5일 기준)", bold=True, align="left")
    _put(ws, r, 5, f"=ROUND({need}/20,0)", bold=True, fmt="#,##0")

    # ⑤ 건강사업팀 전달 메모 -----------------------------------------------
    memo_row = r + 2
    _section(ws, memo_row, "⑤ 건강사업팀 전달 메모 (자동 작성)")
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
        if SHEET_NAME not in wb.sheetnames:
            return False
        ws = wb[SHEET_NAME]
        return (str(ws["C21"].value or "").startswith("=MIN")
                and "SUM(" in str(ws[f"E{_EXP_LAST + 1}"].value or "")
                and str(ws[f"E{_DAY_FIRST}"].value or "").startswith("="))
    except Exception:
        return False
    finally:
        wb.close()
