# -*- coding: utf-8 -*-
"""플랫폼별 게시글 문구 + 해시태그 생성.

- Instagram: 정보 전달 + 저장/공유 유도, 조금 긴 문구
- TikTok: 짧고 후킹, 실사용 후기 톤
- 두 플랫폼 문구를 복사하지 않고 각각 작성한다.
- 입력된 제품 정보에 없는 효능/기능/가격은 절대 추가하지 않는다.
"""
import re

from utils import config

# 카테고리 → 관련 해시태그 후보 (제품 관련 태그 우선)
_CATEGORY_TAGS = {
    "주방": ["주방용품", "주방꿀템", "살림템", "자취필수템"],
    "생활": ["생활용품", "생활꿀템", "살림꿀템", "자취템"],
    "가전": ["가전제품", "가전추천", "생활가전"],
    "디지털": ["전자기기", "테크", "가젯"],
    "뷰티": ["뷰티템", "뷰티추천"],
    "패션": ["패션템", "데일리룩"],
    "식품": ["간편식", "집밥", "먹스타그램"],
    "유아": ["육아템", "육아필수템"],
    "반려": ["반려동물용품", "펫스타그램", "댕댕이", "냥스타그램"],
    "운동": ["홈트", "운동템", "헬스용품"],
    "차량": ["차량용품", "카라이프"],
    "인테리어": ["인테리어소품", "집꾸미기", "홈데코"],
}


def _clean(text: str) -> str:
    return (text or "").strip()


def _tag(text: str) -> str:
    return re.sub(r"[^\w가-힣]", "", text)


def _is_safe(line: str) -> bool:
    """자동 생성 문구에서 금지 표현 배제."""
    return not any(bad in line for bad in config.BANNED_AUTO_PHRASES)


def hashtags(product: dict, platform: str) -> list:
    """제품 관련 태그 우선 해시태그 후보."""
    tags = []
    name_tag = _tag(_clean(product.get("name")))
    if name_tag:
        tags.append(name_tag[:15])

    category = _clean(product.get("category"))
    cat_tag = _tag(category)
    if cat_tag:
        tags.append(cat_tag[:15])
    for key, extra in _CATEGORY_TAGS.items():
        if key in category:
            tags.extend(extra)
            break

    for part in re.split(r"[,\n·/;]+", _clean(product.get("selling_points"))):
        t = _tag(part)
        if 2 <= len(t) <= 12:
            tags.append(t)

    tags.append("쿠팡")
    if platform == "instagram":
        tags += ["내돈내산", "일상템", "추천템"]
    else:
        tags += ["틱톡추천", "꿀템", "추천템"]

    seen, result = set(), []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            result.append(f"#{t}")
    limit = 15 if platform == "instagram" else 6
    return result[:limit]


# 쿠팡 파트너스 활동 시 필수 대가성 표기 문구
PARTNERS_DISCLOSURE = ("이 포스팅은 쿠팡 파트너스 활동의 일환으로, "
                       "이에 따른 일정액의 수수료를 제공받습니다.")


def _is_partners_link(url: str) -> bool:
    url = (url or "").lower()
    return "link.coupang.com" in url or "coupa.ng" in url


def instagram_caption(product: dict, selling_points: list,
                      hook_text: str = "") -> str:
    """instagram_caption.txt 내용."""
    name = _clean(product.get("name"))
    target = _clean(product.get("target"))
    cta = _clean(product.get("cta")) or "프로필 링크에서 확인해보세요"
    url = _clean(product.get("url"))

    lines = []
    if hook_text and _is_safe(hook_text):
        lines.append(f"“{hook_text}”")
        lines.append("")
    if name:
        lines.append(f"요즘 잘 쓰고 있는 {name} 솔직 후기예요 🙂")
    if target:
        lines.append(f"{target} 분들이라면 특히 도움이 될 것 같아요.")
    lines.append("")
    if selling_points:
        lines.append("이런 점이 좋았어요 👇")
        for i, point in enumerate(selling_points, 1):
            lines.append(f"{i}. {point}")
        lines.append("")
    price = _clean(product.get("price"))
    discount = _clean(product.get("discount"))
    if price:
        lines.append(f"가격: {price}" + (f" ({discount})" if discount else ""))
        lines.append("※ 가격/할인 정보는 변동될 수 있어요.")
        lines.append("")
    lines.append(f"👉 {cta}")
    if url:
        lines.append(f"🔗 {url}")
    lines.append("")
    lines.append("저장해두면 나중에 찾기 편해요 📌")
    lines.append("")
    lines.append(" ".join(hashtags(product, "instagram")))
    if _is_partners_link(url):
        lines.append("")
        lines.append(PARTNERS_DISCLOSURE)
    return "\n".join(line for line in lines if _is_safe(line))


def tiktok_caption(product: dict, selling_points: list,
                   hook_text: str = "") -> str:
    """tiktok_caption.txt 내용 — 짧고 후킹."""
    name = _clean(product.get("name"))
    cta = _clean(product.get("cta")) or "쿠팡에서 확인"

    first = hook_text if (hook_text and _is_safe(hook_text)) else \
        (f"{name} 직접 써본 후기" if name else "직접 써본 후기")
    lines = [first]
    if selling_points:
        lines.append(f"한줄평: {selling_points[0]} 👍")
    lines.append(f"{cta} 🔗")
    lines.append(" ".join(hashtags(product, "tiktok")))
    if _is_partners_link(_clean(product.get("url"))):
        lines.append(PARTNERS_DISCLOSURE)
    return "\n".join(line for line in lines if _is_safe(line))
