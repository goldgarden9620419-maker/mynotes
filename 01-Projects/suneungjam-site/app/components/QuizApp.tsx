"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { MotionConfig, animate, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import problemsData from "../../data/problems.json";
import Teacher from "./Teacher";
import { WRONG_ANSWERS_KEY } from "./reviewStorage";
import { renderUnderlinedText } from "./renderUnderline";
import StarField from "./StarField";
import { useBurst } from "./useBurst";

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

const TYPE_TIP: Record<string, string> = {
  어법: "밑줄 다섯 개 중에 딱 하나만 문법이 틀렸어. 하나씩 침착하게 보자!",
  빈칸추론: "빈칸 문제는 흐름이 생명이야. 앞뒤 문장을 꼭 같이 봐줘.",
  순서: "However, As a result 같은 연결어를 먼저 찾으면 순서가 보여.",
  문장삽입: "주어진 문장의 대명사·연결어가 어디로 이어지는지가 힌트야.",
  주제: "글 전체를 관통하는 한 문장을 찾는다는 느낌으로 읽어보자.",
  수열: "등차수열이면 공차부터, 등비수열이면 공비부터 구하는 게 먼저야.",
  미분: "극값은 f'(x) = 0이 되는 지점부터 찾는 거, 기억하지?",
  적분: "곡선과 x축 사이 넓이는 교점을 먼저 구하는 게 순서야.",
  확률과통계: "경우의 수를 나눌 때는 조건을 정확히 나누는 게 핵심이야.",
  삼각함수: "삼각함수 방정식은 치환해서 이차방정식으로 바꾸는 게 자주 쓰는 방법이야.",
};

const CORRECT_LINES = ["정답이야! 역시 잘하네!", "맞았어, 완벽해!", "오, 바로 맞히네!"];
const WRONG_LINES = ["괜찮아, 같이 해설 보면서 이해해보자.", "다음엔 맞을 수 있어, 해설부터 볼까?"];

function CountUp({ to }: { to: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const c = animate(0, to, {
      duration: reduce || to === 0 ? 0.001 : 0.9,
      delay: reduce ? 0 : 0.25,
      ease: "easeOut",
      onUpdate: (v) => setN(Math.round(v)),
    });
    return () => c.stop();
  }, [to]);
  return <>{n}</>;
}

