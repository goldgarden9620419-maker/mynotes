import type { Metadata } from "next";
import GuideArticle from "../components/GuideArticle";
import { EXTRA_GUIDES } from "../guide/guides";

const guide = EXTRA_GUIDES.find((g) => g.slug === "about")!;

export const metadata: Metadata = {
  title: `${guide.title} | 수능잼`,
  description: guide.description,
};

export default function Page() {
  return (
    <GuideArticle
      title={guide.title}
      lead={guide.lead}
      sections={guide.sections}
      related={[
        { href: "/guide", label: "수능 영어·수학 유형별 풀이법 모아보기" },
        { href: "/guide/study-tips", label: "짬 시간에 수능 공부하는 법 — 하루 5문제 루틴" },
      ]}
    />
  );
}
