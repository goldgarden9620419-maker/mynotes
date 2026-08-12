# -*- coding: utf-8 -*-
"""첫 3초 Hook 후보 선정 및 점수 평가.

실제 영상 발화 중에서 스크롤을 멈출 가능성이 높은 구간을 찾는다.
제품에 존재하지 않는 기능/효과를 새로 만들어내지 않는다 —
후보는 반드시 원본 발화에서만 고른다.
"""
import re

from utils import config

_CURIOSITY = ["모르셨", "아직도", "혹시", "왜 이제", "이게 뭐", "충격", "비밀",
              "진짜", "솔직히", "대박", "?"]
_PROBLEM = ["불편", "귀찮", "힘들", "고민", "번거", "짜증", "문제", "스트레스"]
_BENEFIT = ["편해", "간편", "좋아", "해결", "절약", "가성비", "만족", "빨라",
            "쉬워", "깔끔"]
_VISUAL = ["보세요", "이렇게", "여기", "봐봐", "보이시", "짠", "등장"]
_PROOF = ["써보니", "직접", "한 달", "일주일", "후기", "리뷰", "실제로"]


def _keyword_score(text: str, keywords: list, per_hit: float = 18.0) -> float:
    score = 0.0
    for kw in keywords:
        if kw in text:
            score += per_hit
    return min(score, 100.0)


def _tokenize(text: str) -> set:
    return {t for t in re.findall(r"[가-힣A-Za-z0-9]+", text or "") if len(t) >= 2}


def score_candidates(segments: list, product: dict, style: str) -> list:
    """Hook 후보 리스트 반환 (총점 내림차순, 최소 3개 목표).

    각 후보: {"segment": seg, "scores": {...}, "total": float, "label": str}
    """
    weights = config.STYLE_HOOK_WEIGHTS.get(style, {})
    p_tokens = set()
    for key in ("name", "category", "features", "selling_points"):
        p_tokens |= _tokenize(product.get(key, ""))

    candidates = []
    usable = [s for s in segments
              if s.get("role") not in ("NG", "UNNECESSARY") and len(s["text"]) >= 5]
    for seg in usable:
        text = seg["text"]
        dur = seg["end"] - seg["start"]

        curiosity = _keyword_score(text, _CURIOSITY)
        if text.rstrip().endswith("?"):
            curiosity = min(curiosity + 25, 100)
        problem = _keyword_score(text, _PROBLEM, 22.0)
        benefit = _keyword_score(text, _BENEFIT, 20.0)
        visual = _keyword_score(text, _VISUAL, 22.0)
        proof = _keyword_score(text, _PROOF, 22.0)

        # Retention: 1.2~4초 길이의 또렷한 한 문장이 이상적
        if 1.2 <= dur <= 4.0:
            retention = 90.0
        elif dur < 1.2:
            retention = 55.0
        else:
            retention = max(90.0 - (dur - 4.0) * 15.0, 20.0)

        overlap = len(_tokenize(text) & p_tokens)
        relevance = min(40.0 + overlap * 20.0, 100.0)

        scores = {
            "Curiosity Score": curiosity,
            "Problem Score": problem,
            "Benefit Score": benefit,
            "Visual Impact Score": visual,
            "Retention Score": retention,
            "Product Relevance Score": relevance,
        }
        weighted = {
            "curiosity": curiosity * weights.get("curiosity", 1.0),
            "problem": problem * weights.get("problem", 1.0),
            "benefit": benefit * weights.get("benefit", 1.0),
            "visual": visual * weights.get("visual", 1.0),
            "retention": retention * weights.get("retention", 1.0),
            "relevance": relevance,
            "proof": proof * weights.get("proof", 1.0),
        }
        total = round(min(sum(weighted.values()) / len(weighted), 100.0), 1)

        if problem >= max(curiosity, benefit):
            label = "문제 제기형"
        elif curiosity >= benefit:
            label = "호기심형"
        else:
            label = "혜택 강조형"

        candidates.append({
            "segment": seg,
            "scores": {k: round(v, 1) for k, v in scores.items()},
            "total": total,
            "label": label,
            "text": text,
        })

    candidates.sort(key=lambda c: -c["total"])

    # A/B 테스트를 위해 유형이 다른 후보를 우선 배치 (최소 3개 목표)
    diverse, seen_labels = [], set()
    for cand in candidates:
        if cand["label"] not in seen_labels:
            diverse.append(cand)
            seen_labels.add(cand["label"])
    for cand in candidates:
        if cand not in diverse:
            diverse.append(cand)

    return diverse[: max(3, min(len(diverse), 6))]
