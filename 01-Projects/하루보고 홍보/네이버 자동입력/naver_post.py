# -*- coding: utf-8 -*-
"""
하루보고 네이버 블로그 반자동 입력 도구

하는 일
  1. 홍보 폴더에서 가장 최근 "블로그 글 N - ....md" 원고를 읽는다.
  2. 크롬(없으면 엣지)을 띄워 네이버 블로그 글쓰기 화면을 연다.
     - 처음 한 번은 사용자가 직접 로그인한다. ("로그인 상태 유지" 체크)
  3. 제목 → 본문 → 엑셀 첨부 → 태그 → 카테고리까지 자동으로 채운다.
  4. 마지막 "발행" 버튼은 사용자가 직접 확인하고 누른다. (자동 발행하지 않음)

실행
  윈도우: "실행 (윈도우).bat" 더블클릭
  맥    : "실행 (맥).command" 더블클릭
  특정 글: python naver_post.py 4      (블로그 글 4)
  점검만: python naver_post.py --dry   (브라우저 없이 원고 읽기만 확인)

주의
  - 로그인 정보(쿠키)는 이 폴더가 아닌 사용자 홈의 .harubogo-naver-profile 에만 저장된다.
    (이 폴더는 Git으로 동기화되므로 절대 여기에 저장하지 않는다.)
  - 네이버 화면 구조가 바뀌면 일부 단계가 실패할 수 있다. 실패한 단계는 건너뛰고
    안내를 띄우며, 화면 캡처를 "오류기록" 폴더에 남긴다.
"""
import os
import re
import sys
import time
from pathlib import Path

try:  # 윈도우 콘솔에서 한글이 깨지지 않도록
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BLOG_ID = "harubogo"
WRITE_URL = f"https://blog.naver.com/{BLOG_ID}?Redirect=Write&"
HERE = Path(__file__).resolve().parent
PROMO_DIR = HERE.parent  # "하루보고 홍보" 폴더
PROFILE_DIR = Path.home() / ".harubogo-naver-profile"
LOG_DIR = HERE / "오류기록"
PLACEHOLDER = "(여기에 양식 파일 첨부)"


# ---------------------------------------------------------------- 원고 읽기
def find_post(number=None):
    posts = []
    for p in PROMO_DIR.glob("블로그 글 *.md"):
        m = re.match(r"블로그 글 (\d+)", p.name)
        if m:
            posts.append((int(m.group(1)), p))
    if not posts:
        sys.exit(f"[오류] '{PROMO_DIR}' 폴더에 '블로그 글 N - ...md' 원고가 없습니다.")
    posts.sort()
    if number is None:
        return posts[-1][1]
    for n, p in posts:
        if n == number:
            return p
    sys.exit(f"[오류] 블로그 글 {number} 원고를 찾지 못했습니다.")


