"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { WRONG_ANSWERS_KEY } from "../components/reviewStorage";
import { renderUnderlinedText } from "../components/renderUnderline";

type Problem = {
  id: string;
  subject: "english" | "math";
  type: string;
  date: string;
  prompt: string;
  passage?: string;
  givenSentence?: string;
  choices: string[];
  answerIndex: number;
  explanation: string;
  vocab?: { word: string; meaning: string }[];
  concept?: string;
};

export default function ReviewPage() {
  const [problems, setProblems] = useState<Problem[] | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem(WRONG_ANSWERS_KEY);
    setProblems(raw ? (JSON.parse(raw) as Problem[]) : []);
  }, []);

  if (problems === null) return null;

  if (problems.length === 0) {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center px-6 py-16 text-center">
        <h1 className="text-xl font-bold">오답 복습이란?</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          아직 저장된 틀린 문제가 없어요. 이 페이지는 수능잼에서 문제를 풀다가 틀린 문제만 자동으로
          모아서 다시 보여주는 오답노트예요. 정답과 해설을 눈으로만 확인하고 넘어가면 금방 잊어버리기
          쉬운데, 틀린 문제만 따로 모아두면 짧은 시간에 내가 약한 유형만 골라서 복습할 수 있어요.
        </p>
        <div className="mt-6 flex flex-col gap-3 text-left">
          <div className="rounded-2xl border border-border bg-card p-4">
            <h2 className="text-sm font-semibold">오답노트는 어떻게 쌓이나요?</h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">
              메인 페이지에서 오늘의 문제를 풀다가 틀리면, 그 문제가 자동으로 이 페이지 목록에
              추가돼요. 따로 저장 버튼을 누를 필요는 없어요.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <h2 className="text-sm font-semibold">PDF로도 인쇄할 수 있나요?</h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">
              네. 문제가 쌓인 뒤 이 페이지 상단의 &ldquo;PDF로 저장(인쇄)&rdquo; 버튼을 누르면, 틀린
              문제와 해설만 깔끔하게 모아 인쇄하거나 PDF로 저장할 수 있어요.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <h2 className="text-sm font-semibold">기록은 어디에 저장되나요?</h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">
              서버가 아니라 지금 사용 중인 브라우저에만 임시로 저장돼요. 그래서 다른 기기나 브라우저로
              접속하면 이 목록은 비어 있어요.
            </p>
          </div>
        </div>
        <Link href="/" className="mt-8 text-sm text-accent hover:underline">
          ← 문제 풀러 가기
        </Link>
      </div>
    );
  }

  return (
    <div className="review-page mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-10">
      <div className="mb-6 flex items-center justify-between print:hidden">
        <Link href="/" className="text-sm text-muted hover:text-accent">
          ← 메인으로 돌아가기
        </Link>
        <button
          onClick={() => window.print()}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition active:scale-[0.98]"
        >
          📄 PDF로 저장(인쇄)
        </button>
      </div>

      <h1 className="mb-1 text-xl font-bold">오늘 틀린 문제 복습</h1>
      <p className="mb-8 text-sm text-muted">
        수능잼(suneungjam.com) · {new Date().toLocaleDateString("ko-KR")} · 총 {problems.length}문제
      </p>

      <div className="flex flex-col gap-8">
        {problems.map((p, idx) => (
          <div key={p.id} className="review-item border-b border-border pb-8 last:border-none">
            <span className="review-badge inline-block rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-accent">
              {idx + 1}. {p.type}
            </span>
            <p className="mt-3 text-sm font-medium">{p.prompt}</p>

            {p.givenSentence && (
              <div className="mt-3 rounded-xl border border-border bg-secondary px-3 py-2 text-sm italic">
                {p.givenSentence}
              </div>
            )}

            {p.passage && (
              <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">
                {renderUnderlinedText(p.passage)}
              </p>
            )}

            {p.vocab && p.vocab.length > 0 && (
              <p className="mt-3 text-xs leading-relaxed text-muted">
                {p.vocab.map((v, i) => (
                  <span key={v.word}>
                    {i > 0 && " · "}
                    <span className="italic">{v.word}</span> {v.meaning}
                  </span>
                ))}
              </p>
            )}

            <div className="mt-4 flex flex-col gap-1.5">
              {p.choices.map((choice, i) => (
                <div
                  key={i}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    i === p.answerIndex
                      ? "review-answer border-accent bg-accent/10 font-semibold text-accent"
                      : "border-border"
                  }`}
                >
                  {i + 1}. {choice}
                  {i === p.answerIndex && " ✓ 정답"}
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-xl bg-secondary p-3">
              <p className="text-xs font-semibold text-muted">해설</p>
              {p.concept && (
                <p className="mt-1 text-xs font-medium text-accent">💡 {p.concept}</p>
              )}
              <p className="mt-1 text-sm leading-relaxed">{p.explanation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
