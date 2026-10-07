#!/usr/bin/env python3
"""
ig_publish.py — Instagram 릴스 자동 게시 (Instagram API with Instagram Login, 공식 API)

흐름: ① 토큰/계정 확인 → ② 릴스 컨테이너 생성(AI 라벨 포함) → ③ 처리 완료 대기 → ④ 게시 → ⑤ 기록
외부 패키지 없이 파이썬 표준 라이브러리만 사용 (Windows/Mac 공통).

사용법:
  python ig_publish.py --post posts/2026-10-07-ep1.json --dry-run      # 게시 없이 점검만
  python ig_publish.py --post posts/2026-10-07-ep1.json                # 지금 게시
  python ig_publish.py --post posts/2026-10-07-ep1.json --at "2026-10-07 19:30"   # 해당 시각까지 기다렸다 게시 (PC 켜둘 것)
  python ig_publish.py --refresh-token                                 # 60일 토큰 연장

토큰: 환경변수 IG_ACCESS_TOKEN 또는 ~/.ig_token 파일 (저장소/vault에 절대 넣지 말 것)

종료 코드: 0 성공 · 2 입력 오류 · 3 토큰/계정 문제 · 4 영상 처리 실패/시간 초과 · 5 게시 실패 · 6 AI 라벨 미지원
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = os.environ.get("IG_API_VERSION", "v24.0")
BASE = f"https://graph.instagram.com/{API_VERSION}"   # 토큰을 읽은 뒤 set_mode()가 확정
MODE = "instagram"  # "instagram" (IG… 토큰) 또는 "facebook" (EAA… 토큰, 페이스북 페이지 연결 방식)


def set_mode(token):
    """토큰 앞글자로 방식 판별. Facebook 로그인 토큰은 graph.facebook.com 사용."""
    global BASE, MODE
    if token.startswith("EAA"):
        MODE, BASE = "facebook", f"https://graph.facebook.com/{API_VERSION}"
    else:
        MODE, BASE = "instagram", f"https://graph.instagram.com/{API_VERSION}"
TOKEN_FILE = Path.home() / ".ig_token"
LOG_FILE = Path(__file__).resolve().parent.parent / "posts" / "publish_log.jsonl"


def die(code, msg):
    print(f"[ig_publish] ❌ {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg):
    print(f"[ig_publish] {msg}", flush=True)


def load_token():
    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not tok and TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not tok:
        die(3, f"토큰이 없습니다. 환경변수 IG_ACCESS_TOKEN 또는 {TOKEN_FILE} 에 저장하세요.")
    return tok


def call(method, path, params, token, timeout=60):
    """Graph API 호출. 오류 시 Meta 메시지를 그대로 담아 RuntimeError."""
    params = dict(params or {})
    params["access_token"] = token
    url = path if path.startswith("http") else f"{BASE}{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        try:
            err = json.loads(body).get("error", {})
            msg = f"{err.get('message')} (code {err.get('code')}, subcode {err.get('error_subcode')})"
        except Exception:
            msg = body[:300]
        raise RuntimeError(msg)
    except urllib.error.URLError as e:
        raise RuntimeError(f"네트워크 오류: {e.reason}")


def check_account_fb(token):
    want = os.environ.get("IG_USERNAME", "kim_jade0419").lstrip("@")
    try:
        r = call("GET", "/me/accounts", {"fields": "name,instagram_business_account{id,username}"}, token)
    except RuntimeError as e:
        die(3, f"페이스북 토큰 확인 실패: {e}\n→ Graph API 탐색기에서 pages_show_list 권한을 포함해 토큰을 다시 생성하세요.")
    accts = [p["instagram_business_account"] | {"page": p.get("name")}
             for p in r.get("data", []) if p.get("instagram_business_account")]
    if not accts:
        die(3, "페이스북 페이지에 연결된 인스타 프로페셔널 계정을 찾지 못했습니다.\n→ 페이지 설정 → 연결된 계정 → Instagram 연결 후 다시 시도하세요.")
    pick = next((a for a in accts if a.get("username") == want), accts[0])
    info(f"계정 확인(페이스북 방식): @{pick.get('username')} (id {pick['id']}, 페이지 '{pick.get('page')}')")
    return {"user_id": pick["id"], "username": pick.get("username")}


def check_account(token):
    if MODE == "facebook":
        return check_account_fb(token)
    try:
        me = call("GET", "/me", {"fields": "user_id,username,account_type"}, token)
    except RuntimeError as e:
        die(3, f"토큰 확인 실패: {e}\n→ 토큰이 만료됐거나 잘못 복사됐을 수 있어요. Meta 앱 대시보드에서 다시 발급하세요.")
    at = str(me.get("account_type") or "").upper()
    if at and at not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
        info(f"⚠️ 계정 유형이 {at} 입니다. 게시가 거부되면 인스타 설정에서 크리에이터 계정으로 전환하세요.")
    info(f"계정 확인: @{me.get('username')} (id {me.get('user_id')}, {me.get('account_type')})")
    return me


def check_video(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            size = int(r.headers.get("Content-Length") or 0)
            ctype = r.headers.get("Content-Type", "")
    except Exception as e:
        die(2, f"영상 링크를 열 수 없습니다: {e}")
    if "video" not in ctype and not url.lower().endswith(".mp4"):
        die(2, f"영상 파일이 아닌 것 같습니다 (Content-Type: {ctype})")
    info(f"영상 링크 확인: {size/1e6:.1f}MB, {ctype}")


def load_post(path):
    p = Path(path)
    if not p.exists():
        die(2, f"게시 파일이 없습니다: {p}")
    post = json.loads(p.read_text(encoding="utf-8"))
    for k in ("video_url", "caption"):
        if not post.get(k):
            die(2, f"게시 파일에 '{k}'가 없습니다.")
    if len(post["caption"]) > 2200:
        die(2, f"캡션이 2,200자를 넘습니다 ({len(post['caption'])}자).")
    if post["caption"].count("#") > 30:
        die(2, "해시태그는 30개까지입니다.")
    post.setdefault("is_ai_generated", True)
    post.setdefault("share_to_feed", True)
    return post


def wait_until(at_text):
    target = dt.datetime.strptime(at_text, "%Y-%m-%d %H:%M")
    secs = (target - dt.datetime.now()).total_seconds()
    if secs <= 0:
        info("지정 시각이 이미 지났습니다. 바로 게시합니다.")
        return
    info(f"{target:%m/%d %H:%M} 까지 대기합니다 (약 {int(secs//60)}분). PC를 켜두고 이 창을 닫지 마세요.")
    while secs > 0:
        time.sleep(min(60, secs))
        secs = (target - dt.datetime.now()).total_seconds()


def publish(post, token, ig_id):
    params = {
        "media_type": "REELS",
        "video_url": post["video_url"],
        "caption": post["caption"],
        "share_to_feed": "true" if post["share_to_feed"] else "false",
    }
    if post.get("cover_url"):
        params["cover_url"] = post["cover_url"]
    if post.get("thumb_offset_ms") is not None:
        params["thumb_offset"] = str(int(post["thumb_offset_ms"]))
    if post["is_ai_generated"]:
        params["is_ai_generated"] = "true"

    # ② 컨테이너 생성
    try:
        c = call("POST", f"/{ig_id}/media", params, token, timeout=120)
    except RuntimeError as e:
        if post["is_ai_generated"] and "is_ai_generated" in str(e):
            die(6, f"AI 라벨 옵션이 거부됐습니다: {e}\n→ IG_API_VERSION 환경변수를 최신 버전(예: v25.0)으로 바꿔 다시 시도하세요. "
                   "AI 라벨 없이 올리지 않도록 여기서 멈춥니다.")
        die(5, f"릴스 컨테이너 생성 실패: {e}")
    cid = c.get("id")
    info(f"업로드 접수 (container {cid}). 인스타가 영상을 처리하는 중…")

    # ③ 처리 대기 (최대 10분)
    deadline = time.time() + 600
    status = ""
    while time.time() < deadline:
        time.sleep(10)
        try:
            s = call("GET", f"/{cid}", {"fields": "status_code,status"}, token)
        except RuntimeError as e:
            info(f"상태 확인 재시도: {e}")
            continue
        status = s.get("status_code", "")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            die(4, f"인스타 영상 처리 실패: {s.get('status')}")
        info(f"처리 중… ({status or '확인 중'})")
    else:
        die(4, "10분 안에 처리가 끝나지 않았습니다. 잠시 후 같은 명령으로 다시 시도하세요.")

    # ④ 게시
    try:
        r = call("POST", f"/{ig_id}/media_publish", {"creation_id": cid}, token, timeout=120)
    except RuntimeError as e:
        die(5, f"게시 실패: {e}")
    media_id = r.get("id")
    link = ""
    try:
        m = call("GET", f"/{media_id}", {"fields": "permalink,timestamp"}, token)
        link = m.get("permalink", "")
    except RuntimeError:
        pass
    return media_id, link


def refresh_token(token):
    if MODE == "facebook":
        app_id, secret = os.environ.get("FB_APP_ID"), os.environ.get("FB_APP_SECRET")
        if not (app_id and secret):
            die(3, "페이스북 방식 토큰 연장에는 환경변수 FB_APP_ID, FB_APP_SECRET 이 필요합니다 (앱 설정 → 기본 설정).")
        try:
            r = call("GET", f"https://graph.facebook.com/{API_VERSION}/oauth/access_token",
                     {"grant_type": "fb_exchange_token", "client_id": app_id,
                      "client_secret": secret, "fb_exchange_token": token}, token)
        except RuntimeError as e:
            die(3, f"토큰 교환 실패: {e}")
        TOKEN_FILE.write_text(r["access_token"], encoding="utf-8")
        info(f"60일 토큰으로 교환 완료 → {TOKEN_FILE}")
        return
    try:
        r = call("GET", "https://graph.instagram.com/refresh_access_token",
                 {"grant_type": "ig_refresh_token"}, token)
    except RuntimeError as e:
        die(3, f"토큰 연장 실패: {e}")
    TOKEN_FILE.write_text(r["access_token"], encoding="utf-8")
    days = int(r.get("expires_in", 0)) // 86400
    info(f"토큰 연장 완료 (약 {days}일 유효) → {TOKEN_FILE}")


def main():
    ap = argparse.ArgumentParser(description="Instagram 릴스 자동 게시")
    ap.add_argument("--post", help="게시 정보 JSON 파일 (video_url, caption, is_ai_generated)")
    ap.add_argument("--dry-run", action="store_true", help="게시하지 않고 토큰·계정·영상·캡션만 점검")
    ap.add_argument("--at", help='예약 시각 "YYYY-MM-DD HH:MM" (PC 시간 기준)')
    ap.add_argument("--refresh-token", action="store_true", help="토큰 60일 연장")
    a = ap.parse_args()

    token = load_token()
    set_mode(token)
    info(f"연결 방식: {'Instagram 로그인' if MODE == 'instagram' else 'Facebook 로그인(페이지 연결)'}")
    if a.refresh_token:
        refresh_token(token)
        return
    if not a.post:
        die(2, "--post 파일을 지정하세요.")

    post = load_post(a.post)
    me = check_account(token)
    check_video(post["video_url"])
    info(f"캡션 {len(post['caption'])}자 · 해시태그 {post['caption'].count('#')}개 · AI 라벨 {'ON' if post['is_ai_generated'] else 'OFF'}")

    if a.dry_run:
        info("✅ 점검 통과 (dry-run이라 게시하지 않았습니다)")
        return
    if a.at:
        wait_until(a.at)

    media_id, link = publish(post, token, "me" if MODE == "instagram" else me["user_id"])
    info(f"✅ 게시 완료! {link or media_id}")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"),
                            "post": Path(a.post).name, "media_id": media_id,
                            "permalink": link, "ai_label": post["is_ai_generated"]},
                           ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
