# -*- coding: utf-8 -*-
"""최종 Excel 결과물 생성 (25~28번 항목).

시트: 요약 / 4주일별계획 / 13주주별계획 / 팀지출계획_통합 / 예정실제대조
     / 정기지출분석 / 계좌내역통합_RAW / 확인필요 / 카드결제기준
     / 설정및분류 / 업데이트운영
확인필요 목록은 별도 파일로도 저장한다.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from common import CONFIDENTIAL_MASK

EXPECTED_SHEETS = ["요약", "4주일별계획", "13주주별계획", "팀지출계획_통합",
                   "예정실제대조", "정기지출분석", "계좌내역통합_RAW",
                   "확인필요", "카드결제기준", "설정및분류", "업데이트운영"]

_HEADER_FILL = PatternFill("solid", start_color="1F4E79")
_HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
_TITLE_FONT = Font(bold=True, size=14, color="1F4E79")
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


def _write_table(ws, columns: list[tuple], rows: list[dict],
                 start_row: int = 1, state_key: str | None = None) -> None:
    """columns: (헤더, dict키, 폭, 형식) 목록. 형식: text/money/date/dt/int"""
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
            if kind == "money":
                cell.number_format = _MONEY
            elif kind == "date" and isinstance(value, date):
                cell.number_format = _DATE
            elif kind == "int":
                cell.number_format = "0"
            if fill is not None:
                cell.fill = fill
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)


# ---------------------------------------------------------------------------
# 시트별 작성
# ---------------------------------------------------------------------------

def _sheet_summary(ws, report: dict) -> None:
    meta = report["meta"]
    forecast = report["forecast"]
    scenario = forecast.get("scenario", {})
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 34

    ws["A1"] = f"{meta.get('company', '')} 주간 자금계획 요약"
    ws["A1"].font = _TITLE_FONT
    items = [
        ("기준일", meta.get("base_date")),
        ("최종 실행일시", meta.get("run_at")),
        ("실행 주차", meta.get("week_key")),
        ("현재 전체 계좌잔액", report.get("total_balance")),
        ("입금 예측 반영률", f"{int(round(forecast.get('rate', 0) * 100))}%"),
        ("4주 예상 기말잔액", scenario.get("4주 기말잔액")),
        ("4주 최저 예상잔액", scenario.get("4주 최저잔액")),
        ("4주 최저잔액 예상일", scenario.get("4주 최저잔액일")),
        ("13주 예상 기말잔액", scenario.get("13주 기말잔액")),
        ("향후 4주 확정지출", report.get("next4w_confirmed_out")),
        ("카드 결제 예정액(4주)", report.get("card_due_4w")),
        ("확인필요 건수", len(report.get("issues", []))),
        ("자료 미제출 팀", ", ".join(report.get("missing_teams", [])) or "없음"),
        ("자금부족 예상일", scenario.get("자금부족 예상일") or "없음"),
        ("자동화 실행상태", meta.get("status", "")),
        ("안내", scenario.get("안내", "")),
    ]
    r = 3
    for label, value in items:
        label_cell = ws.cell(row=r, column=1, value=label)
        label_cell.font = Font(bold=True, size=10)
        label_cell.fill = PatternFill("solid", start_color="EAF1F8")
        label_cell.border = _BORDER
        cell = ws.cell(row=r, column=2, value=value)
        cell.border = _BORDER
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cell.number_format = _MONEY
        if isinstance(value, date) and not isinstance(value, datetime):
            cell.number_format = _DATE
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="계좌별 최신 잔액").font = Font(bold=True)
    r += 1
    for (bank, account), amount in sorted(report.get("balances", {}).items()):
        ws.cell(row=r, column=1, value=f"{bank} {account}".strip()).border = _BORDER
        cell = ws.cell(row=r, column=2, value=amount)
        cell.number_format = _MONEY
        cell.border = _BORDER
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="입금 반영률 시나리오").font = Font(bold=True)
    r += 1
    headers = ["반영률", "4주 기말잔액", "4주 최저잔액", "13주 기말잔액",
               "자금부족 예상일"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = max(
            ws.column_dimensions[get_column_letter(c)].width or 0, 16)
    for rate, sc in sorted(report["forecast"].get("rate_scenarios", {}).items()):
        r += 1
        values = [f"{int(round(rate * 100))}%", sc.get("4주 기말잔액"),
                  sc.get("4주 최저잔액"), sc.get("13주 기말잔액"),
                  sc.get("자금부족 예상일") or "없음"]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = _BORDER
            if isinstance(v, (int, float)):
                cell.number_format = _MONEY
            if isinstance(v, date):
                cell.number_format = _DATE


_DAILY_COLUMNS = [
    ("일자", "일자", 12, "date"), ("요일", "요일", 6, "text"),
    ("온라인 예상입금", "온라인 예상입금", 14, "money"),
    ("확정·기타입금", "확정·기타입금", 13, "money"),
    ("팀별 송금예정", "팀별 송금예정", 13, "money"),
    ("카드결제", "카드결제", 12, "money"),
    ("자동이체", "자동이체", 12, "money"),
    ("기타지출", "기타지출", 12, "money"),
    ("순현금흐름", "순현금흐름", 13, "money"),
    ("기초잔액", "기초잔액", 14, "money"),
    ("기말잔액", "기말잔액", 14, "money"),
    ("상태", "상태", 9, "text"), ("비고", "비고", 24, "text"),
]

_WEEKLY_COLUMNS = [
    ("주차", "주차", 8, "text"), ("기간", "기간", 14, "text"),
    ("예상입금", "예상입금", 14, "money"),
    ("송금예정", "송금예정", 13, "money"),
    ("카드결제", "카드결제", 12, "money"),
    ("자동이체", "자동이체", 12, "money"),
    ("기타지출", "기타지출", 12, "money"),
    ("순현금흐름", "순현금흐름", 13, "money"),
    ("기말잔액", "기말잔액", 14, "money"), ("상태", "상태", 9, "text"),
]

_PLAN_COLUMNS = [
    ("요청ID", "요청ID", 18, "text"), ("팀명", "팀명", 13, "text"),
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

_RECURRING_COLUMNS = [
    ("은행", "은행", 10, "text"), ("정기지출명", "정기지출명", 20, "text"),
    ("분류", "분류", 16, "text"), ("발생개월수", "발생개월수", 10, "int"),
    ("거래건수", "거래건수", 9, "int"),
    ("평균 월지출", "평균 월지출", 14, "money"),
    ("최소 월지출", "최소 월지출", 14, "money"),
    ("최대 월지출", "최대 월지출", 14, "money"),
    ("대표 지급일", "대표 지급일", 10, "int"), ("신뢰도", "신뢰도", 8, "text"),
]

_BANK_COLUMNS = [
    ("거래일시", "거래일시", 18, "text"), ("거래일", "거래일", 12, "date"),
    ("은행", "은행", 9, "text"), ("계좌", "계좌", 16, "text"),
    ("출금액", "출금액", 13, "money"), ("입금액", "입금액", 13, "money"),
    ("거래후잔액", "거래후잔액", 14, "money"),
    ("적요", "적요", 14, "text"),
    ("기재내용·상대방", "기재내용·상대방", 22, "text"),
    ("취급점", "취급점", 10, "text"), ("자동분류", "자동분류", 15, "text"),
    ("내부이체", "내부이체", 8, "text"),
    ("정기지출후보", "정기지출후보", 10, "text"),
    ("현금유출입", "현금유출입", 13, "money"),
    ("원본파일", "원본파일", 24, "text"), ("반영상태", "반영상태", 10, "text"),
]

_ISSUE_COLUMNS = [
    ("구분", "구분", 18, "text"), ("팀명", "팀명", 13, "text"),
    ("은행", "은행", 10, "text"), ("요청ID", "요청ID", 18, "text"),
    ("내용", "내용", 50, "text"), ("원본파일", "원본파일", 26, "text"),
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
        # 대외비: 지출내용 분류 기준 집계 (상세 미노출)
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


def _sheet_config(ws, report: dict) -> None:
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 70
    ws["A1"] = "설정 및 분류 기준"
    ws["A1"].font = _TITLE_FONT
    r = 3
    for label, value in report.get("config_summary", []):
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, size=10)
        ws.cell(row=r, column=2, value=str(value))
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="자동분류 규칙(JSON)").font = Font(bold=True)
    r += 1
    rules_text = json.dumps(report.get("classify_rules", {}),
                            ensure_ascii=False, indent=2)
    for line in rules_text.splitlines():
        ws.cell(row=r, column=1, value=line)
        r += 1


_OPERATION_GUIDE = [
    "업데이트·운영 안내",
    "",
    "1. 매주 금요일: 각 팀에 다음 주 지출계획 양식 제출을 요청한다.",
    "2. 매주 월요일 오전 9시 전까지:",
    "   - 팀 파일을 01_일반팀_지출계획 / 02_경영지원_대외비 폴더에 저장",
    "   - 농협·우리은행·국민은행에서 최근 14일 거래내역을 내려받아",
    "     03_은행거래내역의 은행별 폴더에 저장",
    "3. 월요일 오전 9시 10분에 프로그램이 자동 실행된다.",
    "   PC가 꺼져 있었다면 켠 뒤 프로그램이 시작되면 자동으로 보완 실행된다.",
    "4. 결과는 05_결과 폴더에 저장된다 (같은 날 여러 번 실행해도 덮어쓰지 않음).",
    "5. 확인필요 파일(06_확인필요·확인필요 시트)을 열어 오류 건을 처리한다.",
    "   오류 건은 임의로 삭제하거나 0원 처리하지 않는다.",
    "6. 실행 후 팀/은행 파일이 바뀌면 트레이 알림이 뜬다.",
    "   '변경자료 반영' 메뉴로만 다시 생성한다 (자동 재생성 없음).",
    "7. 카드 결제일 기준이 바뀌면 04_기준파일의 카드결제기준 시트를 수정한다.",
    "8. 자동분류 키워드는 00_프로그램/classify_rules.json에서 수정한다.",
    "9. 로그는 07_실행로그, 입력 백업은 08_백업에 보관된다.",
]


def _sheet_operations(ws) -> None:
    ws.column_dimensions["A"].width = 90
    for r, line in enumerate(_OPERATION_GUIDE, start=1):
        cell = ws.cell(row=r, column=1, value=line)
        if r == 1:
            cell.font = _TITLE_FONT


# ---------------------------------------------------------------------------
# 파일 생성
# ---------------------------------------------------------------------------

def create_report_workbook(report: dict, out_path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    _sheet_summary(wb.create_sheet("요약"), report)
    _write_table(wb.create_sheet("4주일별계획"), _DAILY_COLUMNS,
                 report["forecast"].get("daily", []), state_key="상태")
    _write_table(wb.create_sheet("13주주별계획"), _WEEKLY_COLUMNS,
                 report["forecast"].get("weekly", []), state_key="상태")
    _write_table(wb.create_sheet("팀지출계획_통합"), _PLAN_COLUMNS,
                 report.get("integrated_masked", []), state_key="반영상태")
    match_rows = _mask_match_rows(report.get("match_results", []),
                                  report.get("unplanned", []))
    _write_table(wb.create_sheet("예정실제대조"), _MATCH_COLUMNS,
                 match_rows, state_key="대조결과")
    _write_table(wb.create_sheet("정기지출분석"), _RECURRING_COLUMNS,
                 report.get("recurring", []))
    bank_rows = [dict(r, 내부이체="예" if r.get("내부이체") else "",
                      정기지출후보="예" if r.get("정기지출후보") else "")
                 for r in report.get("bank_rows", [])]
    _write_table(wb.create_sheet("계좌내역통합_RAW"), _BANK_COLUMNS,
                 bank_rows, state_key="반영상태")
    _write_table(wb.create_sheet("확인필요"), _ISSUE_COLUMNS,
                 report.get("issues", []))
    _write_table(wb.create_sheet("카드결제기준"), _CARD_COLUMNS,
                 report.get("card_rules", []))
    _sheet_config(wb.create_sheet("설정및분류"), report)
    _sheet_operations(wb.create_sheet("업데이트운영"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


def create_issue_workbook(issues: list[dict], out_path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "확인필요"
    _write_table(ws, _ISSUE_COLUMNS, issues)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    wb.close()
    return out_path


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
