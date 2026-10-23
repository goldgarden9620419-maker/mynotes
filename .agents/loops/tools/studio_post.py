"""황금정원 루프 초안 노트를 '블로그+스레드 발행 스튜디오' posts 문서(JSON)로 변환한다.

사용법: python3 studio_post.py <노트.md> <출력.json> [category] [tags] [photoQuery] [photoAlt] [photoCaption] [commentText]
결과 JSON을 ArtifactData set (url=STUDIO_URL, collection=posts, doc_id=p-YYYYMMDD-slug)으로 넣는다.
스튜디오는 bodyHtml을 인라인 스타일로 저장하므로, 카드형 클래스 HTML에 스튜디오와 같은 스타일을 입힌다.
"""
import json, re, sys, time

STUDIO_URL = "https://claude.ai/artifact/JX5794Nywjmji4B8NbwDiH"
ST = {
    'lead': 'font-size:1.05rem;line-height:1.95;color:#1f2937;margin:0 0 10px 0;',
    'p': 'font-size:1rem;line-height:1.95;color:#374151;margin:0 0 14px 0;',
    'card': 'background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,0.05);margin:22px 0;overflow:hidden;',
    'h2': 'font-size:1.3rem;font-weight:700;color:#1e3a8a;margin:0;padding:18px 22px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border-bottom:1px solid #e5e7eb;',
    'faqH2': 'font-size:1.3rem;font-weight:700;margin:0;padding:18px 22px;background:linear-gradient(135deg,#f5f3ff,#ede9fe);color:#5b21b6;border-bottom:1px solid #e5e7eb;',
    'body': 'padding:20px 22px;',
    'summary': 'background:#f0f7ff;border-left:4px solid #3b82f6;border-radius:8px;padding:14px 16px;margin-top:16px;font-size:0.95rem;line-height:1.8;color:#1e40af;',
    'list': 'list-style-type:disc;margin:10px 0 14px 22px;padding:0;',
    'li': 'margin:6px 0;line-height:1.8;color:#374151;font-size:1rem;',
    'a': 'color:#2563eb;text-decoration:underline;',
    'faqQ': 'font-size:1rem;line-height:1.85;color:#5b21b6;margin:0 0 6px 0;',
    'faqA': 'font-size:1rem;line-height:1.9;color:#374151;margin:0;',
}


def stylize(h):
    h = re.sub(r'(<section class="post-card faq-card">\s*)<h2 data-ke-size="size26">',
               lambda m: m.group(1) + '<h2 data-ke-size="size26" style="%s">' % ST['faqH2'], h)
    pairs = [
        ('<section class="post-card faq-card">', '<section class="post-card faq-card" style="%s">' % ST['card']),
        ('<h2 data-ke-size="size26">', '<h2 data-ke-size="size26" style="%s">' % ST['h2']),
        ('<section class="post-card">', '<section class="post-card" style="%s">' % ST['card']),
        ('<div class="card-body">', '<div class="card-body" style="%s">' % ST['body']),
        ('<div class="summary-card">', '<div class="summary-card" style="%s">' % ST['summary']),
        ('<ul style="list-style-type: disc;" data-ke-list-type="disc">', '<ul data-ke-list-type="disc" style="%s">' % ST['list']),
        ('<li data-ke-size="size16">', '<li data-ke-size="size16" style="%s">' % ST['li']),
        ('<p class="lead-intro" data-ke-size="size16">', '<p class="lead-intro" data-ke-size="size16" style="%s">' % ST['lead']),
        ('<p class="faq-q" data-ke-size="size16">', '<p class="faq-q" data-ke-size="size16" style="%s">' % ST['faqQ']),
        ('<p class="faq-a" data-ke-size="size16">', '<p class="faq-a" data-ke-size="size16" style="%s">' % ST['faqA']),
        ('<p data-ke-size="size16">', '<p data-ke-size="size16" style="%s">' % ST['p']),
        ('rel="noopener noreferrer">', 'rel="noopener noreferrer" style="%s">' % ST['a']),
    ]
    for a, b in pairs:
        h = h.replace(a, b)
    return h


def main():
    src, out = sys.argv[1], sys.argv[2]
    extra = sys.argv[3:] + [''] * 6
    category, tags, pq, palt, pcap, comment = extra[:6]
    t = open(src, encoding='utf-8').read()
    title = re.search(r'^# (.+)$', t, re.M).group(1).strip()
    body = t.split('```html')[1].split('```')[0].strip()
    thread_part = t.split('## 쓰레드(Threads)')[1].split('```')[1].strip()
    thread = '\n'.join(l for l in thread_part.split('\n') if 'goldjade0419.com' not in l).strip()
    now = int(time.time() * 1000)
    doc = {
        'title': title, 'category': category, 'styles': '', 'tags': tags,
        'date': time.strftime('%Y-%m-%d'), 'topic': '', 'concept': '', 'query': '',
        'expHint': '', 'thoughtHint': '', 'sourceTitle': '', 'sourceUrl': '',
        'refMemo': '월요일 루프 초안. 원본 노트: ' + src, 'refExperience': '', 'refThoughts': '',
        'bodyHtml': stylize(body), 'threadText': thread, 'commentText': comment,
        'photoQuery': pq, 'photoUrl': '', 'photoPage': '', 'photoAlt': palt, 'photoCaption': pcap,
        'layout': 'A', 'done': {str(i): False for i in range(1, 7)}, 'createdAt': now, 'updatedAt': now,
    }
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(title, len(doc['bodyHtml']))


if __name__ == '__main__':
    main()
