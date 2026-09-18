# -*- coding: utf-8 -*-
"""APScheduler 기반 상주 스케줄러 (3~6, 18, 29번 항목).

- 매주 월요일 09:10 (Asia/Seoul) 자동 실행
- 시작 시 미실행 보완 (PC/프로그램이 꺼져 있던 경우)
- WAITING_FILES 상태면 10분 간격 재검사 (프로그램 재시작 후에도 계속)
- SUCCESS 이후 입력자료 변경 감지 시 알림 (자동 재실행 없음)
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import app as app_module
import file_validator
from common import (
    STATUS_SUCCESS, STATUS_WAITING_FILES, iso_week_key, now_local,
)


class AutomationService:
    """트레이/헤드리스에서 함께 쓰는 실행 서비스."""

    def __init__(self, cfg, state, log):
        self.cfg = cfg
        self.state = state
        self.log = log
        self.scheduler = BackgroundScheduler(
            timezone=cfg.timezone_name,
            job_defaults={"coalesce": True, "misfire_grace_time": 3600,
                          "max_instances": 1})
        self.paused = False
        self.last_result: Optional[app_module.RunResult] = None
        self._job_lock = threading.Lock()
        self._notified_signature = ""
        self._quiet_until: Optional[datetime] = None
        # 트레이가 등록하는 알림 콜백: (제목, 내용)
        self.notify: Callable[[str, str], None] = \
            lambda title, msg: self.log.info("[알림] %s — %s", title, msg)

    # ------------------------------------------------------------------
    # 시작/종료
    # ------------------------------------------------------------------
    def start(self) -> None:
        schedule = self.cfg.get("schedule", default={}) or {}
        self.scheduler.add_job(
            self._scheduled_run, CronTrigger(
                day_of_week=schedule.get("day_of_week", "mon"),
                hour=int(schedule.get("hour", 9)),
                minute=int(schedule.get("minute", 10)),
                timezone=self.cfg.timezone_name),
            id="weekly", name="주간 자금계획 자동 실행")
        interval = int(self.cfg.get("retry", "interval_minutes", default=10))
        self.scheduler.add_job(
            self._periodic_check, IntervalTrigger(minutes=max(1, interval)),
            id="periodic", name="파일 대기·변경 감지 검사")
        self.scheduler.start()
        self.log.info("스케줄러 시작. 다음 자동 실행: %s", self.next_run_text())

        if self.cfg.get("startup", "check_missed_run", default=True):
            threading.Thread(target=self.check_missed_run, daemon=True).start()

    def stop(self) -> None:
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 실행 진입점
    # ------------------------------------------------------------------
    def _scheduled_run(self) -> None:
        if self.paused:
            self.log.info("자동실행 일시정지 상태라 예정 실행을 건너뜁니다.")
            return
        self.run_job(mode="auto")

    def run_job(self, mode: str = "auto", allow_partial: bool = False,
                force: bool = False) -> app_module.RunResult:
        """중복 실행을 막고 파이프라인을 수행한다."""
        if not self._job_lock.acquire(blocking=False):
            self.log.info("이미 작업이 실행 중입니다 (%s 요청 무시).", mode)
            return app_module.RunResult("LOCKED", "이미 실행 중입니다.")
        try:
            self.state.reload()
            result = app_module.run_weekly_job(
                self.cfg, self.state, self.log, mode=mode,
                allow_partial=allow_partial, force=force)
            self.last_result = result
            self._after_run(result, mode)
            return result
        finally:
            self._job_lock.release()

    def _after_run(self, result: app_module.RunResult, mode: str) -> None:
        if result.status == STATUS_SUCCESS:
            self._notified_signature = ""
            self.notify("주간 자금계획 완료",
                        f"{result.message}")
            if mode == "manual" and self.cfg.get(
                    "options", "open_output_folder_after_manual_run",
                    default=True):
                self.open_output_folder()
        elif result.status == STATUS_WAITING_FILES:
            self.notify("필수자료 대기", result.message)
        elif result.status == "FAILED":
            self.notify("실행 실패", result.message)

    # ------------------------------------------------------------------
    # 미실행 보완 (4번 항목)
    # ------------------------------------------------------------------
    def check_missed_run(self, wait: bool = True) -> bool:
        if wait:
            wait_seconds = int(self.cfg.get("startup", "initial_wait_seconds",
                                            default=60))
            self.log.info("시작 후 %d초 대기 (OneDrive·네트워크 동기화 고려)",
                          wait_seconds)
            time.sleep(max(0, wait_seconds))
        if not self.cfg.get("missed_run", "enabled", default=True):
            return False
        if self.paused:
            return False
        now = now_local(self.cfg.timezone_name)
        schedule = self.cfg.get("schedule", default={}) or {}
        self.state.reload()
        if not self.state.should_run_missed_job(
                now, int(schedule.get("hour", 9)),
                int(schedule.get("minute", 10))):
            self.log.info("미실행 보완 불필요 (이번 주 상태: %s)",
                          self.state.state.get("last_run_status"))
            return False
        self.log.info("이번 주 정상 완료 기록이 없어 보완 실행을 시작합니다.")
        result = self.run_job(mode="missed")
        return result.status not in ("SKIPPED", "LOCKED")

    # ------------------------------------------------------------------
    # 주기 검사: 파일 대기 재시도 + 변경 감지 (18, 29번 항목)
    # ------------------------------------------------------------------
    def _periodic_check(self) -> None:
        if self.paused:
            return
        now = now_local(self.cfg.timezone_name)
        self.state.reload()
        status = self.state.state.get("last_run_status")
        week = iso_week_key(now.date())

        if status == STATUS_WAITING_FILES \
                and self.state.state.get("last_run_week") == week:
            validation = file_validator.validate_inputs(self.cfg)
            if not validation.missing_required:
                self.log.info("필수자료가 준비되어 재실행합니다.")
                self.run_job(mode="retry")
            else:
                if self._quiet_until is None or now >= self._quiet_until:
                    self.log.info("필수자료 대기 계속: %s", validation.summary())
                    if now > self._retry_end_time(now):
                        # 재시도 마감 이후에는 1시간에 한 번만 기록
                        self._quiet_until = now + timedelta(hours=1)
            return

        if status == STATUS_SUCCESS \
                and self.state.state.get("last_successful_week") == week \
                and self.cfg.get("input_change", "detect_after_success",
                                 default=True):
            signature = file_validator.current_input_signature(self.cfg)
            if self.state.input_changed_after_success(signature) \
                    and signature != self._notified_signature:
                self._notified_signature = signature
                self.log.info("SUCCESS 이후 입력자료 변경 감지 (서명 %s)",
                              signature)
                if self.cfg.get("input_change", "notify_user", default=True):
                    self.notify(
                        "입력자료 변경",
                        "이번 주 자금계획 생성 후 입력자료가 변경되었습니다. "
                        "트레이 메뉴의 '변경자료 반영'으로 다시 생성할 수 "
                        "있습니다.")

    def _retry_end_time(self, now: datetime) -> datetime:
        text = str(self.cfg.get("retry", "end_time", default="10:30"))
        try:
            hour, minute = (int(x) for x in text.split(":"))
        except ValueError:
            hour, minute = 10, 30
        monday = now.date() - timedelta(days=now.date().weekday())
        return datetime(monday.year, monday.month, monday.day, hour, minute)

    # ------------------------------------------------------------------
    # 트레이 메뉴에서 쓰는 기능
    # ------------------------------------------------------------------
    def run_now(self) -> None:
        threading.Thread(target=self.run_job,
                         kwargs={"mode": "manual", "force": False},
                         daemon=True).start()

    def apply_changes(self) -> None:
        """변경자료 반영: 완료된 주라도 강제로 다시 생성."""
        threading.Thread(target=self.run_job,
                         kwargs={"mode": "rerun", "force": True},
                         daemon=True).start()

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        self.log.info("자동실행 %s", "일시정지" if self.paused else "재개")
        return self.paused

    def next_run_text(self) -> str:
        if self.paused:
            return "일시정지됨"
        try:
            job = self.scheduler.get_job("weekly")
            if job and job.next_run_time:
                return job.next_run_time.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        return "-"

    def status_text(self) -> str:
        self.state.reload()
        s = self.state.state
        now = now_local(self.cfg.timezone_name)
        lines = [
            f"이번 주: {iso_week_key(now.date())}",
            f"마지막 실행: {s.get('last_run_at', '-') or '-'} "
            f"({s.get('last_run_status', 'NOT_RUN')})",
            f"마지막 성공: {s.get('last_successful_date', '-') or '-'} "
            f"{s.get('last_successful_time', '')}",
            f"최근 결과: {s.get('last_output_file', '-') or '-'}",
            f"다음 자동 실행: {self.next_run_text()}",
        ]
        if s.get("last_error"):
            lines.append(f"최근 오류: {s['last_error'][:80]}")
        lines.append(
            f"시작프로그램 등록: {'예' if self.startup_registered() else '아니오'}")
        return "\n".join(lines)

    @staticmethod
    def startup_registered() -> bool:
        """Windows 시작프로그램 바로가기 등록 여부 (34번 항목)."""
        import os
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return False
        from pathlib import Path
        lnk = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" \
            / "Programs" / "Startup" / "에이팜건강 자금계획 자동화.lnk"
        return lnk.exists()

    def missing_files_text(self) -> str:
        validation = file_validator.validate_inputs(self.cfg)
        if validation.ok:
            return "필수 입력파일이 모두 준비되었습니다."
        return validation.summary()

    def open_output_folder(self) -> None:
        _open_folder(self.cfg.folder("output"))

    def open_log_folder(self) -> None:
        _open_folder(self.cfg.folder("log"))


def _open_folder(path) -> None:
    import os
    import subprocess
    import sys
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass
