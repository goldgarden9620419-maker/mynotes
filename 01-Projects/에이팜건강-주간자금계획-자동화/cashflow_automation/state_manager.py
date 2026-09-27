# -*- coding: utf-8 -*-
"""주간 실행상태(state.json)와 중복 실행 방지 lock 파일 관리."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from common import (
    STATUS_NOT_RUN, STATUS_RUNNING, STATUS_SUCCESS,
    atomic_write_json, iso_week_key, pid_alive, read_json,
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


class RunLock:
    """중복 실행 방지 lock. with 문으로 사용한다."""

    def __init__(self, state_dir: Path, week_key: str, mode: str = "auto"):
        self.lock_path = Path(state_dir) / LOCK_FILE_NAME
        self.week_key = week_key
        self.mode = mode
        self.acquired = False

    def _read(self) -> Optional[dict]:
        if not self.lock_path.exists():
            return None
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def acquire(self) -> "RunLock":
        existing = self._read()
        if existing is not None:
            pid = int(existing.get("pid", 0) or 0)
            if pid and pid != os.getpid() and pid_alive(pid):
                raise LockError(
                    f"다른 실행이 진행 중입니다 (PID {pid}, "
                    f"시작 {existing.get('started_at', '?')}).")
            # 남아있는 오래된 lock: 프로세스가 없으므로 제거 후 재개
            try:
                self.lock_path.unlink()
            except OSError:
                pass
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "week": self.week_key,
            "mode": self.mode,
            "auto": self.mode == "auto",
        }
        with open(self.lock_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.acquired = True
        return self

    def release(self) -> None:
        if not self.acquired:
            return
        info = self._read()
        if info and int(info.get("pid", 0) or 0) == os.getpid():
            try:
                self.lock_path.unlink()
            except OSError:
                pass
        self.acquired = False

    def __enter__(self) -> "RunLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
