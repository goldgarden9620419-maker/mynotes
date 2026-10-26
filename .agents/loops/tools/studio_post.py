"""황금정원 루프 초안 노트를 '블로그+스레드 발행 스튜디오' posts 문서(JSON)로 변환한다.

형식 고르기: python3 studio_post.py --pick-layout [최근형식들 예: C,A,I]
  → 12개 형식(layouts.json, 스튜디오와 같은 목록) 중 최근 3편 형식을 뺀 하나를 무작위로 골라 id·설명·HTML 뼈대를 출력한다.
  최근 형식은 스튜디오 posts 문서의 `layout` 값을 createdAt 최신순으로 3개 읽어 넘긴다. 카드형(A)으로 고정하지 않는다 (2026-10-26 사용자 지시).
변환: python3 studio_post.py <노트.md> <출력.json> [category] [tags] [photoQuery] [photoAlt] [photoCaption] [commentText] [layout] [styles]
결과 JSON을 ArtifactData set (url=STUDIO_URL, collection=posts, doc_id=p-YYYYMMDD-slug)으로 넣는다.
스튜디오는 bodyHtml을 인라인 스타일로 저장하므로, 모든 형식의 클래스 HTML에 스튜디오와 같은 스타일을 입힌다.
"""

import json, os, random, re, sys, time
from html.parser import HTMLParser

STUDIO_URL = "https://claude.ai/artifact/JX5794Nywjmji4B8NbwDiH"
ST = {
    'lead': 'font-size:1.05rem;line-height:1.95;color:#1f2937;margin:0 0 10px 0;',
    'p': 'font-size:1rem;line-height:1.95;color:#374151;margin:0 0 14px 0;',
    'card': 'background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,0.05);margin:22px 0;overflow:hidden;',
    'h2': 'font-size:1.3rem;font-weight:700;color:#1e3a8a;margin:0;padding:18px 22px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border-bottom:1px solid #e5e7eb;',
    'faqH2': 'font-size:1.3rem;font-weight:700;margin:0;padding:18px 22px;background:linear-gradient(135deg,#f5f3ff,#ede9fe);color:#5b21b6;border-bottom:1px solid #e5e7eb;',
    'h2plain': 'font-size:1.25rem;font-weight:700;color:#1e3a8a;margin:30px 0 12px 0;padding:2px 0 2px 12px;border-left:4px solid #3b82f6;line-height:1.5;',
    'h3': 'font-size:1.1rem;font-weight:700;color:#1e3a8a;margin:18px 0 10px 0;',
    'body': 'padding:20px 22px;',
    'summary': 'background:#f0f7ff;border-left:4px solid #3b82f6;border-radius:8px;padding:14px 16px;margin-top:16px;font-size:0.95rem;line-height:1.8;color:#1e40af;',
    'list': 'list-style-type:disc;margin:10px 0 14px 22px;padding:0;',
    'li': 'margin:6px 0;line-height:1.8;color:#374151;font-size:1rem;',
    'a': 'color:#2563eb;text-decoration:underline;',
    'faqQ': 'font-size:1rem;line-height:1.85;color:#5b21b6;margin:0 0 6px 0;',
    'faqA': 'font-size:1rem;line-height:1.9;color:#374151;margin:0;',
    'faqItem': 'background:#faf5ff;border:1px solid #ede9fe;border-radius:10px;padding:12px 14px;margin:10px 0;',
    'secNum': 'font-size:0.85rem;font-weight:800;color:#3b82f6;letter-spacing:0.15em;margin:30px 0 0 0;',
    'voiceA': 'background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;padding:14px 16px;margin:12px 40px 12px 0;',
    'voiceB': 'background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:14px 16px;margin:12px 0 12px 40px;',
    'voiceNameA': 'display:block;font-size:0.85rem;color:#9a3412;margin-bottom:6px;',
    'voiceNameB': 'display:block;font-size:0.85rem;color:#1e40af;margin-bottom:6px;',
    'letter': 'background:#fffdf7;border:1px solid #eadfc8;border-radius:12px;padding:22px 24px;margin:10px 0 18px 0;',
    'letterTo': 'font-size:1.05rem;font-weight:700;color:#78350f;margin:0 0 12px 0;',
    'letterSign': 'text-align:right;font-weight:700;color:#78350f;margin:18px 0 0 0;',
    'before': 'background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;margin:10px 0;',
    'after': 'background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 16px;margin:10px 0;',
    'oneline': 'background:#fefce8;border:1px solid #fde68a;border-radius:12px;padding:16px 18px;margin:16px 0;',
    'checklist': 'background:#f0f9ff;border:1px solid #bae6fd;border-radius:12px;padding:14px 18px 6px;margin:16px 0;',
    'keypoints': 'background:#f5f3ff;border:1px solid #ddd6fe;border-radius:12px;padding:16px 18px;margin:16px 0;',
    'noteNum': 'font-weight:800;color:#3b82f6;margin-right:6px;',
    'diaryDate': 'font-size:0.95rem;font-weight:700;color:#64748b;margin:0 0 8px 0;',
}
LAYOUTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layouts.json')
VOID = {'br', 'img', 'hr', 'meta', 'link', 'input'}


