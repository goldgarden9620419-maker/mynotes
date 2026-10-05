# -*- coding: utf-8 -*-
"""확인 파일 중복 열기 방지와 초 단위 파일명 (2차 개선 A).

Excel은 연 통합문서를 쓰기 공유 거부로 잡는다. 테스트에서는 자식
프로세스가 같은 방식(CreateFileW, 읽기 공유만 허용)으로 파일을 잡아
'Excel에 열려 있는 상태'를 흉내 낸다.
"""
import logging
import os
import re
import subprocess
import sys
from datetime import datetime

import pytest

import app
import weekly_reconcile
from tests.conftest import make_full_inputs

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows 전용 동작")

_HOLD = r"""
import ctypes, sys, time
from ctypes import wintypes
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = wintypes.HANDLE
k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                          wintypes.HANDLE]
h = k.CreateFileW(sys.argv[1], 0x80000000, 1, None, 3, 0, None)
if h == wintypes.HANDLE(-1).value:
    print("fail", ctypes.get_last_error(), flush=True)
    sys.exit(1)
print("ready", flush=True)
time.sleep(30)
"""


@pytest.fixture
def held_like_excel():
    procs = []

    def hold(path):
        p = subprocess.Popen([sys.executable, "-c", _HOLD, str(path)],
                             stdout=subprocess.PIPE, text=True)
        procs.append(p)
        assert p.stdout.readline().strip() == "ready"
        return p
    yield hold
    for p in procs:
        p.kill()
        p.wait()


@pytest.fixture
def startfile_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(os, "startfile", lambda p: calls.append(str(p)))
    return calls


def test_Excel에_열려있으면_다시_열지_않는다(tmp_path, held_like_excel,
                                   startfile_calls, caplog, capsys):
    f = tmp_path / "확인필요_20261005_091000.xlsx"
    f.write_bytes(b"x")
    held_like_excel(f)
    with caplog.at_level(logging.INFO, logger="test"):
        opened = app._open_file(f, logging.getLogger("test"))
    assert opened is False
    assert startfile_calls == []
    assert "이미 열려 있음" in caplog.text
    assert "이미 열려 있음" in capsys.readouterr().out


def test_열려있지_않으면_한번_연다(tmp_path, startfile_calls):
    f = tmp_path / "확인필요_20261005_091000.xlsx"
    f.write_bytes(b"x")
    assert app._open_file(f) is True
    assert startfile_calls == [str(f)]


def test_남은_잠금표시파일만_있으면_연다(tmp_path, startfile_calls):
    # Excel 비정상 종료 후 ~$ 파일만 남은 경우 — 실제로는 열려 있지 않다
    f = tmp_path / "확인필요_20261005_091000.xlsx"
    f.write_bytes(b"x")
    (tmp_path / f"~${f.name}").write_bytes(b"owner")
    assert app._open_file(f) is True
    assert startfile_calls == [str(f)]


_SECONDS = re.compile(r"_\d{8}_\d{6}(_\d+)?\.xlsx$")


def test_확인필요_파일명은_초까지(env):
    from state_manager import StateManager
    now = datetime(2026, 9, 21, 9, 15, 42)
    make_full_inputs(env, now)
    app.run_weekly_job(env, StateManager(env.state_dir),
                       logging.getLogger("test"), now=now, mode="auto")
    names = [p.name for p in env.folder("review").glob("확인필요_*.xlsx")]
    assert names and all(_SECONDS.search(n) for n in names), names
    assert any("_20260921_091542" in n for n in names)


def test_주간대조_파일명은_초까지(env):
    now = datetime(2026, 9, 21, 9, 15, 42)
    make_full_inputs(env, now)
    out = weekly_reconcile.run_weekly_reconcile(
        env, logging.getLogger("test"), now=now, open_file=False)
    assert out.name == "주간대조_20260921_091542.xlsx"


def test_같은_초에_다시_만들어도_덮어쓰지_않는다(env):
    now = datetime(2026, 9, 21, 9, 15, 42)
    make_full_inputs(env, now)
    log = logging.getLogger("test")
    a = weekly_reconcile.run_weekly_reconcile(env, log, now=now, open_file=False)
    b = weekly_reconcile.run_weekly_reconcile(env, log, now=now, open_file=False)
    assert a != b and a.exists() and b.exists()
