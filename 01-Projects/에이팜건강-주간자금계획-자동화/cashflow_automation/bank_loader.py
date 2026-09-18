# -*- coding: utf-8 -*-
"""은행 거래내역 읽기·표준화 (16번 항목).

농협·우리은행·국민은행의 XLS/XLSX/CSV를 읽어 표준 항목으로 변환한다.
은행마다 열 이름이 달라 후보 키워드로 헤더를 탐지한다.
과거 거래 누적(bank_history.csv)도 여기서 관리한다 — 정기지출 분석과
온라인 입금 예측은 14일치보다 긴 이력이 필요하기 때문이다.
"""
from __future__ import annotations

import csv
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Optional

from common import (
    BANK_REFLECT_OK, BANKS, normalize_text, parse_amount, parse_date,
    parse_datetime,
)

# 표준 필드별 헤더 후보 (공백 제거 후 부분일치)
_FIELD_CANDIDATES: dict[str, list[str]] = {
    "거래일시": ["거래일시"],
    "거래일": ["거래일자", "거래날짜", "거래일", "일자", "날짜"],
    "거래시간": ["거래시간", "시간"],
    "계좌": ["계좌번호", "계좌"],
    "출금액": ["출금금액", "출금액", "출금(원)", "지급금액", "지급(원)",
              "출금", "지급"],
    "입금액": ["입금금액", "입금액", "입금(원)", "입금"],
    "거래후잔액": ["거래후잔액", "거래후 잔액", "잔액(원)", "잔액"],
    "적요": ["적요", "거래내용", "거래구분"],
    "기재내용·상대방": ["기재내용", "보낸분/받는분", "의뢰인/수취인",
                    "거래기록사항", "기록사항", "상대방", "받는분", "내용"],
    "취급점": ["취급점", "거래점", "처리점", "송금점", "점포"],
}
_MIN_HEADER_MATCHES = 3

SUPPORTED_SUFFIXES = {".xls", ".xlsx", ".csv"}

HISTORY_COLUMNS = ["거래일시", "거래일", "은행", "계좌", "출금액", "입금액",
                   "거래후잔액", "적요", "기재내용·상대방", "취급점", "자동분류"]


def _clean_header(value: Any) -> str:
    return re.sub(r"[\s ]+", "", normalize_text(value))


def _match_field(header: str) -> Optional[str]:
    key = _clean_header(header)
    if not key:
        return None
    for field, candidates in _FIELD_CANDIDATES.items():
        for cand in candidates:
            if cand.replace(" ", "") in key:
                return field
    return None


def _detect_header(rows: list[list[Any]]) -> Optional[tuple[int, dict[int, str]]]:
    """상위 30행에서 헤더 행을 찾는다."""
    best = None
    for i, row in enumerate(rows[:30]):
        mapping: dict[int, str] = {}
        for col, value in enumerate(row):
            field = _match_field(value)
            if field and field not in mapping.values():
                mapping[col] = field
        score = len(mapping)
        has_date = any(f in ("거래일", "거래일시") for f in mapping.values())
        has_amount = any(f in ("출금액", "입금액") for f in mapping.values())
        if score >= _MIN_HEADER_MATCHES and has_date and has_amount:
            if best is None or score > len(best[1]):
                best = (i, mapping)
    return best


def _find_account_hint(rows: list[list[Any]], header_idx: int) -> str:
    """헤더 위쪽에서 '계좌번호: xxx' 형태의 안내를 찾는다.

    은행에 따라 '계좌번호' 라벨과 번호가 다른 셀에 있으므로
    행 전체를 이어붙여 검색한다.
    """
    pattern = re.compile(r"(\d{4,8}(?:[- ]\d{2,6}){1,3}|\d{10,14})")
    for row in rows[:header_idx]:
        row_text = " ".join(normalize_text(v) for v in row if v not in
                            (None, ""))
        if "계좌" in row_text:
            m = pattern.search(row_text)
            if m:
                return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# 파일 읽기
# ---------------------------------------------------------------------------

