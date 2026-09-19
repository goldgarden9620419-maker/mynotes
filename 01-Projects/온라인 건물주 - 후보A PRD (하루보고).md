# PRD — 하루보고 (가칭): 업무일지 → 재무보고 자동 변환 SaaS

> 작성일: 2026-08-31 · 부록 2 「수익 구조를 건물 설계도로 바꾸는 1분 프롬프트」 적용 결과
> 입력: [[온라인 건물주 - 후보A BM 설계서 (재무보고 자동화 SaaS)]] (시장조사 반영판)
> 용도: 이 파일을 `PRD.md`로 프로젝트에 넣고 AI에게 개발 지시 (3편 STEP 1)

## 1. 서비스 개요

- **서비스명(가칭)**: 하루보고
- **한 줄 정의**: 경리·재무 담당자가 업무일지(PDF/엑셀/붙여넣기)를 올리면, 대표 보고용 재무보고서가 1분 만에 나오는 웹 서비스
- **타깃**: 직원 5~50인 중소기업의 경리·재무 담당자(경리·총무 겸직), 직접 챙기는 소기업 대표
- **핵심 가치**: ① 매일 30~60분 걸리던 보고서 작성이 1분 ② 숫자 누락·오타 감소 ③ 담당자가 없어도 보고는 나온다
- **가격**: 무료(월 3건) / 스타터 월 9,900원(월 10건) / 프로 월 29,000원(무제한+커스텀 양식) · 런칭 특가 첫 100명 19,900원

## 2. MVP 범위

### 포함 (이것만 만든다)
1. **F1 변환**: 파일 업로드(PDF/XLSX) 또는 텍스트 붙여넣기 → AI가 표준 재무보고서 생성 (고정 양식 1종)
2. **F2 아카이브**: 날짜별 보고서 목록 + 키워드 검색
3. **F3 내보내기**: 보고서 PDF 다운로드 + 공유 링크(읽기 전용)
4. 회원가입/로그인, 요금제 페이지, 토스페이먼츠 **정기결제(구독)**, 무료 사용량 제한

### 제외 (전부 '나중에')
커스텀 양식 빌더(초기엔 온보딩 수동 대응), 은행·홈택스 API 연동, 경영 대시보드 차트, 팀 계정/승인 플로우, 카톡 알림, 모바일 앱

## 3. 사용자 플로우

```
[랜딩] → 회원가입(이메일 or 구글) → [대시보드]
  → 파일 업로드 or 붙여넣기 → (AI 변환 30초~1분) → [보고서 화면]
  → 확인/간단 수정 → PDF 다운로드 or 공유 링크 복사
  → 다음날 다시 업로드 … 월 3건 소진 → [요금제] → 토스 카드 등록 → 구독 시작
```

- 첫 방문자는 **로그인 없이 샘플 보고서 데모**를 볼 수 있다 (3초 안에 서비스 이해)
- 변환 실패 시: 실패 사유 안내 + "템플릿에 붙여넣기" 대안 흐름 제공 (이탈 방지)

## 4. 기능 명세

### F1. 변환 엔진 (핵심)
- 입력: PDF(텍스트형), XLSX, 플레인 텍스트 붙여넣기 (파일 최대 10MB)
- 처리: 서버(API Route)에서 텍스트 추출 → Claude API에 "변환 프롬프트 + 표준 양식 스키마" 전달 → 구조화 JSON 수신
- 표준 재무보고서 양식(고정 1종):
  1. 보고 헤더 (회사명·보고일·작성자)
  2. 자금 현황 (계좌별 잔액, 전일 대비 증감)
  3. 금일 입금 내역 (주요 건 요약 + 합계)
  4. 금일 출금 내역 (주요 건 요약 + 합계)
  5. 매출 현황 (채널별, 있는 경우)
  6. 특이사항 / 대표 확인 필요 사항
  7. 익일 예정 (입출금 예정, 있는 경우)
