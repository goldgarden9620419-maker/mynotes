# -*- coding: utf-8 -*-
"""광고 관점 대본 분석.

각 발화 구간을 HOOK / PROBLEM / EMPATHY / PRODUCT / BENEFIT / FEATURE /
PROOF / DEMO / OFFER / CTA / UNNECESSARY 로 분류하고,
제품 핵심 소구점(최대 3개)을 선정한다.

원칙: 영상/입력 정보에서 실제 확인할 수 없는 내용은 만들어내지 않는다.
"""
import re

# 역할별 한국어 키워드 뱅크
ROLE_KEYWORDS = {
    "HOOK": ["모르셨", "아직도", "진짜", "대박", "이거 왜", "충격", "솔직히",
             "여러분", "혹시", "?"],
    "PROBLEM": ["불편", "귀찮", "힘들", "고민", "번거", "스트레스", "문제",
                "짜증", "어려웠", "걱정", "지저분", "복잡"],
    "EMPATHY": ["저도", "다들", "공감", "그쵸", "그렇죠", "누구나", "마찬가지",
                "저만 그런"],
    "PRODUCT": ["제품", "소개", "이게 바로", "바로 이", "출시", "구매했",
                "샀는데", "주문", "언박싱", "받았", "도착"],
    "BENEFIT": ["편해", "편리", "좋아", "만족", "간편", "덕분에", "해결",
                "시간이 줄", "절약", "쉬워", "빨라", "깔끔", "가성비"],
    "FEATURE": ["기능", "재질", "소재", "크기", "사이즈", "무게", "용량",
                "구성", "디자인", "색상", "충전", "배터리", "방수", "설치"],
    "PROOF": ["리뷰", "후기", "평점", "써보니", "사용해보니", "한 달", "일주일",
              "직접", "실제로", "비교해"],
    "DEMO": ["이렇게", "보시면", "눌러", "돌려", "닦아", "발라", "켜면",
             "사용법", "넣고", "빼고", "조립", "작동"],
    "OFFER": ["가격", "할인", "쿠폰", "원", "만원", "천원", "세일", "특가",
              "로켓배송", "무료배송", "혜택"],
    "CTA": ["링크", "프로필", "확인해", "구매는", "쿠팡에서", "지금 바로",
            "댓글", "저장", "팔로우", "클릭", "보러 가", "설명란"],
}

_ROLE_PRIORITY = ["CTA", "OFFER", "PROOF", "DEMO", "FEATURE", "BENEFIT",
                  "PROBLEM", "EMPATHY", "PRODUCT", "HOOK"]


def _tokenize(text: str) -> list:
    return [t for t in re.findall(r"[가-힣A-Za-z0-9]+", text or "") if len(t) >= 2]


def _product_tokens(product: dict) -> set:
    tokens = set()
    for key in ("name", "category", "features", "selling_points"):
        tokens.update(_tokenize(product.get(key, "")))
    return tokens


def classify(segments: list, product: dict) -> list:
    """kept 세그먼트에 role / role_scores / ad_score 를 부여한다."""
    total = len(segments) or 1
    p_tokens = _product_tokens(product)
    product_name_tokens = set(_tokenize(product.get("name", "")))

    for idx, seg in enumerate(segments):
        text = seg["text"]
        scores = {}
        for role, keywords in ROLE_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text:
                    score += 2.0
            scores[role] = score

        # 제품 정보 토큰과 겹치면 PRODUCT/FEATURE/BENEFIT 가중
        overlap = len(set(_tokenize(text)) & p_tokens)
        if overlap:
            scores["FEATURE"] += overlap * 1.2
            scores["BENEFIT"] += overlap * 0.8
        if product_name_tokens & set(_tokenize(text)):
            scores["PRODUCT"] += 3.0

        # 위치 사전확률: 초반 → HOOK/PROBLEM, 후반 → OFFER/CTA
        pos = idx / total
        if pos < 0.2:
            scores["HOOK"] += 1.5
            scores["PROBLEM"] += 0.5
        elif pos > 0.85:
            scores["CTA"] += 1.5
            scores["OFFER"] += 0.5

        # 가격 숫자 패턴 → OFFER
        if re.search(r"\d[\d,]*\s*원|만\s*원|퍼센트|%\s*할인", text):
            scores["OFFER"] += 3.0

        best_role, best_score = "UNNECESSARY", 0.0
        for role in _ROLE_PRIORITY:
            if scores.get(role, 0) > best_score:
                best_role, best_score = role, scores[role]

        if best_score < 2.0:
            # 뚜렷한 신호가 없으면 위치 기반 기본값 (버리지 않고 살려둔다)
            if pos < 0.25:
                best_role = "HOOK"
            elif pos > 0.85:
                best_role = "CTA"
            else:
                best_role = "PRODUCT" if overlap else "DEMO"
            best_score = 1.0

        seg["role"] = best_role
        seg["role_scores"] = {k: round(v, 2) for k, v in scores.items() if v > 0}
        # 컷 선별용 종합 점수: 역할 확신도 + 발화 밀도
        dur = max(seg["end"] - seg["start"], 0.3)
        density = min(len(text) / dur / 6.0, 1.5)
        seg["ad_score"] = round(best_score + density * 2.0, 2)

    return segments


def select_selling_points(product: dict, segments: list) -> list:
    """핵심 소구점 최대 3개.

    1순위: 사용자가 직접 입력한 소구점(줄/쉼표 구분)
    2순위: 입력한 특징 중 실제 영상 발화에서 언급된 것
    임의로 새 소구점을 만들어내지 않는다.
    """
    points = []
    raw = product.get("selling_points", "") or ""
    for part in re.split(r"[,\n·/;]+", raw):
        part = part.strip()
        if part and part not in points:
            points.append(part)

    if len(points) < 3:
        transcript = " ".join(s["text"] for s in segments)
        for part in re.split(r"[,\n·/;]+", product.get("features", "") or ""):
            part = part.strip()
            if not part or part in points:
                continue
            tokens = _tokenize(part)
            if tokens and any(t in transcript for t in tokens):
                points.append(part)
            if len(points) >= 3:
                break

    return points[:3]


def summarize(segments: list) -> dict:
    """역할별 분포 요약 (analysis.json 용)."""
    dist = {}
    for seg in segments:
        dist[seg.get("role", "?")] = dist.get(seg.get("role", "?"), 0) + 1
    return {"role_distribution": dist, "segment_count": len(segments)}
