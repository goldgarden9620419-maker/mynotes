# ChatGPT + Claude 협업 워크플로우 설정 (Codex CLI 연동)

- 작성일: 2026-10-04
- 상태: ✅ 설정 완료 (2026-10-05 1~4단계 모두 완료, 실사용 단계)
- 태그: #AI #ClaudeCode #Codex #ChatGPT #자동화

## 목표
ChatGPT가 구조를 짜고, Claude가 검증한 뒤 코드를 짠다. 한쪽 AI가 다른 쪽을 도구처럼 호출하는 구조로, 두 유료 구독의 시너지를 낸다.

## 핵심 결론
- **Claude Code가 Codex CLI(ChatGPT 계정으로 로그인)를 도구처럼 호출하는 구조**로 간다.
- ChatGPT Plus/Pro와 Claude Pro/Max 구독에는 **API 이용료가 포함되지 않는다.** API로 연결하면 사용량만큼 따로 과금된다.
- Codex CLI는 "Sign in with ChatGPT"로 로그인하면 **구독 사용량 안에서** 쓸 수 있다. Claude Code도 Claude 구독으로 로그인해서 쓴다. → 추가 요금 없음
- ~~`codex mcp-server`로 MCP 등록~~ → **2026-08-24 OpenAI가 지원 종료(deprecated)**, 0.160.0에서 연결 실패. **Claude Code가 터미널에서 `codex exec`를 직접 실행하는 방식으로 확정.**

## 역할 분담

| 단계 | 담당 | 하는 일 |
|---|---|---|
| ① 구조 설계 | ChatGPT (Codex) | 요구사항 정리, 아키텍처·폴더 구조·단계별 계획 초안 |
| ② 검증 | Claude | 허점, 엣지 케이스, 보안 문제를 짚고 수정안 제시 |
| ③ 구현 | Claude | 확정 설계대로 코드 작성, 테스트, 실행 |
| ④ 교차 리뷰 (선택) | ChatGPT (Codex) | 완성 코드를 다른 시각에서 리뷰 |

## 설정 체크리스트

- [x] **1단계. Codex CLI 설치 + ChatGPT 계정 로그인** (Node.js 18 이상 필요) ✅ 2026-10-05 완료
  ```bash
  npm install -g @openai/codex
  codex          # 처음 실행하면 로그인 화면 → "Sign in with ChatGPT" 선택 (API key 선택 X)
  codex exec "안녕, 연결 테스트야. 한 줄로 답해줘"   # 답이 나오면 성공
  ```
- [x] **2단계. PC에 Claude Code 설치 + Claude가 `codex exec`로 ChatGPT 호출** ✅ 2026-10-05 완료
  ```powershell
  npm install -g @anthropic-ai/claude-code   # 이미 있으면 업데이트됨
  cd ~\ai-work                               # AI 작업 전용 폴더에서만 실행
  claude                                     # 신뢰 화면에서 "Yes, I trust this folder"
  ```
  - Claude 입력창 테스트 문장: `터미널에서 codex exec --skip-git-repo-check "질문" 를 실행해서 ChatGPT의 답을 받고, 네가 검토해서 장단점을 알려줘`
  - ⚠️ `claude mcp add codex -- cmd /c codex mcp-server` 방식은 실패(CONNECTION_CLOSED) → `claude mcp remove codex -s user`로 삭제함
- [x] **3단계. 프로젝트 `CLAUDE.md`에 아래 협업 규칙 붙여넣기** ✅ 2026-10-05 완료 (`C:\Users\AP\ai-work\CLAUDE.md`, 27줄)
- [x] **4단계. 첫 과제를 정해서 이 흐름으로 실제로 돌려보기** ✅ 2026-10-05 완료 (할 일 목록 앱 `todo-app`)

## CLAUDE.md 템플릿 (복붙용)

```markdown
## ChatGPT(Codex) + Claude 협업 규칙

새 기능이나 프로젝트 요청을 받으면 아래 순서를 따른다.

1. **설계 요청 (ChatGPT)**
   - 터미널에서
     `codex exec --skip-git-repo-check "<요구사항> — 아키텍처, 폴더 구조, 단계별 구현 계획을 마크다운으로 작성해줘"` 실행
   - 받은 설계 원문을 `docs/design-gpt.md`에 저장

2. **검증 (Claude)**
   - 설계를 검토해서 허점, 누락된 엣지 케이스, 보안 문제, 과한 설계를 표로 정리
   - 고친 최종 설계를 `docs/design-final.md`에 저장
   - 크게 바뀐 부분은 사용자에게 3줄로 요약해서 알림

3. **구현 (Claude)**
   - `design-final.md` 기준으로 코드 작성
   - 코드에 주석, 기본 에러 처리, 실행 방법을 포함
   - 테스트나 실행으로 동작 확인

4. **교차 리뷰 (ChatGPT, 선택)**
   - `codex exec --skip-git-repo-check "이 diff를 리뷰해줘: 버그, 보안, 개선점만 짧게"` 실행
   - 타당한 지적만 반영하고, 반영하지 않은 지적은 이유를 남김
```

