# 인스타 릴스 자동 게시 세팅 (Instagram API)

- 작성일: 2026-10-07
- 목적: 힉스필드로 만든 릴스를 Claude가 **공식 Instagram API**로 자동 게시 (AI 라벨 자동 ON)
- 스킬: `.claude/skills/instagram-auto-post/` (스크립트 `scripts/ig_publish.py`, 1편 게시 파일 `posts/2026-10-07-ep1.json`)
- 관련: [[릴스 원고 재료 - 내 경험과 숫자]]
- 근거: [Meta 콘텐츠 게시 문서](https://developers.facebook.com/docs/instagram-platform/content-publishing) · [AI 라벨 is_ai_generated (2026-06-22 추가)](https://developers.facebook.com/documentation/instagram-platform/changelog)

## 흐름
```
게시 파일(영상 링크+캡션) → dry-run 점검 → 릴스 컨테이너 생성(AI 라벨 ON) → 인스타 처리 대기 → 게시 → 링크 기록
```

## 1회 세팅 체크리스트 (약 30~60분)

- [ ] **① 인스타를 크리에이터 계정으로 전환** — 앱 → 설정 → 계정 유형 및 도구 → 프로페셔널 계정으로 전환 → 크리에이터
- [ ] **② Meta 개발자 계정** — https://developers.facebook.com → 시작하기 (페이스북 계정 로그인 + 휴대폰 인증 필요)
- [ ] **③ 앱 만들기** — 내 앱 → 앱 만들기 → 사용 사례 **"Instagram에서 메시지 및 콘텐츠 관리"** → 앱 이름 `harubogo-reels` → 만들기
  - 화면 이름은 Meta가 자주 바꿔요. 비슷한 "Instagram API" 사용 사례를 고르면 됩니다.
- [ ] **④ 권한 확인** — 사용 사례 → 맞춤 설정 → **"Instagram 로그인을 통한 API 설정"** → 권한에 `instagram_business_basic`, `instagram_business_content_publish` 있는지
- [ ] **⑤ 토큰 발급** — 같은 화면 "액세스 토큰 생성" → **계정 추가** → kim_jade0419 로그인·허용 → **토큰 생성** → 복사
  - "테스터 초대"가 필요하다고 나오면: 앱 역할 → Instagram 테스터에 kim_jade0419 추가 → 인스타 앱(웹) 설정 → 앱 및 웹사이트 → 테스터 초대 수락
- [ ] **⑥ 토큰 저장 (PowerShell)** — 채팅이나 vault에 붙여넣지 말 것
  ```powershell
  Set-Content -Path "$HOME\.ig_token" -Value "여기에_토큰_붙여넣기" -NoNewline
  ```
- [ ] **⑦ 스킬 전역 복사**
  ```powershell
  Copy-Item -Recurse -Force "$HOME\Documents\mynotes\.claude\skills\instagram-auto-post" "$HOME\.claude\skills\"
  ```

## 1편 게시
```powershell
cd $HOME\.claude\skills\instagram-auto-post
python scripts\ig_publish.py --post posts\2026-10-07-ep1.json --dry-run          # 점검
python scripts\ig_publish.py --post posts\2026-10-07-ep1.json --at "2026-10-07 19:30"   # 19:30 게시 (PC 켜두기)
```
또는 Claude Code에서: `인스타 자동 게시 스킬로 1편 dry-run 하고, 통과하면 오늘 19:30에 올려줘`

## 주의
- 토큰은 약 **60일** 유효 → 50일마다 `--refresh-token`
- API 게시 한도: 24시간 50개
- `--at` 예약은 PC가 켜져 있어야 동작 (절전 해제)
- AI 영상은 `is_ai_generated: true` 고정. AI 라벨 거부 시 스크립트가 게시하지 않고 멈춤 (종료 코드 6)
- 앱 심사: 내 계정에만 게시하는 개발 모드는 심사 없이 될 것으로 보임(가정) — ⑤에서 막히면 그 화면 캡처해서 확인
