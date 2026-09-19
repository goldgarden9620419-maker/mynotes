# -*- coding: utf-8 -*-
"""최종 Excel 결과물 생성 — 사용자 기존 자금계획 양식으로 고정.

시트 구성(앞 8개는 기존 파일과 동일한 배치, 뒤 4개는 지출 자동화용 추가):
  요약 / 업데이트운영 / 4주일별계획 / 13주주별계획 / 정기지출분석
  / 주간계좌_붙여넣기 / 계좌내역통합_RAW / 설정및분류
  / 팀지출계획_통합 / 예정실제대조 / 확인필요 / 카드결제기준

기존 양식 규칙: 제목 A2, 설명 A3, 표 머리글 5행(RAW 시트는 1행),
자료는 6행(RAW 2행)부터. 확인필요 목록은 별도 파일로도 저장한다.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from common import (CONFIDENTIAL_MASK, RECURRING_BULK_CELL,
                    RECURRING_BULK_KEEP, RECURRING_CAT_NAME_COL,
                    RECURRING_CAT_PICK_COL, RECURRING_NATURE_DISPLAY)

EXPECTED_SHEETS = ["요약", "업데이트운영", "4주일별계획", "13주주별계획",
                   "정기지출분석", "주간계좌_붙여넣기", "계좌내역통합_RAW",
                   "설정및분류", "팀지출계획_통합", "예정실제대조",
                   "확인필요", "카드결제기준"]

_FONT = "맑은 고딕"
_HEADER_FILL = PatternFill("solid", start_color="1F4E79")
_HEADER_FONT = Font(name=_FONT, color="FFFFFF", bold=True, size=10)
_TITLE_FONT = Font(name=_FONT, bold=True, size=13, color="1F4E79")
_NOTE_FONT = Font(name=_FONT, size=9, color="808080")
_BODY_FONT = Font(name=_FONT, size=10)
_LABEL_FILL = PatternFill("solid", start_color="EAF1F8")
_THIN = Side(style="thin", color="D9D9D9")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_FILL_SHORTAGE = PatternFill("solid", start_color="FFC7CE")
_FILL_WARN = PatternFill("solid", start_color="FFEB9C")
_FILL_DUP = PatternFill("solid", start_color="EFEFEF")
_MONEY = "#,##0"
_DATE = "yyyy-mm-dd"

_STATE_FILLS = {"자금부족": _FILL_SHORTAGE, "주의": _FILL_WARN,
                "중복제외": _FILL_DUP, "수동확인필요": _FILL_WARN,
                "계획없는출금": _FILL_WARN, "확인필요": _FILL_WARN}

_CONFIDENCE_LABEL = {"상": "높음", "중": "중간", "하": "낮음"}


def _title(ws, title: str, note: str = "") -> None:
    cell = ws.cell(row=2, column=1, value=title)
    cell.font = _TITLE_FONT
    if note:
        ws.cell(row=3, column=1, value=note).font = _NOTE_FONT


def _write_table(ws, columns: list[tuple], rows: list[dict],
                 start_row: int = 5, state_key: str | None = None) -> None:
    """columns: (헤더, dict키, 폭, 형식). 형식: text/money/date/int"""
    for c, (header, _key, width, _kind) in enumerate(columns, start=1):
        cell = ws.cell(row=start_row, column=c, value=header)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = width
    for r, row in enumerate(rows, start=start_row + 1):
        fill = None
        if state_key:
            fill = _STATE_FILLS.get(str(row.get(state_key, "")))
        for c, (_header, key, _width, kind) in enumerate(columns, start=1):
            value = row.get(key)
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = _BORDER
            cell.font = _BODY_FONT
            if kind == "money":
                cell.number_format = _MONEY
            elif kind == "date" and isinstance(value, date):
                cell.number_format = _DATE
            elif kind == "int":
                cell.number_format = "0"
            if fill is not None:
                cell.fill = fill
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)


def _kv(ws, r: int, label, value, money=False):
    lab = ws.cell(row=r, column=1, value=label)
    lab.font = Font(name=_FONT, bold=True, size=10)
    lab.fill = _LABEL_FILL
    lab.border = _BORDER
    cell = ws.cell(row=r, column=2, value=value)
    cell.font = _BODY_FONT
    cell.border = _BORDER
    if money and isinstance(value, (int, float)):
        cell.number_format = _MONEY
    if isinstance(value, date) and not isinstance(value, datetime):
        cell.number_format = _DATE
    return r + 1


# ---------------------------------------------------------------------------
# 시트 1: 요약 (기존 양식 배치)
# ---------------------------------------------------------------------------

def _sheet_summary(ws, report: dict) -> None:
    meta = report["meta"]
    forecast = report["forecast"]
    scenario = forecast.get("scenario", {})
    stats = report.get("history_stats", {})

    for col, width in (("A", 26), ("B", 16), ("C", 3), ("D", 18),
                       ("E", 14), ("F", 14)):
        ws.column_dimensions[col].width = width
    _title(ws, f"{meta.get('company', '')} 자금계획",
           f"기준일 {meta.get('base_date')} · 최종 실행 {meta.get('run_at', '')}"
           f" · 실행 주차 {meta.get('week_key', '')}")

    # 왼쪽: 항목/금액
    h1 = ws.cell(row=5, column=1, value="항목")
    h2 = ws.cell(row=5, column=2, value="금액")
    for h in (h1, h2):
        h.fill = _HEADER_FILL
        h.font = _HEADER_FONT
        h.border = _BORDER
    r = 6
    r = _kv(ws, r, "현재 계좌잔액", report.get("total_balance"), money=True)
    r = _kv(ws, r, "6개월 외부입금", stats.get("외부입금"), money=True)
    r = _kv(ws, r, "6개월 외부출금", stats.get("외부출금"), money=True)
    r = _kv(ws, r, "온라인매출 입금(6개월)", stats.get("온라인입금"), money=True)
    r = _kv(ws, r, "최근 12주 주평균 온라인입금",
            stats.get("주평균온라인"), money=True)

    # 오른쪽: 계좌별 최신 잔액
    for c, h in ((4, "계좌"), (5, "최종 거래일"), (6, "잔액")):
        cell = ws.cell(row=5, column=c, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _BORDER
    rr = 6
    last_dates = report.get("account_last_dates", {})
    for key, amount in sorted(report.get("balances", {}).items()):
        ws.cell(row=rr, column=4,
                value=report.get("account_labels", {}).get(key, " ".join(
                    str(k) for k in key))).border = _BORDER
        d = ws.cell(row=rr, column=5, value=last_dates.get(key))
        d.number_format = _DATE
        d.border = _BORDER
        a = ws.cell(row=rr, column=6, value=amount)
        a.number_format = _MONEY
        a.border = _BORDER
        for c in (4, 5, 6):
            ws.cell(row=rr, column=c).font = _BODY_FONT
        rr += 1

    # 계획 설정 블록
    r = max(r, rr) + 1
    ws.cell(row=r, column=1, value="계획 설정").font = Font(
        name=_FONT, bold=True, size=11, color="1F4E79")
    ws.cell(row=r, column=4, value="사용 방법").font = Font(
        name=_FONT, bold=True, size=11, color="1F4E79")
    guide = [
        "1. 매주 월요일 오전까지 은행 최근 14일 내역을",
        "   03_은행거래내역 폴더에 넣으면 자동 반영됩니다.",
        "2. 팀 지출계획은 금요일까지 01·02 폴더에 저장하면",
        "   월요일 09:10 자동 취합됩니다.",
        "3. 확인필요 시트의 항목만 검토하면 됩니다.",
    ]
    for i, line in enumerate(guide):
        ws.cell(row=r + 1 + i, column=4, value=line).font = _NOTE_FONT
    r += 1
    r = _kv(ws, r, "입금 예측 반영률",
            f"{int(round(forecast.get('rate', 0) * 100))}%")
    r = _kv(ws, r, "4주 예상 기말잔액", scenario.get("4주 기말잔액"), money=True)
    r = _kv(ws, r, "4주 최저 예상잔액", scenario.get("4주 최저잔액"), money=True)
    r = _kv(ws, r, "4주 최저잔액 예상일", scenario.get("4주 최저잔액일"))
    r = _kv(ws, r, "13주 예상 기말잔액", scenario.get("13주 기말잔액"),
            money=True)
    r = _kv(ws, r, "향후 4주 확정지출", report.get("next4w_confirmed_out"),
            money=True)
    r = _kv(ws, r, "카드 결제 예정액(4주)", report.get("card_due_4w"),
            money=True)
    r = _kv(ws, r, "자금부족 예상일", scenario.get("자금부족 예상일") or "없음")
    r = _kv(ws, r, "확인필요 건수", len(report.get("issues", [])))
    r = _kv(ws, r, "자료 미제출 팀",
            ", ".join(report.get("missing_teams", [])) or "없음")
    note = scenario.get("안내", "")
    if note:
        cell = ws.cell(row=r + 1, column=1, value=note)
        cell.font = Font(name=_FONT, size=10, bold=True,
                         color="9C0006" if "부족" in note else "1F4E79")

    # 반영률 시나리오
    r += 3
    ws.cell(row=r, column=1, value="입금 반영률 시나리오").font = Font(
        name=_FONT, bold=True, size=11, color="1F4E79")
    r += 1
    headers = ["반영률", "4주 기말잔액", "4주 최저잔액", "13주 기말잔액",
               "자금부족 예상일"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _BORDER
    for rate, sc in sorted(report["forecast"].get("rate_scenarios", {}).items()):
        r += 1
        values = [f"{int(round(rate * 100))}%", sc.get("4주 기말잔액"),
                  sc.get("4주 최저잔액"), sc.get("13주 기말잔액"),
                  sc.get("자금부족 예상일") or "없음"]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = _BORDER
            cell.font = _BODY_FONT
            if isinstance(v, (int, float)):
                cell.number_format = _MONEY
            if isinstance(v, date):
                cell.number_format = _DATE


# ---------------------------------------------------------------------------
# 시트 2: 업데이트운영
# ---------------------------------------------------------------------------

_OPERATION_ROWS = [
    ("업로드 주기", "주 1회. 월요일 오전 9시 전까지 최근 14일 내역 저장"),
    ("업로드 장소", "자금계획_자동화\\03_은행거래내역\\농협·우리은행·국민은행 폴더"),
    ("권장 파일형식", "은행에서 내려받은 XLS·XLSX·CSV 원본 그대로"),
    ("지양할 형식", "PDF·사진·화면 캡처는 인식 불가"),
    ("파일명", "은행이 만들어 준 원래 파일명 그대로 사용 가능"),
    ("팀 지출계획", "매주 금요일까지 01_일반팀_지출계획·02_경영지원_대외비 폴더에 저장"),
    ("자동 실행", "매주 월요일 09:10 자동 실행. PC가 꺼져 있었으면 켠 뒤 자동 보완"),
    ("수동 실행", "트레이 아이콘 → '지금 실행' 또는 '변경자료 반영'"),
    ("결과물", "05_결과 폴더에 이 양식의 최신본이 생성됨(기존 파일은 보존)"),
    ("직접 입력 금지", "거래내역을 복사·붙여넣지 않습니다. 파일 저장만 하면 됩니다"),
]

_OPERATION_STEPS = [
    ("1. 파일 인식", "은행별 머리글과 데이터 시작행 자동 탐지", "은행·계좌"),
    ("2. 거래 표준화", "거래일시·입출금·잔액·적요 통일", "표준 14개 항목"),
    ("3. 중복 제거", "기존 거래와 신규 거래 비교", "은행+거래일+금액+잔액(+일시)"),
    ("4. 자동 분류", "매출·내부이체·세금·보험·카드 등", "적요·상대방 키워드"),
    ("5. 지출 취합", "팀 지출계획 요청ID 기준 변경·취소 반영", "요청ID·최종수정일"),
    ("6. 대조", "지급예정 ↔ 실제출금 자동 대조", "금액·거래처·일자·방법"),
    ("7. 계획 갱신", "최근 12주 패턴 × 반영률로 4주·13주 전망", "반영률 설정"),
]


def _sheet_operations(ws) -> None:
    for col, width in (("A", 16), ("B", 52), ("C", 3), ("D", 16),
                       ("E", 38), ("F", 30)):
        ws.column_dimensions[col].width = width
    _title(ws, "계좌·지출 업데이트 운영 기준",
           "6개월 자료는 최초 1회만 필요. 이후는 최근 14일 파일만 넣으면 "
           "자동으로 이어붙습니다.")
    for c, h in ((1, "항목"), (2, "권장 운영 기준"), (4, "처리단계"),
                 (5, "자동 처리 내용"), (6, "판정 기준")):
        cell = ws.cell(row=5, column=c, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _BORDER
    for i, (label, desc) in enumerate(_OPERATION_ROWS, start=6):
        ws.cell(row=i, column=1, value=label).font = Font(
            name=_FONT, bold=True, size=10)
        ws.cell(row=i, column=1).fill = _LABEL_FILL
        ws.cell(row=i, column=1).border = _BORDER
        ws.cell(row=i, column=2, value=desc).font = _BODY_FONT
        ws.cell(row=i, column=2).border = _BORDER
    for i, (step, desc, key) in enumerate(_OPERATION_STEPS, start=6):
        for c, v in ((4, step), (5, desc), (6, key)):
            cell = ws.cell(row=i, column=c, value=v)
            cell.font = _BODY_FONT
            cell.border = _BORDER


# ---------------------------------------------------------------------------
# 시트 3·4: 4주 일별 / 13주 주별 (기존 열 배치)
# ---------------------------------------------------------------------------

_DAILY_COLUMNS = [
    ("일자", "일자", 12, "date"), ("요일", "요일", 6, "text"),
    ("온라인 예상입금", "온라인 예상입금", 14, "money"),
    ("확정·기타입금", "확정·기타입금", 13, "money"),
    ("송금예정", "팀별 송금예정", 13, "money"),
    ("카드결제", "카드결제", 12, "money"),
    ("조정·추정 지출", "_기타지출합", 12, "money"),
    ("순현금흐름", "순현금흐름", 13, "money"),
    ("기초잔액", "기초잔액", 14, "money"),
    ("기말잔액", "기말잔액", 14, "money"),
    ("비고", "_비고", 22, "text"),
]

_WEEKLY_COLUMNS = [
    ("주차", "주차", 8, "text"), ("기간", "기간", 24, "text"),
    ("온라인 예상입금", "온라인입금", 14, "money"),
    ("확정·기타입금", "확정기타입금", 13, "money"),
    ("송금예정", "송금예정", 13, "money"),
    ("카드결제", "카드결제", 12, "money"),
    ("조정·추정 지출", "_기타지출합", 12, "money"),
    ("추가 주간조정", "_주간조정", 12, "money"),
    ("순현금흐름", "순현금흐름", 13, "money"),
    ("기말잔액", "기말잔액", 14, "money"),
    ("상태", "상태", 9, "text"),
]


def _daily_display(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        d["_기타지출합"] = (r.get("자동이체") or 0) + (r.get("기타지출") or 0)
        note = r.get("비고") or ""
        if r.get("상태") in ("자금부족", "주의"):
            note = (f"⚠ {r['상태']}" + ("; " + note if note else ""))
        d["_비고"] = note
        out.append(d)
    return out


def _weekly_display(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        d["_기타지출합"] = (r.get("자동이체") or 0) + (r.get("기타지출") or 0)
        d["_주간조정"] = 0
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# 시트 5: 정기지출분석 (기존 열 배치, 신뢰도 높음/중간/낮음)
# ---------------------------------------------------------------------------

_RECURRING_COLUMNS = [
    ("은행", "은행", 10, "text"), ("정기지출명", "정기지출명", 20, "text"),
    ("분류", "분류", 16, "text"), ("발생개월수", "발생개월수", 10, "int"),
    ("거래건수", "거래건수", 9, "int"),
    ("평균 월지출", "평균 월지출", 14, "money"),
    ("최소 월지출", "최소 월지출", 14, "money"),
    ("최대 월지출", "최대 월지출", 14, "money"),
    ("대표 지급일", "_지급일표시", 14, "text"),
    ("신뢰도", "_신뢰도표시", 8, "text"),
    ("성격", "성격", 8, "text"),
]


def _recurring_display(items: list[dict]) -> list[dict]:
    out = []
    for it in items:
        d = dict(it)
        d["_지급일표시"] = f"매월 {it.get('대표 지급일')}일 전후"
        d["_신뢰도표시"] = _CONFIDENCE_LABEL.get(it.get("신뢰도"),
                                            it.get("신뢰도"))
        if not d.get("분류"):
            d["분류"] = "성격확인필요"
        d["성격"] = RECURRING_NATURE_DISPLAY.get(
            d.get("성격") or "정기", d.get("성격") or "정기")
        out.append(d)
    return out


def _recurring_categories(items: list[dict]) -> list[str]:
    """표시되는 분류 값 목록 (등장 순서, 중복 제거)."""
    seen: list[str] = []
    for it in items:
        cat = str(it.get("분류") or "").strip() or "성격확인필요"
        if cat not in seen:
            seen.append(cat)
    return seen


def add_recurring_controls(ws, last_row: int,
                           categories: list[str] | None = None) -> None:
    """정기지출분석 시트에 필터·성격 드롭다운·일괄 변경 컨트롤을 단다.

    머리글 5행 / 자료 6행~ / 성격 K열 / 분류별 일괄 M·N열 배치 전제.
    적용 우선순위: K4 전체 일괄 > 분류별 일괄(N열) > 개별 행(K열).
    """
    from openpyxl.cell.cell import MergedCell
    from openpyxl.worksheet.datavalidation import DataValidation

    last_row = max(last_row, 6)
    ws.auto_filter.ref = f"A5:K{last_row}"

    nature_dv = DataValidation(type="list", formula1='"정기,비정기,제외"',
                               allow_blank=True)
    nature_dv.error = "'정기', '비정기', '제외'만 입력할 수 있습니다."
    nature_dv.showErrorMessage = True
    ws.add_data_validation(nature_dv)
    nature_dv.add(f"K6:K{last_row}")

    label = ws["J4"]
    if not isinstance(label, MergedCell):
        label.value = "성격 일괄 변경 →"
        label.font = Font(name=_FONT, bold=True, size=9, color="B36B00")
        label.alignment = Alignment(horizontal="right")
    bulk = ws[RECURRING_BULK_CELL]
    if not isinstance(bulk, MergedCell):
        bulk.value = RECURRING_BULK_KEEP
        bulk.fill = PatternFill("solid", start_color="FFF2CC")
        bulk.font = Font(name=_FONT, bold=True, size=10)
        bulk.alignment = Alignment(horizontal="center")
        choices = f"{RECURRING_BULK_KEEP},전체 정기,전체 비정기"
        bulk_dv = DataValidation(type="list", formula1=f'"{choices}"',
                                 allow_blank=True)
        bulk_dv.error = f"{choices} 중에서만 고를 수 있습니다."
        bulk_dv.showErrorMessage = True
        ws.add_data_validation(bulk_dv)
        bulk_dv.add(RECURRING_BULK_CELL)

    if not categories:
        return
    # 분류별 일괄 블록 (M·N열): 분류 하나를 통째로 정기/비정기/제외로
    m, n = RECURRING_CAT_NAME_COL, RECURRING_CAT_PICK_COL
    for c, header in ((m, "분류별 일괄"), (n, "적용할 성격")):
        cell = ws.cell(row=5, column=c, value=header)
        if not isinstance(cell, MergedCell):
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = Alignment(horizontal="center",
                                       vertical="center")
            cell.border = _BORDER
    ws.column_dimensions[get_column_letter(m)].width = 20
    ws.column_dimensions[get_column_letter(n)].width = 12
    cat_dv = DataValidation(
        type="list",
        formula1=f'"{RECURRING_BULK_KEEP},정기,비정기,제외"',
        allow_blank=True)
    cat_dv.error = "변경 안 함, 정기, 비정기, 제외 중에서만 " \
                   "고를 수 있습니다."
    cat_dv.showErrorMessage = True
    ws.add_data_validation(cat_dv)
    for r, cat in enumerate(categories, start=6):
        name_cell = ws.cell(row=r, column=m, value=cat)
        if not isinstance(name_cell, MergedCell):
            name_cell.font = _BODY_FONT
            name_cell.border = _BORDER
        pick = ws.cell(row=r, column=n, value=RECURRING_BULK_KEEP)
        if not isinstance(pick, MergedCell):
            pick.fill = PatternFill("solid", start_color="FFF2CC")
            pick.font = _BODY_FONT
            pick.alignment = Alignment(horizontal="center")
            pick.border = _BORDER
            cat_dv.add(pick.coordinate)


# ---------------------------------------------------------------------------
# 시트 6: 주간계좌_붙여넣기 (안내로 유지)
# ---------------------------------------------------------------------------

def _sheet_paste(ws) -> None:
    ws.column_dimensions["A"].width = 90
    _title(ws, "주간 법인계좌 거래내역 — 이제 붙여넣기가 필요 없습니다")
    for i, line in enumerate([
        "은행에서 내려받은 파일(XLS·XLSX·CSV)을 그대로",
        "자금계획_자동화\\03_은행거래내역\\은행별 폴더에 저장하면",
        "매주 월요일 09:10 자동으로 반영됩니다.",
        "",
        "이 시트에 거래내역을 붙여넣지 않아도 됩니다.",
        "즉시 반영이 필요하면 트레이 아이콘 → '지금 실행'을 누르세요.",
    ], start=5):
        ws.cell(row=i, column=1, value=line).font = _BODY_FONT


# ---------------------------------------------------------------------------
# 시트 7: 계좌내역통합_RAW (기존 14열, 머리글 1행)
# ---------------------------------------------------------------------------

_RAW_COLUMNS = [
    ("거래일시", "_일시표시", 17, "text"), ("거래일", "거래일", 12, "date"),
    ("은행", "은행", 9, "text"), ("계좌", "_계좌표시", 14, "text"),
    ("출금액", "출금액", 13, "money"), ("입금액", "입금액", 13, "money"),
    ("거래후잔액", "거래후잔액", 14, "money"),
    ("적요", "적요", 13, "text"),
    ("기재내용·상대방", "기재내용·상대방", 20, "text"),
    ("취급점", "취급점", 12, "text"), ("자동분류", "_분류표시", 14, "text"),
    ("내부이체", "_내부이체", 8, "text"),
    ("정기지출후보", "_정기후보", 10, "text"),
    ("현금유출입", "현금유출입", 13, "money"),
]

_BANK_SHORT = {"농협": "농협", "국민은행": "국민", "우리은행": "우리"}


def account_label(bank: str, account: str) -> str:
    import re
    digits = re.sub(r"\D", "", account or "")
    tail = digits[-6:] if digits else (account or "").strip()
    return f"{_BANK_SHORT.get(bank, bank)} {tail}".strip()


def _raw_display(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("반영상태") == "중복제외":
            continue
        d = dict(r)
        dt = r.get("거래일시")
        d["_일시표시"] = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
        d["_계좌표시"] = account_label(r.get("은행", ""), r.get("계좌", ""))
        cls = r.get("자동분류") or ""
        if r.get("내부이체"):
            cls = "계좌간이체"
        elif not cls:
            cls = "기타입금" if (r.get("입금액") or 0) > 0 else "기타지출"
        d["_분류표시"] = cls
        d["_내부이체"] = "Y" if r.get("내부이체") else "N"
        d["_정기후보"] = "Y" if r.get("정기지출후보") else "N"
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# 시트 8: 설정및분류
# ---------------------------------------------------------------------------

_WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def _sheet_config(ws, report: dict) -> None:
    for col, width in (("A", 9), ("B", 6), ("C", 24), ("D", 3),
                       ("E", 22), ("F", 56), ("G", 3), ("H", 12)):
        ws.column_dimensions[col].width = width
    _title(ws, "예측 설정 및 자동분류 기준",
           "자동분류 키워드는 00_프로그램\\classify_rules.json에서 수정할 수 "
           "있습니다.")
    for c, h in ((1, "요일번호"), (2, "요일"), (3, "최근 12주 온라인입금 일평균"),
                 (5, "분류"), (6, "대표 키워드"), (8, "반영률 선택값")):
        cell = ws.cell(row=5, column=c, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _BORDER
    weekday_avg = report["forecast"].get("weekday_avg", {})
    for i in range(7):
        r = 6 + i
        ws.cell(row=r, column=1, value=i + 1).border = _BORDER
        ws.cell(row=r, column=2, value=_WEEKDAY_NAMES[i]).border = _BORDER
        cell = ws.cell(row=r, column=3, value=round(weekday_avg.get(i, 0)))
        cell.number_format = _MONEY
        cell.border = _BORDER
        for c in (1, 2, 3):
            ws.cell(row=r, column=c).font = _BODY_FONT

    rules = report.get("classify_rules", {})
    r = 6
    entries = [("내부이체(계좌간이체)",
                ", ".join(rules.get("internal_keywords", [])))]
    top = rules.get("top_withdrawal", {})
    if top:
        entries.append((f"급여 TOP출금({top.get('month_end_day', 25)}일 이후)",
                        ", ".join(top.get("키워드", []))))
    for rule in rules.get("rules", []):
        entries.append((rule.get("분류", ""),
                        ", ".join(rule.get("키워드", []))[:80]))
    for label, kw in entries:
        ws.cell(row=r, column=5, value=label).font = _BODY_FONT
        ws.cell(row=r, column=5).border = _BORDER
        ws.cell(row=r, column=6, value=kw).font = _BODY_FONT
        ws.cell(row=r, column=6).border = _BORDER
        r += 1

    for i, rate in enumerate(sorted(
            report["forecast"].get("rate_scenarios", {}))):
        cell = ws.cell(row=6 + i, column=8, value=rate)
        cell.number_format = "0.0"
        cell.border = _BORDER
        cell.font = _BODY_FONT


# ---------------------------------------------------------------------------
# 추가 시트: 팀지출계획_통합 / 예정실제대조 / 확인필요 / 카드결제기준
# ---------------------------------------------------------------------------

_PLAN_COLUMNS = [
    ("요청ID", "요청ID", 18, "text"), ("팀명", "팀명", 13, "text"),
    ("신청자", "신청자", 9, "text"),
    ("품의승인", "품의승인", 10, "text"),
    ("지급예정일", "지급예정일", 12, "date"),
    ("자금계획 반영일", "자금계획 반영일", 13, "date"),
    ("거래처", "거래처", 16, "text"), ("지출내용", "지출내용", 24, "text"),
    ("예상금액", "예상금액", 13, "money"),
    ("지급방법", "지급방법", 10, "text"), ("카드구분", "카드구분", 10, "text"),
    ("확정여부", "확정여부", 9, "text"), ("진행상태", "진행상태", 9, "text"),
    ("최종수정일", "최종수정일", 12, "date"),
    ("원본파일", "원본파일", 24, "text"),
    ("반영상태", "반영상태", 13, "text"), ("확인사항", "확인사항", 28, "text"),
]

_MATCH_COLUMNS = [
    ("요청ID", "요청ID", 18, "text"), ("팀명", "팀명", 13, "text"),
    ("거래처", "거래처", 18, "text"),
    ("예정금액", "예정금액", 13, "money"),
    ("실제금액", "실제금액", 13, "money"),
    ("차이금액", "차이금액", 13, "money"),
    ("지급예정일", "지급예정일", 12, "date"),
    ("실제출금일", "실제출금일", 12, "date"),
    ("은행", "은행", 10, "text"), ("대조결과", "대조결과", 13, "text"),
    ("비고", "비고", 28, "text"),
]

_ISSUE_COLUMNS = [
    ("구분", "구분", 18, "text"), ("팀명", "팀명", 13, "text"),
    ("은행", "은행", 10, "text"), ("요청ID", "요청ID", 18, "text"),
    ("일자", "일자", 11, "date"), ("내용", "내용", 42, "text"),
    ("금액", "금액", 13, "money"), ("원본파일", "원본파일", 24, "text"),
]

_CARD_COLUMNS = [
    ("카드구분", "카드구분", 12, "text"), ("카드사", "카드사", 12, "text"),
    ("결제일", "결제일", 8, "int"),
    ("이용기간 시작일", "이용기간 시작일", 14, "text"),
    ("이용기간 종료일", "이용기간 종료일", 14, "text"),
    ("출금계좌", "출금계좌", 18, "text"), ("사용여부", "사용여부", 8, "text"),
]


def _mask_match_rows(results: list[dict], unplanned: list[dict]) -> list[dict]:
    """대외비 대조 결과는 분류·총액만 노출한다."""
    display: list[dict] = []
    conf_groups: dict[tuple, dict] = {}
    for row in results:
        if not row.get("confidential"):
            display.append(row)
            continue
        category = row.get("_conf_category") or CONFIDENTIAL_MASK
        key = (category, row.get("대조결과"))
        g = conf_groups.setdefault(key, {
            "요청ID": CONFIDENTIAL_MASK, "팀명": "경영지원팀",
            "거래처": category, "예정금액": 0.0, "실제금액": 0.0,
            "차이금액": 0.0, "지급예정일": row.get("지급예정일"),
            "실제출금일": row.get("실제출금일"), "은행": row.get("은행"),
            "대조결과": row.get("대조결과"),
            "비고": f"{CONFIDENTIAL_MASK} 항목 합계", "건수": 0})
        g["예정금액"] += row.get("예정금액") or 0
        g["실제금액"] += row.get("실제금액") or 0
        g["차이금액"] += row.get("차이금액") or 0
        g["건수"] += 1
        g["비고"] = f"{CONFIDENTIAL_MASK} {g['건수']}건 합계"
    display.extend(conf_groups.values())
    display.extend(unplanned)
    return display


# ---------------------------------------------------------------------------
# 파일 생성
# ---------------------------------------------------------------------------

def create_report_workbook(report: dict, out_path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    _sheet_summary(wb.create_sheet("요약"), report)
    _sheet_operations(wb.create_sheet("업데이트운영"))

    ws = wb.create_sheet("4주일별계획")
    _title(ws, "향후 4주 일별 자금계획",
           f"온라인 예상입금은 최근 12주 요일평균 × 반영률 "
           f"{int(round(report['forecast'].get('rate', 0) * 100))}% 기준. "
           f"조정·추정 지출에는 자동이체와 주간조정·자동추정·확인지시 지출이 포함됩니다.")
    _write_table(ws, _DAILY_COLUMNS,
                 _daily_display(report["forecast"].get("daily", [])),
                 state_key="상태")

    ws = wb.create_sheet("13주주별계획")
    _title(ws, "향후 13주 주별 자금계획",
           f"온라인 예상입금 반영률 "
           f"{int(round(report['forecast'].get('rate', 0) * 100))}%. "
           "1~4주는 일별계획 합산, 5주 이후는 팀계획·정기지출 추정 반영.")
    _write_table(ws, _WEEKLY_COLUMNS,
                 _weekly_display(report["forecast"].get("weekly", [])),
                 state_key="상태")

    ws = wb.create_sheet("정기지출분석")
    _title(ws, "월 정기지출 분석",
           "최근 6개월 중 4개월 이상 반복된 지출입니다. "
           "확인필요 항목은 자동 확정하지 않습니다.")
    _write_table(ws, _RECURRING_COLUMNS,
                 _recurring_display(report.get("recurring", [])))
    add_recurring_controls(ws, 5 + len(report.get("recurring", [])))

    _sheet_paste(wb.create_sheet("주간계좌_붙여넣기"))

    ws = wb.create_sheet("계좌내역통합_RAW")
    _write_table(ws, _RAW_COLUMNS, _raw_display(report.get("bank_rows", [])),
                 start_row=1)

    _sheet_config(wb.create_sheet("설정및분류"), report)

    ws = wb.create_sheet("팀지출계획_통합")
    _title(ws, "팀 지출계획 통합",
           "요청ID 기준 최신자료만 반영. 대외비는 분류·총액만 표시됩니다.")
    _write_table(ws, _PLAN_COLUMNS, report.get("integrated_masked", []),
                 state_key="반영상태")

    ws = wb.create_sheet("예정실제대조")
    _title(ws, "지급예정 ↔ 실제출금 대조",
           "불확실한 거래는 지급완료로 확정하지 않고 수동확인필요로 "
           "표시합니다.")
    match_rows = _mask_match_rows(report.get("match_results", []),
                                  report.get("unplanned", []))
    _write_table(ws, _MATCH_COLUMNS, match_rows, state_key="대조결과")

    ws = wb.create_sheet("확인필요")
    _title(ws, "확인필요 목록",
           "오류 건을 임의로 삭제하거나 0원으로 처리하지 않습니다.")
    _write_table(ws, _ISSUE_COLUMNS, report.get("issues", []))

    ws = wb.create_sheet("카드결제기준")
    _title(ws, "법인카드 결제일 기준",
           "실제 약정과 다르면 04_기준파일의 카드결제기준 시트를 수정하세요.")
    _write_table(ws, _CARD_COLUMNS, report.get("card_rules", []))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


REVIEW_SHEET = "확인필요"
_REVIEW_CONFIRM_CELL = "B2"    # 예/아니오 드롭다운
_REVIEW_WEEK_CELL = "J2"       # 숨김: 주차 키
_REVIEW_SIG_CELL = "K2"        # 숨김: 입력자료 서명
_ACTION_COL = 9                # I: 처리 (정기지출 누락 → 계획에 반영 여부)
_ITEM_COL = 10                 # J(숨김): 정기지출명 (지시 대상 식별)
ACTION_INCLUDE = "계획에 반영"
ACTION_SKIP = "반영 안 함"


def create_issue_workbook(issues: list[dict], out_path: Path,
                          week_key: str = "", signature: str = "") -> Path:
    """확인필요 워크북. week_key/signature가 있으면 '확인 완료' 컨트롤을
    붙인다 — 검토 후 B2를 '예'로 바꿔 저장하면 다음 실행이 결과를 만든다.

    '정기지출 누락 의심' 행에는 '처리' 열(계획에 반영/반영 안 함)이 생겨
    항목별로 지시할 수 있다 — '계획에 반영'을 고르면 결과 생성 때 그
    날짜 지출로 자금계획에 들어간다.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = REVIEW_SHEET
    start = 1
    if week_key or signature:
        start = 4
        from openpyxl.worksheet.datavalidation import DataValidation
        ws.merge_cells("A1:H1")
        guide = ws["A1"]
        guide.value = ("아래 항목을 검토하세요. '정기지출 누락 의심'은 '처리' "
                       "열에서 계획에 반영/반영 안 함을 고르세요. 함께 열리는 "
                       "'정기지출분석' 파일에서 분류·성격(정기/비정기/제외)도 "
                       "확인·수정하세요. 끝나면 "
                       "'확인 완료'(B2)를 '예'로 바꿔 저장하세요 — 다시 "
                       "실행하면(켜져 있으면 10분 안에 자동) 결과 3개가 "
                       "만들어집니다.")
        guide.font = Font(name="맑은 고딕", bold=True, size=10,
                          color="B36B00")
        guide.alignment = Alignment(horizontal="left", vertical="center",
                                    wrap_text=True)
        ws.row_dimensions[1].height = 34
        label = ws["A2"]
        label.value = "확인 완료"
        label.font = Font(name="맑은 고딕", bold=True, size=10)
        confirm = ws[_REVIEW_CONFIRM_CELL]
        confirm.value = "아니오"
        confirm.fill = PatternFill("solid", start_color="FFF2CC")
        confirm.font = Font(name="맑은 고딕", bold=True, size=10)
        confirm.alignment = Alignment(horizontal="center")
        dv = DataValidation(type="list", formula1='"아니오,예"',
                            allow_blank=True)
        dv.error = "'예' 또는 '아니오'만 입력할 수 있습니다."
        dv.showErrorMessage = True
        ws.add_data_validation(dv)
        dv.add(_REVIEW_CONFIRM_CELL)
        week_note = ws["C2"]
        week_note.value = f"(주차 {week_key})"
        week_note.font = Font(name="맑은 고딕", size=9, color="888888")
        ws[_REVIEW_WEEK_CELL] = week_key
        ws[_REVIEW_SIG_CELL] = signature
    _write_table(ws, _ISSUE_COLUMNS, issues, start_row=start)
    if start > 1:
        # '처리' 열(G) + 숨김 데이터 열(H:일자, I:금액, J:항목)
        head = ws.cell(row=start, column=_ACTION_COL, value="처리")
        head.fill = _HEADER_FILL
        head.font = _HEADER_FONT
        head.alignment = Alignment(horizontal="center", vertical="center")
        head.border = _BORDER
        ws.column_dimensions[get_column_letter(_ACTION_COL)].width = 14
        from openpyxl.worksheet.datavalidation import DataValidation
        action_dv = DataValidation(
            type="list", formula1=f'"{ACTION_INCLUDE},{ACTION_SKIP}"',
            allow_blank=True)
        action_dv.error = f"'{ACTION_INCLUDE}' 또는 '{ACTION_SKIP}'만 " \
                          "입력할 수 있습니다."
        action_dv.showErrorMessage = True
        ws.add_data_validation(action_dv)
        for r, issue in enumerate(issues, start=start + 1):
            if not issue.get("지시항목"):
                continue
            cell = ws.cell(row=r, column=_ACTION_COL, value=ACTION_SKIP)
            cell.fill = PatternFill("solid", start_color="FFF2CC")
            cell.font = _BODY_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = _BORDER
            action_dv.add(cell.coordinate)
            ws.cell(row=r, column=_ITEM_COL, value=issue.get("지시항목"))
        for col in ("J", "K"):
            ws.column_dimensions[col].hidden = True
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