## 다른 방법 (상황별)

| 상황 | 방법 | 비용 |
|---|---|---|
| 코딩 없이 질문·기획만 할 때 | ChatGPT 웹에서 구조 짜기 → 결과를 Claude에 붙여넣고 "검증 후 코드로 짜줘" | 추가 요금 없음 |
| 완전 자동 파이프라인이 필요할 때 | Python으로 OpenAI API와 Anthropic API를 직접 호출 | 사용량만큼 별도 과금 |

## 진행 기록
- **2026-10-05 1단계 완료** (Windows PowerShell)
  - Node.js `v24.19.0`, Codex CLI `0.160.0` 설치
  - `cd ~`로 홈 폴더(`C:\Users\AP`)에서 작업 (system32에서 실행하지 않기)
  - `codex login` → 브라우저에서 ChatGPT 계정 로그인 → `Successfully logged in`
  - `codex exec --skip-git-repo-check "..."` 테스트 성공 (모델 `gpt-5.6-sol`, sandbox read-only)
  - 팁: Git 저장소가 아닌 폴더에서는 `--skip-git-repo-check` 옵션을 붙인다.

- **2026-10-05 2단계 완료**
  - Claude Code `2.1.289` (이미 로그인돼 있었음). npm `allow-scripts` 경고는 무시해도 정상 동작
  - 작업 폴더 `C:\Users\AP\ai-work` 생성 (홈 폴더 전체를 신뢰하지 않기 위해)
  - MCP 등록 실패 → `codex exec` 방식으로 전환, 테스트 성공 (ChatGPT가 폴더 구조 제안 → Claude가 장단점·결론 검토)

- **2026-10-05 3단계 완료**
  - PC의 Claude에게 템플릿을 붙여 넣어 `ai-work\CLAUDE.md` 생성 (공통 규칙: 한국어 존댓말, 프로젝트별 하위 폴더)
  - 규칙은 Claude를 **새로 실행할 때부터** 적용된다 (`/exit` 후 `claude` 재실행)
  - `ai-work`는 git 저장소가 아니라서, 교차 리뷰(diff)를 쓰려면 프로젝트 하위 폴더에서 `git init` 필요

- **2026-10-05 4단계 완료** — 첫 과제: 할 일 목록 앱 (`C:\Users\AP\ai-work\todo-app`)
  - 시작 프롬프트: "CLAUDE.md의 협업 규칙대로 할 일 목록 앱을 만들어줘. 프로젝트 폴더 todo-app(그 안에서 git init), Python, 추가/목록/완료/삭제, todos.json 저장, 단계마다 짧게 보고"
  - 소요 시간 약 5분 50초, `auto mode on` 상태라 거의 묻지 않고 진행
  - 결과물: `todo.py`, `test_todo.py`, `README.md`, `.gitignore` (+ `docs/design-gpt.md`, `docs/design-final.md`)
  - 안전장치: 임시 파일에 먼저 쓰고 교체(저장 실패해도 기존 파일 보존), 파일 손상 시 덮어쓰지 않고 오류 표시
  - 교차 리뷰: Codex 지적 4건 중 3건 반영, 1건(터미널 제어문자 필터)은 개인용이라 불필요 → 이유를 설계 문서에 기록
  - Codex는 자기 환경에 Python이 없어 테스트를 못 돌림 → 테스트는 Claude가 실행해 통과
  - 사용법: `cd C:\Users\AP\ai-work\todo-app` → `python todo.py add "장보기"` / `list` / `done 1` / `delete 1` / `python -m unittest -v`

## 실전 사용법 (요약)
1. PowerShell에서 `cd ~\ai-work` → `claude`
2. "CLAUDE.md의 협업 규칙대로 ○○을 만들어줘. 프로젝트 폴더: ○○ (그 안에서 git init). 요구사항: ..." 입력
3. 끝나면 "커밋해줘"로 git에 저장

## 다음에 할 일
1. todo-app 직접 실행해 보고 "커밋해줘"로 저장
2. 실제 업무 과제(예: 자금계획 자동화 개선, 블로그 자동화 도구)에 같은 흐름 적용
2. 만들고 싶은 기능이나 프로그램을 하나 정해서 첫 과제로 진행

## 출처
- [OpenAI Codex CLI README (Sign in with ChatGPT, `codex mcp-server`)](https://github.com/whb07/codex)
- [Simon Willison – MCP in Claude and ChatGPT (2026-07-29)](https://simonwillison.net/2026/Jul/29/mcp-in-claude-and-chatgpt/)
- [codex-mcp: Claude Code에서 Codex 호출하는 MCP 서버](https://glama.ai/mcp/servers/dlbobhsrsy)
