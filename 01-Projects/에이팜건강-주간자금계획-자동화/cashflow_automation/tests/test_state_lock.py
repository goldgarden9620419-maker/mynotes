# -*- coding: utf-8 -*-
"""실행상태·미실행 보완·lock 파일 테스트."""
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from common import STATUS_SUCCESS, STATUS_WAITING_FILES, iso_week_key
from state_manager import LockError, RunLock, StateManager

MON_0800 = datetime(2026, 9, 21, 8, 0)    # 월요일 예정시각 전
MON_1400 = datetime(2026, 9, 21, 14, 0)   # 월요일 오후
WED_1000 = datetime(2026, 9, 23, 10, 0)   # 수요일


def test_pc종료후_미실행_보완(tmp_path):
    state = StateManager(tmp_path)
    # 예정시각 전에는 실행하지 않는다
    assert not state.should_run_missed_job(MON_0800)
    # 월요일 오후에 PC를 켜면 즉시 실행
    assert state.should_run_missed_job(MON_1400)
    # 수요일에 처음 켜도 이번 주 결과가 없으면 실행
    assert state.should_run_missed_job(WED_1000)


def test_성공한_주는_재실행하지_않는다(tmp_path):
    state = StateManager(tmp_path)
    state.mark_result(MON_1400, STATUS_SUCCESS, output_file="결과.xlsx",
                      input_signature="abc")
    assert state.is_week_completed(WED_1000)
    assert not state.should_run_missed_job(WED_1000)
    # 다음 주가 되면 다시 실행 대상
    next_week = datetime(2026, 9, 28, 10, 0)
    assert not state.is_week_completed(next_week)
    assert state.should_run_missed_job(next_week)


def test_프로그램_재시작후_미실행_보완(tmp_path):
    state = StateManager(tmp_path)
    state.mark_result(MON_1400, STATUS_WAITING_FILES, error="파일 대기")
    # 새 프로세스가 state.json을 다시 읽는 상황
    restarted = StateManager(tmp_path)
    assert restarted.state["last_run_status"] == STATUS_WAITING_FILES
    assert restarted.should_run_missed_job(WED_1000)


def test_실행중이면_보완하지_않는다(tmp_path):
    state = StateManager(tmp_path)
    state.mark_running(MON_1400)
    assert not state.should_run_missed_job(MON_1400)


def test_입력변경_감지(tmp_path):
    state = StateManager(tmp_path)
    state.mark_result(MON_1400, STATUS_SUCCESS, input_signature="sig1")
    assert not state.input_changed_after_success("sig1")
    assert state.input_changed_after_success("sig2")


ROOT = str(Path(__file__).resolve().parent.parent)

# 자식 프로세스: RunLock을 잡고 'locked'를 알린 뒤 버틴다
_HOLD = (
    "import os, sys, time; sys.path.insert(0, sys.argv[2])\n"
    "from state_manager import RunLock\n"
    "RunLock(sys.argv[1], '2026-W39', 'manual').acquire()\n"
    "print('locked', os.getpid(), flush=True); time.sleep(60)\n")

# 자식 프로세스: go 파일이 생기면 동시에 잠금을 시도하고 결과를 알린다
_RACE = (
    "import os, sys, time; sys.path.insert(0, sys.argv[2])\n"
    "from state_manager import LockError, RunLock\n"
    "print('ready', flush=True)\n"
    "while not os.path.exists(sys.argv[3]): time.sleep(0.002)\n"
    "try:\n"
    "    RunLock(sys.argv[1], '2026-W39', 'manual').acquire()\n"
    "    print('OK', flush=True); time.sleep(3)\n"
    "except LockError:\n"
    "    print('LOCKED', flush=True)\n")


@pytest.fixture
def holder(tmp_path):
    procs = []

    def start(state_dir=tmp_path):
        p = subprocess.Popen([sys.executable, "-c", _HOLD, str(state_dir), ROOT],
                             stdout=subprocess.PIPE, text=True)
        word, pid = p.stdout.readline().split()
        assert word == "locked"
        # venv의 python.exe는 실제 인터프리터를 자식으로 띄운다 — 잠금을
        # 잡은 실제 프로세스의 PID를 따로 기억해 둔다
        procs.append((p, int(pid)))
        return int(pid)
    yield start
    for p, pid in procs:
        _terminate(pid)
        p.kill()
        p.wait()


def _terminate(pid):
    try:
        os.kill(pid, signal.SIGTERM)    # Windows에서는 TerminateProcess
    except OSError:
        pass


def test_lock_다른_프로세스가_잡고_있으면_이미_실행중(tmp_path, holder):
    pid = holder()
    with pytest.raises(LockError, match="이미 실행 중입니다") as exc:
        RunLock(tmp_path, "2026-W39", "manual").acquire()
    assert str(pid) in str(exc.value)   # 누가 잡고 있는지 안내


def test_lock_강제종료된_실행의_잠금은_바로_풀린다(tmp_path, holder):
    pid = holder()
    _terminate(pid)
    time.sleep(0.5)                     # OS가 핸들을 정리할 시간
    lock = RunLock(tmp_path, "2026-W39", "manual").acquire()
    assert lock.acquired
    lock.release()


