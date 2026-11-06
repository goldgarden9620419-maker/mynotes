import type { Metadata } from "next";
import Link from "next/link";
import AdSenseScript from "../components/AdSenseScript";
import { TYPE_GUIDES } from "./guides";

export const metadata: Metadata = {
  title: "수능 영어·수학 유형별 풀이법 | 수능잼",
  description:
    "수능 영어 어법·빈칸추론·순서·문장삽입·주제, 수학 수열·미분·적분·확률과통계·삼각함수 유형별 풀이 순서와 흔한 실수를 정리한 가이드 모음입니다.",
};

export default function GuideIndex() {
  const groups: { label: string; subject: "영어" | "수학" }[] = [
    { label: "영어", subject: "영어" },
    { label: "수학", subject: "수학" },
  ];
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <AdSenseScript />
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 오늘의 문제 풀러 가기
      </Link>
      <h1 className="mb-3 text-2xl font-bold leading-snug">수능 영어·수학 유형별 풀이법</h1>
      <p className="mb-10 text-sm leading-relaxed text-muted">
        문제를 풀다 막혔을 때 볼 수 있는 유형별 풀이 가이드예요. 어떤 문제인지, 어떤 순서로 풀면 좋은지,
        자주 하는 실수는 무엇인지 정리했어요.
      </p>

      {groups.map((g) => (
        <section key={g.label} className="mb-8">
          <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">{g.label}</h2>
          <div className="flex flex-col gap-3">
            {TYPE_GUIDES.filter((t) => t.subject === g.subject).map((t) => (
              <Link
                key={t.slug}
                href={`/guide/${t.slug}`}
                className="rounded-2xl border border-border bg-card p-4 transition hover:border-accent"
              >
                <p className="text-sm font-semibold">{t.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{t.description}</p>
              </Link>
            ))}
          </div>
        </section>
      ))}

      <section className="mb-8">
        <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">공부 방법</h2>
        <div className="flex flex-col gap-3">
          <Link
            href="/guide/study-tips"
            className="rounded-2xl border border-border bg-card p-4 transition hover:border-accent"
          >
            <p className="text-sm font-semibold">짬 시간에 수능 공부하는 법 — 하루 5문제 루틴</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              짧은 시간을 여러 번 쓰는 학습 루틴과 오답노트 활용법
            </p>
          </Link>
        </div>
      </section>

      <footer className="mt-8 flex flex-wrap justify-center gap-x-4 gap-y-1 text-center text-xs text-muted">
        <Link href="/about" className="hover:text-accent hover:underline">서비스 소개</Link>
        <Link href="/privacy-policy" className="hover:text-accent hover:underline">개인정보처리방침</Link>
        <Link href="/terms" className="hover:text-accent hover:underline">이용약관</Link>
      </footer>
    </div>
  );
}
