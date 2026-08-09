# AD STUDIO — 로컬 실행 (Claude Code)

## 실행 순서
1. `npm install`
2. `npm run dev` → http://localhost:5173 자동 오픈
3. 헤더 오른쪽 **API 키** 버튼 → Anthropic API 키 등록 (console.anthropic.com 발급)
   - 키는 이 브라우저의 localStorage에만 저장됩니다. 코드나 저장소에 넣지 마세요.
4. 브리프 입력 → 제작안 생성

## 동작 차이 (claude.ai 아티팩트 대비)
- 저장: localStorage 사용 (아티팩트에선 window.storage). 같은 브라우저에서 유지됩니다.
- API: 직접 브라우저 호출 (`anthropic-dangerous-direct-browser-access` 헤더). 개인 로컬 개발용으로만 사용하고, 배포 시에는 서버 프록시로 전환하세요.

## 문제 해결
- "API 키가 필요합니다" 오류 → 헤더의 API 키 버튼으로 등록
- 401/403 → 키 오타 또는 크레딧 소진 (console.anthropic.com 확인)
- CORS 오류가 보이면 키 등록 여부부터 확인 (키 없이 호출하면 프리플라이트에서 거절됨)