RECURRING_REVIEW_PREFIX = "정기지출분석"


def recurring_review_name(review_name: str) -> str:
    """확인필요 파일명에서 짝이 되는 정기지출분석 파일명을 만든다."""
    return review_name.replace("확인필요", RECURRING_REVIEW_PREFIX, 1)


def create_recurring_review_workbook(recurring: list[dict],
                                     out_path: Path,
                                     week_key: str = "") -> Path:
    """확인 단계용 별도 '정기지출분석' 파일.

    확인필요 파일과 함께 열려, 분류·성격(정기/비정기/제외)을 검토·수정하는
    전용 파일이다. 수정 후 저장하고 확인필요 파일의 '확인 완료'(B2)를
    '예'로 저장하면 이번 결과 생성에 바로 반영된다.
    성격 적용 우선순위: K4 전체 일괄 > 분류별 일괄(N열) > 개별 행(K열).
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "정기지출분석"
    ws.merge_cells("A1:I1")
    guide = ws["A1"]
    week = f" (주차 {week_key})" if week_key else ""
    guide.value = (f"정기지출의 분류·성격을 검토하세요{week}. 성격은 "
                   "정기/비정기/제외 — 개별 행(K열), 분류별 일괄(N열), "
                   "전체 일괄(K4) 순으로 넓게 적용할 수 있습니다(넓은 쪽 "
                   "우선). 고친 뒤 저장하고, 확인필요 파일의 '확인 완료'"
                   "(B2)를 '예'로 저장하면 이번 결과에 바로 반영됩니다.")
    guide.font = Font(name=_FONT, bold=True, size=10, color="B36B00")
    guide.alignment = Alignment(horizontal="left", vertical="center",
                                wrap_text=True)
    ws.row_dimensions[1].height = 34
    _title(ws, "월 정기지출 분석 — 확인 단계",
           "정기 = 평균 금액 자동 추정 대상 / 비정기 = 팀 지출예정 파일 "
           "금액으로만 반영 / 제외 = 추정·정기지출 체크 모두 안 함")
    _write_table(ws, _RECURRING_COLUMNS, _recurring_display(recurring))
    add_recurring_controls(ws, 5 + len(recurring),
                           categories=_recurring_categories(recurring))
    # '적용할 성격' 선택지 안내 (P열 안내 상자)
    guide_rows = [
        ("적용할 성격 안내", True),
        ("변경 안 함 — 지금 값을 그대로 둡니다 (아무것도 바꾸지 않음)",
         False),
        ("정기 — 평균 월지출을 자동 추정해 자금계획 후보로 올립니다 "
         "(자동추정_지출목록에 등재. 실제 반영 여부는 그 파일의 반영/제외로"
         " 결정)", False),
        ("비정기 — 자동 추정을 하지 않습니다. 팀 지출예정 파일에 적힌 "
         "금액만 자금계획에 반영 (금주 '정기지출 체크' 대조는 계속 함)",
         False),
        ("제외 — 자동 추정도, 정기지출 체크 대조도 하지 않습니다 "
         "(관리 대상에서 완전 제외)", False),
        ("우선순위 — K4 전체 일괄 > N열 분류별 일괄 > K열 개별 행 "
         "(넓은 쪽이 이깁니다)", False),
    ]
    ws.column_dimensions["P"].width = 62
    for i, (text, head) in enumerate(guide_rows, start=5):
        cell = ws.cell(row=i, column=16, value=text)
        if head:
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = Alignment(horizontal="center",
                                       vertical="center")
        else:
            cell.font = Font(name=_FONT, size=9, color="404040")
            cell.fill = PatternFill("solid", start_color="F5F5F5")
            cell.alignment = Alignment(horizontal="left", vertical="center",
                                       wrap_text=True)
        cell.border = _BORDER
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


def load_review_directives(path: Path) -> list[dict]:
    """확인 완료된 확인필요 파일에서 '계획에 반영' 지시를 읽는다.

    반환 행: {일자, 금액, 항목} — 정기지출 누락 의심 항목 중 사용자가
    '처리' 열(I)을 '계획에 반영'으로 고른 것. 일자(E)·금액(G)을 표에서
    고쳐 두면 고친 값으로 반영된다.
    """
    from common import parse_amount, parse_date
    result: list[dict] = []
    try:
        wb = load_workbook(path, data_only=True, read_only=True)
    except Exception:
        return result
    try:
        if REVIEW_SHEET not in wb.sheetnames:
            return result
        ws = wb[REVIEW_SHEET]
        for row in ws.iter_rows(min_row=5, max_col=_ITEM_COL,
                                values_only=True):
            action = str(row[_ACTION_COL - 1] or "").strip() \
                if len(row) >= _ACTION_COL else ""
            if action != ACTION_INCLUDE:
                continue
            d = parse_date(row[4] if len(row) > 4 else None)       # E: 일자
            amount = parse_amount(row[6] if len(row) > 6 else None) or 0.0
            name = str(row[_ITEM_COL - 1] or "").strip() \
                if len(row) >= _ITEM_COL else ""
            if d is None or amount <= 0 or not name:
                continue
            result.append({"일자": d, "금액": amount, "항목": name})
        return result
    except Exception:
        return result
    finally:
        wb.close()


def review_confirmed(path: Path) -> tuple[bool, str, str]:
    """확인필요 파일의 (확인 완료 여부, 주차, 입력 서명)을 읽는다."""
    try:
        wb = load_workbook(path, data_only=True, read_only=True)
    except Exception:
        return False, "", ""
    try:
        if REVIEW_SHEET not in wb.sheetnames:
            return False, "", ""
        ws = wb[REVIEW_SHEET]
        ok = str(ws[_REVIEW_CONFIRM_CELL].value or "").strip().startswith("예")
        week = str(ws[_REVIEW_WEEK_CELL].value or "").strip()
        sig = str(ws[_REVIEW_SIG_CELL].value or "").strip()
        return ok, week, sig
    except Exception:
        return False, "", ""
    finally:
        wb.close()


def find_confirmed_review(review_dir: Path, week_key: str,
                          signature: str = "") -> Path | None:
    """이번 주차·현재 입력자료에 대해 '확인 완료'된 확인필요 파일을 찾는다.

    확인 후 입력파일이 바뀌면 서명이 달라져 다시 확인 단계로 돌아간다.
    """
    review_dir = Path(review_dir)
    if not review_dir.exists():
        return None
    for p in sorted(review_dir.glob("확인필요_*.xlsx"),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        ok, week, sig = review_confirmed(p)
        if ok and week == week_key and (not signature or sig == signature):
            return p
    return None


def verify_workbook(path: Path, expected_sheets: list[str] | None = None) -> bool:
    """저장된 결과파일을 다시 열어 검증한다 (31번 항목)."""
    expected = expected_sheets or EXPECTED_SHEETS
    try:
        wb = load_workbook(path, read_only=True)
    except Exception:
        return False
    try:
        names = set(wb.sheetnames)
        return all(sheet in names for sheet in expected)
    finally:
        wb.close()
