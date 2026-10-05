# -*- coding: utf-8 -*-
"""바탕화면 바로가기용 .bat 파일 구조 검사 (2차 개선: 주간대조 바로가기).

실제 실행은 Windows cmd에서만 가능하므로 여기서는 연결 관계와
cmd가 요구하는 형식(CRLF 줄끝, UTF-8)만 확인한다.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "지금_실행.bat"
RECONCILE = ROOT / "주간대조_실행.bat"
SHORTCUTS = ROOT / "바탕화면_바로가기_만들기.bat"


def _text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def test_주간대조_bat은_지금실행_bat을_reconcile로_부른다():
    assert RECONCILE.exists()
    assert 'call "%~dp0지금_실행.bat" reconcile' in _text(RECONCILE)


def test_지금실행_bat에_주간대조_분기가_있다():
    text = _text(RUN)
    assert 'if /i "%~1"=="reconcile" goto :reconcile' in text
    assert ":reconcile" in text and "--weekly-reconcile" in text
    # 주간대조는 --run-now 전용 옵션을 쓰지 않는다
    reconcile_part = text.split("\r\n:reconcile\r\n", 1)[1]   # 레이블 이후
    assert "--force" not in reconcile_part
    assert "--allow-partial" not in reconcile_part


def test_바로가기_만들기가_주간대조_바로가기도_만든다():
    text = _text(SHORTCUTS)
    assert "자금계획 주간 대조.lnk" in text
    assert "주간대조_실행.bat" in text


@pytest.mark.parametrize("path", [RUN, RECONCILE, SHORTCUTS],
                         ids=lambda p: p.name)
def test_bat은_CRLF_줄끝(path):
    data = path.read_bytes()
    assert data.count(b"\n") == data.count(b"\r\n") > 0
