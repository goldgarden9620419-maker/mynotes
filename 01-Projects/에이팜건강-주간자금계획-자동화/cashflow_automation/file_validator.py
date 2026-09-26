# -*- coding: utf-8 -*-
"""입력파일 존재·상태 검사 (18번 항목).

행 단위 상세 검사는 team_loader / bank_loader가 수행하고,
여기서는 실행 전 필수파일 존재와 열기 가능 여부를 확인한다.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from common import BANKS, STATUS_PARTIAL, STATUS_WAITING_FILES, files_signature
from bank_loader import SUPPORTED_SUFFIXES


class ValidationResult:
    def __init__(self):
        self.missing_teams: list[str] = []
        self.missing_banks: list[str] = []
        self.corrupted: list[dict] = []
        self.input_files: list[Path] = []

    @property
    def missing_required(self) -> list[str]:
        return ([f"팀 파일: {t}" for t in self.missing_teams]
                + [f"은행 거래내역: {b}" for b in self.missing_banks])

    @property
    def ok(self) -> bool:
        return not self.missing_required and not self.corrupted

    @property
    def status_if_incomplete(self) -> str:
        return STATUS_WAITING_FILES if self.missing_required else STATUS_PARTIAL

    def summary(self) -> str:
        parts = []
        if self.missing_teams:
            parts.append("미제출 팀: " + ", ".join(self.missing_teams))
        if self.missing_banks:
            parts.append("은행자료 누락: " + ", ".join(self.missing_banks))
        if self.corrupted:
            parts.append(f"손상 의심 파일 {len(self.corrupted)}건")
        return "; ".join(parts) if parts else "입력파일 정상"


def _xlsx_openable(path: Path) -> bool:
    """xlsx는 zip 컨테이너다. 빠른 손상 검사."""
    try:
        with zipfile.ZipFile(path) as z:
            return "[Content_Types].xml" in z.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _bank_file_readable(path: Path) -> bool:
    """은행 파일은 확장자와 내용이 달라도 읽으므로, 내용 기준으로만
    판독 가능성을 검사한다 (zip/OLE/텍스트 중 하나면 통과 —
    상세 해석은 bank_loader가 담당)."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    if head[:2] == b"PK":
        return _xlsx_openable(path)
    if head == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return True
    try:
        raw = path.read_bytes()
    except OSError:
        return False
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            raw.decode("utf-16")
            return True
        except (UnicodeDecodeError, UnicodeError):
            return False
    if b"\x00" in raw:          # NUL이 섞인 이진 파일은 텍스트가 아니다
        return False
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            raw.decode(encoding)
            return True
        except (UnicodeDecodeError, UnicodeError):
            continue
    return False


def bank_files(cfg, bank: str) -> list[Path]:
    bank_dir = cfg.bank_dir(bank)
    if not bank_dir.exists():
        return []
    return sorted(p for p in bank_dir.glob("*")
                  if p.suffix.lower() in SUPPORTED_SUFFIXES
                  and not p.name.startswith("~$"))


def validate_inputs(cfg) -> ValidationResult:
    """필수 입력파일 검사. 상세 내용 검사는 로더가 담당한다."""
    from team_loader import find_consolidated_file

    result = ValidationResult()

    # 통일 취합 파일이 있으면 그 파일 하나가 전 팀 입력을 대신한다
    consolidated = find_consolidated_file(cfg.folder("confidential_admin"))
    if consolidated is not None:
        result.input_files.append(consolidated)
        if not _xlsx_openable(consolidated):
            result.corrupted.append({"구분": "손상된 파일",
                                     "팀명": "취합",
                                     "내용": "파일을 열 수 없습니다: "
                                            f"{consolidated.name}",
                                     "원본파일": consolidated.name})
    else:
        for team, path in cfg.team_files():
            if not path.exists():
                result.missing_teams.append(team["name"])
                continue
            result.input_files.append(path)
            if path.suffix.lower() == ".xlsx" and not _xlsx_openable(path):
                result.corrupted.append({"구분": "손상된 파일",
                                         "팀명": team["name"],
                                         "내용": "파일을 열 수 없습니다: "
                                                f"{path.name}",
                                         "원본파일": path.name})

    for bank in BANKS:
        files = bank_files(cfg, bank)
        if not files:
            result.missing_banks.append(bank)
            continue
        for path in files:
            result.input_files.append(path)
            if not _bank_file_readable(path):
                result.corrupted.append({"구분": "손상된 파일", "은행": bank,
                                         "내용": f"파일을 열 수 없습니다: {path.name}",
                                         "원본파일": path.name})
    return result


def current_input_signature(cfg) -> str:
    """입력자료 변경 감지용 서명 (29번 항목)."""
    result = validate_inputs(cfg)
    return files_signature(result.input_files)
