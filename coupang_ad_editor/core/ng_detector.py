# -*- coding: utf-8 -*-
"""NG / 침묵 / 버벅임 / 반복 발화 자동 탐지.

원칙: 자연스러운 말투까지 지나치게 삭제하지 않는다.
- 명백한 NG 신호("다시 할게요", "잠깐", "NG", "컷" 등)
- 간투사만 있는 의미 없는 구간
- 같은 문장을 여러 번 말한 재촬영 구간(뒤쪽 테이크 유지)
- 말하다 다시 시작한 구간(뒤 구간이 앞 구간을 포함하면 앞 구간 제거)
- 긴 침묵(컷 편집 시 자동 배제되지만 로그로 기록)
"""
import difflib
import re

# 명백한 NG 신호 (문장 전체 맥락에서 촬영 지시어로 쓰이는 표현)
NG_PATTERNS = [
    r"다시\s*(할게|갈게|찍|해\s*볼게|한번)",
    r"잠깐만", r"잠시만", r"엔지", r"\bNG\b", r"엔쥐",
    r"컷\s*이요", r"^컷$", r"틀렸(다|네|어)", r"아\s*틀렸",
    r"처음부터", r"다시요", r"큐\s*사인", r"카메라\s*(켜|꺼)",
    r"녹화\s*(시작|중지)", r"준비\s*됐", r"시작할게요?$",
]

# 간투사 / 의미 없는 토큰
FILLERS = ["음", "어", "아", "그", "저", "뭐지", "뭐더라", "이제", "막",
           "그니까", "그러니까", "어어", "음음", "아아"]

_SIMILARITY_THRESHOLD = 0.78
_LONG_SILENCE = 1.2  # 초


def _normalize(text: str) -> str:
    text = re.sub(r"[^\w가-힣]+", "", text)
    return text.lower()


def _strip_fillers(text: str) -> str:
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", text)
    remain = [t for t in tokens if t not in FILLERS]
    return "".join(remain)


def _is_ng_signal(text: str) -> bool:
    for pat in NG_PATTERNS:
        if re.search(pat, text.strip()):
            return True
    return False


def detect(segments: list) -> dict:
    """세그먼트에 NG 판정을 붙인다.

    각 세그먼트에 추가되는 키:
      - "ng": bool
      - "ng_reason": str (판정 사유)
    반환: {"kept": [...], "removed": [...], "silences": [...], "log": [...]}
    """
    log = []
    silences = []

    for i, seg in enumerate(segments):
        seg.setdefault("ng", False)
        seg.setdefault("ng_reason", "")
        seg["index"] = i

    # 1) 명백한 NG 신호
    for seg in segments:
        if _is_ng_signal(seg["text"]):
            seg["ng"] = True
            seg["ng_reason"] = "촬영 NG 신호 감지"

    # 2) 간투사만 있는 구간
    for seg in segments:
        if seg["ng"]:
            continue
        core = _strip_fillers(seg["text"])
        if len(core) < 2:
            seg["ng"] = True
            seg["ng_reason"] = "간투사/의미 없는 발화"

    # 3) 반복 촬영(유사 문장) — 뒤쪽 테이크를 유지
    normalized = [_normalize(s["text"]) for s in segments]
    for i in range(len(segments)):
        if segments[i]["ng"] or len(normalized[i]) < 4:
            continue
        for j in range(i + 1, min(i + 6, len(segments))):  # 근접 구간만 비교
            if segments[j]["ng"] or len(normalized[j]) < 4:
                continue
            ratio = difflib.SequenceMatcher(
                None, normalized[i], normalized[j]).ratio()
            if ratio >= _SIMILARITY_THRESHOLD:
                segments[i]["ng"] = True
                segments[i]["ng_reason"] = f"반복 촬영 추정(뒤 테이크 사용, 유사도 {ratio:.2f})"
                break

    # 4) 말하다 다시 시작 — 앞 구간이 뒤 구간의 접두 부분이면 앞 구간 제거
    for i in range(len(segments) - 1):
        a, b = segments[i], segments[i + 1]
        if a["ng"] or b["ng"]:
            continue
        na, nb = _normalize(a["text"]), _normalize(b["text"])
        if 3 <= len(na) < len(nb) and nb.startswith(na[: max(3, int(len(na) * 0.8))]):
            a["ng"] = True
            a["ng_reason"] = "말 끊고 다시 시작한 구간"

    # 5) 긴 침묵 기록 (편집 시 kept 구간만 잘라 붙이므로 자동 제거됨)
    prev_end = 0.0
    for seg in segments:
        gap = seg["start"] - prev_end
        if gap >= _LONG_SILENCE:
            silences.append({"start": round(prev_end, 2),
                            "end": round(seg["start"], 2),
                            "duration": round(gap, 2)})
        prev_end = max(prev_end, seg["end"])

    kept = [s for s in segments if not s["ng"]]
    removed = [s for s in segments if s["ng"]]

    for seg in removed:
        log.append(
            f'[제거] {seg["start"]:.2f}~{seg["end"]:.2f} "{seg["text"]}" — {seg["ng_reason"]}'
        )
    for sil in silences:
        log.append(
            f'[침묵] {sil["start"]:.2f}~{sil["end"]:.2f} ({sil["duration"]:.1f}초) — 컷 편집으로 자동 제거'
        )
    log.append(f"발화 {len(segments)}개 중 {len(kept)}개 유지, {len(removed)}개 제거")

    return {"kept": kept, "removed": removed, "silences": silences, "log": log}
