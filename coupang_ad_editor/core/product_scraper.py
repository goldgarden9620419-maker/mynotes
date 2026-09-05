# -*- coding: utf-8 -*-
"""쿠팡 상품 URL → 제품 정보 자동 추출.

1차: requests로 빠르게 시도
2차: 차단(403 등)되면 PC에 설치된 Edge/Chrome을 Playwright로 잠깐 띄워
     실제 브라우저로 페이지를 읽는다 (쿠팡 봇 차단 우회에 효과적).

실패 시 ok=False와 안내 메시지를 반환한다 (수동 입력으로 진행).
페이지에 없는 정보를 만들어내지 않는다.
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

_PLAYWRIGHT_HINT = (
    "브라우저 자동 조회 기능이 설치되어 있지 않습니다. "
    "검은 창(cmd)에서 프로그램 폴더로 이동 후 "
    "`venv\\Scripts\\python -m pip install playwright` 를 실행하면 "
    "차단 우회 조회를 사용할 수 있어요. 지금은 직접 입력해주세요."
)


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


def _looks_blocked(status_code: int, text: str) -> bool:
    low = (text or "").lower()
    return (status_code in (403, 429, 503) or
            "captcha" in low or "access denied" in low or
            "잠시 후 다시" in (text or ""))


def _fetch_html_requests(url: str, timeout: int):
    """(html, error_message) — 성공 시 error_message는 None."""
    try:
        session = requests.Session()
        resp = session.get(url, headers=_HEADERS, timeout=timeout,
                           allow_redirects=True)
    except requests.RequestException as exc:
        return None, f"쿠팡 접속 실패({type(exc).__name__})"
    if _looks_blocked(resp.status_code, resp.text) or resp.status_code != 200:
        return None, f"차단됨(상태 {resp.status_code})"
    return resp.text, None


def _fetch_html_browser(url: str, timeout: int = 30):
    """설치된 Edge/Chrome을 잠깐 띄워 실제 브라우저로 HTML을 가져온다.

    (html, error) — error: None | "browser-missing" | 상세 메시지
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "browser-missing"

    last_error = "unknown"
    for channel in ("msedge", "chrome", None):
        try:
            with sync_playwright() as p:
                kwargs = {
                    "headless": False,  # 헤드리스는 차단되기 쉬움
                    "args": ["--window-size=480,640",
                             "--window-position=40,40"],
                }
                if channel:
                    kwargs["channel"] = channel
                browser = p.chromium.launch(**kwargs)
                try:
                    context = browser.new_context(
                        locale="ko-KR",
                        viewport={"width": 480, "height": 640})
                    page = context.new_page()
                    # 쿠팡 메인을 먼저 방문해 쿠키를 받아두면 차단이 줄어든다
                    try:
                        page.goto("https://www.coupang.com",
                                  wait_until="domcontentloaded",
                                  timeout=timeout * 1000)
                        page.wait_for_timeout(1500)
                    except Exception:  # noqa: BLE001
                        pass
                    page.goto(url, wait_until="domcontentloaded",
                              timeout=timeout * 1000)
                    page.wait_for_timeout(2500)  # 스크립트 렌더 대기
                    html = page.content()
                    if _looks_blocked(200, html):
                        # 잠시 기다렸다가 한 번 새로고침 재시도
                        page.wait_for_timeout(3000)
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(2500)
                        html = page.content()
                finally:
                    browser.close()
                if html and _looks_blocked(200, html):
                    last_error = "쿠팡이 브라우저 접근도 차단함"
                    continue
                if html and ("og:title" in html or "<title>" in html):
                    return html, None
                last_error = "페이지 내용을 읽지 못함"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)[:120]
            continue
    return None, last_error


def _parse(text: str, image_dir: str, timeout: int) -> dict:
    result = {"ok": False, "name": "", "category": "", "price": "",
              "discount": "", "image_path": None, "message": ""}

    # 제품명: og:title → <title>
    name = _first_match(text, [
        r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:title"',
        r"<title>([^<]+)</title>",
    ])
    result["name"] = _clean_title(name)
    # 차단 페이지 제목을 제품명으로 오인하지 않도록 걸러낸다
    if result["name"].strip().lower() in (
            "access denied", "access to this page has been denied",
            "접근이 거부되었습니다", "잠시만 기다려 주세요", "coupang", "쿠팡"):
        result["name"] = ""

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

    # 대표 이미지 다운로드 (엔드카드용) — CDN은 보통 차단하지 않음
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
                img_resp = requests.get(img_url, headers=_HEADERS,
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


def fetch_product_info(url: str, image_dir: str = None,
                       timeout: int = 15) -> dict:
    """쿠팡 상품 페이지에서 제품 정보를 가져온다.

    반환: {"ok", "name", "category", "price", "discount",
           "image_path", "message"}
    """
    url = (url or "").strip()
    if not url.startswith("http"):
        return {"ok": False, "name": "", "category": "", "price": "",
                "discount": "", "image_path": None,
                "message": "올바른 URL 형식이 아닙니다. https:// 로 시작하는 쿠팡 상품 주소를 붙여넣어주세요."}

    # 1차: requests
    text, err = _fetch_html_requests(url, timeout)

    # 2차: 실제 브라우저 (Edge/Chrome)
    if text is None:
        text, browser_err = _fetch_html_browser(url)
        if text is None:
            if browser_err == "browser-missing":
                message = f"쿠팡이 자동 조회를 차단했습니다({err}). {_PLAYWRIGHT_HINT}"
            else:
                message = (f"쿠팡이 자동 조회를 차단했고({err}), 브라우저 조회도 "
                           f"실패했습니다({browser_err}). 제품 정보를 직접 입력해주세요.")
            return {"ok": False, "name": "", "category": "", "price": "",
                    "discount": "", "image_path": None, "message": message}

    return _parse(text, image_dir, timeout)
