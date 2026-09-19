# -*- coding: utf-8 -*-
"""실행 로그 관리.

automation_YYYYMMDD.log 파일에 기록한다.
대외비 세부정보(임직원 이름, 급여 상세)는 기록하지 않는 것이 원칙이며,
호출부에서 상세 대신 건수·총액만 넘기도록 한다. 방어적으로 급여 관련
키워드가 메시지에 섞이면 마스킹한다.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

_CONF_PATTERN = re.compile(
    r"(급여|상여|퇴직금|퇴직연금)\s*[:=]?\s*[\d,]+원?")


class ConfidentialFilter(logging.Filter):
    """급여 금액 등 대외비로 보이는 패턴을 로그에서 가린다."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        masked = _CONF_PATTERN.sub(lambda m: m.group(0).split()[0].rstrip(
            ":=0123456789,원") + "(대외비: 금액 비공개)", msg)
        if masked != msg:
            record.msg = masked
            record.args = ()
        return True


def get_logger(log_dir: Path, name: str = "cashflow",
               today: date | None = None) -> logging.Logger:
    """일자별 로그 파일 핸들러가 붙은 로거를 돌려준다."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    today = today or date.today()
    log_path = log_dir / f"automation_{today.strftime('%Y%m%d')}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 같은 날짜 파일 핸들러가 이미 붙어있으면 재사용
    want = str(log_path)
    has_handler = False
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            if getattr(handler, "baseFilename", "") == want:
                has_handler = True
            else:
                logger.removeHandler(handler)
                handler.close()
    if not has_handler:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))
        fh.addFilter(ConfidentialFilter())
        logger.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler)
               and not isinstance(h, logging.FileHandler)
               for h in logger.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        sh.addFilter(ConfidentialFilter())
        logger.addHandler(sh)
    return logger
