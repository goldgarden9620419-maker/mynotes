import type { Metadata } from "next";
import GuideArticle from "../../components/GuideArticle";
import { TYPE_GUIDES } from "../guides";

const guide = TYPE_GUIDES.find((g) => g.slug === "english-order")!;

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
      related={[{"href": "/guide/english-grammar", "label": "수능 영어 어법 문제 푸는 법"}, {"href": "/guide/english-blank", "label": "수능 영어 빈칸추론 문제 푸는 법"}, {"href": "/guide/english-insertion", "label": "수능 영어 문장삽입 문제 푸는 법"}, {"href": "/guide/study-tips", "label": "짬 시간에 수능 공부하는 법 — 하루 5문제 루틴"}, {"href": "/problems/en-2026-11-22-3", "label": "영어 순서 문제와 해설 (11월 22일 출제)"}, {"href": "/problems/en-2026-09-09-3", "label": "영어 순서 문제와 해설 (9월 9일 출제)"}, {"href": "/problems/en-2026-11-25-3", "label": "영어 순서 문제와 해설 (11월 25일 출제)"}, {"href": "/problems", "label": "수능 영어 문제와 해설 모음"}]}
    />
  );
}
