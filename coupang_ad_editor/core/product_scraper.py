# -*- coding: utf-8 -*-
"""쿠팡 상품 URL → 제품 정보 자동 추출.

상품 페이지 HTML에서 제품명 / 카테고리 / 가격 / 할인율 / 대표 이미지를
best-effort로 파싱한다. 쿠팡은 봇 차단이 강해서 실패할 수 있으며,
실패 시 ok=False와 안내 메시지를 반환한다 (수동 입력으로 진행).

추출된 정보만 사용하고, 페이지에 없는 정보를 만들어내지 않는다.
"""
import html as html_lib
import os
import re

import requests

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.5",
    "Referer": "https://www.coupang.com/",
    "Cache-Control": "no-cache",
}

_TITLE_SUFFIXES = [" - 쿠팡!", " | 쿠팡", " - 쿠팡", "쿠팡!", "- Coupang"]


def _clean_title(title: str) -> str:
    title = html_lib.unescape(title).strip()
    for suffix in _TITLE_SUFFIXES:
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title


def _first_match(text: str, patterns: list) -> str:
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def _format_price(raw: str) -> str:
    try:
        return f"{int(raw):,}원"
    except (ValueError, TypeError):
        return ""


def fetch_product_info(url: str, image_dir: str = None,
                       timeout: int = 15) -> dict:
    """쿠팡 상품 페이지에서 제품 정보를 가져온다.

    반환: {"ok", "name", "category", "price", "discount",
           "image_path", "message"}
    """
    result = {"ok": False, "name": "", "category": "", "price": "",
              "discount": "", "image_path": None, "message": ""}

    url = (url or "").strip()
    if not url.startswith("http"):
        result["message"] = "올바른 URL 형식이 아닙니다. https:// 로 시작하는 쿠팡 상품 주소를 붙여넣어주세요."
        return result

    try:
        session = requests.Session()
        resp = session.get(url, headers=_HEADERS, timeout=timeout,
                           allow_redirects=True)
    except requests.RequestException as exc:
        result["message"] = f"쿠팡 접속에 실패했습니다({type(exc).__name__}). 인터넷 연결을 확인하거나 수동으로 입력해주세요."
        return result

    text = resp.text or ""
    blocked = (resp.status_code in (403, 429) or
               "captcha" in text.lower() or
               "access denied" in text.lower())
    if blocked or resp.status_code != 200:
        result["message"] = (f"쿠팡이 자동 조회를 차단했습니다(상태 {resp.status_code}). "
                             "잠시 후 다시 시도하거나, 제품 정보를 직접 입력해주세요.")
        return result

    # 제품명: og:title → <title>
    name = _first_match(text, [
        r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:title"',
        r"<title>([^<]+)</title>",
    ])
    result["name"] = _clean_title(name)

    # 가격: 쿠폰가 → 판매가 순
    price_raw = _first_match(text, [
        r'"couponPrice"\s*:\s*"?(\d{3,9})',
        r'"finalPrice"\s*:\s*"?(\d{3,9})',
        r'"salePrice"\s*:\s*"?(\d{3,9})',
        r'"price"\s*:\s*"?(\d{3,9})',
        r'total-price[^>]*>[^0-9]*([\d,]{4,12})\s*원',
    ])
    result["price"] = _format_price(price_raw.replace(",", "")) if price_raw else ""

    # 할인율
    discount_raw = _first_match(text, [
        r'"discountRate"\s*:\s*"?(\d{1,2})',
        r'discount-percentage[^>]*>\s*(\d{1,2})\s*%',
    ])
    if discount_raw and discount_raw != "0":
        result["discount"] = f"{discount_raw}% 할인"

    # 카테고리: breadcrumb JSON에서 상위 1~2개
    cats = re.findall(r'"(?:categoryName|name)"\s*:\s*"([^"]{2,20})"', text)
    seen, picked = set(), []
    for cat in cats:
        cat = html_lib.unescape(cat).strip()
        if cat and cat not in seen and cat != result["name"] and "쿠팡" not in cat:
            seen.add(cat)
            picked.append(cat)
        if len(picked) >= 2:
            break
    result["category"] = "/".join(picked)

    # 대표 이미지 다운로드 (엔드카드용)
    if image_dir:
        img_url = _first_match(text, [
            r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
            r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
        ])
        if img_url:
            img_url = html_lib.unescape(img_url)
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            try:
                img_resp = session.get(img_url, headers=_HEADERS,
                                       timeout=timeout)
                if img_resp.status_code == 200 and len(img_resp.content) > 2000:
                    os.makedirs(image_dir, exist_ok=True)
                    ext = ".png" if ".png" in img_url.lower() else ".jpg"
                    path = os.path.join(image_dir, f"coupang_product{ext}")
                    with open(path, "wb") as f:
                        f.write(img_resp.content)
                    result["image_path"] = path
            except requests.RequestException:
                pass  # 이미지는 선택 사항이므로 실패해도 계속 진행

    if result["name"]:
        result["ok"] = True
        filled = [k for k in ("name", "category", "price", "discount") if result[k]]
        missing = [k for k in ("category", "price", "discount") if not result[k]]
        msg = "상품 정보를 가져왔습니다."
        if missing:
            label = {"category": "카테고리", "price": "가격", "discount": "할인"}
            msg += " (" + ", ".join(label[m] for m in missing) + "은(는) 찾지 못해 비워뒀어요)"
        result["message"] = msg
    else:
        result["message"] = ("페이지는 열렸지만 상품 정보를 읽지 못했습니다. "
                             "쿠팡 상품 상세 페이지 URL인지 확인하거나 직접 입력해주세요.")
    return result
