# AI 릴스 만들기 + GPT설계 → Claude검증 → Claude코딩 파이프라인 세팅

- 작성일: 2026-10-07
- 참고: [디립다 연구소 · AI로 릴스 만드는 법 (2026-09-29)](https://deeripda-marketing-hub.vercel.app/archive/practice/claude-reels-maker) · [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) · [Codex CLI 문서](https://learn.chatgpt.com/docs/codex/cli)
- 스킬 위치(이 vault): `.claude/skills/reels-maker/` · `.claude/skills/gpt-design-claude-build/`

## 한 줄 결론
릴스는 **reels-maker 스킬**(가이드 원문 + GPT 교차검토 단계 추가)로, 코딩은 **gpt-design-claude-build 스킬**로 돌린다. Codex는 ChatGPT 로그인 + read-only 설계 전용이라 추가 API 요금이 들지 않는다(ChatGPT 플랜의 Codex 사용 한도 안에서 차감).

## 전체 흐름

```
[릴스]  @핸들 → 내 계정 분석 → 비슷한 계정 10 → 떡상 릴스 20 → 영상 분석(yt-dlp·whisper·ffmpeg)
        → 리포트(훅 TOP3·구조·빈자리·주제 5) → 주제+내 숫자 → 25~35초 원고
        └ (선택) "GPT랑 교차검토" → Codex 훅 3안·구간 설계 → Claude 검증(지어낸 숫자 제거) → Claude 최종 원고

[코딩]  요청 → Claude brief.md → Codex 설계 plan.r1.md (read-only)
        → Claude 검증 review.r1.md (실제 파일 대조, 6항목) ─REVISE→ Codex 재설계 (최대 3라운드)
        → PASS → Claude 구현 + 테스트 → (선택) codex exec review → summary.md
```

## 1회 설치 체크리스트 (Mac, 터미널)

- [ ] Claude 앱 설치·로그인 → Code 탭 → 이 vault 폴더(`mynotes`) 선택
- [ ] 릴스 분석 도구: Code 탭에 붙여넣기
  ```
  릴스 분석에 필요한 도구를 설치해줘.
  1. Homebrew가 없으면 먼저 설치해.
  2. brew로 yt-dlp, ffmpeg, whisper-cpp 설치.
  3. whisper 모델 ggml-large-v3-turbo-q5_0.bin 을 ~/.cache/whisper 에 받아.
     (https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin)
  4. 맥 비밀번호가 필요한 단계는 내가 터미널에 직접 붙여넣을 명령어를 알려줘.
  5. 다 끝나면 설치된 버전을 확인하고 "설치 끝!"이라고 말해.
  ```
- [ ] Claude in Chrome 설치(claude.com/ko/claude-in-chrome) → 🧩 고정 → 같은 계정 로그인 → 인스타는 **부계정**으로 직접 로그인
- [ ] Codex CLI 설치 + ChatGPT 로그인
  ```bash
  npm install -g @openai/codex      # 또는 brew install codex
  codex login                       # 브라우저 → "Sign in with ChatGPT"
  codex login status                # "Logged in using ChatGPT" 나오면 OK
  unset OPENAI_API_KEY              # 혹시 설정돼 있으면 제거 (종량 과금 방지)
  ```
- [ ] (다른 폴더·저장소에서도 쓰려면) 스킬 전역 복사
  ```bash
  cd ~/경로/mynotes
  mkdir -p ~/.claude/skills
  cp -R .claude/skills/reels-maker .claude/skills/gpt-design-claude-build ~/.claude/skills/
  ```
- [ ] (선택) 공식 플러그인: Claude Code에서 `/plugin marketplace add openai/codex-plugin-cc` → `/plugin install codex@openai-codex` → `/reload-plugins` → `/codex:setup`
  - 쓰임: `/codex:review`(완성 후 리뷰), `/codex:adversarial-review`(설계 반론). 내 스킬과 같이 써도 충돌 없음.
- [ ] Claude 앱 새 대화로 다시 열기 (스킬 인식)

## 바로 쓰는 프롬프트

| 상황 | 붙여넣을 문장 |
|---|---|
| 릴스 분석 시작 | `@내핸들 계정으로 릴스 만들어줘.` |
| 원고 받기 | `이 주제로 릴스 원고 써줘.\n주제: [주제 또는 추천 번호]\n내 경험·숫자: [한 줄]` |
| 원고 GPT 교차검토 | `이 주제로 GPT랑 교차검토해서 릴스 원고 써줘. 주제: … / 내 숫자: …` |
| 코딩 (기본) | `GPT 설계 → 네 검증 → 네 코딩으로 진행해줘: [만들 것]` |
| 코딩 + 마무리 리뷰 | `설계-검증-코딩으로 진행하고, 끝나면 Codex 리뷰까지 돌려줘: [만들 것]` |
| 이어하기 | `.ai-pipeline/<폴더> 이어서 해줘` / 릴스는 `이어서 해줘` |

## 왜 이 구조인가
- **Codex = read-only 설계자**: 두 모델이 같은 파일을 동시에 고치면 충돌 → 쓰기 권한은 Claude 하나만.
- **검증을 실제 파일 대조로**: GPT 설계의 흔한 실패는 "없는 파일·함수 가정". 체크리스트 2번이 이걸 잡는다.
- **최대 3라운드**: 무한 핑퐁으로 사용 한도가 녹는 걸 막는다.
- **API 키 차단**: 스크립트가 ChatGPT 로그인이 아니면 exit 12로 멈춘다.

## 리스크 / 주의
| 리스크 | 대응 |
|---|---|
| 인스타 경고·차단 | 부계정, 천천히, 아무것도 누르지 않기. 경고 뜨면 그날 중단 → 다음 날 "이어서 해줘" |
| Codex 사용 한도(플랜별 상이, Free는 적음) | 스크립트가 한도 감지 시 exit 14 → 리셋 후 재실행 또는 Claude 단독 설계 |
| Claude Code가 codex 실행 시 권한 질문 | 처음 한 번 "항상 허용" 선택 (또는 `/permissions`에 `Bash(bash .claude/skills/gpt-design-claude-build/scripts/codex_design.sh:*)` 추가) |
| 클라우드(웹) 세션 | ChatGPT 로그인·크롬·인스타가 없어서 **로컬 Mac Claude 앱에서만** 돌아감 |
| 원고에 숫자 지어내기 | 두 스킬 모두 `[내 숫자]` 빈칸 규칙 강제 |

## 다음 할 일
1. 위 체크리스트 설치 (30분)
2. `@내핸들 계정으로 릴스 만들어줘.` 로 첫 분석 (30분~1시간)
3. 작은 코딩 과제 하나로 파이프라인 시험 (예: 하루보고 랜딩 문구 수정)
