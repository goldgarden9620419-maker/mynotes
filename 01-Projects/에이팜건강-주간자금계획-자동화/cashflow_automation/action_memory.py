# -*- coding: utf-8 -*-
"""확인필요·주간대조 '처리' 선택 기억 (2026-11-23 사용자 요청).

"처리는 내가 한다 — 반복해서 나타나는 항목이면 지난 선택을 자동으로
채워두고, 나는 확인('예' 저장)만 한다."

확인필요·주간대조 파일에 사용자가 고른 처리 값을 항목별로 기억해
두었다가(action_memory.json, 00_프로그램), 다음 파일을 만들 때 같은
항목의 처리 칸에 미리 채운다. 미리 채운 칸은 연두색으로 표시되고,
사용자는 그대로 두거나 ▼로 바꾼 뒤 '예' 저장으로 확인한다.

키는 "구분|느슨한 텍스트"(숫자·공백 제거) — 금액·날짜·청구번호가
달라져도 같은 항목으로 본다.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from common import normalize_text

_MAX_ENTRIES = 300          # 오래 안 쓴 항목부터 정리
PREFILL_FILL = "E2EFDA"     # 연두 — 자동 입력(지난 선택) 표시


def _loose(text) -> str:
    # 숫자·공백에 더해 금액 표기에 섞이는 구두점도 지운다 ("1,234원")
    return re.sub(r"[\d\s,.\-:()/]+", "", normalize_text(text))


def make_key(kind, text) -> str:
    """기억 키: 구분 + 느슨한 텍스트(앞 60자)."""
    return f"{normalize_text(kind)}|{_loose(text)[:60]}"


def load(path: Path | None) -> dict:
    """기억 파일을 읽는다. {키: {"처리": ..., "갱신": ...}}"""
    if path is None:
        return {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        items = raw.get("항목") or {}
        return {k: v for k, v in items.items()
                if isinstance(v, dict) and v.get("처리")}
    except Exception:
        return {}


def save(path: Path, memory: dict) -> None:
    if len(memory) > _MAX_ENTRIES:
        keep = sorted(memory.items(),
                      key=lambda kv: kv[1].get("갱신") or "",
                      reverse=True)[:_MAX_ENTRIES]
        memory = dict(keep)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"항목": memory}, ensure_ascii=False,
                               indent=1),
                    encoding="utf-8")


def remember(memory: dict, entries, today: date | None = None) -> int:
    """(구분, 텍스트, 처리) 목록을 기억에 합친다. 바뀐 수를 돌려준다."""
    stamp = (today or date.today()).isoformat()
    changed = 0
    for kind, text, action in entries or []:
        action = str(action or "").strip()
        key = make_key(kind, text)
        if not action or len(key.split("|", 1)[1]) < 2:
            continue      # 텍스트가 거의 없는 키는 보류 (키는 정확 일치라
                          # 짧아도 과잉 일치는 없지만, 빈 이름은 의미 없음)
        if memory.get(key, {}).get("처리") != action:
            changed += 1
        memory[key] = {"처리": action, "갱신": stamp}
    return changed


def lookup(memory: dict, kind, text) -> str:
    """기억된 처리 값(없으면 빈 문자열)."""
    entry = memory.get(make_key(kind, text))
    return (entry or {}).get("처리", "")
