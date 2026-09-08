This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

배포: Vercel 프로젝트 `suneungjam`이 이 저장소(`mynotes`)의 `claude/side-income-ideas-9b5crk` 브랜치, Root Directory `01-Projects/수능잼 웹사이트 - 프로토타입 코드`를 바라보도록 연결되어 있습니다.

## 쓰레드(Threads) 자동 발행

`app/api/cron/threads/route.ts`를 Vercel Cron(`vercel.json`, 매일 10:10 KST)이 호출해 `data/threads-queue.json`에서 오늘 날짜(`scheduledDate`, KST)와 정확히 일치하는 대기 항목을 Threads Graph API로 발행합니다.

필요한 Vercel 환경변수:

- `THREADS_ACCESS_TOKEN` — Threads 장기 액세스 토큰 (`threads_basic`, `threads_content_publish` 권한)
- `THREADS_USER_ID` — 위 토큰으로 `GET /v1.0/me?fields=id`를 호출해 확인한 Threads 사용자 ID
- `CRON_SECRET` — 임의 문자열. 설정하면 Vercel Cron이 자동으로 `Authorization: Bearer <값>`을 실어 보내 외부 임의 호출을 막아줍니다

새 글은 `01-Projects/수능잼 홍보/쓰레드 글 모음.md`에 초안을 쓴 뒤 `data/threads-queue.json`에 `{id, status: "pending", scheduledDate, text}`로 추가 → push. 발행이 끝난 항목은 큐에서 지워서 정리합니다(상태를 별도로 저장하지 않고 날짜 일치로만 발행하므로 재발행 방지를 위해 큐를 계속 비워줘야 합니다).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
