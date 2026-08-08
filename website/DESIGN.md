---
name: 황금정원
description: 새벽 기상과 확언으로 바뀐 삶을 기록하는 블로그로 방문자를 안내하는 SNS 유입용 소개 페이지
colors:
  midnight-indigo: "#6366f1"
  twilight-violet: "#7c3aed"
  indigo-glow: "rgba(99, 102, 241, 0.32)"
  abyss-navy: "#0f172a"
  night-navy: "#131a30"
  elevated-navy: "#192134"
  paper-white: "#ffffff"
  slate-muted: "#94a3b8"
  glass-surface: "rgba(255, 255, 255, 0.05)"
  glass-surface-strong: "rgba(255, 255, 255, 0.07)"
  glass-surface-hover: "rgba(255, 255, 255, 0.10)"
  hairline-border: "rgba(255, 255, 255, 0.12)"
  hairline-border-strong: "rgba(255, 255, 255, 0.18)"
typography:
  display:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(2.25rem, 6vw, 4.5rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "normal"
  headline:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(1.875rem, 3vw, 2.25rem)"
    fontWeight: 600
    lineHeight: 1.2
  title:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    letterSpacing: "0.2em"
rounded:
  pill: "9999px"
  card: "1rem"
  showcase: "1.5rem"
spacing:
  page-x: "1.5rem"
  section-y: "8rem"
  card-padding: "1.75rem"
  card-gap: "1.25rem"
components:
  button-primary:
    backgroundColor: "{colors.midnight-indigo}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.pill}"
    padding: "14px 32px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.pill}"
    padding: "14px 32px"
  card:
    backgroundColor: "{colors.glass-surface}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.card}"
    padding: "{spacing.card-padding}"
  chip:
    backgroundColor: "rgba(99, 102, 241, 0.1)"
    textColor: "{colors.midnight-indigo}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
---

# Design System: 황금정원

## Overview

**Creative North Star: "고요한 밤의 정원 (The Quiet Night Garden)"**

어두운 네이비 밤하늘 그라디언트 위로 인디고와 바이올릿 빛 덩어리가 반딧불처럼 천천히 떠다니고, 그 사이사이 서리 낀 유리처럼 반투명한 카드들이 이야기 조각을 하나씩 담고 있다. 그 정원을 작은 캡슐형 마스코트가 손을 흔들고, 메모를 들고, 하트를 띄우며 섹션마다 다른 포즈로 함께 걸어 다닌다.

이 시스템의 성격은 기업형 SaaS의 매끈함이 아니라 사적인 다이어리에 가깝다. 깊이는 딱딱한 중립 드롭섀도우가 아니라 컬러 글로우와 블러가 만드는 유리질감으로 표현되고, 모서리는 예외 없이 둥글며, 보더는 항상 화이트 헤어라인이다. 액센트인 인디고/바이올릿은 팔레트의 극히 일부에서만 등장해 그 희소성 자체가 존재감을 만든다.

이 문서는 코드에 이미 구현된 현재 상태를 있는 그대로 기록한 것이다. "황금정원"이라는 이름은 따뜻한 골드 톤을 연상시키지만, 실제 구현은 차가운 인디고/바이올릿 밤 팔레트다 — 이 간극은 확인된 것이며, 지금은 임의로 보정하지 않는다(따뜻한 톤으로의 전환은 별도의 리디자인 논의가 필요하다).

**Key Characteristics:**
- 어두운 네이비 그라디언트 배경 위에 떠다니는 인디고/바이올릿 빛 덩어리
- `backdrop-blur` 글래스 카드 + 화이트 헤어라인 보더
- 완전히 둥근 형태 언어 — 버튼·배지·카드 전부 `rounded-full`/`2xl`/`3xl`
- 액센트는 드물게, 깊이는 컬러 글로우로
- Lora 세리프 헤드라인 + Inter 산세리프 본문의 에디토리얼 페어링
- 모든 진입 모션이 하나의 이징 곡선을 공유

## Colors

거의 무채색에 가까운 네이비/화이트/슬레이트 베이스 위에, 인디고→바이올릿 그라디언트 액센트를 아주 드물게 얹는 절제된 팔레트.

### Primary
- **깊은 밤의 인디고 (Midnight Indigo)** (#6366f1): 주요 CTA 버튼 배경, 히어로 그라디언트 텍스트의 시작색, 태그 칩 텍스트/보더, 마스코트 몸통 그라디언트 시작점.
- 인디고의 32% 불투명 버전인 **인디고 글로우 (Indigo Glow)** (`rgba(99, 102, 241, 0.32)`)는 버튼과 타임라인 점 아래 번지는 컬러 섀도우로만 쓰이고, 채워진 배경으로는 절대 쓰이지 않는다.

### Secondary
- **황혼의 바이올릿 (Twilight Violet)** (#7c3aed): 인디고와 짝을 이루는 그라디언트 종점 — 히어로 헤드라인 그라디언트 텍스트, 마스코트 몸통 그라디언트 끝점, 배경 두 번째 빛 덩어리에 쓰인다.

### Neutral
- **심연 네이비 (Abyss Navy)** (#0f172a): 배경 그라디언트에서 가장 어두운 지점(상단).
- **베이스 네이비 (Base Navy)** (#131a30): 페이지 기본 배경이자, 내비게이션 바 배경(80% 불투명)의 바탕색.
- **엘리베이티드 네이비 (Elevated Navy)** (#192134): 테마 토큰으로 정의만 되어 있고 현재 어떤 컴포넌트에도 쓰이지 않는 예약된 표면색 — 향후 별도로 들뜬 표면이 필요할 때를 위한 자리로 보인다.
- **페이퍼 화이트 (Paper White)** (#ffffff): 헤드라인과 강조 텍스트.
- **슬레이트 뮤트 (Slate Muted)** (#94a3b8): 보조 설명, 부제, 카드 본문.
- **글래스 서피스 (Glass Surface)** 3단계 — 화이트 5%(`rgba(255,255,255,0.05)`, 기본 카드), 7%(`rgba(255,255,255,0.07)`, 강조 카드·배지·CTA 푸터), 10%(`rgba(255,255,255,0.10)`, 호버).
- **헤어라인 보더 (Hairline Border)** — 화이트 12%(`rgba(255,255,255,0.12)`, 기본), 18%(`rgba(255,255,255,0.18)`, 세컨더리 버튼처럼 더 또렷해야 하는 곳).

### Named Rules
**The Rare Accent Rule.** 인디고/바이올릿은 버튼, 태그 칩, 헤드라인 속 한 구절, 마스코트처럼 화면의 아주 작은 부분에만 등장한다. 나머지는 네이비/화이트/슬레이트로 남겨 액센트의 희소성 자체가 눈에 띄게 만든다.

## Typography

**Display Font:** Lora (with Georgia, serif)
**Body Font:** Inter (with system-ui, sans-serif)

**Character:** 격식 있는 세리프 헤드라인과 차분한 산세리프 본문이 대비를 이루는 에디토리얼 페어링 — 헤드라인이 목소리를 내고, 본문은 여백으로 숨을 고른다.

### Hierarchy
- **Display** (600, `clamp(2.25rem, 6vw, 4.5rem)`, leading-tight): 히어로 h1 전용. 모바일 36px에서 데스크톱 72px까지 반응형으로 커진다.
- **Headline** (600, 1.875rem → 2.25rem): 각 섹션의 h2 제목("작은 습관이 만든 변화" 등).
- **Title** (600, 1.125–1.25rem): 카드·타임라인 안의 h3 소제목.
- **Body** (400, 1rem 기본·leading-relaxed; 히어로 인트로는 1.125rem, 카드 설명은 0.875rem 변형): 문단형 설명 텍스트. 컨테이너 폭 자체를 좁게 잡아(`max-w-xl` 등) 줄 길이를 짧게 유지한다.
- **Label** (500, 0.75rem, letter-spacing 0.2em, uppercase): 히어로 배지·스크롤 인디케이터 같은 아주 짧은 대문자 라벨. 태그 칩은 같은 크기(0.75rem, 500)를 쓰되 대문자·트래킹 없이 더 조용하게 쓰인다.

### Named Rules
**The Serif-Signals-Voice Rule.** Lora는 오직 제목 레벨(h1/h2/h3)에만 등장하고, 본문·라벨·버튼 텍스트는 항상 Inter다 — 세리프가 나오는 순간이 "필자가 직접 말하는 순간"이라는 신호가 된다.

## Layout

모든 섹션은 `mx-auto`로 가운데 정렬된 좁은 컬럼(섹션별 `max-w-2xl`~`max-w-5xl`) 안에 콘텐츠를 담고, 양옆에는 1.5rem(`px-6`) 여백을 둔다 — 화면 전체 폭을 채우지 않는, 읽기 중심의 좁은 리듬이다.

섹션 간 수직 리듬은 8rem(`py-32`)로 고정되어, 스크롤할 때 각 섹션이 충분히 숨 쉴 공간을 갖는다. 카드형 콘텐츠(Pillars, PostPreview)는 모바일 1열 → `sm` 이상에서 2열 그리드(`gap-5`, 1.25rem)로 전환된다. WhyIWrite 섹션만 예외적으로 그리드가 아니라 왼쪽 헤어라인 보더 + 들여쓰기로 만든 세로 타임라인을 쓴다 — 카드들이 시간 순서를 갖는 유일한 곳이다. 내비게이션은 그리드에 속하지 않는 고정(fixed) 플로팅 필로, 콘텐츠 위에 항상 떠 있다.

## Elevation & Depth

전통적인 중립 드롭섀도우 기반 elevation은 쓰지 않는다. 깊이는 세 가지 수단으로 표현된다: (1) 배경에서 부드럽게 떠다니는 `blur-3xl` 처리된 인디고/바이올릿 빛 덩어리가 만드는 대기적 깊이, (2) 카드·배지·내비게이션에 일관되게 쓰이는 `backdrop-blur-xl` + 반투명 화이트 채움으로 만드는 유리질감의 층, (3) 인터랙티브 액센트 요소(주요 버튼, 타임라인 점)에만 쓰이는 컬러 글로우 섀도우. 내비게이션 바만 예외적으로 중립색 소프트 섀도우를 써서 스크롤되는 콘텐츠 위로 들려 있다는 느낌을 준다.

### Shadow Vocabulary
- **버튼 글로우 (Button Glow)** (`box-shadow: 0 0 40px -8px var(--accent-glow)`): 주요 CTA 버튼 아래 액센트 색이 은은하게 번지는 느낌.
- **타임라인 점 글로우 (Timeline Dot Glow)** (`box-shadow: 0 0 12px 2px var(--accent-glow)`): WhyIWrite의 타임라인 점을 작은 빛의 점처럼 보이게 한다.
- **내비 리프트 섀도우 (Nav Lift Shadow)** (`box-shadow: 0 8px 32px rgba(0,0,0,0.35)`): 시스템에서 유일한 중립색 섀도우, 고정 내비게이션을 콘텐츠 위로 들어올린다.

### Named Rules
**The Glow-Not-Shadow Rule.** 깊이는 거의 항상 컬러 글로우나 블러 기반 유리질감으로 표현되고, 중립 드롭섀도우는 내비게이션 한 곳에만 예외적으로 허용된다.

## Shapes

형태 언어는 예외 없이 둥글다. 인터랙티브 크롬(버튼, 배지, 태그 칩, 내비게이션 필)은 전부 완전한 필 형태(`rounded-full`, 9999px)이고, 콘텐츠 카드는 `rounded-2xl`(1rem), 페이지에서 가장 중요한 클로징 블록인 CTA 푸터 카드만 한 단계 더 넉넉한 `rounded-3xl`(1.5rem)을 받는다. 보더는 항상 저채도 화이트 헤어라인(12~18% 불투명도)이며, 직각 모서리나 진한 실선 보더는 시스템 어디에도 없다. 마스코트 캐릭터의 몸통 실루엣(둥근 캡슐형 SVG)도 같은 형태 언어를 반복한다.

### Named Rules
**The No-Sharp-Corners Rule.** 시스템 안에 반경 0인 모서리는 존재하지 않는다 — 가장 작은 요소(태그 칩)부터 가장 큰 컨테이너(CTA 카드)까지 전부 둥글다.

## Components

### Buttons
- **Shape:** 완전한 필 형태(`rounded-full`, 9999px).
- **Primary:** 배경 {colors.midnight-indigo}, 텍스트 흰색, 패딩 14px 32px, 아래에 인디고 글로우 섀도우. 호버 시 배경이 90% 불투명도로 살짝 어두워지고, hover 1.02배·tap 0.98배로 스케일되는 촉각적 모션 반응이 있다.
- **Ghost(Secondary):** 배경 투명, 18% 화이트 헤어라인 보더, 텍스트 흰색, 동일 패딩. 호버 시 7% 화이트로 은은하게 채워진다.
- 두 버튼 모두 폰트 굵기 500(font-medium)이고, 링크 태그(`<a>`)를 버튼처럼 쓰기 때문에 커서를 명시적으로 포인터로 지정한다.

### Chips / Tags
- **Style:** 배경 인디고 10%(`rgba(99,102,241,0.1)`), 보더 인디고 30%, 텍스트 인디고, 완전한 필 형태, 작은 패딩(약 4px 12px).
- **State:** 선택/비선택 상태 없음 — 순수 라벨용.
- 히어로 배지("새벽 기상 · 확언 · 자기암시로 바꾼 삶")는 같은 필 형태를 쓰지만 색은 중립(7% 화이트)이다 — 칩은 항상 액센트색, 배지는 항상 중립색이라는 암묵적 구분이 있다.

### Cards / Containers
- **Corner Style:** `rounded-2xl`(1rem); CTA 푸터 카드만 `rounded-3xl`(1.5rem).
- **Background:** 5%(기본) → 7%(강조/배지/푸터) → 10%(호버) 화이트 오버레이 단계.
- **Shadow Strategy:** 없음 — `backdrop-blur-xl` + 헤어라인 보더가 깊이를 대신한다.
- **Border:** 12% 화이트 헤어라인.
- **Internal Padding:** 1.5–1.75rem(p-6/p-7); CTA 푸터 카드는 2rem/4rem(px-8 py-16)로 훨씬 여유롭다.

### Navigation
- 고정(fixed) 플로팅 필 형태, 상단 중앙 정렬, 최대 폭 5xl.
- 배경은 베이스 네이비의 80% 불투명 버전 + `backdrop-blur-xl`, 12% 화이트 헤어라인 보더, 시스템에서 유일한 중립색 리프트 섀도우.
- 로고는 Lora 세리프, 우측에는 항상 프라이머리 버튼 하나("블로그 방문하기")만 있다 — 내비게이션 메뉴 항목 목록은 없다.
- 등장 시 위에서 아래로 슬라이드+페이드(-20px → 0, opacity 0→1)되는 진입 모션이 있다.

### Mascot (Signature Component)
- 여러 포즈(잎/손흔들기/깃발/하트/메모)를 가진 커스텀 SVG 캐릭터로, 섹션마다 다른 포즈로 등장해 그 섹션의 정서를 대신 표현하는 시그니처 요소다.
- 몸통은 인디고→바이올릿 그라디언트가 채워진 둥근 캡슐 실루엣, 눈은 주기적으로 깜빡이고, 몸 전체가 부드럽게 위아래로 떠다니는 루프 애니메이션을 갖는다.
- 순수 장식 요소이므로 `aria-hidden`과 `pointer-events-none`이 항상 적용되고, `sm` 미만 화면에서는 숨겨진다.

### Reveal (Signature Motion Pattern)
- 콘텐츠 블록마다 반복되는 스크롤 등장 패턴: opacity 0→1, y 24px→0, 뷰포트에 처음 들어올 때 한 번만 실행.
- 카드가 여러 개일 때는 인덱스 순서대로 0.08~0.1초씩 지연을 주어 계단식으로 나타난다.

### Named Rules
**The One Ease Rule.** 히어로 진입, 내비게이션 진입, 스크롤 리빌까지 시스템의 모든 진입 모션이 동일한 커스텀 이징 곡선(`cubic-bezier(0.16, 1, 0.3, 1)`)을 공유한다 — 이 곡선 하나가 사이트 전체의 "움직임의 목소리"다.

## Do's and Don'ts

### Do:
- **Do** 인터랙티브 요소와 컨테이너 모두 `rounded-full` 또는 `rounded-2xl`/`3xl`만 쓴다.
- **Do** 깊이가 필요할 때는 `backdrop-blur-xl` + 화이트 오버레이 + 헤어라인 보더 조합을 먼저 쓰고, 액센트 요소에만 컬러 글로우 섀도우를 더한다.
- **Do** 진입/등장 모션에는 `cubic-bezier(0.16, 1, 0.3, 1)` 이징을 쓴다.
- **Do** 인디고/바이올릿 액센트는 CTA, 태그, 그라디언트 텍스트, 마스코트처럼 화면의 작은 부분에만 쓴다.
- **Do** 헤드라인 레벨(h1/h2/h3)에는 항상 Lora, 본문/라벨/버튼에는 항상 Inter를 쓴다.

### Don't:
- **Don't** 직각 모서리나 진한 실선 보더를 쓰지 않는다 — 헤어라인 화이트 보더만 쓴다.
- **Don't** 중립색 드롭섀도우를 카드나 버튼에 쓰지 않는다(내비게이션 리프트 섀도우가 유일한 예외).
- **Don't** 배경 전체를 액센트 색으로 채우지 않는다 — 액센트는 항상 텍스트, 좁은 배경(10% 이하), 또는 글로우로만 등장한다.
- **Don't** "황금정원"이라는 이름 때문에 임의로 골드/옐로 톤을 넣지 않는다 — 현재 구현된 팔레트는 인디고/바이올릿 기반이며, 이 문서는 그 실제 구현을 기록한 것이다. 따뜻한 톤으로의 전환은 별도의 리디자인 논의를 거쳐야 한다.