def style_for(tag, cls, stack, has_faq_card):
    """스튜디오 stylize()와 같은 규칙: 클래스·부모에 따라 인라인 스타일을 고른다. 이미 style이 있으면 유지(ul/ol은 덮어씀)."""
    c = set(cls.split())
    parents = [(t, set(k.split())) for t, k in stack]
    parent = parents[-1] if parents else (None, set())
    inside = lambda name: any(name in k for _, k in parents)
    if tag == 'p':
        for k, v in (('lead-intro', 'lead'), ('faq-q', 'faqQ'), ('faq-a', 'faqA'), ('sec-num', 'secNum'),
                     ('letter-to', 'letterTo'), ('letter-sign', 'letterSign'), ('diary-date', 'diaryDate')):
            if k in c:
                return ST[v]
        return ST['p']
    if tag == 'h2':
        if parent[0] == 'section' and 'faq-card' in parent[1]:
            return ST['faqH2']
        if parent[0] == 'section' and 'post-card' in parent[1]:
            return ST['h2']
        return ST['h2plain']
    if tag == 'h3':
        return ST['h3']
    if tag == 'section' and 'post-card' in c:
        return ST['card']
    if tag == 'div':
        for k, v in (('card-body', 'body'), ('summary-card', 'summary'), ('voice-a', 'voiceA'), ('voice-b', 'voiceB'),
                     ('letter', 'letter'), ('before', 'before'), ('after', 'after'), ('oneline', 'oneline'),
                     ('checklist', 'checklist'), ('keypoints', 'keypoints')):
            if k in c:
                return ST[v]
        if 'faq-item' in c:
            return '' if has_faq_card else ST['faqItem']
    if 'voice-name' in c:
        return ST['voiceNameA'] if inside('voice-a') else ST['voiceNameB'] if inside('voice-b') else ''
    if tag == 'span' and 'note-num' in c:
        return ST['noteNum']
    if tag in ('ul', 'ol'):
        return ST['list']
    if tag == 'li':
        return ST['li']
    if tag == 'a':
        return ST['a']
    return ''


class _Styler(HTMLParser):
    def __init__(self, has_faq_card):
        super().__init__(convert_charrefs=False)
        self.out, self.stack, self.faq = [], [], has_faq_card

    def _tag(self, tag, attrs, close):
        d = dict(attrs)
        if tag in ('script', 'style', 'iframe', 'link'):
            return
        css = style_for(tag, d.get('class') or '', self.stack, self.faq)
        if css and (not d.get('style') or tag in ('ul', 'ol')):
            d['style'] = css
        parts = ''.join(' %s' % k if v is None else ' %s="%s"' % (k, v.replace('"', '&quot;')) for k, v in d.items())
        self.out.append('<%s%s%s>' % (tag, parts, ' /' if close else ''))
        if not close and tag not in VOID:
            self.stack.append((tag, d.get('class') or ''))

    def handle_starttag(self, tag, attrs): self._tag(tag, attrs, False)
    def handle_startendtag(self, tag, attrs): self._tag(tag, attrs, True)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        self.out.append('</%s>' % tag)

    def handle_data(self, d): self.out.append(d)
    def handle_entityref(self, n): self.out.append('&%s;' % n)
    def handle_charref(self, n): self.out.append('&#%s;' % n)


def stylize(h):
    p = _Styler('faq-card' in h)
    p.feed(h)
    p.close()
    return ''.join(p.out).strip()


def pick_layout(recent):
    layouts = json.load(open(LAYOUTS_PATH, encoding='utf-8'))
    pool = [l for l in layouts if l['id'] not in recent] or layouts
    return random.choice(pool)


def main():
    src, out = sys.argv[1], sys.argv[2]
    extra = sys.argv[3:] + [''] * 8
    category, tags, pq, palt, pcap, comment, layout, styles = extra[:8]
    layout = (layout or 'A').strip().upper()
    t = open(src, encoding='utf-8').read()
    title = re.search(r'^# (.+)$', t, re.M).group(1).strip()
    body = t.split('```html')[1].split('```')[0].strip()
    thread_part = t.split('## 쓰레드(Threads)')[1].split('```')[1].strip()
    thread = '\n'.join(l for l in thread_part.split('\n') if 'goldjade0419.com' not in l).strip()
    now = int(time.time() * 1000)
    doc = {
        'title': title, 'category': category, 'styles': styles, 'tags': tags,
        'date': time.strftime('%Y-%m-%d'), 'topic': '', 'concept': '', 'query': '',
        'expHint': '', 'thoughtHint': '', 'sourceTitle': '', 'sourceUrl': '',
        'refMemo': '월요일 루프 초안. 원본 노트: ' + src, 'refExperience': '', 'refThoughts': '',
        'bodyHtml': stylize(body), 'threadText': thread, 'commentText': comment,
        'photoQuery': pq, 'photoUrl': '', 'photoPage': '', 'photoAlt': palt, 'photoCaption': pcap,
        'layout': layout, 'done': {str(i): False for i in range(1, 7)}, 'createdAt': now, 'updatedAt': now,
    }
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(title, len(doc['bodyHtml']))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--pick-layout':
        recent = [x.strip().upper() for x in (sys.argv[2] if len(sys.argv) > 2 else '').split(',') if x.strip()]
        l = pick_layout(recent[:3])
        print('형식 %s · %s%s\n%s\n\n[HTML 뼈대]\n%s' % (l['id'], l['name'], ' (FAQ 포함)' if l['faq'] else '', l['desc'], l['html']))
    else:
        main()
