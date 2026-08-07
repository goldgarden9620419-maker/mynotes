import { AmbientBackground } from "@/components/AmbientBackground";
import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { Pillars } from "@/components/Pillars";
import { Roadmap } from "@/components/Roadmap";
import { PostPreview } from "@/components/PostPreview";
import { CTAFooter } from "@/components/CTAFooter";

const BLOG_URL = "https://goldjade0419.com/";

export default function Home() {
  return (
    <>
      <AmbientBackground />
      <Nav blogUrl={BLOG_URL} />
      <main>
        <Hero blogUrl={BLOG_URL} />
        <Pillars />
        <Roadmap />
        <PostPreview />
      </main>
      <CTAFooter blogUrl={BLOG_URL} />
    </>
  );
}
