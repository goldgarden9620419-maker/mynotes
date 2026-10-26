"""황금정원 승인글 ChatGPT 교차 검토.

사용법: python3 gpt_review.py <post.json> [출력.json]
  post.json: 스튜디오 posts 문서 형식(title, bodyHtml, refExperience, refThoughts, sourceTitle 사용)
  환경 변수 OPENAI_API_KEY 필요. 모델은 GPT_REVIEW_MODEL(기본 gpt-5.5).
결과: 점수와 함께 AI 티 나는 문장, 애드센스 위험, 사실 확인 필요 항목을 JSON으로 출력한다.
"""
import html, json, os, re, sys, urllib.request

MODEL = os.environ.get('GPT_REVIEW_MODEL', 'gpt-5.5')
RUBRIC = """너는 한국 티스토리 블로그를 구글 애드센스 승인 기준으로 검토하는 편집자다. 아래 글을 읽고 JSON만 출력하라.
검토 기준:
1) AI가 쓴 티: 기계적인 대칭 구조, 뻔한 연결어("결론적으로", "다양한", "중요합니다", "~에 대해 알아보겠습니다"), 모든 문단 길이가 비슷함, 구체성 없는 일반론, 과장된 감탄, 사람이라면 안 쓸 매끈한 문장. 실제 문장을 인용하고 사람 말투로 고친 예시를 준다.
2) 애드센스 적합성: 필자의 직접 경험·의견이 충분히 녹아 있는지(독창성), 얇은 콘텐츠·짜깁기 위험, 오해 소지 있는 건강·금융 단정, 출처 표기.
3) 사실 확인: 연구·수치·연도·인명 중 틀렸거나 과장됐을 가능성이 있는 것.
4) 필자가 준 경험·생각과 본문이 어긋나거나 지어낸 경험이 들어갔는지.
출력 형식:
{"score":0-100,"verdict":"한 줄 총평","ai_tells":[{"quote":"본문 그대로","why":"이유","fix":"고친 문장"}],"adsense_risks":["..."],"fact_checks":[{"claim":"...","note":"..."}],"experience_mismatch":["..."],"strengths":["..."]}
ai_tells는 가장 심한 것부터 최대 8개."""


def text_of(h):
    h = re.sub(r'<br\s*/?>', '\n', h)
    h = re.sub(r'</(p|h2|h3|li|div|section)>', '\n', h)
    return re.sub(r'\n{3,}', '\n\n', html.unescape(re.sub(r'<[^>]+>', '', h))).strip()


def review(p):
    user = '제목: %s\n참고 자료: %s\n\n[필자가 직접 쓴 경험]\n%s\n\n[필자가 직접 쓴 생각/비판]\n%s\n\n[검토할 본문]\n%s' % (
        p.get('title', ''), p.get('sourceTitle', ''), p.get('refExperience', ''), p.get('refThoughts', ''), text_of(p.get('bodyHtml', '')))
    body = json.dumps({'model': MODEL, 'messages': [{'role': 'system', 'content': RUBRIC}, {'role': 'user', 'content': user}],
                       'response_format': {'type': 'json_object'}}).encode()
    req = urllib.request.Request('https://api.openai.com/v1/chat/completions', data=body,
                                 headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit('ChatGPT 검토 실패: %s %s' % (e.code, e.read().decode()[:300]))
    res = json.loads(out['choices'][0]['message']['content'])
    res['model'] = out.get('model', MODEL)
    return res


if __name__ == '__main__':
    if not os.environ.get('OPENAI_API_KEY'):
        sys.exit('OPENAI_API_KEY가 없습니다.')
    p = json.load(open(sys.argv[1], encoding='utf-8'))
    res = review(p)
    s = json.dumps(res, ensure_ascii=False, indent=2)
    if len(sys.argv) > 2:
        open(sys.argv[2], 'w', encoding='utf-8').write(s)
    print(s)
