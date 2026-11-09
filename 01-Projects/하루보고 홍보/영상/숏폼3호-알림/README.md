# 하루보고 홍보 숏폼 3호 — 알림 편 (2026-11-09 제작)

- 18초 · 1080×1920 세로 · 무음 (쓰레드 API는 음악 불가, 릴스·쇼츠엔 앱에서 음악 추가)
- 구성: 📌 훅("일정, 적어두고 잊은 적 있으시죠?") → 하루 3번 알림 푸시 연출(🌅9시 오늘 마감/☀️1시 D-1/🌙6시 내일 시작) → "일정이 당신을 찾아옵니다" → 시리즈 공통 파란 엔딩
- 톤: 1호(효율)·2호(감성)에 이은 3호(신뢰). 알림 내용은 전부 가상 예시
- 발행: 쓰레드 thread-video-3-alarm, 2026-11-12(목) 13:00 예약

## 재렌더 방법
1. 이 폴더에서 `npm init -y && npm i playwright pretendard`
   (ffmpeg-static은 다운로드가 막힐 수 있어 시스템 ffmpeg 사용 — render3.mjs가 /usr/bin/ffmpeg 참조)
2. `node render3.mjs` → harubogo-promo3.mp4 생성 (promo3.html을 프레임 캡처 → ffmpeg 인코딩)
3. 문구·타이밍 수정은 promo3.html의 텍스트와 sceneVis/tw 딜레이 값
