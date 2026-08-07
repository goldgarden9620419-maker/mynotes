import { Mascot } from "./Mascot";
import { Reveal } from "./Reveal";

const steps = [
  {
    tag: "시작",
    title: "그냥, 바뀐 삶의 기록",
    description:
      "새벽 기상과 확언으로 하루하루가 달라지는 걸 직접 경험했어요.",
  },
  {
    tag: "이유",
    title: "적어두고 싶었어요",
    description:
      "작은 습관이 만든 변화를 잊지 않으려, 하나씩 기록하기 시작했어요.",
  },
  {
    tag: "바람",
    title: "함께 나누고 싶어요",
    description:
      "내 습관이 당신의 아침도 바꿀 수 있다면, 그걸로 충분해요.",
  },
];

export function WhyIWrite() {
  return (
    <section id="why" className="relative">
      <Mascot pose="note" size={95} delay={0.1} className="top-10 left-2 lg:left-10 xl:left-20" />
      <div className="mx-auto max-w-4xl px-6 py-32">
        <Reveal className="mb-16 text-center">
          <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
            왜 이 글을 쓰냐면
          </h2>
          <p className="mt-4 text-foreground-muted">
            대단한 목표보다, 그냥 나누고 싶어서 씁니다.
          </p>
        </Reveal>
        <div className="relative space-y-6 border-l border-white/12 pl-8">
          {steps.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.1}>
              <div className="relative rounded-2xl border border-white/12 bg-white/[0.07] p-6 backdrop-blur-xl">
                <span className="absolute top-7 -left-[41px] h-3 w-3 rounded-full bg-accent shadow-[0_0_12px_2px_var(--accent-glow)]" />
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
                    {step.tag}
                  </span>
                  <h3 className="font-serif text-lg font-semibold text-foreground">
                    {step.title}
                  </h3>
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
