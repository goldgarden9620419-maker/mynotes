import type { Metadata } from "next";
import Link from "next/link";
import AdSenseScript from "../components/AdSenseScript";
import problemsData from "../../data/problems.json";
import { FEATURED_IDS } from "./featured";

type Problem = { id: string; subject: "english" | "math"; type: string; date: string; prompt: string; passage?: string };
const problems = problemsData as Problem[];

export const metadata: Metadata = {
  title: "수능 영어 문제와 해설 모음 | 수능잼",
  description:
    "수능잼이 직접 출제한 영어 어법·빈칸추론·순서·문장삽입·주제 대표 문제를 지문, 보기, 정답, 단계별 해설과 함께 읽을 수 있어요.",
};

function dateLabel(iso: string) {
  const [, m, d] = iso.split("-");
  return `${Number(m)}월 ${Number(d)}일`;
}

export default function ProblemsIndex() {
  const featured = FEATURED_IDS.map((id) => problems.find((p) => p.id === id)).filter((p): p is Problem => !!p);
  const groups: { label: string; subject: "english" | "math" }[] = [{ label: "영어", subject: "english" }];
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <AdSenseScript />
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 오늘의 문제 풀러 가기
      </Link>
      <h1 className="mb-3 text-2xl font-bold leading-snug">수능 영어 문제와 해설 모음</h1>
      <p className="mb-10 text-sm leading-relaxed text-muted">
        수능잼이 매일 새로 출제하는 영어 문제 가운데, 풀이에서 배울 점이 많은 문제를 골라 지문과 보기, 정답, 단계별
        해설까지 한 페이지에 모아 두었어요. 풀어 본 뒤 해설을 읽거나, 풀기 전에 어떤 문제인지 미리 살펴볼 때
        활용해 보세요. 유형별 풀이 순서는{" "}
        <Link href="/guide" className="text-accent hover:underline">
          풀이법 가이드
        </Link>
        에서 볼 수 있어요.
      </p>

      {groups.map((g) => (
        <section key={g.subject} className="mb-8">
          <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">{g.label}</h2>
          <div className="flex flex-col gap-3">
            {featured
              .filter((p) => p.subject === g.subject)
              .map((p) => (
                <Link
                  key={p.id}
                  href={`/problems/${p.id}`}
                  className="rounded-2xl border border-border bg-card p-4 transition hover:border-accent"
                >
                  <p className="text-xs text-muted">
                    {p.type} · {dateLabel(p.date)}
                  </p>
                  <p className="mt-1 text-sm font-semibold">{p.prompt}</p>
                </Link>
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}
