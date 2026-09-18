# -*- coding: utf-8 -*-
"""공통 상수와 유틸리티.

팀 정의, 열 이름, 상태 값, 날짜/금액 파싱 등 여러 모듈이 함께 쓰는
기반 요소를 모아 둔다. 대외비 관련 상수도 여기서 관리한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

APP_NAME = "cashflow_automation"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# 팀 정의
# ---------------------------------------------------------------------------
TEAMS = [
    {"name": "경영지원팀", "code": "경영", "confidential": True,
     "file": "경영지원팀_대외비_지출계획.xlsx"},
    {"name": "건강사업팀", "code": "건강", "confidential": False,
     "file": "건강사업팀_주간지출계획.xlsx"},
    {"name": "물류팀", "code": "물류", "confidential": False,
     "file": "물류팀_주간지출계획.xlsx"},
    {"name": "CS팀", "code": "CS", "confidential": False,
     "file": "CS팀_주간지출계획.xlsx"},
    {"name": "디자인팀", "code": "디자인", "confidential": False,
     "file": "디자인팀_주간지출계획.xlsx"},
    {"name": "데이터사이언스팀", "code": "데이터", "confidential": False,
     "file": "데이터사이언스팀_주간지출계획.xlsx"},
    {"name": "연구팀", "code": "연구", "confidential": False,
     "file": "연구팀_주간지출계획.xlsx"},
]
TEAM_CODE_BY_NAME = {t["name"]: t["code"] for t in TEAMS}
TEAM_NAME_BY_CODE = {t["code"]: t["name"] for t in TEAMS}

BANKS = ["농협", "우리은행", "국민은행"]

# ---------------------------------------------------------------------------
# 팀 제출양식 열
# ---------------------------------------------------------------------------
TEAM_SHEET_NAME = "지출계획"
TEAM_TABLE_NAME = "tbl_지출계획"
REQUIRED_TEAM_COLUMNS = [
    "요청ID", "팀코드", "팀명", "최초등록일", "일련번호", "지급예정일",
    "거래처", "지출내용", "예상금액", "지급방법", "카드구분",
    "확정여부", "진행상태", "최종수정일", "비고",
]

PAY_METHOD_TRANSFER = "계좌송금"
PAY_METHOD_CARD = "법인카드"
PAY_METHOD_AUTO = "자동이체"
PAY_METHOD_UNDECIDED = "미정"
PAY_METHODS = [PAY_METHOD_TRANSFER, PAY_METHOD_CARD, PAY_METHOD_AUTO,
               PAY_METHOD_UNDECIDED]

CONFIRM_YES = "확정"
CONFIRM_NO = "미확정"
CONFIRM_VALUES = [CONFIRM_YES, CONFIRM_NO]

PROGRESS_NEW = "신규"
PROGRESS_CHANGED = "변경"
PROGRESS_CANCELLED = "취소"
PROGRESS_PAID = "지급완료"
PROGRESS_VALUES = [PROGRESS_NEW, PROGRESS_CHANGED, PROGRESS_CANCELLED,
                   PROGRESS_PAID]

# 팀지출계획_통합 반영상태 (19번 항목)
REFLECT_OK = "정상반영"
REFLECT_UNCONFIRMED = "미확정"
REFLECT_CANCELLED = "취소"
REFLECT_DUPLICATE = "중복제외"
REFLECT_CARD_DATE_NEEDED = "결제일확인필요"
REFLECT_MISSING_INFO = "정보누락"
REFLECT_PAID = "지급완료"

# 예정·실제 대조 결과 (20번 항목)
MATCH_PAID = "지급완료"
MATCH_PARTIAL = "일부지급"
MATCH_AMOUNT_DIFF = "금액차이"
MATCH_DATE_DIFF = "지급일차이"
MATCH_NOT_FOUND = "실제출금미확인"
MATCH_UNPLANNED = "계획없는출금"
MATCH_MANUAL = "수동확인필요"

# 실행 상태 (5번 항목)
STATUS_NOT_RUN = "NOT_RUN"
STATUS_RUNNING = "RUNNING"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_WAITING_FILES = "WAITING_FILES"
STATUS_PARTIAL = "PARTIAL"
STATUS_CANCELLED = "CANCELLED"

# 은행 표준 열 (16번 항목)
BANK_STD_COLUMNS = [
    "거래일시", "거래일", "은행", "계좌", "출금액", "입금액", "거래후잔액",
    "적요", "기재내용·상대방", "취급점", "자동분류", "내부이체",
    "정기지출후보", "현금유출입", "원본파일", "반영상태",
]
BANK_REFLECT_OK = "정상반영"
BANK_REFLECT_DUPLICATE = "중복제외"

# 대외비 표시 분류 (15번 항목)
CONF_CAT_PAYROLL = "급여·인건비(대외비)"
CONF_CAT_RETIRE = "퇴직금·퇴직연금(대외비)"
CONF_CAT_TAX_INS = "세금·보험(대외비)"
CONF_CAT_ETC = "기타 대외비 지출"
CONFIDENTIAL_CATEGORIES = [CONF_CAT_PAYROLL, CONF_CAT_RETIRE,
                           CONF_CAT_TAX_INS, CONF_CAT_ETC]
CONFIDENTIAL_MASK = "대외비"

# 대외비구분 자동 판정 키워드 (지출내용 기준)
_CONF_KEYWORDS = [
    (CONF_CAT_RETIRE, ["퇴직금", "퇴직연금", "DC형", "DB형", "IRP"]),
    (CONF_CAT_PAYROLL, ["급여", "상여", "인건비", "월급", "성과급"]),
    (CONF_CAT_TAX_INS, ["4대보험", "사대보험", "국민연금", "건강보험", "고용보험",
                        "산재보험", "원천세", "원천징수", "부가세", "부가가치세",
                        "법인세", "지방세", "지방소득세", "세금", "보험료"]),
]


def classify_confidential(text: str, explicit: str = "") -> str:
    """대외비 항목을 표시용 4개 분류 중 하나로 판정한다.

    explicit(양식의 '대외비구분' 열 값)이 유효하면 그것을 우선 사용한다.
    """
    explicit = (explicit or "").strip()
    if explicit in CONFIDENTIAL_CATEGORIES:
        return explicit
    for cat, keywords in _CONF_KEYWORDS:
        for kw in keywords:
            if kw in (text or ""):
                return cat
    return CONF_CAT_ETC


# ---------------------------------------------------------------------------
# 날짜 / 금액 파싱
# ---------------------------------------------------------------------------
_DATE_PATTERNS = [
    "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d",
    "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M", "%Y/%m/%d %H:%M",
    "%Y년 %m월 %d일", "%Y년%m월%d일",
]


def parse_date(value: Any) -> Optional[date]:
    """엑셀/CSV의 다양한 날짜 표현을 date로 변환한다. 실패 시 None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        # 20260918 형태 또는 엑셀 직렬값
        iv = int(value)
        if 19000101 <= iv <= 21001231:
            try:
                return datetime.strptime(str(iv), "%Y%m%d").date()
            except ValueError:
                return None
        if 20000 <= iv <= 80000:  # 엑셀 직렬 날짜 (1954~2119년경)
            return (datetime(1899, 12, 30) + timedelta(days=iv)).date()
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    # "2026-09-18(금)" 같은 꼬리표 제거 후 재시도
    m = re.match(r"(\d{4}[-./]\d{1,2}[-./]\d{1,2})", text)
    if m:
        norm = re.sub(r"[./]", "-", m.group(1))
        try:
            return datetime.strptime(norm, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def parse_datetime(value: Any) -> Optional[datetime]:
    """거래일시 파싱. 시각 정보가 없으면 None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    m = re.match(
        r"(\d{4})[-./]?(\d{2})[-./]?(\d{2})[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?",
        text)
    if m:
        y, mo, d, h, mi = (int(m.group(i)) for i in range(1, 6))
        s = int(m.group(6) or 0)
        try:
            return datetime(y, mo, d, h, mi, s)
        except ValueError:
            return None
    return None


def parse_amount(value: Any) -> Optional[float]:
    """금액 파싱. 콤마·원·공백 허용. 빈 값이면 None."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("원", "")
    text = text.replace(" ", "")
    if not text or text in {"-", "."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_text(value: Any) -> str:
    """비교용 문자열 정규화(NFC, 공백 정리)."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value))
    return re.sub(r"\s+", " ", text).strip()


WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def weekday_ko(d: date) -> str:
    return WEEKDAY_KO[d.weekday()]


def iso_week_key(d: date) -> str:
    """ISO 연도-주차 문자열. 예: 2026-W38"""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def week_monday(d: date) -> date:
    """해당 날짜가 속한 주의 월요일."""
    return d - timedelta(days=d.weekday())


def get_timezone(name: str = "Asia/Seoul"):
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:  # pragma: no cover - tzdata 미설치 환경
            return None
    return None


def now_local(tz_name: str = "Asia/Seoul") -> datetime:
    tz = get_timezone(tz_name)
    if tz is not None:
        return datetime.now(tz).replace(tzinfo=None)
    return datetime.now()


# ---------------------------------------------------------------------------
# 파일 유틸리티
# ---------------------------------------------------------------------------

def atomic_write_json(path: Path, data: dict) -> None:
    """임시파일에 쓴 뒤 교체하여 상태파일 손상을 막는다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path, default: Optional[dict] = None) -> dict:
    path = Path(path)
    if not path.exists():
        return dict(default or {})
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(default or {})


def unique_path(path: Path) -> Path:
    """이미 존재하면 _2, _3 … 접미사를 붙여 덮어쓰기를 막는다."""
    path = Path(path)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 1000):
        candidate = path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"고유한 파일명을 만들 수 없습니다: {path}")


def files_signature(paths: Iterable[Path]) -> str:
    """입력파일 목록의 변경 감지용 서명(경로+크기+수정시각 해시)."""
    items = []
    for p in sorted(Path(x) for x in paths):
        try:
            st = p.stat()
            items.append(f"{p.name}|{st.st_size}|{int(st.st_mtime)}")
        except OSError:
            items.append(f"{p.name}|missing")
    digest = hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()
    return digest[:16]


def pid_alive(pid: int) -> bool:
    """해당 PID의 프로세스가 살아있는지 확인한다(Windows/리눅스 공용)."""
    if pid <= 0:
        return False
    if os.name == "nt":  # pragma: no cover - Windows 전용 경로
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
