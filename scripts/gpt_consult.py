#!/usr/bin/env python3
"""GPT 상의용: brief 파일을 OpenAI API로 보내 의견을 받는다. (jade 결정 2026-11-20: Codex 로그인 대신 API 사용)

사용: python3 scripts/gpt_consult.py <brief.md> [--model gpt-5.5] [--out 답변.md]
- 클라우드 환경에서는 api.openai.com 네트워크 시크릿이 인증 헤더를 자동 첨부한다. 키를 코드·노트·출력에 넣지 않는다.
- 회당 1~2번만 호출한다(요금이 나가는 호출). 답은 검증 없이 따르지 않고 성과 표와 대조한다.
"""
import argparse, json, os, sys, urllib.request, urllib.error

SYSTEM = ("당신은 한국어 인스타그램 릴스 기획을 검토하는 동료입니다. 주어진 성과 숫자와 기획안만 근거로, "
          "주제 선택과 첫 2초 구성에 대해 구체적인 의견을 한국어로 짧게 주세요. "
          "근거 없는 숫자나 경험을 지어내지 말고, 확신이 없으면 그렇다고 말하세요.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("--model", default=os.environ.get("GPT_CONSULT_MODEL", "gpt-5.5"))
    ap.add_argument("--out")
    ap.add_argument("--max-tokens", type=int, default=4000)
    a = ap.parse_args()
    brief = open(a.brief, encoding="utf-8").read()
    body = {"model": a.model, "max_completion_tokens": a.max_tokens,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": brief}]}
    # 프록시가 실제 키로 바꿔 넣는다. 로컬에서는 OPENAI_API_KEY 환경 변수를 쓴다.
    key = os.environ.get("OPENAI_API_KEY", "proxy-injected")
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:400]
        print(f"[gpt_consult] 실패 HTTP {e.code}: {msg}", file=sys.stderr); sys.exit(2)
    except Exception as e:
        print(f"[gpt_consult] 실패: {e}", file=sys.stderr); sys.exit(2)
    text = (d["choices"][0]["message"].get("content") or "").strip()
    u = d.get("usage", {})
    if not text:
        print("[gpt_consult] 빈 답변 (max-tokens를 늘려 보세요)", file=sys.stderr); sys.exit(3)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    print(text)
    print(f"\n[gpt_consult] model={d.get('model')} 입력 {u.get('prompt_tokens')} · 출력 {u.get('completion_tokens')} 토큰", file=sys.stderr)

if __name__ == "__main__":
    main()
