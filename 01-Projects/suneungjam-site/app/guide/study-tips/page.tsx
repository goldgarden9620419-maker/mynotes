import type { Metadata } from "next";
import GuideArticle from "../../components/GuideArticle";
import { EXTRA_GUIDES } from "../guides";

const guide = EXTRA_GUIDES.find((g) => g.slug === "study-tips")!;

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
        { href: "/about", label: "수능잼 소개" },
      ]}
    />
  );
}
