import { NextResponse } from "next/server";
import queue from "../../../../data/threads-queue.json";

export const dynamic = "force-dynamic";

const THREADS_API_BASE = "https://graph.threads.net/v1.0";

type QueueItem = {
  id: string;
  status: "pending" | "published";
  scheduledDate: string; // KST YYYY-MM-DD
  text: string;
};

function todayKST(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Seoul" });
}

async function publishToThreads(accessToken: string, userId: string, text: string) {
  const createParams = new URLSearchParams({
    media_type: "TEXT",
    text,
    access_token: accessToken,
  });
  const createRes = await fetch(`${THREADS_API_BASE}/${userId}/threads?${createParams}`, {
    method: "POST",
  });
  const createData = await createRes.json();
  if (!createRes.ok || !createData.id) {
    throw new Error(`Threads 게시물 생성 실패: ${JSON.stringify(createData)}`);
  }

  const publishParams = new URLSearchParams({
    creation_id: createData.id,
    access_token: accessToken,
  });
  const publishRes = await fetch(`${THREADS_API_BASE}/${userId}/threads_publish?${publishParams}`, {
    method: "POST",
  });
  const publishData = await publishRes.json();
  if (!publishRes.ok || !publishData.id) {
    throw new Error(`Threads 게시 실패: ${JSON.stringify(publishData)}`);
  }
  return publishData.id as string;
}

// Vercel Cron이 매일 호출합니다. 대기열(data/threads-queue.json)에서
// scheduledDate가 오늘(KST)과 정확히 일치하는 대기 항목이 있으면 그것만 발행합니다.
// 별도 DB 없이 정적으로 배포된 큐 파일만 읽으므로, 발행 여부를 파일에 다시
// 기록하지는 않습니다(서버리스 파일시스템은 쓰기가 유지되지 않음) — 대신
// "오늘 날짜와 정확히 일치할 때만" 발행해서 같은 항목이 다음 날 다시
// 발행되는 일을 막습니다. 발행 완료 후에는 이 파일에서 해당 항목을 지우고
// 커밋/푸시해 정리해 주세요.
export async function GET(request: Request) {
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret) {
    const authHeader = request.headers.get("authorization");
    if (authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
  }

  const accessToken = process.env.THREADS_ACCESS_TOKEN;
  const userId = process.env.THREADS_USER_ID;
  if (!accessToken || !userId) {
    return NextResponse.json(
      { error: "환경변수 미설정: THREADS_ACCESS_TOKEN / THREADS_USER_ID" },
      { status: 500 }
    );
  }

  const today = todayKST();
  const items = queue as QueueItem[];
  const nextItem = items.find((item) => item.status === "pending" && item.scheduledDate === today);

  if (!nextItem) {
    return NextResponse.json({ message: "오늘 발행할 대기 항목 없음", date: today });
  }

  try {
    const threadsPostId = await publishToThreads(accessToken, userId, nextItem.text);
    return NextResponse.json({
      message: "발행 완료 — data/threads-queue.json에서 이 항목을 지우고 커밋해 주세요",
      id: nextItem.id,
      threadsPostId,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
