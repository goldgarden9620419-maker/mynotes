import { Mascot } from "./Mascot";
import { Reveal } from "./Reveal";

const pillars = [
  {
    title: "새벽 루틴",
    description: "새벽 기상 하나로 하루가 어떻게 달라지는지, 직접 겪은 변화를 기록합니다.",
  },
  {
    title: "확언 · 자기암시",
    description: "말과 생각이 삶을 바꾸는 과정을, 실제 경험을 바탕으로 풀어드립니다.",
  },
  {
    title: "부자의 습관",
    description: "스텔스 웰스, 절제, 자산관리까지 — 부자들의 생각법을 정리합니다.",
  },
  {
    title: "사주 · 운세",
    description: "재미로 보는 사주와 운세 콘텐츠도 가볍게 곁들입니다.",
  },
];

export function Pillars() {
  return (
    <section id="pillars" className="relative">
      <Mascot pose="wave" size={100} delay={0.1} className="top-10 right-2 lg:right-10 xl:right-24" />
      <div className="mx-auto max-w-5xl px-6 py-32">
        <Reveal className="mb-16 text-center">
          <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
            작은 습관이 만든 변화
          </h2>
          <p className="mt-4 text-foreground-muted">
            새벽 기상과 확언, 부자의 마인드셋까지 — 직접 겪고 검증한 이야기만 정리해서 올립니다.
          </p>
        </Reveal>
        <div className="grid gap-5 sm:grid-cols-2">
          {pillars.map((pillar, i) => (
            <Reveal key={pillar.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-white/12 bg-white/5 p-7 backdrop-blur-xl transition-colors hover:bg-white/[0.07]">
                <h3 className="font-serif text-xl font-semibold text-foreground">
                  {pillar.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-foreground-muted">
                  {pillar.description}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
