# claude-seo 기반 AI 검색(GEO) 최적화 체크리스트

- 적용일: 2026-09-04 (사용자 요청 — 앞으로 모든 승인글에 적용)
- 출처: [claude-seo GitHub](https://github.com/AgriciDaniel/claude-seo) (seo-geo·seo-content 스킬), 참고: [Notion 가이드 "챗GPT가 내 글부터 추천하게 만들기"](https://app.notion.com/p/3eeb6efc6fc58256b08b81e04effb530)
- 목적: 챗GPT·퍼플렉시티·구글 AI 오버뷰 같은 AI 검색이 황금정원 글을 인용·추천하기 좋은 구조로 쓰기

## 글 단위 체크리스트 (매 글 작성·검수 시)

1. **서론에 인용 가능한 한 줄** — 첫 문단 안에 AI가 그대로 발췌해 갈 자기완결형 핵심 문장 1개 ("X는 ~이다" 정의 패턴 또는 구체 수치가 든 단정문)
2. **상단 30% 승부** — AI 인용의 약 44%가 페이지 상단 30%에서 나옴. 핵심 반전·수치·답을 첫 소제목 카드에 배치
3. **자기완결 답변 블록** — 각 summary-card는 맥락 없이 발췌해도 성립하는 2~3문장으로 (주어 포함, 지시어 최소화)
4. **질문형 소제목** — 검색 질문 패턴과 일치하는 질문형 헤딩이 유리 (셀프 문답 카드가 기본적으로 이 역할)
5. **수치·출처 명시** — 구체 통계 + 실존 출처 링크 (E-E-A-T 규칙과 동일)
6. **검색어 기반 키워드** — 제목 괄호 키워드·태그는 사람들이 실제 검색하는 단어로, 핵심 키워드를 본문 첫 100단어 안에
7. **날짜·신선도** — 작성일 기록. 3개월 이내 글이 AI 인용 확률 약 3배(SE Ranking), 6개월 이상 방치된 글은 인용 자격을 잃기 쉬움 → 오래된 글 주기 업데이트가 고효율

## 사이트 단위 (참고 — 티스토리 제약 있음)

- robots.txt에서 GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot 허용 시 AI 검색 노출에 유리 (티스토리는 직접 제어 제한)
- 브랜드 언급 신호(유튜브·레딧·위키 등)가 백링크보다 AI 인용과 3배 강한 상관 — 쓰레드 병행 발행이 이 방향과 일치
- llms.txt는 구글 검색에는 무효과(구글 공식), 다른 AI 크롤러용 선택 사항

## 전체 사이트 진단 방법 (로컬 Claude Code에서)

```
/plugin marketplace add AgriciDaniel/claude-seo
/plugin install claude-seo@agricidaniel-claude-seo
/seo setup
/seo audit https://goldjade0419.com
```

- 글 하나만: `/seo page [글 주소]` / AI 검색 집중 점검: `/seo geo [주소]` / 설치 확인: `/seo doctor`
- 리포트는 우선순위 1~3개만 먼저 고치고, 고친 뒤 같은 명령을 다시 돌려 비교
- ※ 원격 세션 환경에서는 goldjade0419.com 접속이 차단되어 라이브 진단 불가 — 로컬에서 실행할 것
