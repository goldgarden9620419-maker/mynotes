# -*- coding: utf-8 -*-
"""입금 예측과 4주 일별 / 13주 주별 자금계획, 정기지출 분석 (21~24번).

- 온라인 입금: 최근 12주 요일별 평균 × 반영률(기본 80%)
- 4주 일별: 팀 확정 지출 + 주간조정
- 13주 주별: 1~4주는 일별 합산, 5~13주는 요일평균·팀계획·정기지출·카드
- 정기지출: 최근 6개월 중 4개월 이상 반복된 출금
"""
from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Optional

from common import (
    BANK_REFLECT_OK, PAY_METHOD_AUTO, PAY_METHOD_CARD, PAY_METHOD_TRANSFER,
    REFLECT_OK, normalize_text, parse_amount, parse_date, weekday_ko,
    week_monday,
)
from bank_classifier import CLASS_ONLINE_SALES

STATE_OK = "정상"
STATE_WARN = "주의"
STATE_SHORTAGE = "자금부족"

ADJUST_SHEET_NAME = "주간조정"


# ---------------------------------------------------------------------------
# 주간조정 시트 (기준파일, 선택사항)
# ---------------------------------------------------------------------------

def load_adjustments(base_workbook: Path) -> list[dict]:
    """기준파일의 '주간조정' 시트: 일자·조정입금·조정지출·내용."""
    base_workbook = Path(base_workbook)
    if not base_workbook.exists():
        return []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook, data_only=True, read_only=True)
    except Exception:
        return []
    try:
        sheet = None
        for name in wb.sheetnames:
            if normalize_text(name) == ADJUST_SHEET_NAME:
                sheet = wb[name]
                break
        if sheet is None:
            return []
        rows = list(sheet.iter_rows(values_only=True))
        header_idx = None
        header: list[str] = []
        for i, row in enumerate(rows[:10]):
            values = [normalize_text(v) for v in row]
            if "일자" in values:
                header_idx, header = i, values
                break
        if header_idx is None:
            return []
        result = []
        for row in rows[header_idx + 1:]:
            raw = {header[i]: row[i] for i in range(min(len(header), len(row)))
                   if header[i]}
            d = parse_date(raw.get("일자"))
            if d is None:
                continue
            result.append({
                "일자": d,
                "조정입금": parse_amount(raw.get("조정입금")) or 0.0,
                "조정지출": parse_amount(raw.get("조정지출")) or 0.0,
                "내용": normalize_text(raw.get("내용")),
            })
        return result
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# 자동추정 지출 목록 (별도 파일로 관리)
# ---------------------------------------------------------------------------

AUTO_DRAFT_FILE = "자동추정_지출목록.xlsx"
AUTO_DRAFT_SHEET = "자동추정"
ALIAS_SHEET = "별칭"
_DRAFT_PREFIX = "정기지출 추정(자동 초안): "
_DRAFT_HEADERS = ["일자", "정기지출명", "예상금액", "신뢰도", "반영", "메모"]
# 은행 기록명과 취합파일 표기가 다른 대표 사례 (시트 생성 시 예시로 넣음)
_ALIAS_SEED = [("NH기업카드", "농협카드")]
GUIDE_SHEET = "안내"
BULK_MODES = ("개별 관리", "전체 반영", "전체 제외")
_BULK_ROW = 6            # 안내 시트: A6 라벨, B6 선택, D6 적용 기록


def _draft_content(name: str, confidence: str) -> str:
    return f"{_DRAFT_PREFIX}{name} 신뢰도 {confidence or '중'}"


def _ensure_bulk_control(wb, default_mode: str = "개별 관리") -> str:
    """안내 시트의 '일괄 설정' 칸(반영/제외 일괄 스위치)을 보장한다.

    B6에 '전체 반영'/'전체 제외'를 선택해 두면 다음 실행 때 자동추정
    시트의 모든 행에 한 번에 적용된다(적용 기록은 D6). 반환: 현재 모드.
    """
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    ws = (wb[GUIDE_SHEET] if GUIDE_SHEET in wb.sheetnames
          else wb.create_sheet(GUIDE_SHEET, 0))
    label = ws.cell(row=_BULK_ROW, column=1)
    mode_cell = ws.cell(row=_BULK_ROW, column=2)
    if not normalize_text(label.value):
        label.value = "일괄 설정"
        label.font = Font(name="맑은 고딕", bold=True, size=10)
        ws.cell(row=_BULK_ROW + 1, column=1,
                value="'전체 반영' 또는 '전체 제외'를 선택해 두면 다음 실행 때 "
                      "자동추정 시트의 모든 행에 한 번에 적용됩니다. "
                      "적용된 뒤 개별 행을 다시 바꾸는 것은 자유입니다.")
    if not normalize_text(mode_cell.value):
        mode_cell.value = default_mode
    mode_cell.fill = PatternFill("solid", start_color="FFF2CC")
    mode_cell.font = Font(name="맑은 고딕", bold=True, size=10)
    if not any("전체" in str(dv.formula1 or "")
               for dv in ws.data_validations.dataValidation):
        dv = DataValidation(type="list",
                            formula1='"개별 관리,전체 반영,전체 제외"',
                            allow_blank=True)
        dv.error = "개별 관리 / 전체 반영 / 전체 제외 중 하나만 고를 수 있습니다."
        dv.showErrorMessage = True
        ws.add_data_validation(dv)
        dv.add(mode_cell.coordinate)
    mode = normalize_text(mode_cell.value)
    return mode if mode in BULK_MODES else "개별 관리"


def _apply_bulk_mode(wb, ws, mode: str) -> int:
    """일괄 설정이 바뀌었으면 모든 행의 반영 열에 적용한다. 반환: 변경 행 수."""
    from openpyxl.styles import Font

    guide = wb[GUIDE_SHEET]
    applied_cell = guide.cell(row=_BULK_ROW, column=4)
    applied = str(applied_cell.value or "")
    changed = 0
    if mode in ("전체 반영", "전체 제외") and mode not in applied:
        flag = "반영" if mode == "전체 반영" else "제외"
        for r in range(2, ws.max_row + 1):
            if ws.cell(row=r, column=1).value is None \
                    and ws.cell(row=r, column=2).value is None:
                continue
            if ws.cell(row=r, column=5).value != flag:
                ws.cell(row=r, column=5, value=flag)
                changed += 1
    applied_cell.value = f"(마지막 적용: {mode})"
    applied_cell.font = Font(name="맑은 고딕", size=9, color="888888")
    return changed


