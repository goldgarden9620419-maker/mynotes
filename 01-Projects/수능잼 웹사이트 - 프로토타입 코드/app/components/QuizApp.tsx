"use client";

import { useMemo, useState } from "react";
import problemsData from "../../data/problems.json";

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

const problems = problemsData as Problem[];

const SUBJECT_LABEL: Record<Problem["subject"], string> = {
  english: "영어",
  math: "수학",
};

function latestDateFor(subject: Problem["subject"]) {
  const dates = problems.filter((p) => p.subject === subject).map((p) => p.date);
  return dates.reduce((a, b) => (b > a ? b : a), dates[0] ?? "");
}

function formatDate(iso: string) {
  if (!iso) return "";
  const [, m, d] = iso.split("-");
  return `${Number(m)}월 ${Number(d)}일`;
}

export default function QuizApp() {
  const [subject, setSubject] = useState<Problem["subject"] | null>(null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);

  const todaySet = useMemo(() => {
    if (!subject) return [];
    const latest = latestDateFor(subject);
    return problems.filter((p) => p.subject === subject && p.date === latest);
  }, [subject]);

  const current = todaySet[index];
  const isDone = subject !== null && index >= todaySet.length;

  function pickSubject(s: Problem["subject"]) {
    setSubject(s);
    setIndex(0);
    setSelected(null);
    setScore(0);
  }

  function handleChoice(i: number) {
    if (selected !== null || !current) return;
    setSelected(i);
    if (i === current.answerIndex) setScore((s) => s + 1);
  }

  function next() {
    setSelected(null);
    setIndex((i) => i + 1);
  }

  function backToHome() {
    setSubject(null);
    setIndex(0);
    setSelected(null);
    setScore(0);
  }

  if (!subject) {
    return (
      <div className="w-full max-w-md">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <button
            onClick={() => pickSubject("english")}
            className="rounded-2xl border border-border bg-card p-6 text-left transition hover:border-accent"
          >
            <div className="text-sm text-muted">{formatDate(latestDateFor("english"))} 문제</div>
            <div className="mt-1 text-2xl font-bold">영어 5문제</div>
            <div className="mt-2 text-sm text-muted">어법 · 빈칸추론 · 순서 · 문장삽입 · 주제</div>
          </button>
          <button
            onClick={() => pickSubject("math")}
            className="rounded-2xl border border-border bg-card p-6 text-left transition hover:border-accent"
          >
            <div className="text-sm text-muted">{formatDate(latestDateFor("math"))} 문제</div>
            <div className="mt-1 text-2xl font-bold">수학 5문제</div>
            <div className="mt-2 text-sm text-muted">수열 · 미분 · 적분 · 확률과통계 · 삼각함수</div>
          </button>
        </div>
      </div>
    );
  }

  if (isDone) {
    return (
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 text-center">
        <div className="text-3xl">🎉</div>
        <h2 className="mt-3 text-xl font-bold">오늘의 {SUBJECT_LABEL[subject]} 문제 완료!</h2>
        <p className="mt-2 text-muted">
          {todaySet.length}문제 중 <span className="text-accent font-semibold">{score}개</span> 정답
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={backToHome}
            className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-foreground"
          >
            다른 과목 풀기
          </button>
        </div>
        <p className="mt-4 text-xs text-muted">내일 또 새로운 문제로 찾아올게요.</p>
      </div>
    );
  }

  if (!current) return null;

  const isCorrect = selected !== null && selected === current.answerIndex;

  return (
    <div className="w-full max-w-md">
      <div className="mb-3 flex items-center justify-between text-sm text-muted">
        <button onClick={backToHome} className="hover:text-foreground">
          ← 과목 선택
        </button>
        <span>
          {SUBJECT_LABEL[subject]} {index + 1} / {todaySet.length}
        </span>
      </div>

      <div className="rounded-2xl border border-border bg-card p-6">
        <span className="inline-block rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-accent">
          {current.type}
        </span>
        <p className="mt-3 text-sm font-medium">{current.prompt}</p>

        {current.givenSentence && (
          <div className="mt-3 rounded-xl border border-border bg-secondary p-3 text-sm italic">
            {current.givenSentence}
          </div>
        )}

        {current.passage && (
          <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-foreground/90">
            {current.passage}
          </p>
        )}

        <div className="mt-5 flex flex-col gap-2">
          {current.choices.map((choice, i) => {
            const isAnswer = i === current.answerIndex;
            const isPicked = i === selected;
            let style = "border-border bg-secondary";
            if (selected !== null) {
              if (isAnswer) style = "border-accent bg-accent/10 text-accent";
              else if (isPicked) style = "border-wrong bg-wrong/10 text-wrong";
            }
            return (
              <button
                key={i}
                onClick={() => handleChoice(i)}
                disabled={selected !== null}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition ${style}`}
              >
                <span className="mr-2 text-muted">{i + 1}.</span>
                {choice}
              </button>
            );
          })}
        </div>

        {selected !== null && (
          <div className="mt-5">
            <p className={`font-semibold ${isCorrect ? "text-accent" : "text-wrong"}`}>
              {isCorrect ? "정답입니다!" : "틀렸어요 — 해설을 확인해보세요"}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted">{current.explanation}</p>
            <button
              onClick={next}
              className="mt-4 w-full rounded-xl bg-accent px-5 py-3 font-semibold text-accent-foreground"
            >
              다음 문제 →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
