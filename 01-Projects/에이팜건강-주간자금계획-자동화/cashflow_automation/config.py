# -*- coding: utf-8 -*-
"""config.yaml 로드와 폴더 구조 관리."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from common import BANKS, TEAMS

PROGRAM_DIR_NAME = "00_프로그램"

DEFAULT_CONFIG: dict = {
    "company_name": "(주)에이팜건강",
    "timezone": "Asia/Seoul",
    "schedule": {"day_of_week": "mon", "hour": 9, "minute": 10},
    "startup": {
        "auto_start_with_windows": True,
        "initial_wait_seconds": 60,
        "check_missed_run": True,
        "run_missed_job_immediately": True,
    },
    "missed_run": {
        "enabled": True,
        "run_on_any_day_after_monday": True,
        "require_success_status": True,
        "prioritize_current_week": True,
    },
    "retry": {
        "enabled": True,
        "interval_minutes": 10,
        "end_time": "10:30",
        "continue_after_program_restart": True,
    },
    "input_change": {
        "detect_after_success": True,
        "auto_rerun": False,
        "notify_user": True,
    },
    "folders": {
        "general_teams": "./01_일반팀_지출계획",
        "confidential_admin": "./02_경영지원_대외비",
        "bank_root": "./03_은행거래내역",
        "base_workbook": "./04_기준파일",
        "output": "./05_결과",
        "review": "./06_확인필요",
        "log": "./07_실행로그",
        "backup": "./08_백업",
        "archive": "./99_지난자료",
    },
    "forecast": {
        "default_receipt_rate": 0.8,
        "receipt_rates": [0.6, 0.7, 0.8, 0.9, 1.0],
        "minimum_cash_balance": 0,
        "online_history_weeks": 12,
        # 2026-09-18 사용자 결정: 승인대기·미확정도 지급일자 기준 반영
        "include_unconfirmed": True,
        # 자동추정 목록을 새로 만들 때의 일괄 설정 초기값
        # (개별 관리 / 전체 반영 / 전체 제외)
        "auto_draft_default": "개별 관리",
    },
    "matching": {
        "date_window_days": 3,
        "name_similarity_threshold": 70,
        "partial_payment_tolerance": 0.05,
    },
    "bank": {
        "recent_days": 14,
        "month_end_top_day": 25,  # 이 날짜 이후 TOP출금은 월말 급여로 본다
        "internal_account_keywords": ["에이팜건강", "(주)에이팜건강"],
        "classify_rules_file": "classify_rules.json",
    },
    "recurring": {
        "lookback_months": 6,
        "min_months": 4,
    },
    "options": {
        "create_excel": False,
        "create_management_report": True,
        # True면 2단계 실행: 확인필요 검토('확인 완료'=예) 후에만 결과 생성
        "confirm_before_results": False,
        # '지금 실행' 창이 확인 완료 저장을 기다리는 최대 시간(분, 0=대기 안 함)
        "confirm_wait_minutes": 30,
        # 대외비 가림: False면 결과물에 대외비 상세(거래처·내용·신청자)를
        # 그대로 표시 (결과물을 대표이사·관리자만 볼 때)
        "mask_confidential": True,
        # 99_지난자료 보관 일수 — 지나면 자동 삭제 (0이면 정리 안 함)
        "archive_retention_days": 14,
        "create_pdf_summary": True,
        "create_live_workbook": True,
        "live_template_name": "자금계획_라이브템플릿.xlsx",
        # 결과 폴더에는 최신 실행분만 유지 (이전 버전은 99_지난자료/지난결과)
        "keep_only_latest_outputs": True,
        # 은행 폴더도 계좌별 최신 파일만 유지 (이전 파일은 99_지난자료)
        "keep_only_latest_bank_files": True,
        "backup_input_files": True,
        "open_output_folder_after_manual_run": True,
    },
    "base_workbook_name": "에이팜건강_자금계획_기준파일.xlsx",
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def program_dir() -> Path:
    """실행파일(또는 소스) 기준 프로그램 폴더."""
    if getattr(sys, "frozen", False):  # PyInstaller EXE
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class Config:
    """설정 접근 헬퍼. 폴더는 base_dir 기준 상대경로를 허용한다."""

    def __init__(self, data: dict, base_dir: Path, config_path: Optional[Path]):
        self.data = data
        self.base_dir = Path(base_dir)
        self.config_path = config_path

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, config_path: Optional[Path] = None,
             base_dir: Optional[Path] = None) -> "Config":
        """config.yaml을 읽는다. 없으면 기본값으로 생성한다."""
        pdir = program_dir()
        if config_path is None:
            config_path = pdir / "config.yaml"
        config_path = Path(config_path)

        user_data: dict = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                user_data = yaml.safe_load(f) or {}
        data = _deep_merge(DEFAULT_CONFIG, user_data)

        if base_dir is None:
            cfg_dir = config_path.resolve().parent
            # 00_프로그램 안에 설치된 경우 상위가 자금계획_자동화 루트
            base_dir = cfg_dir.parent if cfg_dir.name == PROGRAM_DIR_NAME else cfg_dir
        cfg = cls(data, Path(base_dir), config_path)

        if not config_path.exists():
            cfg.save()
        return cfg

    def save(self) -> None:
        if self.config_path is None:
            return
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, allow_unicode=True, sort_keys=False)

    # ------------------------------------------------------------------
    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def folder(self, name: str) -> Path:
        rel = self.get("folders", name,
                       default=DEFAULT_CONFIG["folders"].get(name, f"./{name}"))
        path = Path(rel)
        if not path.is_absolute():
            path = self.base_dir / rel
        return path.resolve()

    @property
    def state_dir(self) -> Path:
        """state.json, lock 파일 위치 (00_프로그램)."""
        d = self.base_dir / PROGRAM_DIR_NAME
        return d

    def ensure_folders(self) -> None:
        """최초 실행 시 전체 폴더 구조를 만든다."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for name in DEFAULT_CONFIG["folders"]:
            self.folder(name).mkdir(parents=True, exist_ok=True)
        for bank in BANKS:
            (self.folder("bank_root") / bank).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def team_file_path(self, team: dict) -> Path:
        if team.get("confidential"):
            return self.folder("confidential_admin") / team["file"]
        return self.folder("general_teams") / team["file"]

    def team_files(self) -> list[tuple[dict, Path]]:
        return [(team, self.team_file_path(team)) for team in TEAMS]

    def bank_dir(self, bank: str) -> Path:
        return self.folder("bank_root") / bank

    def base_workbook_path(self) -> Path:
        return self.folder("base_workbook") / self.get(
            "base_workbook_name", default="에이팜건강_자금계획_기준파일.xlsx")

    @property
    def timezone_name(self) -> str:
        return self.get("timezone", default="Asia/Seoul")