- 원문에 없는 항목은 "해당 없음" 처리 — **AI가 숫자를 지어내지 않도록 프롬프트에 명시** (환각 = 이 서비스의 치명타)
- 결과 화면에서 섹션별 인라인 수정 가능, 수정본 저장

### F2. 아카이브
- 보고서 목록: 보고일 역순, 월별 그룹핑
- 검색: 제목·본문 키워드 (Supabase full-text 또는 ilike)
- 보고서 상태: processing / done / failed

### F3. 내보내기
- PDF 다운로드 (보고서 화면을 A4 양식으로 렌더 → 서버 사이드 PDF 생성)
- 공유 링크: `/share/[token]` 읽기 전용, 만료일 설정(기본 7일), 로그인 불필요

### F4. 계정·결제
- Supabase Auth: 이메일+비밀번호, 구글 OAuth
- 요금제: free / starter / pro — 월 변환 횟수 카운터로 제한 (3 / 10 / 무제한)
- 토스페이먼츠 **빌링(정기결제)**: 카드 등록 → billingKey 발급 → 매월 자동 결제 → 웹훅으로 결제 성공/실패 반영
- 결제 실패 시 3일 유예 후 free로 강등, 데이터는 보존
- 구독 해지: 즉시 해지 아닌 현재 결제 기간 말까지 유지

### F5. 보안·데이터 정책 (첫날부터)
- 모든 테이블 RLS: `user_id = auth.uid()`
- 업로드 원본 파일: 변환 완료 후 **자동 삭제 옵션** (기본 ON) — 보안 불신 대응
- 계좌번호 마스킹 안내 (업로드 화면에 고지)
- 개인정보처리방침·이용약관 페이지 (토스 심사에도 필요)

## 5. ERD (Supabase 테이블 설계)

```
profiles            -- auth.users 1:1
  id uuid PK (= auth.users.id)
  email text, name text, company_name text
  plan text default 'free'        -- free | starter | pro
  delete_source_on_done boolean default true
  created_at timestamptz

reports
  id uuid PK, user_id uuid FK→profiles
  report_date date, title text
  source_type text                -- pdf | xlsx | paste
  source_path text null           -- Storage 경로 (삭제 옵션 시 null)
  status text                     -- processing | done | failed
  content jsonb                   -- 섹션별 구조화 본문
  content_text text               -- 검색용 플레인 텍스트
  created_at, updated_at

share_links
  id uuid PK, report_id uuid FK→reports
  token text unique, expires_at timestamptz, created_at

subscriptions
  id uuid PK, user_id uuid FK unique
  plan text, status text          -- active | past_due | canceled
  toss_customer_key text, billing_key text
  current_period_end timestamptz, created_at, updated_at

payments
  id uuid PK, user_id uuid FK
  amount int, status text         -- paid | failed | refunded
  toss_payment_key text, order_id text, paid_at timestamptz

usage_counters
  user_id uuid FK, month text     -- '2026-09'
  conversions int default 0
  PK (user_id, month)
```

Storage 버킷: `uploads` (비공개, RLS 정책 동일)

## 6. TRD (기술 스택)

| 영역 | 선택 | 이유 |
|---|---|---|
| 프레임워크 | Next.js 14 (App Router) + TypeScript | Vercel 배포 최적, 책 스택과 일치 |
| UI | Tailwind CSS + shadcn/ui | 빠른 제작, 반응형 기본 |
| DB/인증/스토리지 | Supabase (서울 리전) | Auth+DB+Storage 일체형, MCP로 AI 개발 연동 |
| AI 변환 | Claude API (claude-sonnet-5) | 한국어 문서 구조화에 강함. 응답은 JSON 스키마 강제 |
| PDF 추출 | unpdf 또는 pdf-parse (서버) | 텍스트형 PDF 대응. 스캔본은 MVP 제외 |
| XLSX 추출 | SheetJS (xlsx) | |
| PDF 생성 | @react-pdf/renderer 또는 Playwright print | A4 보고서 출력 |
| 결제 | 토스페이먼츠 빌링(정기결제) SDK + 웹훅 | 구독 모델. 일회성 결제로 만들지 말 것 |
| 배포 | Vercel (GitHub 연동, main 푸시 시 자동 배포) | |

