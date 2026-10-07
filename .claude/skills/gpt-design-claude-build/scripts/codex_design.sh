#!/usr/bin/env bash
# codex_design.sh — Codex CLI(ChatGPT 로그인)에게 "설계만" 맡기는 래퍼.
# Claude Code가 Bash로 호출한다. Codex는 read-only 샌드박스라 파일을 고치지 못한다.
#
# 사용법:
#   codex_design.sh <brief.md> <out_dir> [--mode code|content] [--round N]
#                   [--feedback review.md] [--workdir DIR] [--model MODEL]
# 결과:
#   <out_dir>/plan.r<N>.md  (Codex의 최종 답변)
#   <out_dir>/codex.r<N>.log (진행 로그 — 실패 시 확인용)
#
# 종료 코드:
#   0 성공 · 2 인자 오류 · 10 codex 미설치 · 11 로그인 안 됨
#   12 API 키 로그인(추가 요금 위험) · 13 빈 결과 · 14 codex 실행 실패/한도 초과/시간 초과
# macOS 기본 bash 3.2와 Windows Git Bash(Claude Code의 Bash 도구)에서 모두 돌도록 작성.

set -euo pipefail

die() { echo "[codex_design] $2" >&2; exit "$1"; }

# ---------- 인자 파싱 ----------
[ $# -ge 2 ] || die 2 "사용법: codex_design.sh <brief.md> <out_dir> [--mode code|content] [--round N] [--feedback review.md] [--workdir DIR] [--model MODEL]"
BRIEF="$1"; OUT_DIR="$2"; shift 2
MODE="code"; ROUND=1; FEEDBACK=""; WORKDIR="$(pwd)"; MODEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode)     MODE="${2:-}"; shift 2 ;;
    --round)    ROUND="${2:-}"; shift 2 ;;
    --feedback) FEEDBACK="${2:-}"; shift 2 ;;
    --workdir)  WORKDIR="${2:-}"; shift 2 ;;
    --model)    MODEL="${2:-}"; shift 2 ;;
    *) die 2 "알 수 없는 옵션: $1" ;;
  esac
done
[ -f "$BRIEF" ] || die 2 "brief 파일이 없습니다: $BRIEF"
[ -d "$WORKDIR" ] || die 2 "workdir가 없습니다: $WORKDIR"
case "$MODE" in code|content) ;; *) die 2 "--mode는 code 또는 content" ;; esac
case "$ROUND" in ''|*[!0-9]*) die 2 "--round는 숫자" ;; esac
if [ -n "$FEEDBACK" ] && [ ! -f "$FEEDBACK" ]; then die 2 "feedback 파일이 없습니다: $FEEDBACK"; fi
mkdir -p "$OUT_DIR"

PLAN="$OUT_DIR/plan.r$ROUND.md"
LOG="$OUT_DIR/codex.r$ROUND.log"
PREV_PLAN="$OUT_DIR/plan.r$((ROUND - 1)).md"

# ---------- 사전 점검: 설치 + ChatGPT 로그인 ----------
command -v codex >/dev/null 2>&1 || die 10 "codex가 없습니다. 설치: npm install -g @openai/codex  (또는 brew install codex)"

# API 키 환경변수가 섞이면 종량 과금될 수 있으니 이 프로세스에서 제거한다.
unset OPENAI_API_KEY CODEX_API_KEY 2>/dev/null || true

STATUS="$(codex login status 2>&1 || true)"
if echo "$STATUS" | grep -qi "not logged in"; then
  die 11 "Codex 로그인이 필요합니다. 터미널에서: codex login  → 'Sign in with ChatGPT' 선택"
fi
if ! echo "$STATUS" | grep -qi "chatgpt"; then
  if [ "${ALLOW_API_KEY:-0}" != "1" ]; then
    die 12 "Codex가 ChatGPT가 아닌 방식으로 로그인돼 있습니다(API 키 등). 추가 요금을 막기 위해 중단합니다. 'codex logout && codex login'으로 ChatGPT 로그인 후 다시 실행하세요. (API 키 사용을 원하면 ALLOW_API_KEY=1)"
  fi
fi

# ---------- 프롬프트 만들기 ----------
PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/codex_prompt.XXXXXX")"
trap 'rm -f "$PROMPT_FILE"' EXIT

if [ "$MODE" = "code" ]; then
  cat > "$PROMPT_FILE" <<'EOF'
