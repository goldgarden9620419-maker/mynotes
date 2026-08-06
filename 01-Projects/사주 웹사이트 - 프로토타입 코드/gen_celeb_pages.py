# -*- coding: utf-8 -*-
"""
celebrities.json 기반으로 유명인별 개별 SEO 페이지(celebs/<이름>.html),
목록 페이지(celebs/index.html), sitemap.xml을 생성/재생성하는 스크립트.
celebrities.json이 바뀔 때마다(인물 추가/수정) 다시 실행해야 함.

사용법: python3 gen_celeb_pages.py  (이 스크립트가 있는 폴더 기준으로 파일을 읽고 씀)
"""
import json
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
celebs = json.load(open(f"{BASE}/celebrities.json", encoding="utf-8"))
ohang_copy = json.load(open(f"{BASE}/ohang_copy.json", encoding="utf-8"))

OHANG_COLORS = {
    "木": "#4ade80", "火": "#fb7185", "土": "#e0a458", "金": "#facc15", "水": "#60a5fa",
}
STEM_TO_OHANG = {
    "甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
}

# 직업군별 실루엣 아이콘 (실존 인물의 얼굴을 그리지 않고, 분야를 상징하는 아이콘으로 대체 - 초상권 이슈 회피)
FIELD_ICONS = {
    "biz": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="3" y1="13" x2="21" y2="13"/></svg>',
    "sports": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4h8v5a4 4 0 0 1-8 0V4z"/><path d="M8 5H5a3 3 0 0 0 3 5"/><path d="M16 5h3a3 3 0 0 1-3 5"/><line x1="12" y1="13" x2="12" y2="17"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="17" x2="12" y2="20"/></svg>',
    "music": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8" y1="21" x2="16" y2="21"/></svg>',
    "film": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="9" width="18" height="12" rx="1.5"/><path d="M3 9l2-5h4l-2 5"/><path d="M9 9l2-5h4l-2 5"/><path d="M15 9l2-5h3l-1.5 5"/></svg>',
    "writer": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5C6 4.5 9 4.5 12 5.5V19c-3-1-6-1-8 0V5.5z"/><path d="M20 5.5c-2-1-5-1-8 0V19c3-1 6-1 8 0V5.5z"/></svg>',
    "science": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.6.6 1 1.4 1 2.5h6c0-1.1.4-1.9 1-2.5A6 6 0 0 0 12 3z"/></svg>',
    "fashion": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l-2 2-4 1 1 4 2-1v11h6V9l2 1 1-4-4-1-2-2z"/></svg>',
    "art": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a9 8 0 0 0 0 16c1.5 0 2-1 2-2s-1-1.5-1-2.5a1.5 1.5 0 0 1 1.5-1.5H17a4 4 0 0 0 4-4c0-3.3-4-6-9-6z"/><circle cx="8" cy="10" r="1"/><circle cx="12" cy="8" r="1"/><circle cx="16" cy="10" r="1"/></svg>',
    "humanitarian": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.4-9.5-9A5 5 0 0 1 12 6a5 5 0 0 1 9.5 5c-2.5 4.6-9.5 9-9.5 9z"/></svg>',
    "dance": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="4" r="2"/><path d="M12 6v6"/><path d="M12 12l-5 6"/><path d="M12 12l5 3"/><path d="M9 9l-3-2"/><path d="M15 9l3-1"/></svg>',
    "esports": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="8" width="20" height="10" rx="5"/><line x1="7" y1="11" x2="7" y2="15"/><line x1="5" y1="13" x2="9" y2="13"/><circle cx="16" cy="11" r="1"/><circle cx="18" cy="14" r="1"/></svg>',
}
FIELD_LABELS = {
    "biz": "경영자", "sports": "운동선수", "music": "음악가", "film": "배우·감독",
    "writer": "작가", "science": "과학자", "fashion": "디자이너", "art": "예술가",
    "humanitarian": "사회공헌가", "dance": "무용수", "esports": "프로게이머",
}

def slugify(name):
    # 괄호/점/쉼표 등 파일명에 부적절한 문자 제거, 공백은 하이픈으로
    s = re.sub(r"[()·./,]", "", name)
    s = re.sub(r"\s+", "-", s.strip())
    return s

