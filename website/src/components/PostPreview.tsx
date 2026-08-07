import { Reveal } from "./Reveal";

const posts = [
  {
    tag: "건강",
    title: "여름철 식중독 예방법과 증상별 대처법",
    excerpt: "무더운 여름, 식중독을 예방하는 방법과 증상별 대처법을 정리했습니다.",
  },
  {
    tag: "생활 경제",
    title: "영수증 환급 기간·조건 총정리",
    excerpt: "몰라서 손해 보는 영수증 환급 관련 정보를 한눈에 정리했습니다.",
  },
];

export function PostPreview() {
  return (
    <section id="posts" className="relative mx-auto max-w-5xl px-6 py-32">
      <Reveal className="mb-16 text-center">
        <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
          먼저 살짝 보여드릴게요
        </h2>
        <p className="mt-4 text-foreground-muted">
          지금 이 순간에도 글감을 쌓고, 한 편씩 완성해가고 있어요.
        </p>
      </Reveal>
      <div className="grid gap-5 sm:grid-cols-2">
        {posts.map((post, i) => (
          <Reveal key={post.title} delay={i * 0.1}>
            <div className="h-full rounded-2xl border border-white/12 bg-white/[0.07] p-7 backdrop-blur-xl">
              <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
                {post.tag}
              </span>
              <h3 className="mt-4 font-serif text-xl font-semibold text-foreground">
                {post.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-foreground-muted">
                {post.excerpt}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
