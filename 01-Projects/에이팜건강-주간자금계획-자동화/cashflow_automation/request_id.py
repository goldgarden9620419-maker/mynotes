# -*- coding: utf-8 -*-
"""요청ID 생성·검증과 변경/취소 반영 규칙 (11~12번 항목)."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from common import (
    CONFIRM_YES, PROGRESS_CANCELLED, PROGRESS_CHANGED, PROGRESS_NEW,
    PROGRESS_PAID, REFLECT_CANCELLED, REFLECT_DUPLICATE, REFLECT_OK,
    REFLECT_PAID, REFLECT_UNCONFIRMED, TEAM_NAME_BY_CODE, parse_date,
)

_ID_PATTERN = re.compile(r"^(?P<code>[^-]+)-(?P<date>\d{8})-(?P<serial>\d{3})$")


def make_request_id(team_code: str, reg_date: Any, serial: Any) -> str:
    """팀코드-최초등록일-일련번호 형식의 요청ID를 만든다.

    예: 경영-20260918-001
    """
    team_code = (team_code or "").strip()
    d = parse_date(reg_date)
    try:
        serial_no = int(serial)
    except (TypeError, ValueError):
        serial_no = 0
    if not team_code or d is None or serial_no <= 0:
        return ""
    return f"{team_code}-{d.strftime('%Y%m%d')}-{serial_no:03d}"


def parse_request_id(request_id: str) -> Optional[dict]:
    """요청ID를 분해한다. 형식이 틀리면 None."""
    m = _ID_PATTERN.match((request_id or "").strip())
    if not m:
        return None
    code = m.group("code")
    try:
        reg = date(int(m.group("date")[:4]), int(m.group("date")[4:6]),
                   int(m.group("date")[6:8]))
    except ValueError:
        return None
    return {
        "team_code": code,
        "team_name": TEAM_NAME_BY_CODE.get(code, ""),
        "reg_date": reg,
        "serial": int(m.group("serial")),
    }


def is_valid_request_id(request_id: str) -> bool:
    return parse_request_id(request_id) is not None


# ---------------------------------------------------------------------------
# 동일 요청ID 최신자료 선택 (12번 항목)
# ---------------------------------------------------------------------------

def select_latest(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """요청ID별로 최신 1건만 남긴다.

    선택 순서: 최종수정일 → 원본파일 수정일시(file_mtime) → 파일 내 순서.
    반환: (선택된 행 목록, 중복으로 제외된 행 목록).
    중복 행에는 반영상태='중복제외'를 표시한다. 이전 금액은 합산하지 않는다.
    """
    groups: dict[str, list[dict]] = {}
    no_id_rows: list[dict] = []
    for row in rows:
        rid = (row.get("요청ID") or "").strip()
        if rid:
            groups.setdefault(rid, []).append(row)
        else:
            no_id_rows.append(row)

    selected: list[dict] = []
    duplicates: list[dict] = []
    for rid, group in groups.items():
        if len(group) == 1:
            selected.append(group[0])
            continue

        def sort_key(row: dict):
            modified = parse_date(row.get("최종수정일")) or date.min
            mtime = row.get("file_mtime") or 0
            order = row.get("row_order", 0)
            return (modified, mtime, order)

        ordered = sorted(group, key=sort_key, reverse=True)
        winner = ordered[0]
        selected.append(winner)
        for loser in ordered[1:]:
            loser["반영상태"] = REFLECT_DUPLICATE
            loser["확인사항"] = f"요청ID 중복: 최신자료({winner.get('원본파일', '')} " \
                              f"{winner.get('최종수정일', '')})만 반영"
            duplicates.append(loser)
    selected.extend(no_id_rows)
    return selected, duplicates


def decide_reflect_status(row: dict) -> str:
    """확정여부·진행상태에 따른 반영상태를 정한다 (12번 항목).

    - 취소: 합계 제외, 기록 유지
    - 지급완료: 은행 대조 대상
    - 미확정: 합계 제외, 확인필요
    - 확정 + (신규|변경): 정상반영
    """
    progress = (row.get("진행상태") or "").strip()
    confirmed = (row.get("확정여부") or "").strip()
    if progress == PROGRESS_CANCELLED:
        return REFLECT_CANCELLED
    if progress == PROGRESS_PAID:
        return REFLECT_PAID
    if confirmed != CONFIRM_YES:
        return REFLECT_UNCONFIRMED
    if progress in (PROGRESS_NEW, PROGRESS_CHANGED):
        return REFLECT_OK
    # 진행상태가 비어있거나 알 수 없는 값
    return REFLECT_UNCONFIRMED


def is_countable(reflect_status: str) -> bool:
    """자금계획 합계에 반영되는 상태인지."""
    return reflect_status == REFLECT_OK
