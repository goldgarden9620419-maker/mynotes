import type { Metadata } from "next";
import GuideArticle from "../../components/GuideArticle";
import { TYPE_GUIDES } from "../guides";

const guide = TYPE_GUIDES.find((g) => g.slug === "math-integration")!;

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
      related={[{"href": "/guide/math-sequence", "label": "수능 수학 수열 문제 푸는 법"}, {"href": "/guide/math-differentiation", "label": "수능 수학 미분 문제 푸는 법"}, {"href": "/guide/math-probability", "label": "수능 수학 확률과통계 문제 푸는 법"}, {"href": "/guide/study-tips", "label": "짬 시간에 수능 공부하는 법 — 하루 5문제 루틴"}]}
    />
  );
}