os.makedirs(f"{BASE}/celebs", exist_ok=True)

PAGE_TMPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-E3PN7WKYWV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-E3PN7WKYWV');
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6636318203503169"
     crossorigin="anonymous"></script>
<title>{name} 사주 · 일주 {ilju} | 나와 닮은 사주의 유명인은?</title>
<meta name="description" content="{name}({ilju}, 오행 {ohang}) - {story}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{name} 사주 · 일주 {ilju}">
<meta property="og:description" content="{story}">
<meta property="og:image" content="../og-image.png">
<style>
  :root {{
    --bg: #0f1115; --card-bg: #1a1d24; --text: #f0f0f2;
    --muted: #9a9fab; --accent: {color}; --border: #2a2e38;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; display: flex; justify-content: center;
    padding: 40px 16px 80px; line-height: 1.7;
  }}
  .container {{ width: 100%; max-width: 560px; }}
  a {{ color: var(--accent); }}
  .back-link {{
    display: inline-block; margin-bottom: 24px; color: var(--muted);
    text-decoration: none; font-size: 0.9rem;
  }}
  .back-link:hover {{ color: var(--text); }}
  .badge {{
    display: inline-block; padding: 5px 14px; border-radius: 999px;
    background: var(--accent); color: #14110a; font-weight: 700;
    font-size: 0.85rem; margin-bottom: 16px;
  }}
  .avatar {{
    width: 72px; height: 72px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: color-mix(in srgb, var(--accent) 16%, #12141a);
    border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--border));
    margin-bottom: 14px;
    animation: avatarFloat 3.2s ease-in-out infinite;
  }}
  .avatar svg {{ width: 36px; height: 36px; color: var(--accent); }}
  .field-label {{ font-size: 0.72rem; color: var(--muted); margin: -10px 0 14px; }}
  @keyframes avatarFloat {{
    0%, 100% {{ transform: translateY(0) rotate(0deg); }}
    50% {{ transform: translateY(-5px) rotate(-3deg); }}
  }}
  @media (prefers-reduced-motion: reduce) {{ .avatar {{ animation: none; }} }}
  h1 {{ font-size: 1.7rem; margin: 0 0 6px; }}
  .sub {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 28px; }}
  .field {{ margin-bottom: 20px; }}
  .field .label {{
    color: var(--muted); font-size: 0.78rem; text-transform: uppercase;
    letter-spacing: 0.04em; display: block; margin-bottom: 6px;
  }}
  .field .value {{ font-size: 1rem; }}
  .motto {{
    margin-top: 28px; padding: 18px 20px; background: var(--card-bg);
    border: 1px solid var(--border); border-radius: 12px;
    font-style: italic; font-size: 1.05rem;
  }}
  .motto-note {{
    margin-top: 8px; font-size: 0.72rem; color: var(--muted); font-style: normal;
  }}
  .cta {{
    display: block; text-align: center; margin-top: 36px; padding: 14px;
    background: var(--accent); color: #14110a; border-radius: 10px;
    font-weight: 700; text-decoration: none;
  }}
  footer {{
    margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.78rem;
  }}
  footer a {{ color: var(--muted); text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
  <a class="back-link" href="../index.html">← 나와 닮은 사주 확인하기</a>
  <div class="avatar">{field_icon}</div>
  <div class="field-label">{field_label}</div>
  <span class="badge">일주 {ilju} · 오행 {ohang}</span>
  <h1>{name}</h1>
  <p class="sub">{name}의 사주(일주 {ilju})와 성공 스토리</p>

  <div class="field">
    <span class="label">성공 스토리</span>
    <span class="value">{story}</span>
  </div>
  <div class="field">
    <span class="label">핵심 습관 · 마인드셋</span>
    <span class="value">{habit}</span>
  </div>

  <div class="motto">
    &ldquo;{motto}&rdquo;
    <p class="motto-note">※ 실제 어록이거나, 공개된 자료를 바탕으로 요약·재구성한 대표 문구입니다.</p>
  </div>

  <a class="cta" href="../index.html">내 생년월일로 나의 사주 유형 확인하기 →</a>

  <footer>
    <a href="index.html">전체 유명인 목록</a> · <a href="../privacy-policy.html">개인정보처리방침</a> · <a href="../terms.html">이용약관</a>
  </footer>
</div>
</body>
</html>
"""

generated = []
for c in celebs:
    ohang = STEM_TO_OHANG[c["ilju"][0]]
    slug = slugify(c["name"])
    field = c.get("field", "biz")
    html = PAGE_TMPL.format(
        name=c["name"], ilju=c["ilju"], ohang=ohang,
        story=c["story"], habit=c["habit"], motto=c["motto"],
        color=OHANG_COLORS[ohang],
        field_icon=FIELD_ICONS.get(field, FIELD_ICONS["biz"]),
        field_label=FIELD_LABELS.get(field, ""),
    )
    path = f"{BASE}/celebs/{slug}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    generated.append((c["name"], slug, c["ilju"], ohang))

print(f"{len(generated)}개 페이지 생성 완료")

# ---- 유명인 전체 목록 페이지 (celebs/index.html) ----
by_ohang = {}
for name, slug, ilju, ohang in generated:
    by_ohang.setdefault(ohang, []).append((name, slug, ilju))

ohang_order = ["木", "火", "土", "金", "水"]
sections = []
for oh in ohang_order:
    items = sorted(by_ohang.get(oh, []), key=lambda x: x[0])
    lis = "\n".join(
        f'    <li><a href="{slug}.html">{name}</a> <span class="ilju">{ilju}</span></li>'
        for name, slug, ilju in items
    )
    sections.append(f"""  <h2><span class="dot" style="background:{OHANG_COLORS[oh]}"></span>{oh} ({len(items)}명)</h2>
  <ul class="celeb-grid">
{lis}
  </ul>""")

INDEX_TMPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-E3PN7WKYWV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-E3PN7WKYWV');
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6636318203503169"
     crossorigin="anonymous"></script>
<title>전체 유명인 목록 | 나와 닮은 사주의 유명인은?</title>
<meta name="description" content="사주 매칭에 사용되는 전체 {total}명의 유명인 목록 - 오행(木火土金水)별로 정리">
<style>
  :root {{
    --bg: #0f1115; --card-bg: #1a1d24; --text: #f0f0f2;
    --muted: #9a9fab; --accent: #e0a458; --border: #2a2e38;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    background: var(--bg); color: var(--text);
    display: flex; justify-content: center;
    padding: 40px 16px 80px;
  }}
  .container {{ width: 100%; max-width: 640px; }}
  a {{ color: inherit; text-decoration: none; }}
  .back-link {{
    display: inline-block; margin-bottom: 24px; color: var(--muted);
    text-decoration: none; font-size: 0.9rem;
  }}
  h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
  .sub {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 32px; }}
  h2 {{
    font-size: 1rem; margin-top: 32px; margin-bottom: 12px;
    display: flex; align-items: center; gap: 8px;
  }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  .celeb-grid {{
    list-style: none; padding: 0; margin: 0;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 8px;
  }}
  .celeb-grid li {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px; font-size: 0.85rem;
  }}
  .celeb-grid a:hover {{ color: var(--accent); }}
  .ilju {{ color: var(--muted); font-size: 0.75rem; margin-left: 4px; }}
</style>
</head>
<body>
<div class="container">
  <a class="back-link" href="../index.html">← 나와 닮은 사주 확인하기</a>
  <h1>전체 유명인 목록</h1>
  <p class="sub">사주 매칭에 사용되는 총 {total}명 · 오행(木火土金水)별 정리</p>
{sections}
</div>
</body>
</html>
"""

index_html = INDEX_TMPL.format(total=len(generated), sections="\n\n".join(sections))
with open(f"{BASE}/celebs/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)
print("celebs/index.html 생성 완료")

# ---- sitemap.xml ----
urls = ["index.html", "celebs/index.html"] + [f"celebs/{slug}.html" for _, slug, _, _ in generated]
sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    sitemap.append(f"  <url><loc>https://sajutwin.com/{u}</loc></url>")
sitemap.append("</urlset>")
with open(f"{BASE}/sitemap.xml", "w", encoding="utf-8") as f:
    f.write("\n".join(sitemap))
print("sitemap.xml 생성 완료 (도메인: sajutwin.com)")
