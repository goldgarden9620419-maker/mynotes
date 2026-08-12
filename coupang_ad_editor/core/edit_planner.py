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
    """세그먼트를 max_len 이하로 자를 때 단어 경계에서 끝점을 찾는다.

    문장이 max_len을 약간(35% 이내) 초과하는 정도라면 자르지 않고
    문장 전체를 유지한다 — 말이 중간에 뚝 끊기는 것을 방지.
    """
    start = seg["start"]
    dur = seg["end"] - start
    if dur <= max_len * 1.35:
        return seg["end"]
    limit = start + max_len
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

    # Hook도 문장을 중간에 끊지 않는다 — hook_max는 '이보다 짧은 후보 선호'의
    # 의미로만 남기고, 실제 컷은 문장 단위로 유지한다.
    budget = target
    budget -= clip_dur(hook_seg, max_len) if hook_seg else 0.0
    if cta_seg:
        budget -= clip_dur(cta_seg, max_len)

    # 3) 원본 발화 총량이 목표 길이 이내라면 전부 사용한다
    #    (짧은 원본인데 일부만 골라 뚝뚝 끊기는 것 방지)
    all_usable = [s for lst in by_role.values() for s in lst]
    total_usable = sum(clip_dur(s, max_len) for s in all_usable)
    use_everything = total_usable <= budget * 1.05
    if use_everything:
        for seg in sorted(all_usable, key=lambda s: s["start"]):
            if push(seg, seg.get("role", "PRODUCT")):
                budget -= clip_dur(seg, max_len)
    else:
        # 4) 원본이 길면 광고 구조 순서대로 골라 담는다
        for role in config.AD_STRUCTURE:
            limit_n = config.ROLE_CLIP_LIMITS.get(role, 1)
            for seg in by_role.get(role, [])[:limit_n]:
                d = clip_dur(seg, max_len)
                if d > budget:
                    continue
                if push(seg, role):
                    budget -= d

        # 5) 예산이 남으면 역할과 무관하게 좋은 컷으로 마저 채운다
        leftovers = sorted(
            (s for s in all_usable
             if id(s) not in used_ids and s is not cta_seg),
            key=lambda s: -s.get("ad_score", 0))
        for seg in leftovers:
            d = clip_dur(seg, max_len)
            if d > budget:
                continue
            if push(seg, seg.get("role", "PRODUCT")):
                budget -= d

    # 5) CTA는 항상 마지막
    if cta_seg:
        push(cta_seg, "CTA")
        log.append(f'CTA 선정: "{cta_seg["text"]}"')
    else:
        log.append("발화 중 CTA 없음 → 엔드카드 CTA로 마무리")

    # 6) 배치 순서 결정
    if use_everything:
        # 짧은 원본은 이야기 흐름 유지: 선택된 Hook만 맨 앞, 나머지는 촬영 순서
        chosen.sort(key=lambda pair: (0 if pair[0] is hook_seg else 1,
                                      pair[0]["start"]))
    else:
        # 긴 원본은 광고 구조 순서 우선, 같은 역할끼리는 원본 시간순
        order_key = {"HOOK": 0,
                     **{r: i + 1 for i, r in enumerate(config.AD_STRUCTURE)},
                     "CTA": 99}
        chosen.sort(key=lambda pair: (order_key.get(pair[1], 50),
                                      pair[0]["start"]))

    # 7) 클립 생성 + 자동 Zoom
    clips = []
    zoom_cycle = itertools.cycle([1.05, 1.10])
    for seg, role in chosen:
        limit = max_len
        src_start = max(seg["start"] - pad, 0.0)
        src_end = _cut_at_word_boundary(seg, limit) + pad
        src_end = max(src_end, src_start + 0.5)

        zoom = 1.0
        if src_end - src_start >= platform_cfg["zoom_threshold"]:
            zoom = next(zoom_cycle)  # 100% → 105% → 110% 미세 punch-in

        words = [w for w in seg.get("words", [])
                 if src_start <= w["start"] and w["end"] <= src_end + 0.05]
        clips.append({
            "src_start": round(src_start, 3),
            "src_end": round(src_end, 3),
            "role": role,
            "text": seg["text"],
            "words": words,
            "zoom": zoom,
        })

    # 8) 소스 구간 겹침 제거 — 패딩/인식 구간 겹침으로 같은 대사가
    #    두 번 재생되는 문제 방지 (겹치면 중간 지점에서 나눠 가진다)
    by_src = sorted(clips, key=lambda c: (c["src_start"], c["src_end"]))
    for a, b in zip(by_src, by_src[1:]):
        if a["src_end"] > b["src_start"]:
            cut = round((a["src_end"] + b["src_start"]) / 2, 3)
            a["src_end"] = cut
            b["src_start"] = cut

    # 너무 짧아진 클립 제거 후 출력 타임라인 재계산
    clips = [c for c in clips if c["src_end"] - c["src_start"] >= 0.3]
    out_t = 0.0
    for c in clips:
        dur = c["src_end"] - c["src_start"]
        c["out_start"] = round(out_t, 3)
        c["out_end"] = round(out_t + dur, 3)
        c["words"] = [w for w in c["words"]
                      if c["src_start"] <= w["start"] and
                      w["end"] <= c["src_end"] + 0.05]
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
