# -*- coding: utf-8 -*-
"""광고 구조 재구성 — Edit Decision List(EDL) 생성.

원본 촬영 순서보다 광고 전환 가능성이 높은 구조를 우선한다:
HOOK → 문제/공감 → 제품 등장 → 특징/시연 → 장점/증거 → 혜택 → CTA

좋은 장면이 원본 뒤쪽에 있어도 앞으로 이동시킨다.
플랫폼별로 목표 길이·컷 패딩·최대 컷 길이가 다르다.
"""
import itertools

from utils import config


def _cut_at_word_boundary(seg: dict, max_len: float) -> float:
    """세그먼트를 max_len 이하로 자를 때 단어 경계에서 끝점을 찾는다."""
    start = seg["start"]
    limit = start + max_len
    if seg["end"] <= limit:
        return seg["end"]
    best = None
    for w in seg.get("words", []):
        if w["end"] <= limit:
            best = w["end"]
        else:
            break
    return best if best and best > start + 0.6 else limit


def build_edl(segments: list, hook_seg: dict, platform_cfg: dict,
              style: str = "UGC 후기형", options: dict = None) -> dict:
    """EDL 생성.

    반환: {"clips": [...], "timeline": [...], "total_duration": float,
           "log": [...]}
    각 clip: {src_start, src_end, out_start, out_end, role, text, words, zoom}
    """
    options = options or {}
    log = []
    tempo = config.STYLE_TEMPO.get(style, 1.0)
    target = float(options.get("target_duration") or platform_cfg["target_duration"])
    pad = platform_cfg["clip_pad"]
    max_len = platform_cfg["max_clip_len"] * tempo
    hook_max = platform_cfg["hook_max_len"]
    cut_speed = options.get("cut_speed", "보통")  # 느리게/보통/빠르게
    if cut_speed == "빠르게":
        max_len *= 0.75
        pad *= 0.6
    elif cut_speed == "느리게":
        max_len *= 1.25
        pad *= 1.4

    chosen = []          # (seg, role)
    used_ids = set()

    def push(seg, role):
        if seg is None or id(seg) in used_ids:
            return False
        used_ids.add(id(seg))
        chosen.append((seg, role))
        return True

    # 1) Hook은 항상 맨 앞
    if hook_seg is not None:
        push(hook_seg, "HOOK")
        log.append(f'HOOK 선정: "{hook_seg["text"]}" '
                   f'({hook_seg["start"]:.1f}s — 원본 위치와 무관하게 맨 앞 배치)')

    # 2) 역할별 후보 정리
    by_role = {}
    for seg in segments:
        if id(seg) in used_ids:
            continue
        role = seg.get("role", "PRODUCT")
        if role in ("NG", "UNNECESSARY"):
            continue
        by_role.setdefault(role, []).append(seg)
    for role in by_role:
        by_role[role].sort(key=lambda s: -s.get("ad_score", 0))

    cta_seg = by_role.get("CTA", [None])[0] if by_role.get("CTA") else None

    def clip_dur(seg, limit):
        end = _cut_at_word_boundary(seg, limit)
        return min(end, seg["end"]) - seg["start"] + pad * 2

    budget = target
    budget -= clip_dur(hook_seg, hook_max) if hook_seg else 0.0
    if cta_seg:
        budget -= clip_dur(cta_seg, max_len)

    # 3) 광고 구조 순서대로 채운다
    for role in config.AD_STRUCTURE:
        limit_n = config.ROLE_CLIP_LIMITS.get(role, 1)
        for seg in by_role.get(role, [])[:limit_n]:
            d = clip_dur(seg, max_len)
            if d > budget:
                continue
            if push(seg, role):
                budget -= d

    # 4) 너무 짧으면 남은 좋은 컷으로 보강
    current = target - budget
    if current < platform_cfg["min_duration"]:
        leftovers = sorted(
            (s for role, lst in by_role.items() if role != "CTA" for s in lst
             if id(s) not in used_ids),
            key=lambda s: -s.get("ad_score", 0))
        for seg in leftovers:
            d = clip_dur(seg, max_len)
            if budget < d:
                break
            if push(seg, seg.get("role", "PRODUCT")):
                budget -= d

    # 5) CTA는 항상 마지막
    if cta_seg:
        push(cta_seg, "CTA")
        log.append(f'CTA 선정: "{cta_seg["text"]}"')
    else:
        log.append("발화 중 CTA 없음 → 엔드카드 CTA로 마무리")

    # 6) 같은 역할 그룹 내에서는 원본 시간순 유지 (점프컷 어색함 감소)
    order_key = {"HOOK": 0, **{r: i + 1 for i, r in enumerate(config.AD_STRUCTURE)},
                 "CTA": 99}
    chosen.sort(key=lambda pair: (order_key.get(pair[1], 50), pair[0]["start"]))

    # 7) 클립 생성 + 출력 타임라인 계산 + 자동 Zoom
    clips = []
    out_t = 0.0
    zoom_cycle = itertools.cycle([1.05, 1.10])
    for seg, role in chosen:
        limit = hook_max if role == "HOOK" else max_len
        src_start = max(seg["start"] - pad, 0.0)
        src_end = _cut_at_word_boundary(seg, limit) + pad
        src_end = max(src_end, src_start + 0.5)
        dur = src_end - src_start

        zoom = 1.0
        if dur >= platform_cfg["zoom_threshold"]:
            zoom = next(zoom_cycle)  # 100% → 105% → 110% 미세 punch-in

        words = [w for w in seg.get("words", [])
                 if src_start <= w["start"] and w["end"] <= src_end + 0.05]
        clips.append({
            "src_start": round(src_start, 3),
            "src_end": round(src_end, 3),
            "out_start": round(out_t, 3),
            "out_end": round(out_t + dur, 3),
            "role": role,
            "text": seg["text"],
            "words": words,
            "zoom": zoom,
        })
        out_t += dur

    timeline = [
        f'{int(c["out_start"] // 60)}:{c["out_start"] % 60:04.1f} '
        f'{c["role"]} — {c["text"][:30]}'
        for c in clips
    ]
    log.append(f"총 {len(clips)}컷, 본편 {out_t:.1f}초 "
               f'({platform_cfg["label"]}, 스타일: {style}, 컷 속도: {cut_speed})')

    return {
        "clips": clips,
        "timeline": timeline,
        "total_duration": round(out_t, 2),
        "log": log,
    }
