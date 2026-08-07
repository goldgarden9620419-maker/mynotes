import { Reveal } from "./Reveal";
import { getLatestPosts, type BlogPost } from "@/lib/tistory-rss";

const fallbackPosts: BlogPost[] = [
  {
    tag: "새벽 루틴",
    title: "새벽 기상 한 달, 무엇이 달라졌을까",
    excerpt: "매일 새벽 5시 기상을 한 달간 이어가며 실제로 느낀 변화를 정리했습니다.",
    link: "https://goldjade0419.com/",
    pubDate: "",
  },
  {
    tag: "부자의 습관",
    title: "스텔스 웰스, 조용한 부자들의 절제 습관",
    excerpt: "드러내지 않는 부자들이 공통적으로 지키는 절제와 자산관리 습관을 살펴봤습니다.",
    link: "https://goldjade0419.com/",
    pubDate: "",
  },
];

export async function PostPreview() {
  const livePosts = await getLatestPosts(2);
  const posts = livePosts.length > 0 ? livePosts : fallbackPosts;
  const isLive = livePosts.length > 0;

  return (
    <section id="posts" className="relative mx-auto max-w-5xl px-6 py-32">
      <Reveal className="mb-16 text-center">
        <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
          먼저 살짝 보여드릴게요
        </h2>
        <p className="mt-4 text-foreground-muted">
          {isLive
            ? "블로그에 최근 올라온 이야기예요."
            : "지금 이 순간에도 글감을 쌓고, 한 편씩 완성해가고 있어요."}
        </p>
      </Reveal>
      <div className="grid gap-5 sm:grid-cols-2">
        {posts.map((post, i) => (
          <Reveal key={post.link + post.title} delay={i * 0.1}>
            <a
              href={post.link}
              target="_blank"
              rel="noopener noreferrer"
              className="block h-full cursor-pointer rounded-2xl border border-white/12 bg-white/[0.07] p-7 backdrop-blur-xl transition-colors hover:bg-white/[0.1]"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
                  {post.tag}
                </span>
                {post.pubDate && (
                  <span className="text-xs text-foreground-muted">{post.pubDate}</span>
                )}
              </div>
              <h3 className="mt-4 font-serif text-xl font-semibold text-foreground">
                {post.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-foreground-muted">
                {post.excerpt}
              </p>
            </a>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
