import { Mascot } from "./Mascot";
import { Reveal } from "./Reveal";

const steps = [
  {
    phase: "1단계 · 준비",
    week: "1주차 · 진행 중",
    description:
      "블로그 플랫폼 확정, 반응형 스킨 적용, 소개·개인정보처리방침 페이지 준비",
  },
  {
    phase: "2단계 · 콘텐츠 쌓기",
    week: "2~9주차 · 예정",
    description:
      "주 3~4편, 총 25편 이상 발행 — 건강·생활정보 한 축을 유지하며 독창적인 콘텐츠로 채웁니다.",
  },
  {
    phase: "3단계 · 신청 및 심사",
    week: "10~12주차 · 예정",
    description:
      "글 20~25편, 운영 2~3개월 시점에 애드센스 신청 · 심사 중에도 꾸준히 발행합니다.",
  },
];

export function Roadmap() {
  return (
    <section id="roadmap" className="relative">
      <Mascot pose="flag" size={95} delay={0.1} className="top-10 left-2 lg:left-10 xl:left-20" />
      <div className="mx-auto max-w-4xl px-6 py-32">
        <Reveal className="mb-16 text-center">
          <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
            12주, 목표는 단 하나
          </h2>
          <p className="mt-4 text-foreground-muted">
            애드센스 승인을 향해 가는 과정을 숨김없이 공개합니다. 성공도 실패도 이곳에 남깁니다.
          </p>
        </Reveal>
        <div className="relative space-y-6 border-l border-white/12 pl-8">
          {steps.map((step, i) => (
            <Reveal key={step.phase} delay={i * 0.1}>
              <div className="relative rounded-2xl border border-white/12 bg-white/[0.07] p-6 backdrop-blur-xl">
                <span className="absolute top-7 -left-[41px] h-3 w-3 rounded-full bg-accent shadow-[0_0_12px_2px_var(--accent-glow)]" />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-serif text-lg font-semibold text-foreground">
                    {step.phase}
                  </h3>
                  <span className="rounded-full border border-white/12 px-3 py-1 text-xs font-medium tracking-wide text-foreground-muted uppercase">
                    {step.week}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-foreground-muted">
                  {step.description}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
