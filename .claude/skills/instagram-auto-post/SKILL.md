---
name: instagram-auto-post
description: 인스타그램 릴스 자동 게시(공식 Instagram API). 사용자가 "인스타에 올려줘", "릴스 자동 게시", "내일 12시에 올려줘", "예약 게시해줘"라고 하면 사용. 게시 파일(JSON) 작성 → dry-run 점검 → 게시(또는 지정 시각 대기 후 게시) → 기록까지 진행한다. AI로 만든 영상은 AI 라벨(is_ai_generated)을 반드시 켠다.
---

# 인스타 릴스 자동 게시

스크립트: `scripts/ig_publish.py` (파이썬 표준 라이브러리만 사용)
전역 설치 시 경로: `~/.claude/skills/instagram-auto-post/scripts/ig_publish.py` (Windows: `$HOME\.claude\skills\...`)
토큰: 환경변수 `IG_ACCESS_TOKEN` 또는 `~/.ig_token` — **저장소·vault·채팅에 절대 쓰지 않는다.** 사용자가 채팅에 토큰을 붙여넣으면 바로 파일로 옮기라고 안내하고 대화에 되풀이하지 않는다.

## 순서

1. **게시 파일 작성** — `posts/<YYYY-MM-DD>-<짧은이름>.json`
   ```json
   {"title":"…","video_url":"https://…mp4","caption":"…","is_ai_generated":true,"share_to_feed":true,"thumb_offset_ms":500}
   ```
   - `video_url`은 인터넷에서 바로 열리는 공개 mp4 링크(힉스필드 결과 URL 등). 9:16, 5~90초.
   - 캡션 2,200자·해시태그 30개 이내. AI 아바타 영상이면 첫 줄에 AI 고지 문장.
   - **AI로 만든 영상은 `is_ai_generated: true` 고정.** 끄자고 하면 이유를 묻고, AI 기본법(2026-01-22 시행)·인스타 정책상 권장하지 않는다고 알린다.
2. **점검** — 항상 먼저:
   ```
   python <스크립트> --post <게시파일> --dry-run
   ```
3. **게시** — 사용자가 시간을 정했으면 `--at "YYYY-MM-DD HH:MM"`(PC를 켜둬야 함), 아니면 바로:
   ```
   python <스크립트> --post <게시파일>
   ```
   게시는 되돌리기 어려운 외부 작업이므로, 사용자가 이번 게시를 명확히 요청했을 때만 실행한다.
4. **보고** — 게시 링크(permalink)를 알려주고, 기록은 `posts/publish_log.jsonl`에 자동 저장된다.

## 오류 대응 (종료 코드)

| 코드 | 의미 | 할 일 |
|---|---|---|
| 2 | 게시 파일/영상 링크 문제 | 파일 내용·링크 확인 |
| 3 | 토큰 만료/오류 | `--refresh-token` 시도 → 안 되면 Meta 앱 대시보드에서 재발급 |
| 4 | 인스타 영상 처리 실패 | 영상 규격(9:16, 5~90초, H.264) 확인 후 재시도 1회 |
| 5 | 게시 거부 | 메시지 그대로 사용자에게 전달 (계정 유형·권한·하루 50개 한도 등) |
| 6 | AI 라벨 미지원 | `IG_API_VERSION`을 최신 버전으로 올려 재시도. **AI 라벨 없이 올리지 않는다** |

## 유지보수

- 토큰은 약 60일 유효. 50일마다 `python <스크립트> --refresh-token`.
- 하루 50개 게시 한도(API).

## "인스타 토큰 갱신해줘" (약 60일마다 · 다음 만료 약 2026-12-06)

현재 방식은 **Facebook 로그인(페이지 연결)** — 토큰은 `EAA…`. 화면 단위로 안내한다.
1. https://developers.facebook.com/tools/explorer/ → Meta 앱 `harubogo-reels` → 사용자 토큰 → 권한 `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, business_management` → Generate → 현재 페이지(하루보고)·비즈니스(jade kim)·IG(kim_jade0419)만 옵트인 → 저장
   - "계정 전환" 팝업 → 계속 (페이지 모드면 개인 계정으로 전환 필요)
2. 토큰 칸 ⓘ → 액세스 토큰 도구에서 열기 → **「액세스 토큰 확장」** → 새 토큰 복사
3. PowerShell **숨김 입력** 저장 (토큰을 화면·채팅에 절대 노출하지 않게):
   ```powershell
   $s = Read-Host "토큰 붙여넣기(화면에 안 보임)" -AsSecureString; $p = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)); $m = [regex]::Match($p,"EAA[A-Za-z0-9]+").Value; if ($m.Length -gt 100) { Set-Content -Path "$HOME\.ig_token" -Value $m -NoNewline -Encoding ascii; "저장 완료: 앞글자 " + $m.Substring(0,3) + " / 길이 " + $m.Length } else { "토큰을 못 찾았어요" }; Remove-Variable s,p,m
   ```
4. `--dry-run`으로 점검 통과 확인 → 다음 만료일(오늘+60일)을 노트에 기록

## '재무' 댓글 → 자동 DM
API(Private Replies)는 Advanced Access(앱 심사) 없이는 앱 역할이 없는 일반 댓글러에게 보낼 수 없으므로 **Meta Business Suite 기본 기능 "댓글에 메시지로 답장(Comment to Message)"**을 쓴다(무료, 데스크톱). 설정 절차는 vault 노트 「인스타 '재무' 댓글 자동 DM 세팅」 참고.