def _read_raw_rows(path: Path) -> list[list[Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
            try:
                with open(path, encoding=encoding, newline="") as f:
                    return [row for row in csv.reader(f)]
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError("CSV 인코딩을 판별하지 못했습니다")
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True, read_only=True)
        try:
            ws = wb[wb.sheetnames[0]]
            return [list(row) for row in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
    if suffix == ".xls":
        import xlrd
        book = xlrd.open_workbook(str(path))
        sheet = book.sheet_by_index(0)
        rows = []
        for r in range(sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(datetime(*xlrd.xldate_as_tuple(
                        cell.value, book.datemode)))
                else:
                    row.append(cell.value)
            rows.append(row)
        return rows
    raise ValueError(f"지원하지 않는 파일 형식: {suffix}")


def load_bank_file(path: Path, bank: str) -> tuple[list[dict], list[dict]]:
    """은행 파일 하나를 표준 행으로 변환한다. (행, 확인필요) 반환."""
    path = Path(path)
    issues: list[dict] = []
    try:
        raw_rows = _read_raw_rows(path)
    except Exception as exc:
        return [], [{"구분": "손상된 파일", "은행": bank,
                     "내용": f"파일 열기 실패: {exc}", "원본파일": path.name}]
    header = _detect_header(raw_rows)
    if header is None:
        return [], [{"구분": "필수 열 누락", "은행": bank,
                     "내용": "거래내역 헤더를 찾지 못했습니다",
                     "원본파일": path.name}]
    header_idx, mapping = header
    account_hint = _find_account_hint(raw_rows, header_idx)

    rows: list[dict] = []
    for order, raw in enumerate(raw_rows[header_idx + 1:], start=1):
        values = {field: (raw[col] if col < len(raw) else None)
                  for col, field in mapping.items()}
        row = _normalize_bank_row(values, bank, path.name, account_hint, order)
        if row is None:
            continue
        if row.get("_잘못된날짜"):
            issues.append({"구분": "잘못된 날짜", "은행": bank,
                           "내용": f"{order}행 거래일 해석 불가",
                           "원본파일": path.name})
            continue
        rows.append(row)
    if not rows:
        issues.append({"구분": "은행 자료 누락", "은행": bank,
                       "내용": "읽을 수 있는 거래가 없습니다",
                       "원본파일": path.name})
    return rows, issues


def _normalize_bank_row(values: dict, bank: str, filename: str,
                        account_hint: str, order: int) -> Optional[dict]:
    tx_datetime = parse_datetime(values.get("거래일시"))
    tx_date = parse_date(values.get("거래일")) or (
        tx_datetime.date() if tx_datetime else None)
    if tx_datetime is None and tx_date is None:
        raw_date = normalize_text(values.get("거래일")
                                  or values.get("거래일시"))
        if not raw_date:
            return None  # 빈 행
        # '총 862건', '합계' 같은 요약 행은 거래가 아니다
        if raw_date.startswith("총") or "합계" in raw_date \
                or raw_date.endswith("건"):
            return None
        return {"_잘못된날짜": True}
    if tx_datetime is None and values.get("거래시간") is not None:
        t = normalize_text(values.get("거래시간"))
        m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", t)
        if m and tx_date is not None:
            tx_datetime = datetime.combine(tx_date, time(
                int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)))
    if tx_date is None and tx_datetime is not None:
        tx_date = tx_datetime.date()

    out_amount = parse_amount(values.get("출금액")) or 0.0
    in_amount = parse_amount(values.get("입금액")) or 0.0
    balance = parse_amount(values.get("거래후잔액"))
    if out_amount == 0 and in_amount == 0 and balance is None:
        return None  # 합계·안내 행

    return {
        "거래일시": tx_datetime,
        "거래일": tx_date,
        "은행": bank,
        "계좌": normalize_text(values.get("계좌")) or account_hint,
        "출금액": out_amount,
        "입금액": in_amount,
        "거래후잔액": balance,
        "적요": normalize_text(values.get("적요")),
        "기재내용·상대방": normalize_text(values.get("기재내용·상대방")),
        "취급점": normalize_text(values.get("취급점")),
        "자동분류": "",
        "내부이체": False,
        "정기지출후보": False,
        "현금유출입": in_amount - out_amount,
        "원본파일": filename,
        "반영상태": BANK_REFLECT_OK,
        "row_order": order,
    }


def load_all_banks(cfg) -> dict:
    """세 은행 폴더의 모든 지원 파일을 읽는다."""
    all_rows: list[dict] = []
    issues: list[dict] = []
    missing_banks: list[str] = []
    for bank in BANKS:
        bank_dir = cfg.bank_dir(bank)
        files = sorted(p for p in bank_dir.glob("*")
                       if p.suffix.lower() in SUPPORTED_SUFFIXES
                       and not p.name.startswith("~$"))
        if not files:
            missing_banks.append(bank)
            issues.append({"구분": "은행 자료 누락", "은행": bank,
                           "내용": f"{bank} 폴더에 거래내역 파일이 없습니다",
                           "원본파일": ""})
            continue
        for path in files:
            rows, file_issues = load_bank_file(path, bank)
            all_rows.extend(rows)
            issues.extend(file_issues)
    return {"rows": all_rows, "issues": issues, "missing_banks": missing_banks}


# ---------------------------------------------------------------------------
# 잔액 요약
# ---------------------------------------------------------------------------

def summarize_balances(rows: list[dict]) -> tuple[dict[tuple, float], float]:
    """(은행, 계좌)별 최신 거래후잔액과 전체 합계."""
    latest: dict[tuple, tuple] = {}
    for row in rows:
        if row.get("반영상태") != BANK_REFLECT_OK:
            continue
        balance = row.get("거래후잔액")
        if balance is None:
            continue
        key = (row["은행"], row.get("계좌") or "")
        sort_key = (row.get("거래일") or date.min,
                    row.get("거래일시") or datetime.min,
                    row.get("row_order", 0))
        if key not in latest or sort_key >= latest[key][0]:
            latest[key] = (sort_key, balance)
    balances = {key: value[1] for key, value in latest.items()}
    return balances, sum(balances.values())


# ---------------------------------------------------------------------------
# 거래 이력 누적 (정기지출·입금 예측용)
# ---------------------------------------------------------------------------

def load_history(history_path: Path) -> list[dict]:
    history_path = Path(history_path)
    if not history_path.exists():
        return []
    rows: list[dict] = []
    with open(history_path, encoding="utf-8-sig", newline="") as f:
        for record in csv.DictReader(f):
            row = {
                "거래일시": parse_datetime(record.get("거래일시")),
                "거래일": parse_date(record.get("거래일")),
                "은행": record.get("은행", ""),
                "계좌": record.get("계좌", ""),
                "출금액": parse_amount(record.get("출금액")) or 0.0,
                "입금액": parse_amount(record.get("입금액")) or 0.0,
                "거래후잔액": parse_amount(record.get("거래후잔액")),
                "적요": record.get("적요", ""),
                "기재내용·상대방": record.get("기재내용·상대방", ""),
                "취급점": record.get("취급점", ""),
                "자동분류": record.get("자동분류", ""),
                "내부이체": record.get("내부이체", "") == "True",
                "정기지출후보": False,
                "현금유출입": (parse_amount(record.get("입금액")) or 0.0)
                            - (parse_amount(record.get("출금액")) or 0.0),
                "원본파일": record.get("원본파일", "history"),
                "반영상태": BANK_REFLECT_OK,
                "row_order": 0,
            }
            if row["거래일"] is not None:
                rows.append(row)
    return rows


def save_history(history_path: Path, rows: list[dict]) -> None:
    history_path = Path(history_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = history_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HISTORY_COLUMNS + ["내부이체", "원본파일"])
        for row in sorted(rows, key=lambda r: (r.get("거래일") or date.min,
                                               r.get("거래일시") or datetime.min)):
            writer.writerow([
                row["거래일시"].strftime("%Y-%m-%d %H:%M:%S")
                if row.get("거래일시") else "",
                row["거래일"].strftime("%Y-%m-%d") if row.get("거래일") else "",
                row.get("은행", ""), row.get("계좌", ""),
                row.get("출금액", 0), row.get("입금액", 0),
                "" if row.get("거래후잔액") is None else row["거래후잔액"],
                row.get("적요", ""), row.get("기재내용·상대방", ""),
                row.get("취급점", ""), row.get("자동분류", ""),
                bool(row.get("내부이체")), row.get("원본파일", ""),
            ])
    tmp.replace(history_path)