def test_lock_PID_재사용에_속지_않는다(tmp_path):
    # 남은 잠금 파일의 PID를 지금 살아 있는 '관계없는' 프로세스가
    # 재사용한 상황 — 잠금을 잡고 있지 않으므로 실행돼야 한다
    unrelated = subprocess.Popen([sys.executable, "-c",
                                  "import time; time.sleep(30)"])
    try:
        (tmp_path / "cashflow_automation.lock").write_text(json.dumps({
            "pid": unrelated.pid, "started_at": "2026-09-14 09:10:00",
            "week": "2026-W38", "mode": "manual"}), encoding="utf-8")
        lock = RunLock(tmp_path, "2026-W39", "manual").acquire()
        assert lock.acquired
        lock.release()
    finally:
        unrelated.kill()
        unrelated.wait()


def test_lock_동시에_여러개_실행해도_하나만_성공(tmp_path):
    go = tmp_path / "go"
    procs = [subprocess.Popen([sys.executable, "-c", _RACE, str(tmp_path),
                               ROOT, str(go)],
                              stdout=subprocess.PIPE, text=True)
             for _ in range(6)]
    try:
        for p in procs:
            assert p.stdout.readline().strip() == "ready"
        go.write_text("go")
        results = [p.stdout.readline().strip() for p in procs]
    finally:
        for p in procs:
            p.kill()
            p.wait()
    assert sorted(results) == ["LOCKED"] * 5 + ["OK"]


def test_lock_같은_프로세스_안에서는_다시_잡을_수_있다(tmp_path):
    # main()이 세션 전체를 잡고, 안쪽 run_weekly_job도 잠금을 잡는다
    with RunLock(tmp_path, "2026-W39", "manual"):
        with RunLock(tmp_path, "2026-W39", "manual"):
            pass
        # 안쪽이 풀려도 바깥 잠금은 유지된다
        with pytest.raises(LockError):
            _try_from_child(tmp_path)
    _try_from_child(tmp_path)   # 바깥까지 풀리면 다른 프로세스가 잡는다


def _try_from_child(tmp_path):
    code = ("import sys; sys.path.insert(0, sys.argv[2])\n"
            "from state_manager import RunLock\n"
            "RunLock(sys.argv[1], 'W', 'manual').acquire()\n")
    r = subprocess.run([sys.executable, "-c", code, str(tmp_path), ROOT],
                       capture_output=True)
    if r.returncode != 0:
        raise LockError("다른 프로세스가 잠금을 잡지 못함")


def test_오래된_lock_복구(tmp_path):
    lock_path = tmp_path / "cashflow_automation.lock"
    lock_path.write_text(json.dumps({
        "pid": 99999999, "started_at": "2026-09-14 09:10:00",
        "week": "2026-W38", "mode": "auto", "auto": True}),
        encoding="utf-8")
    # 죽은 프로세스가 남긴 lock 파일이 있어도 작업을 재개한다
    lock = RunLock(tmp_path, "2026-W39", "auto").acquire()
    assert lock.acquired
    lock.release()
    again = RunLock(tmp_path, "2026-W39", "auto").acquire()
    again.release()


def test_지난주_미완료_기록(tmp_path):
    state = StateManager(tmp_path)
    state.record_pending_week("2026-W38", STATUS_WAITING_FILES)
    assert state.state["pending_weeks"][0]["week"] == "2026-W38"
    assert iso_week_key(WED_1000.date()) == "2026-W39"


# --- 바탕화면 바로가기(.bat) → app.main() 수동 실행 ---------------------

def _cli(env, *flags):
    return ["--config", str(env.config_path), "--base-dir", str(env.base_dir),
            *flags]


@pytest.mark.parametrize("flag", ["--run-now", "--weekly-reconcile"])
def test_main_이미_실행중이면_안내하고_종료코드3(env, holder, capsys, flag):
    import app
    holder(env.state_dir)
    assert app.main(_cli(env, flag)) == 3
    assert "이미 실행 중입니다" in capsys.readouterr().out


def test_main_확인대기까지_잠금을_유지한다(env, monkeypatch):
    # 확인필요 검토를 기다리는 동안 다시 눌러도 새 실행이 시작되면 안 된다
    import app
    from common import STATUS_REVIEW_WAIT

    seen = []

    def fake_job(*a, **k):
        return app.RunResult(STATUS_REVIEW_WAIT, "대기")

    def fake_wait(*a, **k):
        try:
            _try_from_child(env.state_dir)
            seen.append("다른 실행이 잠금을 잡음")
        except LockError:
            seen.append("막힘")
        return app.RunResult(STATUS_REVIEW_WAIT, "대기 종료")

    monkeypatch.setattr(app, "run_weekly_job", fake_job)
    monkeypatch.setattr(app, "_wait_for_confirmation", fake_wait)
    assert app.main(_cli(env, "--run-now")) == 0
    assert seen == ["막힘"]
    _try_from_child(env.state_dir)          # 끝나면 풀린다


def test_lock_같은_프로세스라도_다른_스레드는_막는다(tmp_path):
    import threading
    errors = []

    def other_thread():
        try:
            RunLock(tmp_path, "2026-W39", "auto").acquire().release()
        except LockError as exc:
            errors.append(str(exc))

    with RunLock(tmp_path, "2026-W39", "manual"):
        t = threading.Thread(target=other_thread)
        t.start()
        t.join()
    assert len(errors) == 1 and "이미 실행 중입니다" in errors[0]
