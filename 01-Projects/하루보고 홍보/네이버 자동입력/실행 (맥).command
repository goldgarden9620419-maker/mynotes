#!/bin/bash
# 하루보고 네이버 반자동 입력 — 맥용 실행 파일 (더블클릭)
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] 파이썬이 없습니다. https://www.python.org/downloads/ 에서 설치 후 다시 실행해 주세요."
  read -r -p "Enter를 누르면 닫힙니다." _; exit 1
fi
VENV="$HOME/.harubogo-naver-venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
echo "필요한 프로그램 확인 중... (처음 한 번은 1~2분 걸립니다)"
"$VENV/bin/pip" install --quiet --disable-pip-version-check --upgrade playwright pyperclip
"$VENV/bin/python" naver_post.py "$@"
read -r -p "Enter를 누르면 창이 닫힙니다." _
