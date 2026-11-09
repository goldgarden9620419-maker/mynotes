#!/usr/bin/env bash
# 새 클라우드 세션에서 Codex CLI(ChatGPT 계정 로그인 방식)를 준비한다. 토큰은 출력하지 않는다.
# 환경 설정의 "설정 스크립트(setup script)"에서 한 줄로 호출: bash scripts/setup-codex.sh
set -u
command -v codex >/dev/null 2>&1 || npm install -g @openai/codex >/dev/null 2>&1 || { echo "[codex] 설치 실패"; exit 1; }
# 로그인 정보는 저장소에 넣지 않는다. 환경 시크릿 CODEX_AUTH_JSON(jade PC의 ~/.codex/auth.json 내용)이 있으면 복원.
if [ -n "${CODEX_AUTH_JSON:-}" ] && [ ! -s "$HOME/.codex/auth.json" ]; then
  mkdir -p "$HOME/.codex" && umask 077 && printf '%s' "$CODEX_AUTH_JSON" > "$HOME/.codex/auth.json"
fi
codex login status 2>&1 | head -1
