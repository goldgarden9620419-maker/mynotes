# -*- coding: utf-8 -*-
"""실행상태·미실행 보완·lock 파일 테스트."""
import json
import os
from datetime import datetime

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


def test_lock_동시실행_방지(tmp_path):
    with RunLock(tmp_path, "2026-W39", "auto"):
        # 살아있는 다른 프로세스(PID 1)가 잡은 것으로 위장
        lock_path = tmp_path / "cashflow_automation.lock"
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        data["pid"] = 1
        lock_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(LockError):
            RunLock(tmp_path, "2026-W39", "manual").acquire()
        # 원상복구 후 release가 정상 동작하도록
        data["pid"] = os.getpid()
        lock_path.write_text(json.dumps(data), encoding="utf-8")
    assert not lock_path.exists()


def test_오래된_lock_복구(tmp_path):
    lock_path = tmp_path / "cashflow_automation.lock"
    lock_path.write_text(json.dumps({
        "pid": 99999999, "started_at": "2026-09-14 09:10:00",
        "week": "2026-W38", "mode": "auto", "auto": True}),
        encoding="utf-8")
    # 죽은 프로세스의 lock은 제거하고 작업을 재개한다
    lock = RunLock(tmp_path, "2026-W39", "auto").acquire()
    assert lock.acquired
    lock.release()
    assert not lock_path.exists()


def test_지난주_미완료_기록(tmp_path):
    state = StateManager(tmp_path)
    state.record_pending_week("2026-W38", STATUS_WAITING_FILES)
    assert state.state["pending_weeks"][0]["week"] == "2026-W38"
    assert iso_week_key(WED_1000.date()) == "2026-W39"
