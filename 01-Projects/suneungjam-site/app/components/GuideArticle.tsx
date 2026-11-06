import Link from "next/link";
import AdSenseScript from "./AdSenseScript";
import type { GuideSection } from "../guide/guides";

type Props = {
  title: string;
  lead: string;
  sections: GuideSection[];
  related?: { href: string; label: string }[];
};

export default function GuideArticle({ title, lead, sections, related }: Props) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <AdSenseScript />
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 오늘의 문제 풀러 가기
      </Link>

      <h1 className="mb-3 text-2xl font-bold leading-snug">{title}</h1>
      <p className="mb-10 text-sm leading-relaxed text-muted">{lead}</p>

      <div className="flex flex-col gap-8">
        {sections.map((s) => (
          <section key={s.h}>
            <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">{s.h}</h2>
            {s.p?.map((t, i) => (
              <p key={i} className="mb-3 text-sm leading-relaxed text-muted">
                {t}
              </p>
            ))}
            {s.ol && (
              <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted">
                {s.ol.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ol>
            )}
            {s.ul && (
              <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
                {s.ul.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      {related && related.length > 0 && (
        <div className="mt-10 rounded-2xl bg-secondary p-5 text-sm leading-relaxed">
          <h2 className="mb-2 font-semibold">함께 보면 좋은 글</h2>
          <ul className="list-disc space-y-1 pl-4">
            {related.map((r) => (
              <li key={r.href}>
                <Link href={r.href} className="text-accent hover:underline">
                  {r.label}
                </Link>
              </li>
            ))}
          </ul>
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
