import type { Metadata } from "next";
import GuideArticle from "../../components/GuideArticle";
import { TYPE_GUIDES } from "../guides";

const guide = TYPE_GUIDES.find((g) => g.slug === "english-insertion")!;

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
      related={[{"href": "/guide/english-grammar", "label": "수능 영어 어법 문제 푸는 법"}, {"href": "/guide/english-blank", "label": "수능 영어 빈칸추론 문제 푸는 법"}, {"href": "/guide/english-order", "label": "수능 영어 글의 순서 문제 푸는 법"}, {"href": "/guide/study-tips", "label": "짬 시간에 수능 공부하는 법 — 하루 5문제 루틴"}, {"href": "/problems/en-2026-09-27-4", "label": "영어 문장삽입 문제와 해설 (9월 27일 출제)"}, {"href": "/problems/en-2026-09-07-4", "label": "영어 문장삽입 문제와 해설 (9월 7일 출제)"}, {"href": "/problems/en-2026-09-10-4", "label": "영어 문장삽입 문제와 해설 (9월 10일 출제)"}, {"href": "/problems", "label": "수능 영어 문제와 해설 모음"}]}
    />
  );
}
