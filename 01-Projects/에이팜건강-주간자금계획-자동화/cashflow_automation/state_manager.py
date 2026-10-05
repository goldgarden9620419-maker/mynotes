# -*- coding: utf-8 -*-
"""주간 실행상태(state.json)와 중복 실행 방지 lock 파일 관리."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from common import (
    STATUS_NOT_RUN, STATUS_RUNNING, STATUS_SUCCESS,
    atomic_write_json, iso_week_key, read_json,
)

STATE_FILE_NAME = "state.json"
LOCK_FILE_NAME = "cashflow_automation.lock"

DEFAULT_STATE = {
    "last_successful_week": "",
    "last_successful_date": "",
    "last_successful_time": "",
    "last_run_status": STATUS_NOT_RUN,
    "last_run_week": "",
    "last_run_at": "",
    "last_output_file": "",
    "last_error": "",
    "input_signature": "",
    "pending_weeks": [],          # 완료하지 못하고 넘어간 지난 주차 기록
    "running": False,
}


class StateManager:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_path = self.state_dir / STATE_FILE_NAME
        self.state = read_json(self.state_path, DEFAULT_STATE)
        for key, value in DEFAULT_STATE.items():
            self.state.setdefault(key, value)

    # ------------------------------------------------------------------
    def save(self) -> None:
        atomic_write_json(self.state_path, self.state)

    def reload(self) -> None:
        self.state = read_json(self.state_path, DEFAULT_STATE)
        for key, value in DEFAULT_STATE.items():
            self.state.setdefault(key, value)

    # ------------------------------------------------------------------
    def is_week_completed(self, now: datetime) -> bool:
        """이번 주 작업이 SUCCESS로 끝났는지."""
        return (self.state.get("last_run_status") == STATUS_SUCCESS
                and self.state.get("last_successful_week")
                == iso_week_key(now.date()))

    def mark_running(self, now: datetime) -> None:
        self.state["last_run_status"] = STATUS_RUNNING
        self.state["last_run_week"] = iso_week_key(now.date())
        self.state["last_run_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self.state["running"] = True
        self.save()

    def mark_result(self, now: datetime, status: str,
                    output_file: str = "", input_signature: str = "",
                    error: str = "") -> None:
        self.state["last_run_status"] = status
        self.state["last_run_week"] = iso_week_key(now.date())
        self.state["last_run_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self.state["running"] = False
        self.state["last_error"] = error
        if status == STATUS_SUCCESS:
            self.state["last_successful_week"] = iso_week_key(now.date())
            self.state["last_successful_date"] = now.strftime("%Y-%m-%d")
            self.state["last_successful_time"] = now.strftime("%H:%M:%S")
            if output_file:
                self.state["last_output_file"] = output_file
            if input_signature:
                self.state["input_signature"] = input_signature
        self.save()

    def record_pending_week(self, week_key: str, status: str) -> None:
        """다음 주로 넘어가며 완료하지 못한 주차를 별도 기록한다."""
        pending = [p for p in self.state.get("pending_weeks", [])
                   if p.get("week") != week_key]
        pending.append({"week": week_key, "status": status,
                        "recorded_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S")})
        self.state["pending_weeks"] = pending[-20:]
        self.save()

    # ------------------------------------------------------------------
    def should_run_missed_job(self, now: datetime, schedule_hour: int = 9,
                              schedule_minute: int = 10,
                              current_signature: str = "") -> bool:
        """미실행 보완 조건(4번 항목) 판정.

        1) 이번 주 월요일 예정시각 이후이고
        2) 이번 주 SUCCESS 기록이 없고
        3) 동일 작업이 실행 중이 아니고
        4) SUCCESS라면 입력자료가 바뀐 경우에만(그 경우도 자동 재실행은
           하지 않으므로 여기서는 False) 실행한다.
        """
        monday = now.date() - timedelta(days=now.date().weekday())
        scheduled = datetime(monday.year, monday.month, monday.day,
                             schedule_hour, schedule_minute)
        if now < scheduled:
            return False
        if self.is_week_completed(now):
            return False
        if self.state.get("running"):
            return False
        return True

    def input_changed_after_success(self, current_signature: str) -> bool:
        if self.state.get("last_run_status") != STATUS_SUCCESS:
            return False
        saved = self.state.get("input_signature", "")
        return bool(saved) and bool(current_signature) \
            and saved != current_signature


# ---------------------------------------------------------------------------
# Lock 파일
# ---------------------------------------------------------------------------
class LockError(RuntimeError):
    pass


# 잠금은 lock 파일 내용(JSON)과 겹치지 않는 먼 위치의 1바이트에 건다.
# Windows 바이트 잠금은 강제라서 내용 위치를 잠그면 두 번째 실행이
# '누가 잡고 있는지'(PID·시작시각)를 읽지 못한다.
_LOCK_OFFSET = 1 << 20
# 같은 프로세스 안의 재진입용 (main 세션 잠금 → run_weekly_job 잠금)
_HELD: dict[str, list] = {}   # lock 경로 → [열린 파일, 잡은 횟수, 스레드]


def _try_os_lock(f) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(_LOCK_OFFSET)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


class RunLock:
    """중복 실행 방지 lock. with 문으로 사용한다.

    OS 파일 잠금(Windows msvcrt.locking, 그 외 flock)을 쓴다. 잡는 순간이
    원자적이라 동시에 여러 개를 실행해도 하나만 성공하고, 프로세스가
    비정상 종료하면 OS가 잠금을 풀어 주므로 남은 lock 파일이나 PID
    재사용에 속지 않는다. lock 파일 내용(PID·시작시각)은 안내용일 뿐이고,
    파일은 지우지 않는다 (지우면 다른 실행이 새 파일을 잡는 경쟁이 생김).
    같은 프로세스 안에서는 다시 잡을 수 있고, 바깥 잠금이 풀릴 때 해제된다.
    """

    def __init__(self, state_dir: Path, week_key: str, mode: str = "auto"):
        self.lock_path = Path(state_dir) / LOCK_FILE_NAME
        self.week_key = week_key
        self.mode = mode
        self.acquired = False
        self._key = os.path.abspath(self.lock_path)

    def _read(self) -> Optional[dict]:
        if not self.lock_path.exists():
            return None
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return {}

    def acquire(self) -> "RunLock":
        held = _HELD.get(self._key)
        if held is not None:
            if held[2] != threading.get_ident():
                # 같은 프로그램 안이라도 다른 스레드(스케줄러 등)는 막는다
                raise LockError("이미 실행 중입니다 (같은 프로그램의 다른 작업).")
            held[1] += 1
            self.acquired = True
            return self
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.lock_path, "a+b")      # 기존 내용을 지우지 않고 연다
        if not _try_os_lock(f):
            f.close()
            info = self._read() or {}
            raise LockError(
                f"이미 실행 중입니다 (PID {info.get('pid', '?')}, "
                f"시작 {info.get('started_at', '?')}).")
        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "week": self.week_key,
            "mode": self.mode,
            "auto": self.mode == "auto",
        }
        f.seek(0)
        f.truncate()
        f.write(json.dumps(payload, ensure_ascii=False,
                           indent=2).encode("utf-8"))
        f.flush()
        _HELD[self._key] = [f, 1, threading.get_ident()]
        self.acquired = True
        return self

    def release(self) -> None:
        if not self.acquired:
            return
        self.acquired = False
        held = _HELD.get(self._key)
        if held is None:
            return
        held[1] -= 1
        if held[1] > 0:
            return
        del _HELD[self._key]
        f = held[0]
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(_LOCK_OFFSET)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        f.close()                            # 닫으면 flock도 풀린다

    def __enter__(self) -> "RunLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
