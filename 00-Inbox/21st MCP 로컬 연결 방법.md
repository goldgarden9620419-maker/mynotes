---
tags: [Claude Code, MCP, 개발환경]
created: 2026-08-07
---

# 21st MCP 로컬 연결 방법

21st.dev의 Magic MCP(AI로 UI 컴포넌트 생성해주는 도구)를 Claude Code에 연결하는 방법.

## 준비물
- [21st.dev/mcp](https://21st.dev/mcp) 계정 + API 키

## 연결 명령어
PowerShell(또는 터미널)에서 프로젝트 폴더로 이동한 뒤:

```
claude mcp add --transport http 21st https://21st.dev/api/mcp --header "x-api-key: <API 키>"
```

## 확인
```
claude mcp list
```
`21st: ... ✓ Connected` 로 뜨면 성공.

## 주의사항
- API 키는 채팅에 평문으로 남기면 안 됨 → 노출됐다면 21st.dev 보안 설정에서 재발급(rotate)
- 클라우드/원격 Claude Code 세션은 조직 네트워크 정책으로 외부 도메인(21st.dev 등)이 막혀 있을 수 있음 → 이 경우 로컬 PC에서 직접 연결해야 함

## 관련
- [[website 디자인 스킬 설치 (design-taste-frontend, impeccable)]]