너는 이 저장소의 "설계 담당"이다. 코드는 Claude가 쓰고, 너는 설계서만 쓴다.
규칙:
- 파일을 만들거나 고치지 마라. 필요한 파일은 읽어서 근거로 써라.
- 실제 코드 대신 시그니처·의사코드만(블록당 15줄 이내).
- 저장소에서 확인한 사실과 추측을 구분해 추측에는 (가정)을 붙여라.
- 한국어로, 아래 제목을 순서대로 모두 채워라.

## 1. 목표와 범위 (안 하는 것 포함)
## 2. 확인한 현재 구조 (파일 경로 근거)
## 3. 설계 결정 (대안 1개와 고르지 않은 이유)
## 4. 파일별 변경 계획 (경로 | 새로/수정 | 무엇을)
## 5. 데이터·인터페이스 (타입, 함수 시그니처, API)
## 6. 구현 순서 (각 단계 완료 기준)
## 7. 테스트 계획 (실행 명령 포함)
## 8. 리스크와 되돌리기 방법
## 9. 열린 질문 (없으면 "없음")
EOF
else
  cat > "$PROMPT_FILE" <<'EOF'
너는 인스타 릴스 "원고 설계 담당"이다. 최종 원고는 Claude가 쓴다.
규칙:
- 파일을 만들거나 고치지 마라.
- brief에 없는 성과·숫자·경험을 절대 지어내지 말고 [내 숫자] [내 경험]으로 비워라.
- 훅 틀과 구조는 brief의 떡상 릴스 분석에 근거가 있는 것만 써라. 근거 릴스 링크를 붙여라.
- 25~35초(약 125~175자) 기준. 한국어로, 아래 제목을 모두 채워라.

## 1. 훅 3안 (첫 3초 멘트 원문 | 훅 방식 | 근거 릴스)
## 2. 추천 훅과 이유
## 3. 구간 설계 (몇 초 | 역할 | 멘트 요지 | 화면 | 자막)
## 4. 댓글 유도 문장 (댓글에 ○○ 남겨주시면 ○○ 보내드릴게요)
## 5. 빈칸으로 둔 곳 목록
EOF
fi

{
  printf '\n\n---\n# 요청(brief)\n\n'; cat "$BRIEF"
  if [ -n "$FEEDBACK" ]; then
    if [ -f "$PREV_PLAN" ]; then printf '\n\n---\n# 너의 이전 설계 (round %s)\n\n' "$((ROUND - 1))"; cat "$PREV_PLAN"; fi
    printf '\n\n---\n# Claude 검증 결과 — 지적된 항목을 모두 반영해 설계서 전체를 다시 써라\n\n'; cat "$FEEDBACK"
  fi
} >> "$PROMPT_FILE"

# ---------- 실행 (read-only, 시간 제한) ----------
TIMEOUT_SEC="${CODEX_TIMEOUT:-900}"
TO=""
# GNU timeout만 쓴다 (Windows의 timeout.exe는 다른 프로그램이라 --version 검사로 걸러냄)
if timeout --version >/dev/null 2>&1; then TO="timeout $TIMEOUT_SEC"
elif gtimeout --version >/dev/null 2>&1; then TO="gtimeout $TIMEOUT_SEC"; fi

MODEL_ARGS=""
[ -n "$MODEL" ] && MODEL_ARGS="--model $MODEL"

echo "[codex_design] round $ROUND · mode $MODE · Codex 설계 요청 중 (수 분 걸릴 수 있음)…" >&2
set +e
# shellcheck disable=SC2086
$TO codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  --color never \
  -C "$WORKDIR" \
  $MODEL_ARGS \
  -o "$PLAN" \
  - < "$PROMPT_FILE" > "$LOG" 2>&1
RC=$?
set -e

if [ $RC -ne 0 ]; then
  echo "----- codex 로그 마지막 20줄 -----" >&2; tail -n 20 "$LOG" >&2
  if [ $RC -eq 124 ]; then die 14 "시간 초과(${TIMEOUT_SEC}s). CODEX_TIMEOUT을 늘리거나 brief를 줄이세요."; fi
  if grep -qiE "usage limit|rate limit|quota" "$LOG"; then die 14 "ChatGPT 플랜의 Codex 사용 한도에 걸렸습니다. 한도 리셋 후 다시 실행하세요."; fi
  die 14 "codex exec 실패 (exit $RC). 로그: $LOG"
fi
[ -s "$PLAN" ] || die 13 "Codex가 빈 설계를 돌려줬습니다. 로그: $LOG"

echo "[codex_design] 완료 → $PLAN" >&2
echo "$PLAN"
