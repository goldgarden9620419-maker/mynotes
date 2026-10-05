# ChatGPT + Claude 협업 워크플로우 설정 (Codex CLI 연동)

- 작성일: 2026-10-04
- 상태: 🔄 진행 중 (2026-10-05 1단계 완료 → 2단계 진행)
- 태그: #AI #ClaudeCode #Codex #ChatGPT #자동화

## 목표
ChatGPT가 구조를 짜고, Claude가 검증한 뒤 코드를 짠다. 한쪽 AI가 다른 쪽을 도구처럼 호출하는 구조로, 두 유료 구독의 시너지를 낸다.

## 핵심 결론
- **Claude Code가 Codex CLI(ChatGPT 계정으로 로그인)를 도구처럼 호출하는 구조**로 간다.
- ChatGPT Plus/Pro와 Claude Pro/Max 구독에는 **API 이용료가 포함되지 않는다.** API로 연결하면 사용량만큼 따로 과금된다.
- Codex CLI는 "Sign in with ChatGPT"로 로그인하면 **구독 사용량 안에서** 쓸 수 있다. Claude Code도 Claude 구독으로 로그인해서 쓴다. → 추가 요금 없음
- `codex mcp-server`로 Claude Code에 MCP 도구로 등록할 수 있다. 더 간단하게는 Claude가 Bash로 `codex exec`를 실행하게 해도 된다.

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
- [ ] **2단계. Claude Code에 Codex를 MCP 도구로 등록**
  ```bash
  npm install -g @anthropic-ai/claude-code   # 이미 설치돼 있다면 생략
  claude mcp add codex -- codex mcp-server
  claude mcp list        # 목록에 codex가 보이면 성공
  ```
  - 오류가 나면 `codex --help`로 명령 형식을 확인한다. 안 되면 `codex exec` 방식만 써도 충분하다.
- [ ] **3단계. 프로젝트 `CLAUDE.md`에 아래 협업 규칙 붙여넣기**
- [ ] **4단계. 첫 과제를 정해서 이 흐름으로 실제로 돌려보기**

## CLAUDE.md 템플릿 (복붙용)

```markdown
## ChatGPT(Codex) + Claude 협업 규칙

새 기능이나 프로젝트 요청을 받으면 아래 순서를 따른다.

1. **설계 요청 (ChatGPT)**
   - codex MCP 도구를 쓰거나, 없으면 Bash로
     `codex exec "<요구사항> — 아키텍처, 폴더 구조, 단계별 구현 계획을 마크다운으로 작성해줘"` 실행
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
   - `codex exec "이 diff를 리뷰해줘: 버그, 보안, 개선점만 짧게"` 실행
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

## 다음에 할 일
1. 2단계: PC에 Claude Code 설치 → Codex를 MCP로 등록
2. 만들고 싶은 기능이나 프로그램을 하나 정해서 첫 과제로 진행

## 출처
- [OpenAI Codex CLI README (Sign in with ChatGPT, `codex mcp-server`)](https://github.com/whb07/codex)
- [Simon Willison – MCP in Claude and ChatGPT (2026-07-29)](https://simonwillison.net/2026/Jul/29/mcp-in-claude-and-chatgpt/)
- [codex-mcp: Claude Code에서 Codex 호출하는 MCP 서버](https://glama.ai/mcp/servers/dlbobhsrsy)
