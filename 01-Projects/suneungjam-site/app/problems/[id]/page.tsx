import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import AdSenseScript from "../../components/AdSenseScript";
import { renderUnderlinedText } from "../../components/renderUnderline";
import { TYPE_GUIDES } from "../../guide/guides";
import problemsData from "../../../data/problems.json";
import { FEATURED_IDS } from "../featured";

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

function find(id: string) {
  return FEATURED_IDS.includes(id) ? problems.find((p) => p.id === id) : undefined;
}

function dateLabel(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${y}년 ${Number(m)}월 ${Number(d)}일`;
}

export function generateStaticParams() {
  return FEATURED_IDS.map((id) => ({ id }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const p = find(id);
  if (!p) return {};
  const subject = p.subject === "english" ? "영어" : "수학";
  return {
    title: `${subject} ${p.type} 문제와 해설 (${dateLabel(p.date)}) | 수능잼`,
    description: `수능잼이 ${dateLabel(p.date)}에 출제한 ${subject} ${p.type} 문제의 지문, 보기, 정답과 단계별 해설을 정리했어요.`,
  };
}

export default async function ProblemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = find(id);
  if (!p) notFound();

  const subject = p.subject === "english" ? "영어" : "수학";
  const guide = TYPE_GUIDES.find((g) => g.subject === subject && g.type === p.type);
  const checkSection = guide?.sections.find((s, i) => i >= 2 && s.ul && !s.h.includes("실수") && !s.h.includes("실제 문제"));
  const checkpoints = checkSection?.ul;
  const marks = ["①", "②", "③", "④", "⑤"];
  const isMarkedPassage = p.type === "문장삽입";

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <AdSenseScript />
      <Link href="/problems" className="mb-6 text-sm text-muted hover:text-accent">
        ← 문제와 해설 모음
      </Link>

      <p className="mb-2 text-xs text-muted">{dateLabel(p.date)} 출제 · {subject}</p>
      <h1 className="mb-6 text-2xl font-bold leading-snug">
        {subject} {p.type} 문제와 해설
      </h1>

      <section className="rounded-2xl border border-border bg-card p-5">
        <span className="inline-block rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-accent">
          {p.type}
        </span>
        <h2 className="mt-3 text-sm font-semibold">{p.prompt}</h2>

        {p.givenSentence && (
          <div className="mt-3 rounded-xl border border-border bg-secondary p-3 text-sm italic">
            {p.givenSentence}
          </div>
        )}

        {p.passage && (
          <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-foreground/90">
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

        <ol className="mt-5 flex flex-col gap-2 text-sm">
          {p.choices.map((c, i) => (
            <li
              key={i}
              className={`rounded-xl border px-4 py-3 ${
                i === p.answerIndex ? "border-accent bg-accent/10 text-accent" : "border-border bg-secondary"
              }`}
            >
              <span className="mr-2 text-muted">{isMarkedPassage ? marks[i] : `${i + 1}.`}</span>
              {c}
              {i === p.answerIndex && <span className="ml-2 text-xs font-semibold">← 정답</span>}
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">해설</h2>
        <p className="text-sm leading-relaxed text-muted">{p.explanation}</p>
        {p.concept && (
          <p className="mt-3 rounded-lg bg-secondary px-3 py-2 text-xs font-medium text-accent">💡 {p.concept}</p>
        )}
      </section>

      {checkpoints && (
        <section className="mt-8">
          <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">
            {checkSection?.h ?? `${p.type} 문제를 풀 때 다시 확인할 점`}
          </h2>
          <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
            {checkpoints.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </section>
      )}

      {guide && (
        <div className="mt-10 rounded-2xl bg-secondary p-5 text-sm leading-relaxed">
          <h2 className="mb-2 font-semibold">이 유형을 더 자세히</h2>
          <Link href={`/guide/${guide.slug}`} className="text-accent hover:underline">
            {guide.title}
          </Link>
        </div>
      )}

      <div className="mt-10 flex justify-center">
        <Link
          href="/"
          className="rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground transition active:scale-[0.98]"
        >
          오늘의 5문제 풀어보기
        </Link>
      </div>

      <footer className="mt-12 flex flex-wrap justify-center gap-x-4 gap-y-1 text-center text-xs text-muted">
        <Link href="/guide" className="hover:text-accent hover:underline">풀이법 가이드</Link>
        <Link href="/about" className="hover:text-accent hover:underline">서비스 소개</Link>
        <Link href="/privacy-policy" className="hover:text-accent hover:underline">개인정보처리방침</Link>
        <Link href="/terms" className="hover:text-accent hover:underline">이용약관</Link>
      </footer>
    </div>
  );
}
