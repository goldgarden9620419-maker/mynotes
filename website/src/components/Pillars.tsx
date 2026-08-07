import { Mascot } from "./Mascot";
import { Reveal } from "./Reveal";

const pillars = [
  {
    title: "건강 관리",
    description: "계절성 질환부터 생활 습관까지, 근거 있는 건강 정보를 정리합니다.",
  },
  {
    title: "생활 꿀팁",
    description: "몰라서 손해 보는 생활 정보와 절차를 알기 쉽게 풀어드립니다.",
  },
  {
    title: "계절 정보",
    description: "그 시기에 꼭 필요한 예방법과 대처법을 미리 준비합니다.",
  },
  {
    title: "생활 경제",
    description: "환급, 혜택, 지원 제도 등 실생활에 도움이 되는 정보를 다룹니다.",
  },
];

export function Pillars() {
  return (
    <section id="pillars" className="relative">
      <Mascot pose="wave" size={100} delay={0.1} className="top-10 right-2 lg:right-10 xl:right-24" />
      <div className="mx-auto max-w-5xl px-6 py-32">
        <Reveal className="mb-16 text-center">
          <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
            몰라서 손해 보지 않게
          </h2>
          <p className="mt-4 text-foreground-muted">
            건강·생활정보 한 축을 꾸준히 유지하며, 검증한 정보만 정리해서 올립니다.
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
