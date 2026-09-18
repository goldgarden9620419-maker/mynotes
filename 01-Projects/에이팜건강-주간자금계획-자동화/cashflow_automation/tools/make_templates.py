# -*- coding: utf-8 -*-
"""팀별 제출양식(자동화 서식 v2)·경영지원 대외비 양식·기준파일 생성.

실행:
    python tools/make_templates.py [출력폴더]

직원이 직접 입력하는 칸은 6개뿐이다:
    최초등록일 · 지급예정일 · 거래처 · 지출내용 · 예상금액 · 지급방법
나머지는 수식이 자동 처리한다:
    요청ID / 팀코드 / 팀명 / 일련번호(같은 날 자동 순번) /
    확정여부(기본 '확정') / 진행상태(기본 '신규') / 최종수정일(기본 등록일) /
    입력확인(누락 실시간 표시)
자동 기본값 칸은 드롭다운으로 덮어쓸 수 있다(변경·취소 시).
요청ID·입력확인 열만 잠그고 시트 보호(암호: apharm)한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableColumn, TableStyleInfo

from common import (
    CONFIDENTIAL_CATEGORIES, CONFIRM_VALUES, PAY_METHODS, PROGRESS_VALUES,
    REQUIRED_TEAM_COLUMNS, TEAMS,
)
from card_payment import CARD_SHEET_COLUMNS, CARD_SHEET_NAME, DEFAULT_CARD_RULES

SHEET_PASSWORD = "apharm"
DATA_ROWS = 200
FONT_NAME = "맑은 고딕"

# 열 성격: 직원이 입력하는 열 / 자동(수식) 열
INPUT_COLUMNS = {"최초등록일", "지급예정일", "거래처", "지출내용", "예상금액",
                 "지급방법", "카드구분", "비고", "대외비구분"}
LOCKED_COLUMNS = {"요청ID", "입력확인"}

_AUTO_HEADER_FILL = PatternFill("solid", start_color="1F4E79")   # 자동: 남색
_INPUT_HEADER_FILL = PatternFill("solid", start_color="FFD966")  # 입력: 노랑
_INPUT_HEADER_FONT = Font(name=FONT_NAME, bold=True, size=10,
                          color="1F1F1F")
_AUTO_HEADER_FONT = Font(name=FONT_NAME, color="FFFFFF", bold=True, size=10)
_BODY_FONT = Font(name=FONT_NAME, size=10)
_THIN = Side(style="thin", color="C0C0C0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_FILL_MISSING = PatternFill("solid", start_color="FFC7CE")   # 빨강: 필수 누락
_FILL_CARD = PatternFill("solid", start_color="FFEB9C")      # 노랑: 카드구분 필요

_COLUMN_WIDTHS = {
    "요청ID": 19, "팀코드": 8, "팀명": 13, "최초등록일": 12, "일련번호": 8,
    "지급예정일": 12, "거래처": 18, "지출내용": 28, "예상금액": 13,
    "지급방법": 11, "카드구분": 11, "확정여부": 9, "진행상태": 9,
    "최종수정일": 12, "비고": 18, "대외비구분": 21, "입력확인": 16,
}


def _dv(values: list[str], ranges: str, title: str = "",
        prompt: str = "") -> DataValidation:
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"',
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="입력 오류",
                        error="목록에서 선택해 주세요.",
                        showInputMessage=bool(prompt),
                        promptTitle=title or None, prompt=prompt or None)
    dv.add(ranges)
    return dv


def _active_pred(r: int, exclude: str = "") -> str:
    """행에 내용이 있는지 판단하는 수식 조각. exclude 열은 제외."""
    cols = [c for c in ("D", "F", "G", "H", "I") if c != exclude]
    return "OR(" + ",".join(f"${c}{r}<>\"\"" for c in cols) + ")"


def _missing_count(r: int) -> str:
    return (f'($D{r}="")+($F{r}="")+($I{r}="")+($J{r}="")'
            f'+IF(AND($J{r}="법인카드",$K{r}=""),1,0)')


def create_team_template(path: Path, team: dict) -> Path:
    confidential = bool(team.get("confidential"))
    columns = list(REQUIRED_TEAM_COLUMNS)          # A~O (15열)
    if confidential:
        columns.append("대외비구분")               # P
    columns.append("입력확인")                     # P 또는 Q
    check_col = get_column_letter(len(columns))

    wb = Workbook()
    ws = wb.active
    ws.title = "지출계획"

    # ── 헤더 ──────────────────────────────────────────────
    for c, name in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        if name in INPUT_COLUMNS:
            cell.fill = _INPUT_HEADER_FILL
            cell.font = _INPUT_HEADER_FONT
        else:
            cell.fill = _AUTO_HEADER_FILL
            cell.font = _AUTO_HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = \
            _COLUMN_WIDTHS.get(name, 12)
    ws.row_dimensions[1].height = 22

    # ── 데이터 행 (수식 자동화) ───────────────────────────
    last_row = 1 + DATA_ROWS
    code = team["code"]
    for r in range(2, last_row + 1):
        # A 요청ID (11번 항목 수식)
        ws.cell(row=r, column=1, value=(
            f'=IF(OR(B{r}="",D{r}="",E{r}=""),"",'
            f'B{r}&"-"&TEXT(D{r},"yyyymmdd")&"-"&TEXT(E{r},"000"))'))
        # B 팀코드 / C 팀명: 행에 내용이 생기면 자동 표기
        ws.cell(row=r, column=2,
                value=f'=IF({_active_pred(r)},"{code}","")')
        ws.cell(row=r, column=3,
                value=f'=IF({_active_pred(r)},"{team["name"]}","")')
        # E 일련번호: 같은 최초등록일의 몇 번째 행인지 자동 계산
        ws.cell(row=r, column=5,
                value=f'=IF($D{r}="","",COUNTIF($D$2:$D{r},$D{r}))')
        # L 확정여부 / M 진행상태 기본값 (덮어쓰기 가능)
        ws.cell(row=r, column=12,
                value=f'=IF(OR($G{r}<>"",$I{r}<>""),"확정","")')
        ws.cell(row=r, column=13,
                value=f'=IF(OR($G{r}<>"",$I{r}<>""),"신규","")')
        # N 최종수정일 기본값 = 최초등록일 (변경 시 직접 수정)
        ws.cell(row=r, column=14, value=f'=IF($D{r}="","",$D{r})')
        # 입력확인 (마지막 열)
        mc = _missing_count(r)
        ws.cell(row=r, column=len(columns), value=(
            f'=IF(NOT({_active_pred(r)}),"",'
            f'IF({mc}=0,"✔ 완료","⚠ 누락 "&{mc}&"칸"))'))

        for c, name in enumerate(columns, start=1):
            cell = ws.cell(row=r, column=c)
            cell.border = _BORDER
            cell.font = _BODY_FONT
            cell.protection = Protection(locked=(name in LOCKED_COLUMNS))
            if name in ("최초등록일", "지급예정일", "최종수정일"):
                cell.number_format = "yyyy-mm-dd"
            elif name == "예상금액":
                cell.number_format = "#,##0"
            elif name == "일련번호":
                cell.number_format = "0"

    # ── 드롭다운 + 입력 도움말 ────────────────────────────
    def col_of(name: str) -> str:
        return get_column_letter(columns.index(name) + 1)

    rng = lambda name: f"{col_of(name)}2:{col_of(name)}{last_row}"
    ws.add_data_validation(_dv(
        PAY_METHODS, rng("지급방법"), "지급방법",
        "법인카드를 선택하면 카드구분도 선택하고,\n"
        "지급예정일에는 '카드 사용일'을 입력하세요."))
    ws.add_data_validation(_dv(
        ["우리카드", "국민카드"], rng("카드구분"), "카드구분",
        "지급방법이 법인카드일 때만 선택합니다."))
    ws.add_data_validation(_dv(
        CONFIRM_VALUES, rng("확정여부"), "확정여부",
        "자동으로 '확정'이 들어갑니다.\n아직 미정이면 '미확정'으로 바꾸세요."))
    ws.add_data_validation(_dv(
        PROGRESS_VALUES, rng("진행상태"), "진행상태",
        "새 요청은 '신규'(자동).\n내용이 바뀌면 '변경', 취소되면 '취소'로 "
        "바꾸고 최종수정일을 고치세요. 행은 지우지 마세요."))
    if confidential:
        ws.add_data_validation(_dv(
            CONFIDENTIAL_CATEGORIES, rng("대외비구분"), "대외비구분",
            "보고서에는 이 분류의 합계만 표시됩니다."))
    dv_date = DataValidation(
        type="date", operator="greaterThan", formula1="DATE(2020,1,1)",
        allow_blank=True, showErrorMessage=True, errorTitle="날짜 오류",
        error="날짜 형식(예: 2026-09-18)으로 입력하세요.",
        showInputMessage=True, promptTitle="최초등록일",
        prompt="이 요청을 '처음 적는 날'의 날짜입니다.\n"
               "일련번호·요청ID는 자동으로 만들어집니다.")
    dv_date.add(rng("최초등록일"))
    ws.add_data_validation(dv_date)

    # ── 조건부 서식: 누락 빨강, 카드구분 노랑, 입력확인 색 ─
    for name in ("최초등록일", "지급예정일", "예상금액", "지급방법"):
        col = col_of(name)
        ws.conditional_formatting.add(
            rng(name),
            FormulaRule(formula=[f'AND({_active_pred(2, exclude=col)},'
                                 f'{col}2="")'],
                        fill=_FILL_MISSING, stopIfTrue=False))
    ws.conditional_formatting.add(
        rng("카드구분"),
        FormulaRule(formula=[f'AND($J2="법인카드",{col_of("카드구분")}2="")'],
                    fill=_FILL_CARD, stopIfTrue=False))
    ws.conditional_formatting.add(
        f"{check_col}2:{check_col}{last_row}",
        FormulaRule(formula=[f'LEFT({check_col}2,1)="⚠"'],
                    font=Font(name=FONT_NAME, size=10, bold=True,
                              color="9C0006"), stopIfTrue=False))
    ws.conditional_formatting.add(
        f"{check_col}2:{check_col}{last_row}",
        FormulaRule(formula=[f'LEFT({check_col}2,1)="✔"'],
                    font=Font(name=FONT_NAME, size=10, bold=True,
                              color="006100"), stopIfTrue=False))

    # ── 표(구조화 참조) ───────────────────────────────────
    table_ref = f"A1:{get_column_letter(len(columns))}{last_row}"
    table = Table(displayName="tbl_지출계획", ref=table_ref,
                  tableColumns=[TableColumn(id=i + 1, name=name)
                                for i, name in enumerate(columns)])
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2",
                                          showRowStripes=True)
    ws.add_table(table)

    # ── 시트 보호: 요청ID·입력확인만 잠금 ────────────────
    ws.protection.sheet = True
    ws.protection.password = SHEET_PASSWORD
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.protection.sort = True
    ws.protection.autoFilter = True

    ws.freeze_panes = "D2"
    _guide_sheet(wb, team, confidential)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    wb.close()
    return path


def _guide_sheet(wb: Workbook, team: dict, confidential: bool) -> None:
    ws = wb.create_sheet("사용안내")
    ws.sheet_view.showGridLines = False
    for col, width in (("A", 4), ("B", 16), ("C", 30), ("D", 44)):
        ws.column_dimensions[col].width = width

    def put(row, col, value, bold=False, size=10, color="1F1F1F",
            fill=None):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = Font(name=FONT_NAME, size=size, bold=bold, color=color)
        if fill:
            cell.fill = PatternFill("solid", start_color=fill)
        return cell

    r = 1
    put(r, 2, f"[{team['name']}] 주간 지출계획 — 작성 안내", bold=True,
        size=14, color="1F4E79"); r += 2
    put(r, 2, "딱 6칸만 입력하면 됩니다. 나머지는 자동입니다.", bold=True,
        size=11); r += 2

    put(r, 2, "직접 입력 (노란 머리글)", bold=True, fill="FFD966")
    put(r, 3, "무엇을", bold=True)
    put(r, 4, "예시", bold=True); r += 1
    for name, what, example in [
        ("최초등록일", "이 요청을 처음 적는 날", "2026-09-18"),
        ("지급예정일", "돈이 나가야 하는 날 (법인카드는 카드 사용일)", "2026-09-24"),
        ("거래처", "돈 받는 곳", "한진택배"),
        ("지출내용", "무엇에 쓰는 돈인지", "9월 4주차 택배비"),
        ("예상금액", "숫자만 (원)", "1,250,000"),
        ("지급방법", "드롭다운에서 선택", "계좌송금"),
    ]:
        put(r, 2, name, fill="FFF2CC")
        put(r, 3, what)
        put(r, 4, example, color="0000FF")
        r += 1
    r += 1
    put(r, 2, "자동 처리 (남색 머리글)", bold=True, fill="1F4E79")
    ws.cell(row=r, column=2).font = Font(name=FONT_NAME, bold=True,
                                         color="FFFFFF", size=10); r += 1
    for name, what in [
        ("요청ID·일련번호", "등록일을 넣으면 자동 생성 (예: "
                        f"{team['code']}-20260918-001)"),
        ("팀코드·팀명", "자동 표기"),
        ("확정여부", "자동 '확정' — 아직 미정이면 '미확정'으로 바꾸세요"),
        ("진행상태", "자동 '신규' — 바뀌면 '변경', 취소면 '취소' 선택"),
        ("최종수정일", "자동으로 등록일과 같게 — 내용 수정 시 그날 날짜로 변경"),
        ("입력확인", "'✔ 완료'가 뜨면 끝. '⚠ 누락'이면 빨간 칸을 채우세요"),
    ]:
        put(r, 2, name, fill="DEEBF7")
        put(r, 3, what)
        r += 1
    r += 1
    put(r, 2, "꼭 지켜주세요", bold=True, size=11, color="9C0006"); r += 1
    rules = [
        "행을 삭제하지 마세요. 취소된 건은 진행상태를 '취소'로 바꾸면 됩니다.",
        "금액·날짜가 바뀌면 그 행에서 고치고 진행상태 '변경' + 최종수정일 수정.",
        "법인카드는 카드구분(우리/국민)을 고르고 지급예정일에 '사용일'을 입력.",
        "월요일 오전 9시 전까지 지정 폴더에 저장하면 자동으로 취합됩니다.",
        "열 이름·시트명·파일명은 바꾸지 마세요 (자동 취합이 인식하지 못합니다).",
    ]
    if confidential:
        rules += [
            "이 파일은 대외비입니다. 02_경영지원_대외비 폴더 밖으로 옮기지 마세요.",
            "대외비구분을 선택하면 보고서에는 분류별 합계만 표시됩니다.",
        ]
    for i, rule in enumerate(rules, start=1):
        put(r, 2, f"{i}.")
        put(r, 3, rule)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        r += 1
    r += 1
    put(r, 2, "※ 시트가 보호되어 있어 자동 칸(요청ID·입력확인)은 수정되지 "
              "않습니다. 서식 관리는 자금 담당자에게 문의하세요.",
        color="808080")


def create_base_workbook(path: Path) -> Path:
    wb = Workbook()

    ws = wb.active
    ws.title = "안내"
    ws.column_dimensions["A"].width = 95
    for r, line in enumerate([
        "(주)에이팜건강 자금계획 기준파일",
        "",
        "· 카드결제기준: 법인카드 결제일 계산 기준. 실제 카드 약정에 맞게",
        "  결제일과 이용기간을 반드시 수정해 주세요.",
        "  이용기간은 '전전월/전월/당월 N일' 또는 '… 말일' 형식으로 입력합니다.",
        "· 주간조정: 자금계획에 수동으로 반영할 입금/지출 조정액을 입력합니다.",
        "  (예: 일회성 대출 상환, 투자금 입금 등)",
        "· 계좌목록: 회사 계좌 목록(참고용). 내부이체 판정 키워드는",
        "  00_프로그램/classify_rules.json에서 관리합니다.",
        "· 이 파일은 04_기준파일 폴더에 두고 파일명을 바꾸지 않습니다.",
    ], start=1):
        cell = ws.cell(row=r, column=1, value=line)
        cell.font = Font(name=FONT_NAME, size=10,
                         bold=(r == 1), color="1F4E79" if r == 1 else "1F1F1F")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet(CARD_SHEET_NAME)
    for c, name in enumerate(CARD_SHEET_COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill = _AUTO_HEADER_FILL
        cell.font = _AUTO_HEADER_FONT
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = 16
    for r, rule in enumerate(DEFAULT_CARD_RULES, start=2):
        for c, name in enumerate(CARD_SHEET_COLUMNS, start=1):
            cell = ws.cell(row=r, column=c, value=rule.get(name))
            cell.border = _BORDER
            cell.font = _BODY_FONT
    ws.add_data_validation(_dv(["사용", "미사용"], "G2:G20"))

    ws = wb.create_sheet("주간조정")
    for c, (name, width) in enumerate([("일자", 12), ("조정입금", 14),
                                       ("조정지출", 14), ("내용", 40)],
                                      start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill = _AUTO_HEADER_FILL
        cell.font = _AUTO_HEADER_FONT
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = width
    for r in range(2, 102):
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=2).number_format = "#,##0"
        ws.cell(row=r, column=3).number_format = "#,##0"

    ws = wb.create_sheet("계좌목록")
    for c, (name, width) in enumerate([("은행", 12), ("계좌번호", 22),
                                       ("용도", 30)], start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill = _AUTO_HEADER_FILL
        cell.font = _AUTO_HEADER_FONT
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = width
    for r, (bank, note) in enumerate([("농협", "수금(소액)·콕송금"),
                                      ("우리은행", "스마트스토어 정산·세금"),
                                      ("국민은행", "주거래·급여"),
                                      ("국민은행", "보험·네이버 정산용")],
                                     start=2):
        ws.cell(row=r, column=1, value=bank).font = _BODY_FONT
        ws.cell(row=r, column=3, value=note).font = _BODY_FONT

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    wb.close()
    return path


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 \
        else Path(__file__).resolve().parent.parent.parent / "양식"
    created = []
    for team in TEAMS:
        created.append(create_team_template(out_dir / team["file"], team))
    created.append(create_base_workbook(
        out_dir / "에이팜건강_자금계획_기준파일.xlsx"))
    for p in created:
        print("생성:", p)


if __name__ == "__main__":
    main()
