import { Reveal } from "./Reveal";
import { getTodayAffirmation } from "@/lib/affirmations";

const audience = [
  "아침이 무기력한 분",
  "확언이 진짜 효과 있는지 궁금한 분",
  "조용히 부자가 되고 싶은 분",
  "작은 습관으로 삶을 바꾸고 싶은 분",
];

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="shrink-0">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeOpacity="0.4" strokeWidth="1.3" />
      <path
        d="M5 8.2 7 10l4-4.4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IntroStrip() {
  const affirmation = getTodayAffirmation();

  return (
    <section className="relative mx-auto max-w-4xl px-6 py-16">
      <Reveal className="mb-10 text-center">
        <h2 className="font-serif text-2xl font-semibold text-foreground sm:text-3xl">
          이런 분이라면
        </h2>
        <p className="mt-3 text-foreground-muted">이미 겪어본 이야기일 수도 있어요.</p>
      </Reveal>

      <Reveal delay={0.05}>
        <ul className="grid gap-3 sm:grid-cols-2">
          {audience.map((item) => (
            <li
              key={item}
              className="flex items-center gap-2.5 rounded-xl border border-white/12 bg-white/[0.05] px-4 py-3 text-sm text-foreground-muted"
            >
              <span className="text-accent">
                <CheckIcon />
              </span>
              {item}
            </li>
          ))}
        </ul>
      </Reveal>

      <Reveal delay={0.1} className="mt-10">
        <div className="mx-auto max-w-lg rounded-2xl border border-accent/20 bg-accent/[0.06] p-6 text-center">
          <span className="text-xs font-medium tracking-[0.2em] text-accent uppercase">
            오늘의 확언
          </span>
          <p className="mt-3 font-serif text-lg leading-relaxed text-foreground">
            &ldquo;{affirmation}&rdquo;
          </p>
        </div>
      </Reveal>
    </section>
  );
}
