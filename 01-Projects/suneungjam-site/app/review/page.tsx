"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { WRONG_ANSWERS_KEY } from "../components/reviewStorage";

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
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-6 py-16 text-center">
        <p className="text-muted">저장된 틀린 문제가 없어요.</p>
        <Link href="/" className="mt-4 text-sm text-accent hover:underline">
          ← 메인으로 돌아가기
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
              <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{p.passage}</p>
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
              <p className="mt-1 text-sm leading-relaxed">{p.explanation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
