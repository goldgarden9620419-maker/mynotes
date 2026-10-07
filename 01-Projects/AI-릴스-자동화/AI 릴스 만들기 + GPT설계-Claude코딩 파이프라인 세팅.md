# AI 릴스 만들기 + GPT설계 → Claude검증 → Claude코딩 파이프라인 세팅 (v2, Windows)

- 작성일: 2026-10-07
- 환경: Windows PC (`C:\Users\AP`), Claude Code + Codex CLI 0.160 (ChatGPT 로그인) — 10/5 세팅 완료 상태 기준
- 이전 노트: [[ChatGPT + Claude 협업 워크플로우 설정 (Codex CLI 연동)]] (v1: CLAUDE.md 규칙 방식)
- 참고: [디립다 연구소 · AI로 릴스 만드는 법 (2026-09-29)](https://deeripda-marketing-hub.vercel.app/archive/practice/claude-reels-maker) · [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) · [Codex CLI 문서](https://learn.chatgpt.com/docs/codex/cli)
- 스킬 위치(이 vault): `.claude/skills/reels-maker/` · `.claude/skills/gpt-design-claude-build/`

## 한 줄 결론
v1(`codex exec` + CLAUDE.md 규칙)은 그대로 살리고, **스킬 2개로 업그레이드**한다.
- 릴스: **reels-maker** (가이드 원문 스킬 + Windows 보완 + GPT 교차검토 단계)
- 코딩: **gpt-design-claude-build** (Codex read-only 강제 · 실제 파일 대조 검증 · 최대 3라운드 · API 키 로그인 차단)

## v1 → v2 무엇이 좋아지나
| 항목 | v1 (10/5) | v2 (오늘) |
|---|---|---|
| Codex 권한 | 기본값 | `--sandbox read-only` 강제 → Codex가 파일을 못 고침 |
| 검증 | Claude가 표로 정리 | 실제 파일·함수 존재 대조 6항목 ✅/❌ → PASS/REVISE |
| 재설계 | 없음 | ❌ 항목을 Codex에 돌려보내 재설계 (최대 3라운드) |
| 요금 안전 | 수동 확인 | ChatGPT 로그인 아니면 자동 중단 (exit 12) |
| 기록 | `docs/design-*.md` | `.ai-pipeline/<날짜-이름>/` brief·plan.rN·review.rN·summary |
| 범위 | `ai-work` 폴더만 | 전역 스킬 → 어느 폴더에서든 "GPT 설계로 진행해줘" |

## 전체 흐름
```
[릴스]  @핸들 → 내 계정 분석 → 비슷한 계정 10 → 떡상 릴스 20 → 영상 분석(yt-dlp·whisper·ffmpeg)
        → 리포트(훅 TOP3·구조·빈자리·주제 5) → 주제+내 숫자 → 25~35초 원고
        └ (선택) "GPT랑 교차검토" → Codex 훅 3안·구간 설계 → Claude 검증(지어낸 숫자 제거) → Claude 최종 원고

[코딩]  요청 → Claude brief.md → Codex 설계 plan.r1.md (read-only)
        → Claude 검증 review.r1.md ─REVISE→ Codex 재설계 (최대 3라운드)
        → PASS → Claude 구현 + 테스트 → (선택) codex exec review → summary.md
```

## 1회 설치 체크리스트 (PowerShell)

- [ ] **① 스킬 전역 설치** — Obsidian이 이 노트를 pull했다면 스킬 파일도 같이 내려와 있음
  ```powershell
  # vault 위치: C:\Users\AP\Documents\mynotes
  New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
  Copy-Item -Recurse -Force "$HOME\Documents\mynotes\.claude\skills\reels-maker" "$HOME\.claude\skills\"
  Copy-Item -Recurse -Force "$HOME\Documents\mynotes\.claude\skills\gpt-design-claude-build" "$HOME\.claude\skills\"
  Get-ChildItem "$HOME\.claude\skills"    # 두 폴더가 보이면 OK
  ```
  - 안 보이면: Obsidian에서 Git pull 한 번 → `.claude` 폴더는 Obsidian 화면엔 안 보이지만(숨김 폴더) 탐색기에는 있음
- [ ] **② Codex 로그인 상태 확인** (10/5에 완료했으면 확인만)
  ```powershell
  codex login status          # "Logged in using ChatGPT" 이면 OK
  $env:OPENAI_API_KEY         # 아무것도 안 나와야 정상 (나오면 종량 과금 위험)
  ```
- [ ] **③ 릴스 분석 도구** — `cd ~\ai-work` → `claude` 실행 후 붙여넣기
  ```
  릴스 분석에 필요한 도구를 Windows에 설치해줘.
  1. winget으로 yt-dlp(yt-dlp.yt-dlp)와 ffmpeg(Gyan.FFmpeg) 설치.
  2. whisper.cpp 최신 Windows 릴리스(whisper-bin-x64.zip)를 GitHub ggml-org/whisper.cpp에서 받아
     C:\Users\AP\tools\whisper 에 풀고, whisper-cli.exe가 있는 폴더를 사용자 PATH에 추가해.
  3. 모델 ggml-large-v3-turbo-q5_0.bin 을 C:\Users\AP\.cache\whisper 에 받아.
     (https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin)
  4. 관리자 권한이 필요한 단계는 내가 PowerShell에 직접 붙여넣을 명령어를 알려줘.
  5. 새 터미널 기준으로 yt-dlp, ffmpeg, whisper-cli 버전을 확인하고 "설치 끝!"이라고 말해.
  ```
- [ ] **④ Claude in Chrome** — claude.com/ko/claude-in-chrome → Chrome에 추가 → 🧩 고정 → 같은 계정 로그인 → 인스타는 **부계정**으로 직접 로그인
- [ ] **⑤ ai-work\CLAUDE.md 협업 규칙 교체** (v1 1~4단계 블록을 아래로 바꾸기 — 선택이지만 권장)
  ```markdown
  ## ChatGPT(Codex) + Claude 협업 규칙 (v2)
  새 기능·프로젝트 요청은 `gpt-design-claude-build` 스킬 순서로 진행한다.
  - Codex는 read-only 설계만. 코드 작성·수정은 Claude만.
  - 검증은 실제 파일과 대조해 PASS/REVISE, 최대 3라운드.
  - 기록은 프로젝트 폴더의 `.ai-pipeline/`에 남기고, 끝나면 summary를 3줄로 보고.
  ```
- [ ] **⑥ (선택) 공식 플러그인** — Claude Code 입력창에서
  `/plugin marketplace add openai/codex-plugin-cc` → `/plugin install codex@openai-codex` → `/reload-plugins` → `/codex:setup`
  - 쓰임: `/codex:review`(완성 후 리뷰), `/codex:adversarial-review`(설계 반론). 스킬과 같이 써도 충돌 없음.
- [ ] **⑦ Claude 재시작** — `/exit` 후 `claude` (스킬은 새로 켤 때 인식)

## 바로 쓰는 프롬프트
| 상황 | 붙여넣을 문장 |
|---|---|
| 릴스 분석 시작 | `@내핸들 계정으로 릴스 만들어줘.` |
| 원고 받기 | `이 주제로 릴스 원고 써줘. 주제: [주제 또는 추천 번호] / 내 경험·숫자: [한 줄]` |
| 원고 GPT 교차검토 | `이 주제로 GPT랑 교차검토해서 릴스 원고 써줘. 주제: … / 내 숫자: …` |
| 코딩 (기본) | `GPT 설계 → 네 검증 → 네 코딩으로 진행해줘: [만들 것]` |
| 코딩 + 마무리 리뷰 | `설계-검증-코딩으로 진행하고, 끝나면 Codex 리뷰까지 돌려줘: [만들 것]` |
| 이어하기 | `.ai-pipeline/<폴더> 이어서 해줘` / 릴스는 `이어서 해줘` |

## 리스크 / 주의
| 리스크 | 대응 |
|---|---|
| 인스타 경고·차단 | 부계정, 천천히, 아무것도 누르지 않기. 경고 뜨면 그날 중단 → 다음 날 "이어서 해줘" |
| Windows에서 yt-dlp 쿠키 읽기 실패 (크롬 실행 중) | 스킬이 edge/firefox 쿠키 시도 → 안 되면 크롬 잠깐 닫기 |
| Codex 사용 한도 (플랜별 상이) | 스크립트가 감지 시 exit 14 → 리셋 후 재실행 또는 Claude 단독 설계 |
| 권한 질문이 매번 뜸 | 처음에 "항상 허용" 선택 (auto mode면 거의 안 물음) |
| 웹(클라우드) 세션에서 실행 | ChatGPT 로그인·크롬·인스타가 없어 **PC의 Claude Code에서만** 실제 실행 가능 |
| 원고에 숫자 지어내기 | 두 스킬 모두 `[내 숫자]` 빈칸 규칙 강제 |

## 다음 할 일
1. 체크리스트 ①②⑦ (5분) → `GPT 설계 → 네 검증 → 네 코딩으로 진행해줘: todo-app에 마감일 기능 추가` 로 v2 시험
2. ③④ 설치 후 `@내핸들 계정으로 릴스 만들어줘.` (30분~1시간)
3. 리포트 받으면 주제+내 숫자 한 줄로 첫 원고 → 촬영

## 진행 기록
- **2026-10-07 v2 첫 실전 성공** — 과제: todo-app 마감일 기능 (`C:\Users\AP\ai-work\todo-app`)
  - 스킬 전역 복사 → `Successfully loaded skill`, Codex `Logged in using ChatGPT`, `OPENAI_API_KEY` 비어 있음 → API 요금 없음 확인
  - 설계(GPT) r1 **PASS** (❌ 0개) → 구현 → 테스트 8개(기존 5 + 신규 3) 전부 통과, 총 4분 5초
  - 바꾼 파일: `todo.py`, `test_todo.py`, `README.md` (새 라이브러리 없음)
  - 설계와 다르게 한 점: 날짜 검사 함수 2개 → 1개로 합침, 지남 판단은 ISO 날짜 문자열 비교 (deviations에 기록됨)
  - 사용법: `python todo.py add "보고서" --due 2026-10-10` / `due 1 2026-10-12` / `due 1 --clear` / `list` → 지난 항목 `[지남]`
  - 기록: `todo-app\.ai-pipeline\20261007-due-date\`
  - 커밋 `8d8a8b4` (설계 기록 `.ai-pipeline/` 포함) → GitHub CLI 설치·로그인(`gh auth login --web`) → 비공개 저장소 푸시 완료: https://github.com/goldgarden9620419-maker/todo-app (Private, 2 commits)
- 다음: 릴스 도구 설치(체크리스트 ③④) → 첫 분석