export default function QuizApp() {
  const router = useRouter();
  const [subject, setSubject] = useState<Problem["subject"] | null>(null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [wrongAnswers, setWrongAnswers] = useState<Problem[]>([]);
  const { fire, Canvas } = useBurst();

  const todaySet = useMemo(() => {
    if (!subject) return [];
    const latest = latestDateFor(subject);
    return problems.filter((p) => p.subject === subject && p.date === latest);
  }, [subject]);

  const current = todaySet[index];
  const isDone = subject !== null && index >= todaySet.length;

  useEffect(() => {
    if (isDone && todaySet.length > 0 && score > 0) fire(score === todaySet.length ? "perfect" : "finish");
  }, [isDone, score, todaySet.length, fire]);

  const shell = (children: ReactNode) => (
    <MotionConfig reducedMotion="user">
      <StarField />
      {Canvas}
      {children}
    </MotionConfig>
  );

  function pickSubject(s: Problem["subject"]) {
    setSubject(s);
    setIndex(0);
    setSelected(null);
    setScore(0);
    setWrongAnswers([]);
  }

  function handleChoice(i: number, el?: HTMLElement) {
    if (selected !== null || !current) return;
    setSelected(i);
    if (i === current.answerIndex) {
      setScore((s) => s + 1);
      const r = el?.getBoundingClientRect();
      fire("correct", r ? r.left + r.width / 2 : undefined, r ? r.top + r.height / 2 : undefined);
    } else {
      setWrongAnswers((w) => [...w, current]);
    }
  }

  function downloadWrongAnswersPdf() {
    sessionStorage.setItem(WRONG_ANSWERS_KEY, JSON.stringify(wrongAnswers));
    router.push("/review");
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
    setWrongAnswers([]);
  }

  if (!subject) {
    return shell(
      <div className="w-full max-w-md">
        <div className="mb-3 sm:mb-5">
          <Teacher size="sm" message="안녕! 짬날 때마다 5문제씩 풀어볼까? 어떤 과목부터 해볼래?" />
        </div>
        <div className="grid grid-cols-2 gap-2.5 sm:gap-4">
          <motion.button
            onClick={() => pickSubject("english")}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1, ease: "easeOut" }}
            whileHover={{ y: -4, boxShadow: "0 8px 28px -8px rgba(52,211,153,0.45)" }}
            whileTap={{ scale: 0.97 }}
            className="rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background sm:p-6"
          >
            <div className="text-xs text-muted sm:text-sm">{formatDate(latestDateFor("english"))} 문제</div>
            <div className="mt-1 text-xl font-bold sm:text-2xl">영어 5문제</div>
            <div className="mt-1.5 text-xs text-muted sm:mt-2 sm:text-sm">어법 · 빈칸추론 · 순서 · 문장삽입 · 주제</div>
          </motion.button>
          <motion.button
            onClick={() => pickSubject("math")}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.2, ease: "easeOut" }}
            whileHover={{ y: -4, boxShadow: "0 8px 28px -8px rgba(52,211,153,0.45)" }}
            whileTap={{ scale: 0.97 }}
            className="rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background sm:p-6"
          >
            <div className="text-xs text-muted sm:text-sm">{formatDate(latestDateFor("math"))} 문제</div>
            <div className="mt-1 text-xl font-bold sm:text-2xl">수학 5문제</div>
            <div className="mt-1.5 text-xs text-muted sm:mt-2 sm:text-sm">수열 · 미분 · 적분 · 확률과통계 · 삼각함수</div>
          </motion.button>
        </div>
      </div>,
    );
  }

  if (isDone) {
    const ratio = score / todaySet.length;
    const wrapUpLine =
      ratio === 1
        ? "다 맞혔어! 오늘 짬 시간 완벽하게 썼다!"
        : ratio >= 0.6
          ? "오늘도 수고했어! 이 페이스면 금방 늘 거야."
          : "틀린 건 해설로 다 짚었으니 괜찮아. 내일 또 도전해보자!";
    return shell(
      <div className="w-full max-w-md">
        <div className="mb-5">
          <Teacher message={`${wrapUpLine} 내일 또 새로운 문제로 만나자.`} />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 220, damping: 20 }}
          className="rounded-2xl border border-border bg-card p-8 text-center"
        >
          <motion.div
            className="text-3xl"
            initial={{ scale: 0, rotate: -25 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 12, delay: 0.15 }}
          >
            🎉
          </motion.div>
          <h2 className="mt-3 text-xl font-bold">오늘의 {SUBJECT_LABEL[subject]} 문제 완료!</h2>
          <p className="mt-2 text-muted">
            {todaySet.length}문제 중 <span className="text-accent font-semibold"><CountUp to={score} />개</span> 정답
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            {wrongAnswers.length > 0 && (
              <button
                onClick={downloadWrongAnswersPdf}
                className="rounded-xl border border-border px-5 py-3 font-semibold transition active:scale-[0.98] hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                📄 틀린 문제 PDF로 저장 ({wrongAnswers.length}개)
              </button>
            )}
            <button
              onClick={backToHome}
              className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-foreground transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              다른 과목 풀기
            </button>
          </div>
        </motion.div>
      </div>,
    );
  }

  if (!current) return null;

  const isCorrect = selected !== null && selected === current.answerIndex;
  const feedbackLine = selected === null
    ? ""
    : isCorrect
      ? CORRECT_LINES[index % CORRECT_LINES.length]
      : WRONG_LINES[index % WRONG_LINES.length];

  const progress = (index + (selected !== null ? 1 : 0)) / todaySet.length;

  return shell(
    <div className="w-full max-w-md">
      <div className="mb-3 flex items-center justify-between text-sm text-muted">
        <button
          onClick={backToHome}
          className="rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent hover:text-foreground"
        >
          ← 과목 선택
        </button>
        <span>
          {SUBJECT_LABEL[subject]} {index + 1} / {todaySet.length}
        </span>
      </div>

      <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-secondary" role="progressbar" aria-valuemin={0} aria-valuemax={todaySet.length} aria-valuenow={index + (selected !== null ? 1 : 0)} aria-label="진행도">
        <motion.div
          className="h-full rounded-full bg-accent"
          initial={false}
          animate={{ width: `${progress * 100}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
      </div>

      <div className="mb-4">
        <Teacher
          size="sm"
          message={selected === null ? (TYPE_TIP[current.type] ?? "이번 문제도 차근차근 풀어보자!") : feedbackLine}
        />
      </div>

      <motion.div
        key={current.id}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="rounded-2xl border border-border bg-card p-6"
      >
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
            {renderUnderlinedText(current.passage)}
          </p>
        )}

        {current.vocab && current.vocab.length > 0 && (
          <p className="mt-3 text-xs leading-relaxed text-muted">
            {current.vocab.map((v, i) => (
              <span key={v.word}>
                {i > 0 && " · "}
                <span className="italic">{v.word}</span> {v.meaning}
              </span>
            ))}
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
              <motion.button
                key={i}
                onClick={(e) => handleChoice(i, e.currentTarget)}
                disabled={selected !== null}
                initial={{ opacity: 0, x: -8 }}
                animate={
                  selected !== null && isAnswer
                    ? { opacity: 1, x: 0, scale: [1, 1.04, 1], boxShadow: "0 0 18px rgba(52,211,153,0.35)" }
                    : selected !== null && isPicked
                      ? { opacity: 1, x: [0, -7, 7, -5, 5, 0], scale: 1, boxShadow: "0 0 0 rgba(0,0,0,0)" }
                      : { opacity: 1, x: 0, scale: 1, boxShadow: "0 0 0 rgba(0,0,0,0)" }
                }
                transition={{ duration: 0.4, delay: selected === null ? i * 0.05 : 0 }}
                whileTap={selected === null ? { scale: 0.98 } : undefined}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${style}`}
              >
                <span className="mr-2 text-muted">{i + 1}.</span>
                {choice}
              </motion.button>
            );
          })}
        </div>

        {selected !== null && (
          <motion.div
            className="mt-5"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.15, ease: "easeOut" }}
          >
            <p className={`font-semibold ${isCorrect ? "text-accent" : "text-wrong"}`}>
              {isCorrect ? "정답입니다!" : "틀렸어요 — 해설을 확인해보세요"}
            </p>
            {current.concept && (
              <p className="mt-2 rounded-lg bg-secondary px-3 py-2 text-xs font-medium text-accent">
                💡 {current.concept}
              </p>
            )}
            <p className="mt-2 text-sm leading-relaxed text-muted">{current.explanation}</p>
            <button
              onClick={next}
              className="mt-4 w-full rounded-xl bg-accent px-5 py-3 font-semibold text-accent-foreground transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              다음 문제 →
            </button>
          </motion.div>
        )}
      </motion.div>
    </div>,
  );
}