def parse_post(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")

    title = ""
    m = re.search(r"## 제목[^\n]*\n(.*?)\n## ", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if re.match(r"\s*1\.\s+", line):
                title = re.sub(r"^\s*1\.\s+", "", line).strip()
                break
    if not title:
        sys.exit("[오류] 원고에서 '## 제목' 아래 '1. ...' 제목을 찾지 못했습니다.")

    m = re.search(r"## 본문\s*\n(.*)$", text, re.S)
    if not m:
        sys.exit("[오류] 원고에서 '## 본문' 부분을 찾지 못했습니다.")
    body = m.group(1).strip()

    tags = []
    m = re.search(r"추천 태그:\s*(.+)", text)
    if m:
        tags = [t.strip() for t in m.group(1).split("#") if t.strip()]

    category = ""
    m = re.search(r"권장 카테고리:\s*(.+)", text)
    if m:
        category = m.group(1).strip().split("(")[0].split("또는")[0].strip(" *")

    attach = None
    m = re.search(r'"([^"]+\.xlsx)"', text)
    if m:
        cand = PROMO_DIR / m.group(1)
        attach = cand if cand.exists() else None
        if not attach:
            print(f"[주의] 첨부할 엑셀 '{m.group(1)}'이 폴더에 없어 첨부는 건너뜁니다.")

    return {"title": title, "body": body, "tags": tags, "category": category, "attach": attach}


# ---------------------------------------------------------------- 브라우저 보조
def snap(page, name):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        f = LOG_DIR / f"{time.strftime('%m%d-%H%M%S')}-{name}.png"
        page.screenshot(path=str(f))
        print(f"      화면 캡처 저장: {f.name} (오류 문의 시 이 파일을 보내주세요)")
    except Exception:
        pass


def first_visible(scope, selectors, timeout=4000):
    """여러 후보 선택자 중 먼저 보이는 요소를 돌려준다. 없으면 None."""
    end = time.time() + timeout / 1000
    while time.time() < end:
        for sel in selectors:
            try:
                loc = scope.locator(sel).first
                if loc.count() and loc.is_visible():
                    return loc
            except Exception:
                pass
        time.sleep(0.3)
    return None


def paste(page, text):
    import pyperclip
    pyperclip.copy(text)
    time.sleep(0.2)
    page.keyboard.press("ControlOrMeta+V")
    time.sleep(0.8)


def launch(p):
    PROFILE_DIR.mkdir(exist_ok=True)
    opts = dict(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport=None,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation", "--no-sandbox"],
        chromium_sandbox=True,
    )
    for channel in ("chrome", "msedge"):
        try:
            return p.chromium.launch_persistent_context(channel=channel, **opts)
        except Exception:
            continue
    sys.exit("[오류] 크롬 또는 엣지 브라우저를 찾지 못했습니다. 크롬을 설치한 뒤 다시 실행해 주세요.")


def get_editor(page):
    """글쓰기 에디터가 뜰 때까지 기다린다. 로그인 화면이면 사용자가 로그인할 때까지 대기."""
    told = False
    end = time.time() + 600  # 최대 10분 대기
    while time.time() < end:
        if "nid.naver.com" in page.url and not told:
            print("\n  >> 브라우저에서 네이버에 로그인해 주세요. ('로그인 상태 유지' 체크 추천)")
            print("     로그인하면 자동으로 다음 단계로 넘어갑니다.\n")
            told = True
        for fr in [page.main_frame] + page.frames:
            try:
                if fr.locator(".se-documentTitle, .se-section-documentTitle").count():
                    return fr
            except Exception:
                pass
        if told and "blog.naver.com" in page.url and "Write" not in page.url and "PostWriteForm" not in page.url:
            page.goto(WRITE_URL)  # 로그인 후 블로그 홈으로 튄 경우 다시 글쓰기로
        time.sleep(1)
    return None


# ---------------------------------------------------------------- 단계별 입력
def close_popups(ed):
    # "작성 중인 글이 있습니다" → 새로 쓰기(취소), 도움말 패널 닫기
    for sel in (".se-popup-button-cancel", ".se-help-panel-close-button", "button.se-popup-close-button"):
        loc = first_visible(ed, [sel], timeout=1500)
        if loc:
            try:
                loc.click()
                time.sleep(0.5)
            except Exception:
                pass


def fill_title(page, ed, title):
    loc = first_visible(ed, [".se-documentTitle .se-text-paragraph", ".se-section-documentTitle .se-text-paragraph",
                             ".se-documentTitle"])
    if not loc:
        raise RuntimeError("제목 칸을 찾지 못함")
    loc.click()
    paste(page, title)


def click_body(ed):
    loc = first_visible(ed, [".se-section-text .se-text-paragraph", ".se-component.se-text .se-text-paragraph",
                             ".se-component.se-text"])
    if not loc:
        raise RuntimeError("본문 칸을 찾지 못함")
    loc.click()


def click_body_end(page, ed):
    paras = ed.locator(".se-section-text .se-text-paragraph, .se-component.se-text .se-text-paragraph")
    if paras.count():
        paras.last.click()
    page.keyboard.press("ControlOrMeta+End")


def attach_file(page, ed, file_path):
    btn = first_visible(ed, ['button[data-name="file"]', ".se-file-toolbar-button", 'button:has-text("파일")'])
    if not btn:
        raise RuntimeError("파일 첨부 버튼을 찾지 못함")
    try:
        with page.expect_file_chooser(timeout=4000) as fc:
            btn.click()
        fc.value.set_files(str(file_path))
    except Exception:
        # 파일 버튼을 누르면 "파일 불러오기 — 내 컴퓨터 / 네이버 MYBOX" 창이 먼저 뜬다
        done = False
        pc = first_visible(ed, ['button:has-text("내 컴퓨터")', 'label:has-text("내 컴퓨터")',
                                ':text("내 컴퓨터")', 'button:has-text("내 PC")'], timeout=4000)
        if pc:
            try:
                with page.expect_file_chooser(timeout=5000) as fc:
                    pc.click()
                fc.value.set_files(str(file_path))
                done = True
            except Exception:
                pass
        if not done:
            # 숨겨진 파일 입력칸에 직접 넣기 (창이 안 열려도 동작)
            inputs = ed.locator('input[type="file"]')
            if inputs.count():
                inputs.last.set_input_files(str(file_path))
                done = True
        if not done:
            raise RuntimeError("파일 선택 창이 열리지 않음")
    time.sleep(5)  # 업로드 대기
    click_body_end(page, ed)
    page.keyboard.press("Enter")


def open_publish_panel(ed):
    btn = first_visible(ed, ['button[class*="publish_btn"]', 'button:has-text("발행")'])
    if not btn:
        raise RuntimeError("상단 '발행' 버튼을 찾지 못함")
    btn.click()
    time.sleep(1.5)


def fill_tags(page, ed, tags):
    box = first_visible(ed, ['input[placeholder*="태그"]', "#tag-input"])
    if not box:
        raise RuntimeError("태그 입력칸을 찾지 못함")
    for t in tags[:30]:
        box.click()
        box.type(t, delay=30)
        page.keyboard.press("Enter")
        time.sleep(0.2)


def pick_category(ed, category):
    btn = first_visible(ed, ['button[class*="selectbox_button"]', 'button[aria-label*="카테고리"]'])
    if not btn:
        raise RuntimeError("카테고리 선택 버튼을 찾지 못함")
    btn.click()
    time.sleep(0.7)
    opt = first_visible(ed, [f'label:has-text("{category}")', f'span:text-is("{category}")',
                             f'li:has-text("{category}")'], timeout=3000)
    if not opt:
        raise RuntimeError(f"카테고리 '{category}' 항목을 찾지 못함")
    opt.click()


# ---------------------------------------------------------------- 메인
def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry" in args
    nums = [int(a) for a in args if a.isdigit()]
    path = find_post(nums[0] if nums else None)
    post = parse_post(path)

    print(f"\n[원고] {path.name}")
    print(f"  제목    : {post['title']}")
    print(f"  본문    : {len(post['body'])}자")
    print(f"  첨부    : {post['attach'].name if post['attach'] else '없음'}")
    print(f"  태그    : {', '.join(post['tags']) or '없음'}")
    print(f"  카테고리: {post['category'] or '지정 안 함'}")
    if dry:
        print("\n(--dry 점검 모드라 브라우저는 열지 않습니다.)")
        return

    try:
        from playwright.sync_api import sync_playwright
        import pyperclip  # noqa: F401
    except ImportError:
        sys.exit("[오류] 필요한 프로그램이 설치되지 않았습니다. '실행' 파일로 다시 시작해 주세요.")

    failed = []
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(WRITE_URL)

        print("\n[1/5] 글쓰기 화면 여는 중...")
        ed = get_editor(page)
        if not ed:
            snap(page, "editor")
            sys.exit("[오류] 글쓰기 화면을 열지 못했습니다. 브라우저를 닫고 다시 실행해 주세요.")
        time.sleep(2)
        close_popups(ed)

        print("[2/5] 제목 입력")
        try:
            fill_title(page, ed, post["title"])
        except Exception as e:
            failed.append(f"제목: {e}")
            snap(page, "title")

        print("[3/5] 본문 입력" + (" + 엑셀 첨부" if post["attach"] else ""))
        try:
            click_body(ed)
            body = post["body"]
            if post["attach"] and PLACEHOLDER in body:
                before, after = body.split(PLACEHOLDER, 1)
                paste(page, before.rstrip() + "\n")
                try:
                    attach_file(page, ed, post["attach"])
                except Exception as e:
                    failed.append(f"엑셀 첨부: {e} → 본문의 첨부 자리에 직접 첨부해 주세요")
                    snap(page, "attach")
                    page.keyboard.press("Escape")
                    x = first_visible(ed, [".se-popup-close-button", 'button[aria-label*="닫기"]'], timeout=1000)
                    if x:
                        x.click()
                    click_body_end(page, ed)
                    paste(page, PLACEHOLDER + "\n")
                paste(page, after.lstrip("\n"))
            else:
                paste(page, body)
        except Exception as e:
            failed.append(f"본문: {e}")
            snap(page, "body")

        print("[4/5] 발행 설정 열기 + 태그 입력")
        try:
            open_publish_panel(ed)
            if post["tags"]:
                fill_tags(page, ed, post["tags"])
        except Exception as e:
            failed.append(f"태그: {e}")
            snap(page, "tags")

        print("[5/5] 카테고리 선택")
        if post["category"]:
            try:
                pick_category(ed, post["category"])
            except Exception as e:
                failed.append(f"카테고리: {e}")
                snap(page, "category")

        print("\n" + "=" * 56)
        if failed:
            print(" 일부 단계는 직접 해주셔야 합니다:")
            for f in failed:
                print("   -", f)
        else:
            print(" 입력 완료! 모든 단계가 정상적으로 채워졌습니다.")
        print(" 브라우저에서 내용을 훑어보고, 발행 창의 초록색 '발행' 버튼을 눌러주세요.")
        print(" (발행 후 이 창에서 Enter를 누르면 브라우저가 닫힙니다.)")
        print("=" * 56)
        try:
            input()
        except EOFError:
            pass
        ctx.close()


if __name__ == "__main__":
    main()