def _style_draft_sheet(ws) -> None:
    """자동추정 시트를 보기 좋은 표로 꾸민다 (매 실행 재적용).

    남색 머리글, 얇은 테두리, 일자·금액 서식, 머리글 필터, 틀 고정,
    그리고 반영 열이 '제외'인 행은 회색 처리(조건부서식이라 드롭다운을
    바꾸면 즉시 색이 바뀐다).
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.formatting.rule import FormulaRule

    thin = Border(*(Side(style="thin", color="BBBBBB"),) * 4)
    for c in range(1, len(_DRAFT_HEADERS) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = PatternFill("solid", start_color="1F4E79")
        cell.font = Font(name="맑은 고딕", bold=True, color="FFFFFF",
                         size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin
    last = max(ws.max_row, 2)
    for r in range(2, last + 1):
        if ws.cell(row=r, column=2).value is None \
                and ws.cell(row=r, column=1).value is None:
            continue
        for c in range(1, len(_DRAFT_HEADERS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = thin
            cell.font = Font(name="맑은 고딕", size=10)
            if c == 1:
                cell.number_format = "yyyy-mm-dd"
            elif c == 3:
                cell.number_format = "#,##0"
            if c in (4, 5):
                cell.alignment = Alignment(horizontal="center")
    ws.auto_filter.ref = f"A1:F{last}"
    ws.freeze_panes = "A2"
    has_gray = any(
        r.formula and "제외" in str(r.formula[0])
        for rules in ws.conditional_formatting for r in rules.rules)
    if not has_gray:
        ws.conditional_formatting.add(
            "A2:F500",
            FormulaRule(formula=['$E2="제외"'],
                        fill=PatternFill("solid", start_color="E0E0E0")))


def _sort_draft_rows(ws) -> None:
    """데이터 행을 일자순(같은 날은 금액 큰 순)으로 다시 쓴다."""
    rows = []
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value
                  for c in range(1, len(_DRAFT_HEADERS) + 1)]
        if any(v is not None and str(v).strip() != "" for v in values):
            rows.append(values)
    rows.sort(key=lambda v: (parse_date(v[0]) or date.max,
                             -(parse_amount(v[2]) or 0)))
    for i, values in enumerate(rows, start=2):
        for c, v in enumerate(values, start=1):
            ws.cell(row=i, column=c, value=v)
    for r in range(len(rows) + 2, ws.max_row + 1):
        for c in range(1, len(_DRAFT_HEADERS) + 1):
            ws.cell(row=r, column=c, value=None)


def _ensure_draft_dropdown(ws) -> bool:
    """반영 열(E)에 '반영/제외' 드롭다운을 보장한다. 추가 시 True."""
    for dv in ws.data_validations.dataValidation:
        if dv.formula1 and "반영" in str(dv.formula1):
            return False
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"반영,제외"',
                        allow_blank=True)
    dv.error = "'반영' 또는 '제외'만 입력할 수 있습니다."
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add("E2:E500")
    return True


def _ensure_alias_sheet(wb) -> bool:
    """'별칭' 시트를 보장한다. 새로 만들었으면 True.

    은행 기록명(자동추정 이름)과 취합파일 거래처 표기가 다를 때
    여기 연결해 두면, 같은 달에 취합 입력이 있는 자동추정은 금액
    차이와 무관하게 자동 제외된다 (카드대금처럼 금액이 변하는 정기
    지출용).
    """
    if ALIAS_SHEET in wb.sheetnames:
        return False
    ws = wb.create_sheet(ALIAS_SHEET)
    ws.append(["정기지출명", "별칭(쉼표로 여러 개)"])
    for name, alias in _ALIAS_SEED:
        ws.append([name, alias])
    ws["D1"] = ("같은 달에 취합 지출예정 파일에 별칭과 비슷한 항목이 있으면 "
                "해당 자동추정은 금액과 무관하게 제외됩니다.")
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 30
    return True


def _create_draft_workbook(draft_path: Path, rows: list[dict],
                           default_mode: str = "개별 관리") -> None:
    from openpyxl import Workbook
    wb = Workbook()
    guide = wb.active
    guide.title = GUIDE_SHEET
    guide["A1"] = "자동추정 지출 목록 — 은행 이력에서 추정한 정기지출입니다."
    guide["A2"] = ("'자동추정' 시트에서 일자·예상금액을 고치거나 반영 열을 "
                   "'제외'로 바꾸면 다음 실행부터 그대로 적용됩니다.")
    guide["A3"] = ("새로 발견되는 정기지출은 매 실행 때 자동으로 추가되고, "
                   "이미 있는 행(사용자 수정 포함)은 건드리지 않습니다.")
    guide["A4"] = ("'별칭' 시트: 은행 기록명과 취합파일 표기가 다르면 연결해 "
                   "두세요 — 같은 달 취합 입력이 있으면 자동추정이 제외됩니다.")
    _ensure_bulk_control(wb, default_mode)
    ws = wb.create_sheet(AUTO_DRAFT_SHEET)
    ws.append(_DRAFT_HEADERS)
    for r in sorted(rows, key=lambda x: (x["일자"], -x["예상금액"])):
        ws.append([r["일자"], r["정기지출명"], round(r["예상금액"]),
                   r.get("신뢰도") or "", r.get("반영") or "반영",
                   r.get("메모") or ""])
    for col, width in zip("ABCDEF", (12, 26, 14, 8, 8, 24)):
        ws.column_dimensions[col].width = width
    _ensure_draft_dropdown(ws)
    _ensure_alias_sheet(wb)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(draft_path)
    wb.close()


def migrate_auto_drafts(base_workbook: Path, draft_path: Path,
                        overrides: dict[str, dict],
                        default_mode: str = "개별 관리") -> int:
    """기준파일 주간조정의 '자동 초안' 지출 행을 목록 파일로 이관한다.

    목록 파일이 이미 있으면 아무것도 하지 않는다. 이관 후 주간조정
    시트에는 수동 조정과 입금 추정만 남는다. 성격이 변동·제외인
    항목은 목록에 '제외'로 표시해 둔다.
    """
    draft_path = Path(draft_path)
    if draft_path.exists():
        return 0
    drafts = []
    for a in load_adjustments(base_workbook):
        content = a.get("내용") or ""
        if "자동 초안" not in content or (a.get("조정지출") or 0) <= 0:
            continue
        m = re.search(r":\s*(.+?)\s*신뢰도\s*(\S*)", content)
        name = (m.group(1) if m else content).strip()
        conf = (m.group(2) if m else "").strip()
        ov = overrides.get(normalize_text(name), {})
        flag = "제외" if ov.get("성격") in ("변동", "제외") else "반영"
        drafts.append({"일자": a["일자"], "정기지출명": name,
                       "예상금액": a["조정지출"], "신뢰도": conf,
                       "반영": flag, "메모": ""})
    _create_draft_workbook(draft_path, drafts, default_mode)
    # 주간조정 시트에서 자동 초안 행 제거 (수동 조정·입금 추정은 유지)
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook)
        for name in wb.sheetnames:
            if normalize_text(name) == ADJUST_SHEET_NAME:
                ws = wb[name]
                for r in range(ws.max_row, 1, -1):
                    row_text = " ".join(str(c.value or "")
                                        for c in ws[r])
                    if "자동 초안" in row_text:
                        ws.delete_rows(r)
                wb.save(base_workbook)
                break
        wb.close()
    except Exception:
        pass  # 제거 실패해도 이중 반영은 실행부에서 걸러진다
    return len(drafts)


def refresh_auto_draft_file(draft_path: Path, recurring_items: list[dict],
                            base_date: date,
                            horizon_days: int = 27,
                            default_mode: str = "개별 관리",
                            holidays: Optional[dict] = None
                            ) -> tuple[int, int]:
    """정기지출 분석 결과로 목록 파일을 갱신한다.

    같은 (정기지출명, 연·월) 행이 없으면 4주(기준일+27일) 안에서만
    추가하고 — 5주차 이후는 13주 계획이 정기지출을 직접 배분하므로
    여기 넣으면 이중 반영된다 — 이미 있는 행은 사용자 수정 보존을
    위해 건드리지 않는다. 기준일 이전의 지난 행은 정리한다.
    안내 시트의 '일괄 설정'이 바뀌어 있으면 모든 행의 반영 열에
    한 번에 적용한다 (이후 개별 수정은 다시 보존).
    반환: (추가 건수, 정리 건수)
    """
    from openpyxl import load_workbook
    draft_path = Path(draft_path)
    if not draft_path.exists():
        _create_draft_workbook(draft_path, [], default_mode)
    wb = load_workbook(draft_path)
    if AUTO_DRAFT_SHEET not in wb.sheetnames:
        ws = wb.create_sheet(AUTO_DRAFT_SHEET)
        ws.append(_DRAFT_HEADERS)
    else:
        ws = wb[AUTO_DRAFT_SHEET]
    mode = _ensure_bulk_control(wb, default_mode)
    new_flag = "제외" if mode == "전체 제외" else "반영"
    existing: set[tuple] = set()
    pruned = 0
    for r in range(ws.max_row, 1, -1):
        name = normalize_text(ws.cell(row=r, column=2).value)
        d = parse_date(ws.cell(row=r, column=1).value)
        if not name and d is None:
            continue
        if d is not None and d < base_date:
            ws.delete_rows(r)
            pruned += 1
            continue
        # 주말·공휴일에 걸린 예정일은 다음 영업일로 옮긴다
        if d is not None:
            adj = adjust_to_business_day(d, holidays)
            if adj != d:
                ws.cell(row=r, column=1, value=adj)
                d = adj
        if name and d is not None:
            existing.add((name, d.year, d.month))
    added = 0
    end = base_date + timedelta(days=horizon_days)
    for item in recurring_items:
        name = normalize_text(item.get("정기지출명"))
        day = item.get("대표 지급일")
        amount = item.get("평균 월지출") or 0
        if not name or not day or amount <= 0:
            continue
        y, m = base_date.year, base_date.month
        while True:
            d = adjust_to_business_day(
                date(y, m, min(int(day), calendar.monthrange(y, m)[1])),
                holidays)
            if d > end:
                break
            if base_date <= d and (name, d.year, d.month) not in existing:
                ws.append([d, item.get("정기지출명"), round(amount),
                           item.get("신뢰도") or "", new_flag, ""])
                existing.add((name, d.year, d.month))
                added += 1
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    _apply_bulk_mode(wb, ws, mode)
    _ensure_draft_dropdown(ws)  # 이관 초기 파일에도 드롭다운 보장
    _ensure_alias_sheet(wb)
    _sort_draft_rows(ws)        # 일자순 정렬로 보기 좋게
    _style_draft_sheet(ws)      # 표 서식 재적용
    wb.save(draft_path)
    wb.close()
    return added, pruned


def read_draft_table(draft_path: Path) -> dict:
    """자동추정 목록 파일의 현재 일괄 모드와 전체 행을 읽는다.

    확인 파일의 '자동추정_지출목록' 시트를 만들 때 쓴다.
    반환: {"mode": 현재 일괄 설정, "rows": [(일자, 이름, 금액, 신뢰도,
    반영, 메모), ...]}
    """
    result = {"mode": "개별 관리", "rows": []}
    draft_path = Path(draft_path)
    if not draft_path.exists():
        return result
    try:
        from openpyxl import load_workbook
        wb = load_workbook(draft_path, data_only=True, read_only=True)
    except Exception:
        return result
    try:
        if GUIDE_SHEET in wb.sheetnames:
            mode_row = next(wb[GUIDE_SHEET].iter_rows(
                min_row=_BULK_ROW, max_row=_BULK_ROW, min_col=2, max_col=2,
                values_only=True), (None,))
            mode = normalize_text(mode_row[0] if mode_row else None)
            if mode in BULK_MODES:
                result["mode"] = mode
        if AUTO_DRAFT_SHEET not in wb.sheetnames:
            return result
        for row in wb[AUTO_DRAFT_SHEET].iter_rows(min_row=2, max_col=6,
                                                  values_only=True):
            d = parse_date(row[0] if len(row) > 0 else None)
            name = normalize_text(row[1] if len(row) > 1 else None)
            if d is None and not name:
                continue
            result["rows"].append(
                (d, name, parse_amount(row[2] if len(row) > 2 else None),
                 normalize_text(row[3] if len(row) > 3 else None),
                 normalize_text(row[4] if len(row) > 4 else None) or "반영",
                 normalize_text(row[5] if len(row) > 5 else None)))
        return result
    finally:
        wb.close()


def apply_review_draft_edits(review_path: Path, draft_path: Path) -> int:
    """확인 파일의 '자동추정_지출목록' 시트 수정을 목록 파일에 반영한다.

    확인 단계에서 사용자가 고친 일자·금액·반영/제외와 '일괄 설정'을
    원본 목록 파일(04_기준파일/자동추정_지출목록.xlsx)에 되쓴다.
    바뀐 것이 없으면 저장하지 않는다. 반환: 반영 건수(모드 변경 포함).
    """
    from common import (DRAFT_REVIEW_HEAD_ROW, DRAFT_REVIEW_MODE_CELL,
                        DRAFT_REVIEW_SHEET)
    from openpyxl import load_workbook

    review_path = Path(review_path)
    draft_path = Path(draft_path)
    if not review_path.exists() or not draft_path.exists():
        return 0
    try:
        rv = load_workbook(review_path, data_only=True, read_only=True)
    except Exception:
        return 0
    try:
        if DRAFT_REVIEW_SHEET not in rv.sheetnames:
            return 0
        ws = rv[DRAFT_REVIEW_SHEET]
        mode_row = next(ws.iter_rows(min_row=2, max_row=2, min_col=2,
                                     max_col=2, values_only=True), (None,))
        new_mode = normalize_text(mode_row[0] if mode_row else None)
        new_rows = []
        for row in ws.iter_rows(min_row=DRAFT_REVIEW_HEAD_ROW + 1,
                                max_col=6, values_only=True):
            d = parse_date(row[0] if len(row) > 0 else None)
            name = normalize_text(row[1] if len(row) > 1 else None)
            if d is None and not name:
                continue
            new_rows.append(
                (d, name, parse_amount(row[2] if len(row) > 2 else None),
                 normalize_text(row[3] if len(row) > 3 else None),
                 normalize_text(row[4] if len(row) > 4 else None) or "반영",
                 normalize_text(row[5] if len(row) > 5 else None)))
    finally:
        rv.close()

    current = read_draft_table(draft_path)
    mode_changed = new_mode in BULK_MODES and new_mode != current["mode"]
    rows_changed = new_rows != current["rows"]
    if not mode_changed and not rows_changed:
        return 0

    wb = load_workbook(draft_path)
    try:
        changed = 0
        if mode_changed:
            _ensure_bulk_control(wb, new_mode)
            wb[GUIDE_SHEET].cell(row=_BULK_ROW, column=2, value=new_mode)
            changed += 1
        if rows_changed:
            if AUTO_DRAFT_SHEET in wb.sheetnames:
                ws = wb[AUTO_DRAFT_SHEET]
                if ws.max_row > 1:
                    ws.delete_rows(2, ws.max_row - 1)
            else:
                ws = wb.create_sheet(AUTO_DRAFT_SHEET)
                ws.append(_DRAFT_HEADERS)
            old = {r[:2]: r for r in current["rows"]}
            for r in new_rows:
                ws.append(list(r))
                if old.get(r[:2]) != r:
                    changed += 1
            _ensure_draft_dropdown(ws)
            _sort_draft_rows(ws)
            _style_draft_sheet(ws)
        wb.save(draft_path)
        return changed
    finally:
        wb.close()


def load_draft_aliases(draft_path: Path) -> dict[str, list[str]]:
    """'별칭' 시트: 정기지출명(정규화) → 별칭 목록."""
    aliases: dict[str, list[str]] = {}
    draft_path = Path(draft_path)
    if not draft_path.exists():
        return aliases
    try:
        from openpyxl import load_workbook
        wb = load_workbook(draft_path, data_only=True, read_only=True)
    except Exception:
        return aliases
    try:
        if ALIAS_SHEET not in wb.sheetnames:
            return aliases
        for row in wb[ALIAS_SHEET].iter_rows(min_row=2, max_col=2,
                                             values_only=True):
            name = normalize_text(row[0] if len(row) > 0 else None)
            raw = str(row[1] or "") if len(row) > 1 else ""
            if not name or not raw.strip():
                continue
            aliases[name] = [a.strip() for a in raw.split(",") if a.strip()]
        return aliases
    finally:
        wb.close()


def load_auto_drafts(draft_path: Path, base_date: Optional[date] = None,
                     horizon_days: int = 27) -> tuple[list[dict], int]:
    """목록 파일에서 반영 대상 자동추정을 조정 형식으로 읽는다.

    base_date가 주어지면 4주(기준일+27일) 구간의 행만 반영한다 —
    그 밖의 미래 행은 해당 주가 오면 자동으로 반영된다.
    반환: (조정 목록, 제외 건수)
    """
    draft_path = Path(draft_path)
    result: list[dict] = []
    excluded = 0
    if not draft_path.exists():
        return result, excluded
    try:
        from openpyxl import load_workbook
        wb = load_workbook(draft_path, data_only=True, read_only=True)
    except Exception:
        return result, excluded
    try:
        if AUTO_DRAFT_SHEET not in wb.sheetnames:
            return result, excluded
        end = (base_date + timedelta(days=horizon_days)
               if base_date is not None else None)
        for row in wb[AUTO_DRAFT_SHEET].iter_rows(min_row=2, max_col=5,
                                                  values_only=True):
            d = parse_date(row[0] if len(row) > 0 else None)
            name = normalize_text(row[1] if len(row) > 1 else None)
            amount = parse_amount(row[2] if len(row) > 2 else None) or 0.0
            conf = normalize_text(row[3] if len(row) > 3 else None)
            flag = normalize_text(row[4] if len(row) > 4 else None)
            if d is None or not name or amount <= 0:
                continue
            if end is not None and d > end:
                continue  # 4주 밖 미래 행은 그 주가 오면 반영된다
            if flag.startswith("제외"):
                excluded += 1
                continue
            result.append({"일자": d, "조정입금": 0.0, "조정지출": amount,
                           "내용": _draft_content(name, conf)})
        return result, excluded
    finally:
        wb.close()


def load_auto_draft_rows(draft_path: Path,
                         start: Optional[date] = None,
                         end: Optional[date] = None) -> list[dict]:
    """목록 파일의 모든 행(반영·제외 포함)을 상태와 함께 읽는다."""
    draft_path = Path(draft_path)
    rows: list[dict] = []
    if not draft_path.exists():
        return rows
    try:
        from openpyxl import load_workbook
        wb = load_workbook(draft_path, data_only=True, read_only=True)
    except Exception:
        return rows
    try:
        if AUTO_DRAFT_SHEET not in wb.sheetnames:
            return rows
        for row in wb[AUTO_DRAFT_SHEET].iter_rows(min_row=2, max_col=5,
                                                  values_only=True):
            d = parse_date(row[0] if len(row) > 0 else None)
            name = normalize_text(row[1] if len(row) > 1 else None)
            amount = parse_amount(row[2] if len(row) > 2 else None) or 0.0
            conf = normalize_text(row[3] if len(row) > 3 else None)
            flag = normalize_text(row[4] if len(row) > 4 else None)
            if d is None or not name or amount <= 0:
                continue
            if (start is not None and d < start) \
                    or (end is not None and d > end):
                continue
            rows.append({"일자": d, "정기지출명": name, "예상금액": amount,
                         "신뢰도": conf,
                         "반영": "제외" if flag.startswith("제외") else "반영"})
        return rows
    finally:
        wb.close()


# 금주 정기지출 체크의 판정 문구
CHECK_MISSING = "누락 의심 — 팀 재제출 요청"
CHECK_TEAM_OK = "팀 계획 반영"
CHECK_ACTUAL = "실제 금액 반영 (자동추정 제외)"
CHECK_AUTO = "자동 반영 (평균 금액)"


def weekly_recurring_check(draft_rows: list[dict],
                           countable_plans: list[dict],
                           aliases: dict[str, list[str]] | None,
                           start: date, end: date,
                           variable_items: list[dict] | None = None,
                           name_threshold: int = 60,
                           holidays: Optional[dict] = None) -> list[dict]:
    """실행 구간(start~end)에 도래하는 정기지출의 팀 제출 여부를 대조한다.

    자동추정 목록의 행(반영·제외)과 성격 '변동' 정기지출(목록에 없는
    달 포함)을 대상으로, 같은 달 팀 지출예정(취합)에 이름이 이어지는
    입력이 있는지 본다. '제외'·'변동'인데 팀 입력이 없으면 누락 의심 —
    팀에 지출예정 재제출을 요청할 항목이다.
    """
    from rapidfuzz import fuzz

    aliases = aliases or {}
    plans = []
    for p in countable_plans:
        d = p.get("자금계획 반영일")
        amt = p.get("예상금액") or 0.0
        if d is None or amt <= 0:
            continue
        name = " ".join(str(p.get(k) or "") for k in ("거래처", "지출내용"))
        plans.append((d, amt, name.lower()))

    entries = []
    seen: set[tuple] = set()
    for row in draft_rows:
        d = row.get("일자")
        if d is None or not (start <= d <= end):
            continue
        entries.append({"예정일": d, "항목": row.get("정기지출명") or "",
                        "예상금액": row.get("예상금액") or 0.0,
                        "관리상태": row.get("반영") or "반영"})
        seen.add((normalize_text(row.get("정기지출명")), d.year, d.month))
    # 성격 '변동' 항목은 목록에서 지워져도 매월 도래하므로 직접 만든다
    for item in (variable_items or []):
        name = item.get("정기지출명") or ""
        day = item.get("대표 지급일")
        amount = item.get("평균 월지출") or 0.0
        if not name or not day:
            continue
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            d = adjust_to_business_day(
                date(y, m, min(int(day), calendar.monthrange(y, m)[1])),
                holidays)
            key = (normalize_text(name), y, m)
            if start <= d <= end and key not in seen:
                entries.append({"예정일": d, "항목": name,
                                "예상금액": amount, "관리상태": "변동"})
                seen.add(key)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    entries = sorted(entries, key=lambda x: (x["예정일"], -x["예상금액"]))
    # 취합 입력 한 건은 정기지출 한 항목만 커버한다 — 유사도가 높은
    # 짝부터 배정해, 같은 달 카드대금 한 건이 여러 카드 추정을 모두
    # '제출됨'으로 만드는 착시를 막는다
    pairs = []
    for i, e in enumerate(entries):
        names = [str(e["항목"]).lower()] + [
            a.lower() for a in aliases.get(normalize_text(e["항목"]), [])]
        for j, (d, _amt, plan_name) in enumerate(plans):
            if (d.year, d.month) != (e["예정일"].year, e["예정일"].month):
                continue
            score = max(fuzz.partial_ratio(n, plan_name) for n in names)
            if score >= name_threshold:
                pairs.append((score, i, j))
    pairs.sort(key=lambda p: -p[0])
    hit_by_entry: dict[int, int] = {}
    used_plans: set[int] = set()
    for score, i, j in pairs:
        if i in hit_by_entry or j in used_plans:
            continue
        hit_by_entry[i] = j
        used_plans.add(j)

    results = []
    for i, e in enumerate(entries):
        hit = plans[hit_by_entry[i]] if i in hit_by_entry else None
        auto = e["관리상태"] == "반영"
        if hit:
            verdict = CHECK_ACTUAL if auto else CHECK_TEAM_OK
        elif auto:
            verdict = CHECK_AUTO
        else:
            verdict = CHECK_MISSING
        results.append({**e,
                        "팀제출일": hit[0] if hit else None,
                        "팀제출금액": hit[1] if hit else None,
                        "누락": verdict == CHECK_MISSING,
                        "판정": verdict})
    return results


# ---------------------------------------------------------------------------
# 온라인 입금 요일 평균 (21번 항목)
# ---------------------------------------------------------------------------

def weekday_online_averages(history_rows: list[dict], base_date: date,
                            weeks: int = 12,
                            recency_halflife: float = 4.0
                            ) -> dict[int, float]:
    """최근 N주의 요일별 온라인 매출 입금 가중 평균.

    recency_halflife(주 단위 반감기, 기본 4주)만큼 지난 주의 가중치가
    절반이 되도록 최근 실적에 더 큰 비중을 준다 — 매주 새 입출금
    파일을 올리면 최신 주가 곧바로 예상 입금액에 반영된다.
    0 이하면 가중 없이 단순 평균.
    """
    start = base_date - timedelta(days=weeks * 7)
    daily: dict[date, float] = defaultdict(float)
    for row in history_rows:
        if row.get("자동분류") != CLASS_ONLINE_SALES or row.get("내부이체"):
            continue
        d = row.get("거래일")
        if d is None or not (start <= d < base_date):
            continue
        daily[d] += row.get("입금액") or 0.0

    if not daily:
        return {i: 0.0 for i in range(7)}

    data_start = max(start, min(daily))
    sums = defaultdict(float)
    counts = defaultdict(float)
    d = data_start
    while d < base_date:
        if recency_halflife > 0:
            age_weeks = (base_date - d).days / 7.0
            weight = 0.5 ** (age_weeks / recency_halflife)
        else:
            weight = 1.0
        sums[d.weekday()] += daily.get(d, 0.0) * weight
        counts[d.weekday()] += weight
        d += timedelta(days=1)
    return {i: (sums[i] / counts[i] if counts[i] else 0.0) for i in range(7)}


# ---------------------------------------------------------------------------
# 정기지출 분석 (24번 항목)
# ---------------------------------------------------------------------------

OVERRIDE_SHEET_NAME = "정기지출분류"
_NATURE_VALUES = ("정기", "변동", "제외")


def _normalize_nature(value) -> str:
    """성격 값 정규화 — 사용자 용어 '비정기'는 내부 '변동'으로 통일."""
    from common import RECURRING_NATURE_ALIAS
    text = normalize_text(value)
    text = RECURRING_NATURE_ALIAS.get(text, text)
    return text if text in _NATURE_VALUES else ""


HOLIDAY_SHEET = "공휴일"
# 시트 최초 생성 시 채워 주는 공휴일 (사용자가 해마다 추가·수정)
_HOLIDAY_SEED = [
    (date(2026, 9, 24), "추석 연휴"),
    (date(2026, 9, 25), "추석"),
    (date(2026, 9, 26), "추석 연휴"),
    (date(2026, 10, 3), "개천절"),
    (date(2026, 10, 5), "개천절 대체공휴일"),
    (date(2026, 10, 9), "한글날"),
    (date(2026, 12, 25), "성탄절"),
    (date(2027, 1, 1), "신정"),
]


def ensure_holiday_sheet(base_workbook: Path) -> int:
    """기준파일에 '공휴일' 시트를 만들고 기본 공휴일을 채운다.

    이미 있으면 건드리지 않는다(사용자 관리). 추가된 행 수를 돌려준다.
    """
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook)
    except Exception:
        return 0
    try:
        if HOLIDAY_SHEET in wb.sheetnames:
            return 0
        ws = wb.create_sheet(HOLIDAY_SHEET)
        ws.append(["일자", "이름"])
        ws.append(["(안내) 해마다 설날·추석·임시공휴일 등을 여기에 추가하세요. "
                   "일자·요일이 결과물에서 붉은 글자로 표시됩니다.", ""])
        for d, name in _HOLIDAY_SEED:
            ws.append([d, name])
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 24
        for row in ws.iter_rows(min_row=3, max_col=1):
            row[0].number_format = "yyyy-mm-dd"
        wb.save(base_workbook)
        return len(_HOLIDAY_SEED)
    finally:
        wb.close()


def load_holidays(base_workbook: Path) -> dict[date, str]:
    """'공휴일' 시트: 일자 → 이름."""
    result: dict[date, str] = {}
    base_workbook = Path(base_workbook)
    if not base_workbook.exists():
        return result
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook, data_only=True, read_only=True)
    except Exception:
        return result
    try:
        if HOLIDAY_SHEET not in wb.sheetnames:
            return result
        for row in wb[HOLIDAY_SHEET].iter_rows(min_row=2, max_col=2,
                                               values_only=True):
            d = parse_date(row[0] if len(row) > 0 else None)
            if d is None:
                continue
            result[d] = normalize_text(row[1] if len(row) > 1 else "")
        return result
    finally:
        wb.close()


def adjust_to_business_day(d: date, holidays: Optional[dict] = None) -> date:
    """주말(토·일)·공휴일 정기지출 예정일을 다음 영업일로 옮긴다.

    다음 영업일이 달을 넘기면(월말이 연휴인 경우) 그 달 마지막
    영업일로 앞당긴다 — 월 단위 정기지출이 다른 달로 밀리지 않게.
    (2026-09-20 사용자 요청)
    """
    holidays = holidays or {}

    def _off(x: date) -> bool:
        return x.weekday() >= 5 or x in holidays

    if not _off(d):
        return d
    nxt = d
    while _off(nxt):
        nxt += timedelta(days=1)
    if nxt.month == d.month and nxt.year == d.year:
        return nxt
    prev = d
    while _off(prev):
        prev -= timedelta(days=1)
    return prev


def load_recurring_overrides(base_workbook: Path) -> dict[str, dict]:
    """기준파일 '정기지출분류' 시트: 정기지출명 → {분류, 성격}.

    성격은 정기(기본)/변동/제외. 변동·제외는 13주 자동 추정에서 뺀다
    (예: 외상대 지급처럼 매월 나가지만 금액이 구매량에 따라 변하는 지출).
    사용자가 이 시트를 수정하면 다음 실행부터 반영된다.
    """
    overrides: dict[str, dict] = {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook, data_only=True, read_only=True)
    except Exception:
        return overrides
    try:
        if OVERRIDE_SHEET_NAME not in wb.sheetnames:
            return overrides
        ws = wb[OVERRIDE_SHEET_NAME]
        for row in ws.iter_rows(min_row=2, max_col=3, values_only=True):
            name = normalize_text(row[0] if len(row) > 0 else None)
            if not name:
                continue
            cls = normalize_text(row[1] if len(row) > 1 else None)
            nature = _normalize_nature(row[2] if len(row) > 2 else None)
            overrides[name] = {"분류": cls, "성격": nature or "정기"}
        return overrides
    finally:
        wb.close()


def harvest_recurring_edits(workbook_path: Path) -> dict[str, dict]:
    """'정기지출분석' 시트에서 사용자 수정을 읽는다 (검토 파일·라이브 공용).

    사용자가 분류(3열)·성격(11열)을 고치면 이 함수가 수확해 기준파일
    '정기지출분류'에 저장한다. '성격확인필요'는 미입력 표시이므로 무시한다.
    성격 적용 우선순위: K4 전체 일괄 > 분류별 일괄(M·N열) > 개별 행.
    '비정기'는 '변동'과 같은 값으로 읽는다.
    """
    from common import (RECURRING_BULK_MODES, RECURRING_CAT_BASE_COL,
                        RECURRING_CAT_NAME_COL, RECURRING_CAT_PICK_COL)
    edits: dict[str, dict] = {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(workbook_path, data_only=True, read_only=True)
    except Exception:
        return edits
    try:
        if "정기지출분석" not in wb.sheetnames:
            return edits
        ws = wb["정기지출분석"]
        bulk_row = next(ws.iter_rows(min_row=4, max_row=4, min_col=11,
                                     max_col=11, values_only=True), (None,))
        bulk_nature = RECURRING_BULK_MODES.get(
            normalize_text(bulk_row[0] if bulk_row else None), "")
        cat_nature: dict[str, str] = {}
        rows = list(ws.iter_rows(min_row=6,
                                 max_col=RECURRING_CAT_BASE_COL,
                                 values_only=True))
        for row in rows:
            cat = normalize_text(row[RECURRING_CAT_NAME_COL - 1]
                                 if len(row) >= RECURRING_CAT_NAME_COL
                                 else None)
            pick = _normalize_nature(row[RECURRING_CAT_PICK_COL - 1]
                                     if len(row) >= RECURRING_CAT_PICK_COL
                                     else None)
            # N열은 현재 성격을 보여주므로, 기준값(숨김 O열)과 다르게
            # 바꾼 분류만 일괄 적용한다 ('혼합'은 기준 없음으로 취급)
            base = _normalize_nature(row[RECURRING_CAT_BASE_COL - 1]
                                     if len(row) >= RECURRING_CAT_BASE_COL
                                     else None)
            if cat and pick and pick != base:
                cat_nature[cat] = pick
        for row in rows:
            name = normalize_text(row[1] if len(row) > 1 else None)
            if not name:
                continue
            cls_raw = normalize_text(row[2] if len(row) > 2 else None)
            cls = "" if cls_raw == "성격확인필요" else cls_raw
            nature = _normalize_nature(row[10] if len(row) > 10 else None)
            if cls_raw in cat_nature:
                nature = cat_nature[cls_raw]
            if bulk_nature:
                nature = bulk_nature
            if cls or nature:
                edits[name] = {"분류": cls, "성격": nature}
        return edits
    finally:
        wb.close()


def update_override_sheet(base_workbook: Path, edits: dict) -> int:
    """수확한 분류·성격 수정을 기준파일 '정기지출분류' 시트에 반영한다.

    변경된 셀 수를 돌려준다 (같은 값이면 건드리지 않음).
    """
    if not edits:
        return 0
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook)
    except Exception:
        return 0
    try:
        if OVERRIDE_SHEET_NAME in wb.sheetnames:
            ws = wb[OVERRIDE_SHEET_NAME]
        else:
            ws = wb.create_sheet(OVERRIDE_SHEET_NAME)
            ws.append(["정기지출명", "분류", "성격"])
        rows_by_name = {}
        for row in ws.iter_rows(min_row=2, max_col=3):
            name = normalize_text(row[0].value)
            if name:
                rows_by_name[name] = row
        changed = 0
        for name, ov in edits.items():
            row = rows_by_name.get(name)
            if row is not None:
                if ov.get("분류") and \
                        normalize_text(row[1].value) != ov["분류"]:
                    row[1].value = ov["분류"]
                    changed += 1
                if ov.get("성격") and \
                        normalize_text(row[2].value) != ov["성격"]:
                    row[2].value = ov["성격"]
                    changed += 1
            else:
                ws.append([name, ov.get("분류") or "",
                           ov.get("성격") or "정기"])
                changed += 1
        if changed:
            wb.save(base_workbook)
        return changed
    finally:
        wb.close()


def apply_recurring_overrides(recurring_items: list[dict],
                              overrides: dict[str, dict]) -> None:
    """정기지출 목록에 사용자 분류·성격을 적용한다 (제자리 수정)."""
    for item in recurring_items:
        ov = overrides.get(item.get("정기지출명", ""))
        if ov:
            if ov.get("분류"):
                item["분류"] = ov["분류"]
            item["성격"] = ov.get("성격") or "정기"
        elif "외상" in (item.get("분류") or ""):
            item["성격"] = "변동"  # 외상대 지급은 기본적으로 변동 취급
        else:
            item.setdefault("성격", "정기")


def ensure_recurring_override_sheet(base_workbook: Path,
                                    recurring_items: list[dict]) -> int:
    """기준파일에 '정기지출분류' 시트를 만들고 새 항목을 추가한다.

    기존 행(사용자 수정 포함)은 건드리지 않는다. 추가된 행 수를 돌려준다.
    """
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook)
    except Exception:
        return 0
    try:
        if OVERRIDE_SHEET_NAME in wb.sheetnames:
            ws = wb[OVERRIDE_SHEET_NAME]
        else:
            ws = wb.create_sheet(OVERRIDE_SHEET_NAME)
            ws.append(["정기지출명", "분류", "성격"])
            ws.append(["(안내) 성격: 정기=매월 자동 추정 반영 / "
                       "변동=외상대 등 금액 변동(추정 제외) / 제외",
                       "", ""])
        existing = {normalize_text(row[0])
                    for row in ws.iter_rows(min_row=2, max_col=1,
                                            values_only=True)
                    if row and row[0]}
        added = 0
        for item in recurring_items:
            name = item.get("정기지출명", "")
            if not name or name in existing:
                continue
            ws.append([name, item.get("분류") or "",
                       item.get("성격") or "정기"])
            existing.add(name)
            added += 1
        if added:
            wb.save(base_workbook)
        return added
    finally:
        wb.close()


def _recurring_name_key(row: dict) -> str:
    text = normalize_text(row.get("기재내용·상대방")) \
        or normalize_text(row.get("적요"))
    text = re.sub(r"[\d\-/.,()*:]+", "", text)
    return text.strip()[:20]


def analyze_recurring(history_rows: list[dict], base_date: date,
                      lookback_months: int = 6,
                      min_months: int = 4) -> list[dict]:
    """최근 6개월 중 4개월 이상 반복된 출금을 찾는다."""
    start = base_date - timedelta(days=lookback_months * 31)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in history_rows:
        if row.get("내부이체") or (row.get("출금액") or 0) <= 0:
            continue
        d = row.get("거래일")
        if d is None or not (start <= d < base_date):
            continue
        key_name = _recurring_name_key(row)
        if not key_name:
            continue
        groups[(row.get("은행", ""), key_name)].append(row)

    items = []
    for (bank, name), rows in groups.items():
        months: dict[tuple, float] = defaultdict(float)
        days = []
        for row in rows:
            d = row["거래일"]
            months[(d.year, d.month)] += row["출금액"]
            days.append(d.day)
        if len(months) < min_months:
            continue
        monthly = list(months.values())
        rep_day = int(median(days))
        day_spread = max(days) - min(days)
        if len(months) >= lookback_months and day_spread <= 5:
            confidence = "상"
        elif day_spread <= 10:
            confidence = "중"
        else:
            confidence = "하"
        cls = next((r.get("자동분류") for r in rows if r.get("자동분류")), "")
        items.append({
            "은행": bank,
            "정기지출명": name,
            "분류": cls,
            "발생개월수": len(months),
            "거래건수": len(rows),
            "평균 월지출": sum(monthly) / len(monthly),
            "최소 월지출": min(monthly),
            "최대 월지출": max(monthly),
            "대표 지급일": rep_day,
            "신뢰도": confidence,
        })
        for row in rows:
            row["정기지출후보"] = True
    items.sort(key=lambda x: -x["평균 월지출"])
    return items


# ---------------------------------------------------------------------------
# 4주 일별 / 13주 주별 계획 (22~23번 항목)
# ---------------------------------------------------------------------------

def _plan_amounts_by_date(plans: list[dict]) -> dict[date, dict[str, float]]:
    """반영일별 (송금, 카드, 자동이체) 합계."""
    result: dict[date, dict[str, float]] = defaultdict(
        lambda: {"송금": 0.0, "카드": 0.0, "자동이체": 0.0})
    for plan in plans:
        d = plan.get("자금계획 반영일")
        amount = plan.get("예상금액") or 0.0
        if d is None or amount == 0:
            continue
        method = plan.get("지급방법")
        if method == PAY_METHOD_TRANSFER:
            result[d]["송금"] += amount
        elif method == PAY_METHOD_CARD:
            result[d]["카드"] += amount
        elif method == PAY_METHOD_AUTO:
            result[d]["자동이체"] += amount
        else:
            result[d]["송금"] += amount
    return result


def intraday_actuals(countable_plans: list[dict], history_rows: list[dict],
                     adjustments: list[dict], run_date: date,
                     holds: Optional[set] = None,
                     holidays: Optional[dict] = None) -> Optional[dict]:
    """실행일 당일의 계획 vs 실제 대조 (2026-09-21 사용자 확정 방식).

    실행일 행은 은행 파일 그대로 '실적'으로 마감한다 — 순현금흐름은
    실제 입출금만이고 송금예정·조정추정은 넣지 않는다. 당일 지급계획과
    실제 출금을 대조해:
    - 집행분은 당일 실적에 포함된 것으로 확인만 하고
    - 아직 안 나간 잔여(미집행·일부지급)는 익일(다음 영업일)로 이월한다
    - holds(확인 단계에서 '보류(제외)'로 고른 요청ID)의 잔여는 이월하지
      않는다 — 차이는 자동 판단하지 않고 사용자가 결정
    그래서 익일 기초 = 실행일 실잔고가 되고, 자금 예산은 익일부터
    시작된다. 대조내역은 확인필요 시트 표시용.
    """
    holds = holds or set()
    todays = [r for r in history_rows
              if r.get("거래일") == run_date and not r.get("내부이체")]
    plans_today = [p for p in countable_plans
                   if (p.get("자금계획 반영일") == run_date
                       and (p.get("예상금액") or 0) > 0)]
    in_total = sum((r.get("입금액") or 0) for r in todays)
    out_total = sum((r.get("출금액") or 0) for r in todays)
    if not plans_today and in_total == 0 and out_total == 0:
        return None

    online_in = sum((r.get("입금액") or 0) for r in todays
                    if r.get("자동분류") == CLASS_ONLINE_SALES)
    other_in_rows = [(r.get("입금액") or 0) for r in todays
                     if (r.get("입금액") or 0) > 0
                     and r.get("자동분류") != CLASS_ONLINE_SALES]
    planned_in = [(a.get("조정입금") or 0) for a in adjustments
                  if a.get("일자") == run_date and (a.get("조정입금") or 0) > 0]
    used_plan = [False] * len(planned_in)
    arrived = 0.0          # 확정입금 계획과 같은 금액으로 도착한 실제 입금
    for amt in other_in_rows:
        hit = next((j for j, v in enumerate(planned_in)
                    if not used_plan[j] and abs(v - amt) < 1), None)
        if hit is not None:
            used_plan[hit] = True
            arrived += amt

    import payment_matcher
    executed = {id(p): 0.0 for p in plans_today}
    matched_txt: dict[int, list[str]] = {id(p): [] for p in plans_today}
    unplanned_out = 0.0

    def _hit(plan: dict, tx: dict, amt: float) -> None:
        executed[id(plan)] += amt
        name = (normalize_text(tx.get("기재내용·상대방"))
                or normalize_text(tx.get("적요")) or "(무기재)")
        matched_txt[id(plan)].append(f"{name} {amt:,.0f}")

    txs = sorted((t for t in todays if (t.get("출금액") or 0) > 0),
                 key=lambda t: -(t.get("출금액") or 0))
    for tx in txs:
        amt = tx.get("출금액") or 0
        # ① 거래처 이름이 비슷하고(유사도 40+, 은행 표기는 '국민네이버
        #    apha'처럼 잘려 70을 못 넘는다) 금액이 계획의 남은 몫 안이면
        #    그 계획의 집행으로 본다 (분할 집행 포함)
        named = [(payment_matcher._name_similarity(p, tx), p)
                 for p in plans_today]
        named = [(sim, p) for sim, p in named
                 if sim >= 40
                 and (p.get("예상금액") or 0) - executed[id(p)] >= amt - 1]
        if named:
            _hit(max(named, key=lambda t: t[0])[1], tx, amt)
            continue
        # ② 금액·일자·지급방법 점수 매칭 (계획 초과 집행도 여기서 잡힘)
        best, best_score = None, 0.0
        for p in plans_today:
            sc = payment_matcher._score(p, tx, name_threshold=40,
                                        window_days=3)
            if sc > best_score:
                best, best_score = p, sc
        if best is not None and best_score >= 40:
            _hit(best, tx, amt)
        else:
            unplanned_out += amt

    def _category(plan: dict) -> str:
        method = plan.get("지급방법")
        if method == PAY_METHOD_CARD:
            return "카드"
        if method == PAY_METHOD_AUTO:
            return "자동이체"
        return "송금"

    remaining = {"송금": 0.0, "카드": 0.0, "자동이체": 0.0}
    executed_cat = {"송금": 0.0, "카드": 0.0, "자동이체": 0.0}
    details, held = [], []
    for p in plans_today:
        cat = _category(p)
        exe = executed[id(p)]
        planned = p.get("예상금액") or 0
        rest = max(0.0, planned - exe)
        on_hold = (p.get("요청ID") or "") in holds
        executed_cat[cat] += exe
        if on_hold:
            held.append(f"{p.get('거래처') or p.get('요청ID')} {rest:,.0f}")
        else:
            remaining[cat] += rest
        if exe <= 0:
            status, why = "미집행", "당일 실제 출금에서 일치 항목 없음"
        elif abs(exe - planned) < 1:
            status, why = "집행 확인", " + ".join(matched_txt[id(p)])
        elif exe < planned:
            status = "일부지급"
            why = (" + ".join(matched_txt[id(p)])
                   + f" — 잔여 {rest:,.0f}")
        else:
            status = "초과집행"
            why = (" + ".join(matched_txt[id(p)])
                   + f" — 계획보다 {exe - planned:,.0f} 많음")
        details.append({"요청ID": p.get("요청ID", ""),
                        "팀명": p.get("팀명", ""),
                        "거래처": p.get("거래처", ""),
                        "예상금액": planned, "집행액": exe, "잔여": rest,
                        "구분": cat, "상태": status, "사유": why,
                        "보류": on_hold})

    carry = run_date + timedelta(days=1)
    while carry.weekday() >= 5 or (holidays and carry in holidays):
        carry += timedelta(days=1)
    return {"일자": run_date,
            "이월일": carry,
            "온라인실제": online_in,
            "기타입금실제": sum(other_in_rows),
            "확정도착": arrived,
            "집행": executed_cat,
            "남은계획": remaining,
            "계획외지출": unplanned_out,
            "입금실제": in_total,
            "출금실제": out_total,
            "대조내역": details,
            "보류내역": held}


def actual_daily_flows(history_rows: list[dict],
                       base_date: date) -> tuple[dict, Optional[date]]:
    """기준일 이후 실제 외부 입출금을 일자별로 집계한다.

    반환: ({일자: {"온라인입금","기타입금","출금"}}, 마지막 실적일)
    내부이체는 총잔액에 영향이 없으므로 제외한다.
    """
    flows: dict[date, dict[str, float]] = {}
    last: Optional[date] = None
    for r in history_rows:
        d = r.get("거래일")
        if d is None or d < base_date or r.get("내부이체"):
            continue
        f = flows.setdefault(d, {"온라인입금": 0.0, "기타입금": 0.0,
                                 "출금": 0.0, "입금내역": [], "지출내역": []})
        amount_in = r.get("입금액") or 0.0
        amount_out = r.get("출금액") or 0.0
        name = (normalize_text(r.get("기재내용·상대방"))
                or normalize_text(r.get("적요")) or "")
        if amount_in:
            if r.get("자동분류") == CLASS_ONLINE_SALES:
                f["온라인입금"] += amount_in
            else:
                f["기타입금"] += amount_in
                f["입금내역"].append((amount_in, name))
        if amount_out:
            f["출금"] += amount_out
            f["지출내역"].append((amount_out, name))
        if last is None or d > last:
            last = d
    return flows, last


def _actual_note(f: dict) -> str:
    """실적일 비고: 주요 지출·기타입금 내역을 짧게 나열한다."""
    parts = ["실적"]
    outs = sorted(f.get("지출내역") or [], reverse=True)
    if outs:
        head = ", ".join(f"{n or '(무기재)'} {a:,.0f}" for a, n in outs[:3])
        if len(outs) > 3:
            head += f" 외 {len(outs) - 3}건"
        parts.append("지출: " + head)
    ins = sorted(f.get("입금내역") or [], reverse=True)
    if ins:
        head = ", ".join(f"{n or '(무기재)'} {a:,.0f}" for a, n in ins[:2])
        if len(ins) > 2:
            head += f" 외 {len(ins) - 2}건"
        parts.append("기타입금: " + head)
    return " | ".join(parts)


def filter_duplicate_adjustments(adjustments: list[dict],
                                 countable_plans: list[dict],
                                 window_days: int = 5,
                                 tolerance: float = 0.25,
                                 name_threshold: int = 60,
                                 aliases: dict[str, list[str]] | None = None
                                 ) -> tuple[list[dict], list[dict]]:
    """팀 지출계획과 겹치는 '자동 초안' 추정 조정을 제외한다.

    같은 지출이 정기지출 추정과 팀 제출 계획 양쪽에서 이중 반영되는
    것을 막는다. 금액만 비슷한 우연 일치를 배제하기 위해 이름
    유사도(거래처·지출내용)가 임계값 이상일 때만 중복으로 본다.
    별칭(aliases)이 등록된 항목은 같은 달의 취합 입력과 이름이
    이어지면 금액 차이와 무관하게 제외한다 — 카드대금처럼 시기는
    정기지만 금액이 매월 변하는 지출용.
    사용자가 직접 넣은 조정(내용에 '자동 초안'이 없는 행)은 건드리지 않는다.
    반환: (남긴 조정, 제외한 조정)
    """
    from rapidfuzz import fuzz

    aliases = aliases or {}
    kept, skipped = [], []
    plans = []
    for p in countable_plans:
        d = p.get("자금계획 반영일")
        amt = p.get("예상금액") or 0.0
        if d is None or amt <= 0:
            continue
        name = " ".join(str(p.get(k) or "") for k in ("거래처", "지출내용"))
        plans.append((d, amt, name.lower()))
    for adj in adjustments:
        amount = adj.get("조정지출") or 0.0
        content = adj.get("내용") or ""
        dup = False
        if "자동 초안" in content and amount > 0:
            m = re.search(r":\s*(.+?)\s*신뢰도", content)
            adj_name = (m.group(1) if m else content).strip()
            names = [adj_name.lower()] + [
                a.lower() for a in aliases.get(normalize_text(adj_name), [])]
            has_alias = len(names) > 1
            for d, plan_amt, plan_name in plans:
                same_month = (d.year, d.month) == (adj["일자"].year,
                                                   adj["일자"].month)
                name_hit = any(fuzz.partial_ratio(n, plan_name)
                               >= name_threshold for n in names)
                if not name_hit:
                    continue
                # 별칭 등록 항목: 같은 달 취합 입력이면 금액 무관 제외
                if has_alias and same_month:
                    dup = True
                    break
                if abs((d - adj["일자"]).days) > window_days:
                    continue
                if abs(plan_amt - amount) > max(plan_amt, amount) * tolerance:
                    continue
                dup = True
                break
        (skipped if dup else kept).append(adj)
    return kept, skipped


def filter_adjustments_by_overrides(adjustments: list[dict],
                                    overrides: dict[str, dict]
                                    ) -> tuple[list[dict], list[dict]]:
    """성격이 변동·제외인 정기지출의 '자동 초안' 지출 조정을 걸러낸다.

    금액이 매번 달라지는 항목(예: 외상매입금)은 팀 지출예정 파일에
    입력된 금액으로만 반영하고, 과거 평균 기반 추정은 쓰지 않는다.
    성격을 '정기'로 되돌리면 추정이 다시 반영된다.
    반환: (남긴 조정, 제외한 조정)
    """
    excluded_names = {normalize_text(name) for name, ov in overrides.items()
                      if ov.get("성격") in ("변동", "제외")}
    if not excluded_names:
        return adjustments, []
    kept, dropped = [], []
    for adj in adjustments:
        content = adj.get("내용") or ""
        name = ""
        if "자동 초안" in content and (adj.get("조정지출") or 0) > 0:
            m = re.search(r":\s*(.+?)\s*신뢰도", content)
            name = normalize_text(m.group(1) if m else "")
        (dropped if name and name in excluded_names else kept).append(adj)
    return kept, dropped


APALM_KEYWORD = "에이팜"
_OWN_COMPANY = "에이팜건강"
APALM_EXCLUDED_STATUS = "에이팜 별도관리"


def mentions_apalm(*texts) -> bool:
    """㈜에이팜 관련 항목인지 판별. 자사명(에이팜건강)은 제외한다."""
    for t in texts:
        s = str(t or "").replace(" ", "")
        if APALM_KEYWORD in s.replace(_OWN_COMPANY, ""):
            return True
    return False


def split_apalm_marked(plan: dict) -> list[dict]:
    """비고에 '에이팜'이 적힌 팀 지출계획을 자금계획 집계에서 뺀다.

    해당 행의 반영상태를 '에이팜 별도관리'로 바꾸고 countable에서
    제거한다(취합 시트에는 그 상태로 남는다). 뺀 행 목록을 돌려준다.
    """
    marked = []
    for r in plan.get("countable", []):
        if mentions_apalm(r.get("비고")):
            r["반영상태"] = APALM_EXCLUDED_STATUS
            marked.append(r)
    if marked:
        plan["countable"] = [r for r in plan["countable"]
                             if r.get("반영상태") != APALM_EXCLUDED_STATUS]
    return marked


_CONF_SENSITIVE = ("급여", "인건비", "퇴직", "세금", "보험")


def collect_apalm_expenses(masked_rows: list[dict],
                           adjustments: list[dict],
                           marked_rows: Optional[list[dict]] = None
                           ) -> list[dict]:
    """에이팜 관련 지출을 '에이팜 지출계획' 시트용으로 모은다.

    비고에 '에이팜'이 적힌 행(marked_rows)은 자금계획에서 뺀 별도관리
    건(미반영)으로 원본 상세를 싣는다 — 단, 급여·퇴직·세금보험류
    대외비 분류는 분류명·금액만 노출한다. 이름으로 인식된 행과
    정기지출 자동 추정은 자금계획에 포함된 참고 건(반영)이다.
    """
    from common import classify_confidential

    out = []
    for r in marked_rows or []:
        vendor = r.get("거래처") or ""
        detail = r.get("지출내용") or ""
        if r.get("confidential"):
            category = classify_confidential(detail, r.get("대외비구분", ""))
            if any(k in category for k in _CONF_SENSITIVE):
                vendor, detail = "(대외비)", category
        out.append({"일자": r.get("자금계획 반영일") or r.get("지급예정일"),
                    "출처": "팀 지출계획",
                    "반영": "미반영(별도 관리)",
                    "팀명": r.get("팀명") or "",
                    "거래처": vendor,
                    "지출내용": detail,
                    "예상금액": r.get("예상금액") or 0.0,
                    "지급방법": r.get("지급방법") or "",
                    "비고": r.get("비고") or ""})
    for r in masked_rows:
        if r.get("confidential"):
            continue
        if r.get("반영상태") != REFLECT_OK:
            continue
        if not mentions_apalm(r.get("거래처"), r.get("지출내용")):
            continue
        out.append({"일자": r.get("자금계획 반영일") or r.get("지급예정일"),
                    "출처": "팀 지출계획",
                    "반영": "반영",
                    "팀명": r.get("팀명") or "",
                    "거래처": r.get("거래처") or "",
                    "지출내용": r.get("지출내용") or "",
                    "예상금액": r.get("예상금액") or 0.0,
                    "지급방법": r.get("지급방법") or "",
                    "비고": r.get("비고") or ""})
    for adj in adjustments:
        amount = adj.get("조정지출") or 0.0
        content = adj.get("내용") or ""
        if amount <= 0 or "자동 초안" not in content:
            continue
        if not mentions_apalm(content):
            continue
        m = re.search(r":\s*(.+?)\s*신뢰도", content)
        out.append({"일자": adj.get("일자"),
                    "출처": "정기지출 추정",
                    "반영": "반영",
                    "팀명": "",
                    "거래처": (m.group(1) if m else content).strip(),
                    "지출내용": content,
                    "예상금액": amount,
                    "지급방법": "",
                    "비고": ""})
    out.sort(key=lambda r: (r["일자"] or date.max, -r["예상금액"]))
    return out


def build_daily_plan(countable_plans: list[dict], base_date: date,
                     opening_balance: float, weekday_avg: dict[int, float],
                     rate: float, adjustments: list[dict],
                     minimum_balance: float = 0,
                     days: int = 28,
                     actual_flows: Optional[dict] = None,
                     actual_until: Optional[date] = None,
                     holidays: Optional[dict] = None,
                     intraday: Optional[dict] = None) -> list[dict]:
    """4주(28일) 일별 자금계획.

    actual_until까지의 날짜는 예측 대신 실제 입출금(실적)으로 채운다.
    opening_balance는 base_date 시작 시점 잔액이어야 한다.
    intraday(intraday_actuals 결과)가 있으면 실행일 행은 은행 파일
    그대로 실적으로 마감하고(순현금흐름 = 실제 입출금만, 기말 = 오늘
    실잔고), 아직 안 나간 예정(보류 제외)은 익일로 이월한다.
    """
    by_date = _plan_amounts_by_date(countable_plans)
    adj_by_date: dict[date, dict] = defaultdict(
        lambda: {"입금": 0.0, "지출": 0.0, "내용": []})
    for adj in adjustments:
        a = adj_by_date[adj["일자"]]
        a["입금"] += adj["조정입금"]
        a["지출"] += adj["조정지출"]
        if adj["내용"]:
            a["내용"].append(adj["내용"])

    rows = []
    balance = opening_balance
    for i in range(days):
        d = base_date + timedelta(days=i)
        is_actual = (actual_until is not None and d <= actual_until)
        if is_actual:
            f = (actual_flows or {}).get(
                d, {"온라인입금": 0.0, "기타입금": 0.0, "출금": 0.0})
            online = f["온라인입금"]
            adj_in = f["기타입금"]
            planned = {"송금": 0.0, "카드": 0.0, "자동이체": 0.0}
            etc_out = f["출금"]
            note = _actual_note(f)
        else:
            # 공휴일은 은행·정산이 쉬므로 예상입금 0 (2026-09-20 사용자 결정)
            if holidays and d in holidays:
                online = 0.0
            else:
                online = weekday_avg.get(d.weekday(), 0.0) * rate
            adj = adj_by_date.get(d, {"입금": 0.0, "지출": 0.0, "내용": []})
            adj_in = adj["입금"]
            planned = by_date.get(d, {"송금": 0.0, "카드": 0.0,
                                      "자동이체": 0.0})
            etc_out = adj["지출"]
            note = "; ".join(adj["내용"])
            if intraday and d == intraday["일자"]:
                # 실행일 = 은행 파일 기준 실적 마감 (2026-09-21 사용자
                # 확정): 송금예정·조정추정은 넣지 않고, 미도착 확정입금·
                # 조정지출·미집행 예정은 익일로 이월한다
                intraday["_이월확정"] = max(0.0,
                                        adj_in - intraday["확정도착"])
                intraday["_이월조정지출"] = etc_out
                online = intraday["온라인실제"]
                adj_in = intraday["기타입금실제"]
                planned = dict(intraday["집행"])
                etc_out = intraday["계획외지출"]
                carried = sum(intraday["남은계획"].values())
                extra = (f"실적(은행 확인): 입금 {intraday['입금실제']:,.0f}"
                         f"·출금 {intraday['출금실제']:,.0f}")
                if carried > 0:
                    extra += f" — 미집행 예정 {carried:,.0f} 익일 이월"
                if intraday.get("보류내역"):
                    extra += (" / 보류 제외: "
                              + ", ".join(intraday["보류내역"][:3]))
                note = f"{note}; {extra}" if note else extra
            elif intraday and d == intraday.get("이월일"):
                planned = {k: planned.get(k, 0.0)
                           + intraday["남은계획"].get(k, 0.0)
                           for k in ("송금", "카드", "자동이체")}
                adj_in += intraday.get("_이월확정", 0.0)
                etc_out += intraday.get("_이월조정지출", 0.0)
                carried = (sum(intraday["남은계획"].values())
                           + intraday.get("_이월확정", 0.0)
                           + intraday.get("_이월조정지출", 0.0))
                if carried > 0:
                    extra = f"전일 미집행 예정 {carried:,.0f} 이월 반영"
                    note = f"{note}; {extra}" if note else extra
        inflow = online + adj_in
        outflow = planned["송금"] + planned["카드"] + planned["자동이체"] + etc_out
        net = inflow - outflow
        opening = balance
        balance = opening + net
        if balance < 0:
            state = STATE_SHORTAGE
        elif balance < minimum_balance:
            state = STATE_WARN
        else:
            state = STATE_OK
        rows.append({
            "일자": d, "요일": weekday_ko(d),
            "당일실적": bool(intraday and d == intraday["일자"]),
            "온라인 예상입금": online,
            "확정·기타입금": adj_in,
            "팀별 송금예정": planned["송금"],
            "카드결제": planned["카드"],
            "자동이체": planned["자동이체"],
            "기타지출": etc_out,
            "순현금흐름": net,
            "기초잔액": opening,
            "기말잔액": balance,
            "상태": state,
            "비고": note,
            "실적": is_actual,
        })
    return rows


def build_weekly_plan(countable_plans: list[dict], base_date: date,
                      daily_rows: list[dict], weekday_avg: dict[int, float],
                      rate: float, recurring_items: list[dict],
                      adjustments: list[dict],
                      minimum_balance: float = 0,
                      weeks: int = 13,
                      holidays: Optional[dict] = None) -> list[dict]:
    """13주 주별 자금계획. base_date는 월요일이어야 한다."""
    base_monday = week_monday(base_date)
    by_date = _plan_amounts_by_date(countable_plans)

    # 정기지출 추정은 자금계획에 반영하지 않는다 (2026-09-21 사용자
    # 결정) — 정기지출은 확인용(정기지출 체크·정기지출분석)으로만 쓰고,
    # 계획에는 팀 지출예정(취합)·주간조정·온라인 예상입금만 넣는다
    adj_by_date: dict[date, dict] = defaultdict(lambda: {"입금": 0.0, "지출": 0.0})
    for adj in adjustments:
        adj_by_date[adj["일자"]]["입금"] += adj["조정입금"]
        adj_by_date[adj["일자"]]["지출"] += adj["조정지출"]

    weekly_online_full = sum(weekday_avg.values()) * rate

    rows = []
    balance = None
    for w in range(weeks):
        w_start = base_monday + timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        label = f"{w + 1}주차"
        period = f"{w_start.strftime('%m/%d')}~{w_end.strftime('%m/%d')}"
        if w < 4 and daily_rows:
            in_week = [r for r in daily_rows if w_start <= r["일자"] <= w_end]
            online = sum(r["온라인 예상입금"] for r in in_week)
            adj_in = sum(r["확정·기타입금"] for r in in_week)
            transfer = sum(r["팀별 송금예정"] for r in in_week)
            card = sum(r["카드결제"] for r in in_week)
            auto = sum(r["자동이체"] for r in in_week)
            etc = sum(r["기타지출"] for r in in_week)
            if balance is None and in_week:
                balance = in_week[0]["기초잔액"]
        else:
            online = weekly_online_full
            if holidays:
                # 공휴일이 낀 주는 그 요일 평균만큼 입금을 뺀다 (입금 0)
                online -= sum(
                    weekday_avg.get((w_start + timedelta(days=i)).weekday(),
                                    0.0) * rate
                    for i in range(7)
                    if (w_start + timedelta(days=i)) in holidays)
            adj_in = 0.0
            transfer = card = auto = etc = 0.0
            d = w_start
            while d <= w_end:
                planned = by_date.get(d)
                if planned:
                    transfer += planned["송금"]
                    card += planned["카드"]
                    auto += planned["자동이체"]
                adj = adj_by_date.get(d)
                if adj:
                    adj_in += adj["입금"]
                    etc += adj["지출"]
                d += timedelta(days=1)
        income = online + adj_in
        net = income - (transfer + card + auto + etc)
        opening = balance if balance is not None else 0.0
        closing = opening + net
        balance = closing
        if closing < 0:
            state = STATE_SHORTAGE
        elif closing < minimum_balance:
            state = STATE_WARN
        else:
            state = STATE_OK
        rows.append({
            "주차": label, "기간": period,
            "예상입금": income, "온라인입금": online, "확정기타입금": adj_in,
            "송금예정": transfer, "카드결제": card,
            "자동이체": auto, "기타지출": etc, "순현금흐름": net,
            "기말잔액": closing, "상태": state,
        })
    return rows


def build_account_scenario(daily_rows: list[dict], balances: dict,
                           history_rows: list[dict],
                           actual_until: Optional[date] = None,
                           backout_from: Optional[date] = None) -> dict:
    """계좌별 일별 잔액 시나리오 (인출 우선순위: 우리은행→농협→국민은행).

    지출은 전액 우리은행에서 집행하고, 부족분은 농협→국민 순으로
    우리은행에 이체해 채우는 것으로 가정한다. 입금은 최근 이력의
    계좌별 외부입금 비중대로 배분한다.
    backout_from(보통 실행일)이 있으면 그날 이후 거래를 시작 잔액에서
    되돌린다 — 실행일은 실적으로 확정하지 않고 하루 전체를 예측하므로,
    당일 새벽 거래가 이중으로 반영되지 않게 전일 마감 잔액에서 출발한다.
    반환: {"accounts": [(은행, 계좌) 우선순위 순], "shares": {계좌: 비중},
          "rows": [...]} — 각 행의 "입금"에 그날 계좌별 배분액을 담는다.
    """
    _PRIORITY = {"우리은행": 0, "농협": 1, "국민은행": 2}
    accounts = sorted(balances.keys(),
                      key=lambda k: (_PRIORITY.get(k[0], 9),
                                     -(balances.get(k) or 0)))
    if not accounts:
        return {"accounts": [], "shares": {}, "opening": {}, "rows": []}

    inflow_by_acct = {k: 0.0 for k in accounts}
    for r in history_rows:
        if r.get("내부이체") or (r.get("입금액") or 0) <= 0:
            continue
        key = (r.get("은행"), r.get("계좌") or "")
        if key in inflow_by_acct:
            inflow_by_acct[key] += r["입금액"]
    total_in = sum(inflow_by_acct.values())
    shares = ({k: v / total_in for k, v in inflow_by_acct.items()}
              if total_in > 0 else {k: 1 / len(accounts) for k in accounts})

    bal = {k: float(balances.get(k) or 0) for k in accounts}
    # 실행일 이후 거래를 되돌린다 — 내부이체도 계좌별 잔액은 바꾸므로 포함
    if backout_from is not None:
        for r in history_rows:
            d = r.get("거래일")
            if d is None or d < backout_from:
                continue
            key = (r.get("은행"), r.get("계좌") or "")
            if key in bal:
                bal[key] -= (r.get("입금액") or 0) - (r.get("출금액") or 0)
    opening = dict(bal)          # 예측 시작(전일 마감) 시점의 계좌별 잔액
    # 오늘 실잔고 (표시용): 은행 파일의 계좌별 마지막 거래 기준
    current = {k: float(balances.get(k) or 0) for k in accounts}
    woori = accounts[0]
    rows = []
    for day in daily_rows:
        d = day["일자"]
        if day.get("실적"):
            rows.append({"일자": d, "요일": day.get("요일"), "실적": True,
                         "잔액": dict(bal) if d == actual_until else None,
                         "입금": {}, "지출": None, "이체": {},
                         "비고": "실적 구간"})
            continue
        if day.get("당일실적"):
            # 실행일 = 은행 확인 실잔고로 마감 — 익일 예측은 여기서 출발
            bal = dict(current)
            rows.append({"일자": d, "요일": day.get("요일"), "실적": False,
                         "당일실적": True, "잔액": dict(bal),
                         "입금": {}, "지출": None, "이체": {},
                         "비고": "실적(은행 확인)"})
            continue
        inflow = ((day.get("온라인 예상입금") or 0)
                  + (day.get("확정·기타입금") or 0))
        outflow = ((day.get("팀별 송금예정") or 0)
                   + (day.get("카드결제") or 0)
                   + (day.get("자동이체") or 0)
                   + (day.get("기타지출") or 0))
        deposits = {k: inflow * shares[k] for k in accounts}
        for k in accounts:
            bal[k] += deposits[k]
        transfers: dict = {}
        note = ""
        need = outflow - bal[woori]
        bal[woori] -= outflow
        if need > 0:
            for k in accounts[1:]:
                if need <= 0:
                    break
                move = min(bal[k], need) if bal[k] > 0 else 0.0
                if move > 0:
                    bal[k] -= move
                    bal[woori] += move
                    transfers[k] = transfers.get(k, 0.0) + move
                    need -= move
            if need > 0:
                note = f"전 계좌 소진 — 부족 {need:,.0f}원"
        rows.append({"일자": d, "요일": day.get("요일"), "실적": False,
                     "잔액": dict(bal), "입금": deposits, "지출": outflow,
                     "이체": transfers, "비고": note})
    return {"accounts": accounts, "shares": shares, "opening": opening,
            "current": current, "rows": rows}


# ---------------------------------------------------------------------------
# 반영률 시나리오 (21번 항목)
# ---------------------------------------------------------------------------

def build_forecast(countable_plans: list[dict], base_date: date,
                   opening_balance: float, history_rows: list[dict],
                   adjustments: list[dict], recurring_items: list[dict],
                   rates: list[float], default_rate: float,
                   minimum_balance: float = 0,
                   history_weeks: int = 12,
                   recency_halflife: float = 4.0,
                   display_week_start: Optional[date] = None,
                   holidays: Optional[dict] = None,
                   run_date: Optional[date] = None,
                   intraday_holds: Optional[set] = None) -> dict:
    """전체 예측 결과와 반영률별 시나리오를 만든다.

    opening_balance는 '현재(최신 거래내역 기준) 총잔액'이다.
    기준일~마지막 실적일 구간은 실제 입출금으로 채우므로,
    일별 계획의 시작잔액은 실적 순증감을 되돌린 기준일 시작잔액을 쓴다.
    display_week_start는 대표보고 '일별 잔액 전망(월~금)'의 시작 월요일 —
    주말 실행이면 차주 월요일을 넘겨 다가오는 주를 보여준다. 없으면 기준주.
    """
    weekday_avg = weekday_online_averages(history_rows, base_date,
                                          history_weeks, recency_halflife)
    actual_flows, actual_until = actual_daily_flows(history_rows, base_date)
    # 실행일 당일은 아직 끝나지 않은 날이라 실적으로 확정하지 않는다 —
    # 은행 파일에 당일 새벽 거래만 찍힌 채 그날의 계획 지출(팀 송금 등)이
    # 통째로 사라지는 것을 막는다 (2026-09-21 사용자 발견). 당일 거래의
    # 순증감은 아래 net_actual(전체 합)로 시작잔액에서 되돌려지므로,
    # 당일을 다시 예측해도 이중계산이 없다.
    if (run_date is not None and actual_until is not None
            and actual_until >= run_date):
        actual_until = run_date - timedelta(days=1)
        if actual_until < base_date:
            actual_until = None
    net_actual = sum(f["온라인입금"] + f["기타입금"] - f["출금"]
                     for f in actual_flows.values())
    start_balance = opening_balance - net_actual
    # 실행일 당일: 계획 vs 실제 대조 + 하이브리드(실제 + 남은 예정).
    # 기초는 전일 마감이고 당일 실제가 행에 포함되므로, net_actual
    # 백아웃과 합쳐 이중계산 없이 기말 = 현재 실잔고 + 남은 예정이 된다
    intraday = None
    if run_date is not None and run_date >= base_date:
        intraday = intraday_actuals(countable_plans, history_rows,
                                    adjustments, run_date,
                                    holds=intraday_holds,
                                    holidays=holidays)
    today_actual = None
    if run_date is not None:
        f = actual_flows.get(run_date)
        if f:
            today_actual = {"일자": run_date,
                            "온라인": f["온라인입금"],
                            "기타입금": f["기타입금"],
                            "출금": f["출금"],
                            "순증감": (f["온라인입금"] + f["기타입금"]
                                    - f["출금"])}
    scenarios = {}
    main = None
    for rate in sorted(set(list(rates) + [default_rate])):
        daily = build_daily_plan(countable_plans, base_date, start_balance,
                                 weekday_avg, rate, adjustments,
                                 minimum_balance,
                                 actual_flows=actual_flows,
                                 actual_until=actual_until,
                                 holidays=holidays,
                                 intraday=intraday)
        weekly = build_weekly_plan(countable_plans, base_date, daily,
                                   weekday_avg, rate, recurring_items,
                                   adjustments, minimum_balance,
                                   holidays=holidays)
        min_row = min(daily, key=lambda r: r["기말잔액"]) if daily else None
        shortage = next((r["일자"] for r in daily
                         if r["상태"] == STATE_SHORTAGE), None)
        week_start = display_week_start or base_date
        scenario = {
            "rate": rate,
            # 다가오는 주(월~금)의 일별 기말잔액 — 대표 보고용
            "금주일별": [(r["일자"], r["기말잔액"], r["상태"]) for r in daily
                      if week_start <= r["일자"]
                      < week_start + timedelta(days=5)],
            "4주 온라인입금": sum(r["온라인 예상입금"] for r in daily),
            "4주 기말잔액": daily[-1]["기말잔액"] if daily else 0.0,
            "4주 최저잔액": min_row["기말잔액"] if min_row else 0.0,
            "4주 최저잔액일": min_row["일자"] if min_row else None,
            "13주 온라인입금": sum(r["예상입금"] for r in weekly),
            "13주 기말잔액": weekly[-1]["기말잔액"] if weekly else 0.0,
            "자금부족 예상일": shortage,
            "안내": _scenario_note(rate, daily, minimum_balance),
        }
        scenarios[rate] = scenario
        if abs(rate - default_rate) < 1e-9:
            main = {"daily": daily, "weekly": weekly, "scenario": scenario}

    return {
        "base_date": base_date,
        "rate": default_rate,
        "weekday_avg": weekday_avg,
        "daily": main["daily"] if main else [],
        "weekly": main["weekly"] if main else [],
        "scenario": main["scenario"] if main else {},
        "rate_scenarios": scenarios,
        "opening_balance": opening_balance,
        "start_balance": start_balance,
        "actual_until": actual_until,
        "today_actual": today_actual,
        "intraday": intraday,
        "minimum_balance": minimum_balance,
    }


def _scenario_note(rate: float, daily: list[dict],
                   minimum_balance: float) -> str:
    if not daily:
        return "계산할 일별 자료가 없습니다."
    shortage = [r for r in daily if r["상태"] == STATE_SHORTAGE]
    warn = [r for r in daily if r["상태"] == STATE_WARN]
    pct = int(round(rate * 100))
    if shortage:
        first = shortage[0]["일자"]
        return (f"반영률 {pct}% 기준 {first.strftime('%m월 %d일')}에 "
                f"잔액이 0원 미만으로 예상됩니다. 자금 조치가 필요합니다.")
    if warn:
        first = warn[0]["일자"]
        return (f"반영률 {pct}% 기준 {first.strftime('%m월 %d일')}에 "
                f"최소 필요잔액({minimum_balance:,.0f}원) 아래로 내려갑니다.")
    return f"반영률 {pct}% 기준 4주간 자금부족 없이 운영 가능합니다."
