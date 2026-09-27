# -*- coding: utf-8 -*-
"""은행 거래 중복 제거 (16번 항목).

중복 판정 기준: 은행 + 거래일 + 출금액 + 입금액 + 거래후잔액.
같은 기준키 안에서 모든 행이 거래일시를 갖고 있으면 거래일시도
키에 추가한다(같은 날 같은 금액의 서로 다른 거래 보호).
중복 행은 반영상태='중복제외', 현금유출입=0 처리하고 기록은 남긴다.
"""
from __future__ import annotations

from datetime import date, datetime

from common import BANK_REFLECT_DUPLICATE, BANK_REFLECT_OK


def _base_key(row: dict) -> tuple:
    return (
        row.get("은행"),
        row.get("거래일"),
        round(row.get("출금액") or 0, 2),
        round(row.get("입금액") or 0, 2),
        None if row.get("거래후잔액") is None else round(row["거래후잔액"], 2),
    )


def remove_duplicates(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(유효 행, 중복 행) 반환. 입력 행 자체에 상태를 표시한다."""
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault(_base_key(row), []).append(row)

    kept: list[dict] = []
    duplicates: list[dict] = []
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        # 모든 행에 거래일시가 있으면 거래일시까지 키에 포함
        if all(r.get("거래일시") is not None for r in group):
            subgroups: dict[datetime, list[dict]] = {}
            for r in group:
                subgroups.setdefault(r["거래일시"], []).append(r)
        else:
            subgroups = {datetime.min: group}
        for sub in subgroups.values():
            ordered = sorted(sub, key=lambda r: (r.get("원본파일") or "",
                                                 r.get("row_order", 0)))
            kept.append(ordered[0])
            for dup in ordered[1:]:
                dup["반영상태"] = BANK_REFLECT_DUPLICATE
                dup["현금유출입"] = 0.0
                duplicates.append(dup)
    kept.sort(key=lambda r: (r.get("거래일") or date.min,
                             r.get("거래일시") or datetime.min,
                             r.get("row_order", 0)))
    return kept, duplicates


def merge_with_history(new_rows: list[dict],
                       history_rows: list[dict]) -> list[dict]:
    """이력 파일과 이번 주 자료를 합쳐 고유 거래만 남긴다.

    같은 거래가 양쪽에 있으면 이번 주 자료(분류가 최신)를 우선한다.
    """
    merged: dict[tuple, dict] = {}
    for row in history_rows:
        key = _base_key(row) + (row.get("거래일시"),)
        merged[key] = row
    for row in new_rows:
        if row.get("반영상태") != BANK_REFLECT_OK:
            continue
        key = _base_key(row) + (row.get("거래일시"),)
        merged[key] = row
    result = list(merged.values())
    result.sort(key=lambda r: (r.get("거래일") or date.min,
                               r.get("거래일시") or datetime.min))
    return result