**환경변수 (env.local + Vercel 등록, 코드에 절대 하드코딩 금지)**
```
NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY
ANTHROPIC_API_KEY
NEXT_PUBLIC_TOSS_CLIENT_KEY / TOSS_SECRET_KEY / TOSS_WEBHOOK_SECRET
```

## 7. 화면 구성 (7개)

1. **랜딩** `/` — 3초 안에 이해되는 헤드라인("업무일지 올리면, 대표 보고서가 1분 만에"), Before/After 데모, 요금제 요약, CTA
2. **가입/로그인** `/login` — 이메일 + 구글, 5단계 이하
3. **대시보드** `/app` — 업로드 드롭존 + 붙여넣기 탭, 이번 달 사용량 (3건 중 2건 사용), 최근 보고서 5개
4. **보고서 상세** `/app/reports/[id]` — 표준 양식 렌더, 인라인 수정, PDF 다운로드·공유 링크 버튼
5. **아카이브** `/app/reports` — 월별 목록 + 검색
6. **요금제** `/pricing` — 3개 플랜 비교표, 토스 카드 등록 플로우
7. **설정** `/app/settings` — 회사명, 원본 자동삭제 토글, 구독 관리(해지)

## 8. 개발 태스크 (우선순위별)

### P0 (필수 — 이것 없이 런칭 불가)
- [ ] Next.js 프로젝트 셋업 + Supabase 연결 (MCP로 테이블·RLS 생성)
- [ ] Auth: 이메일/구글 가입·로그인·로그아웃
- [ ] F1: 업로드/붙여넣기 → 텍스트 추출 → Claude 변환 → reports 저장 (`app/api/convert`)
- [ ] 보고서 상세 화면 + 인라인 수정
- [ ] F2: 아카이브 목록·검색
- [ ] F3: PDF 다운로드
- [ ] 사용량 카운터 + 플랜별 제한 (free 3건)
- [ ] 랜딩 + 요금제 페이지
- [ ] 토스 빌링: 카드 등록 → 정기결제 → 웹훅 처리 (`app/api/toss/webhook`)
- [ ] RLS 전 테이블 적용 + 비로그인 접근 차단

### P1 (중요 — 런칭 직후 2주 내)
- [ ] 공유 링크 (`/share/[token]`, 만료 처리)
- [ ] 원본 자동 삭제 옵션 실작동
- [ ] 변환 실패 처리 UX (사유 안내 + 템플릿 붙여넣기 대안)
- [ ] 월간 요약 리포트 (프로 전용: 한 달치 보고서 집계)
- [ ] 커스텀 양식: 관리자(나)가 회사별 양식 JSON을 수동 등록하는 내부 도구

### P2 (개선 — 검증 후)
- [ ] B2B 다계정 (세무사무소용)
- [ ] 경영 대시보드 (잔액 추이·매출 차트)
- [ ] 카톡/이메일 아침 보고 자동 발송
- [ ] 스캔 PDF OCR 지원

## 9. 성공 기준

- 기술: 업로드→보고서까지 90초 이내, 변환 성공률 90%+ (베타 기준), 로딩 3초 이내
- 비즈니스: 베타 10명 중 4명 이상이 "매일 쓰겠다" / 첫 달 유료 전환 5명 / 3개월 내 유료 30명(MRR 약 60~90만 원)
- 체크리스트: [[바이브 코딩 SaaS 실행 체크리스트 (169가지)]] 3편 + 최종 점검 전 항목 통과

## 10. AI 개발 지시문 (이 PRD와 함께 사용)

```
PRD.md 파일 보고, Supabase MCP 통해 DB(테이블·RLS·Storage) 만들고,
Next.js 앱 완성해줘. 결제는 토스페이먼츠 정기결제(빌링)로 구현해줘.
오류 있으면 고쳐줘.
```
