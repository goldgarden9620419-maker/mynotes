#!/usr/bin/env python3
"""수능잼 문제/확언 중복 검사.

매일 새 문제를 problems.json에 넣기 **전에** 실행해서, 기존 항목과 지문·수식·소재가
겹치는지 확인한다. (매 실행이 이전 맥락 없이 시작되어 같은 소재를 반복 생성하던 문제 방지용)

사용법 (프로젝트 루트 01-Projects/suneungjam-site 에서):

  python3 scripts/check_duplicates.py topics
      이미 쓴 소재 목록 출력 (영어 지문 첫머리, 수학 문제 지시문, 확언). 작성 전에 훑어본다.

  python3 scripts/check_duplicates.py check <후보.json>
      후보 파일 형식: {"problems": [문제 객체...], "affirmation": {확언 객체}}
      (affirmation은 생략 가능, 문제 배열만 있는 파일도 허용)
      겹침이 하나라도 있으면 종료 코드 1, 없으면 0.

  python3 scripts/check_duplicates.py audit
      기존 problems.json 안에서 서로 겹치는 항목을 날짜순으로 보고 (점검용).
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = ROOT / "data" / "problems.json"
AFFIRMATIONS = ROOT / "data" / "affirmations.json"

# 임계값: 이 값 이상이면 "겹침"으로 본다.
EN_JACCARD = 0.20      # 영어 지문 내용어 집합의 자카드 유사도
EN_RARE_DF = 6         # 기존 지문 중 이 개수 이하에만 나오는 단어를 "소재어"로 본다
EN_SHARED_MIN = 5      # 또는 공유 소재어가 이 개수 이상
MATH_RATIO = 0.97      # 수학 지시문(공백 제거) 문자열 유사도 — 숫자만 다른 변형은 허용, 사실상 같은 문제만 잡는다
AFF_RATIO = 0.62       # 확언 main 두 줄 문자열 유사도

STOP = set("""
about above after again against almost along already also although always among another
around because become becomes before being below between both cannot could different
during each either enough every example first found from have having however into itself
just known less like likely made make makes many might more most much must never often
once only other others over people rather really result same should simply since some
something still such than that their them then there therefore these they thing things
this those though through thus time today under until upon very were what when where
whether which while will with within without would years your study studies research
researchers scientists found suggest suggests actually usually whose instead even
""".split())


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def en_text(item):
    return " ".join([item.get("passage", ""), item.get("givenSentence", "")])


def content_words(text):
    text = re.sub(r"\[/?u\]", " ", text)
    words = re.findall(r"[a-z]{5,}", text.lower())
    out = set()
    for w in words:
        if w in STOP:
            continue
        # 아주 단순한 어간 처리 (복수형/시제 차이 흡수)
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def norm_math(text):
    return re.sub(r"\s+", "", text)


def build_df(items):
    df = {}
    for it in items:
        if it.get("subject") == "english":
            for w in content_words(en_text(it)):
                df[w] = df.get(w, 0) + 1
    return df


def en_similar(cand, existing, df, n_docs):
    cw = content_words(en_text(cand))
    hits = []
    for ex in existing:
        if ex.get("subject") != "english":
            continue
        ew = content_words(en_text(ex))
        shared = cw & ew
        if not shared:
            continue
        jac = len(shared) / len(cw | ew)
        # 소재를 드러내는 드문 단어(coral, algae 등)만 센 공유 개수
        rare = sorted((w for w in shared if df.get(w, 0) <= EN_RARE_DF), key=lambda w: (df.get(w, 0), w))
        if jac >= EN_JACCARD or len(rare) >= EN_SHARED_MIN:
            hits.append((jac, ex, rare))
    hits.sort(key=lambda h: -h[0])
    return hits


def math_similar(cand, existing):
    c = norm_math(cand.get("prompt", ""))
    hits = []
    for ex in existing:
        if ex.get("subject") != "math":
            continue
        e = norm_math(ex.get("prompt", ""))
        if c == e:
            hits.append((1.0, ex))
            continue
        sm = difflib.SequenceMatcher(None, c, e)
        if sm.quick_ratio() < MATH_RATIO:
            continue
        r = sm.ratio()
        if r >= MATH_RATIO:
            hits.append((r, ex))
    hits.sort(key=lambda h: -h[0])
    return hits


def aff_text(a):
    return re.sub(r"[\s,.]", "", "".join(a.get("main", [])))


def aff_similar(cand, existing):
    c = aff_text(cand)
    hits = []
    for ex in existing:
        r = difflib.SequenceMatcher(None, c, aff_text(ex)).ratio()
        if r >= AFF_RATIO:
            hits.append((r, ex))
    hits.sort(key=lambda h: -h[0])
    return hits


def report_problem(cand, existing, df, n_docs):
    """겹침이 있으면 출력하고 True 반환."""
    if cand.get("subject") == "english":
        hits = en_similar(cand, existing, df, n_docs)
        if hits:
            print(f"[겹침] {cand.get('id')} ({cand.get('type')})")
            for jac, ex, rare in hits[:4]:
                print(f"    ↔ {ex['id']} ({ex['type']}) 유사도 {jac:.2f} / 공유 단어: {', '.join(rare[:12])}")
                print(f"      기존 지문: {en_text(ex)[:110].strip()}…")
            return True
    else:
        hits = math_similar(cand, existing)
        if hits:
            print(f"[겹침] {cand.get('id')} ({cand.get('type')})")
            for r, ex in hits[:4]:
                print(f"    ↔ {ex['id']} 유사도 {r:.2f}: {ex['prompt']}")
            return True
    return False


def cmd_topics():
    problems = load(PROBLEMS)
    df = build_df(problems)
    print("== 영어: 이미 쓴 지문의 소재어 (지문마다 가장 드문 단어 4개, 어간 형태) ==")
    line = []
    for it in problems:
        if it.get("subject") == "english":
            ws = sorted(content_words(en_text(it)), key=lambda w: (df.get(w, 0), w))[:4]
            line.append("/".join(ws))
            if len(line) == 4:
                print("  ".join(line))
                line = []
    if line:
        print("  ".join(line))
    print("\n== 수학: 이미 2번 이상 나온 문제 (다시 내지 말 것) ==")
    count = {}
    for it in problems:
        if it.get("subject") == "math":
            count.setdefault(norm_math(it["prompt"]), [0, it])[0] += 1
    for n, it in sorted(count.values(), key=lambda v: -v[0]):
        if n >= 2:
            print(f"{n}회 {it['type']} | {it['prompt'][:90]}")
    print("\n== 확언 ==")
    for a in load(AFFIRMATIONS):
        print(f"{a['date'][5:]} | {' '.join(a.get('main', []))}")


def cmd_check(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        cands, aff = data, None
    else:
        cands, aff = data.get("problems", []), data.get("affirmation")
    cand_ids = {c.get("id") for c in cands}
    existing = [p for p in load(PROBLEMS) if p.get("id") not in cand_ids]
    df = build_df(existing)
    n_docs = sum(1 for p in existing if p.get("subject") == "english")
    bad = 0
    for i, c in enumerate(cands):
        # 기존 항목 + 같은 후보 묶음의 앞선 항목과 비교
        if report_problem(c, existing + cands[:i], df, n_docs):
            bad += 1
    if aff:
        olds = [a for a in load(AFFIRMATIONS) if a.get("date") != aff.get("date")]
        hits = aff_similar(aff, olds)
        if hits:
            bad += 1
            print(f"[겹침] 확언: {' '.join(aff.get('main', []))}")
            for r, ex in hits[:4]:
                print(f"    ↔ {ex['date']} 유사도 {r:.2f}: {' '.join(ex.get('main', []))}")
    if bad:
        print(f"\n결과: {bad}개 항목이 기존 항목과 겹칩니다. 해당 항목만 다른 소재/수식으로 다시 만드세요.")
        return 1
    print(f"결과: 겹침 없음 (문제 {len(cands)}개{', 확언 1개' if aff else ''} 검사)")
    return 0


def cmd_audit():
    problems = load(PROBLEMS)
    df = build_df(problems)
    n_docs = sum(1 for p in problems if p.get("subject") == "english")
    bad = 0
    for i, c in enumerate(problems):
        if report_problem(c, problems[:i], df, n_docs):
            bad += 1
    print(f"\n전체 {len(problems)}개 중 앞선 항목과 겹치는 항목: {bad}개")
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "topics":
        cmd_topics()
        return 0
    if len(argv) >= 3 and argv[1] == "check":
        return cmd_check(argv[2])
    if len(argv) >= 2 and argv[1] == "audit":
        return cmd_audit()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
