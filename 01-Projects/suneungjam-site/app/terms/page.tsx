import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "이용약관 | 수능잼",
};

export default function Terms() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 메인으로 돌아가기
      </Link>
      <h1 className="mb-1 text-2xl font-bold">이용약관</h1>
      <p className="mb-8 text-sm text-muted">시행일: 2026-08-29 · 최종 수정일: 2026-08-29</p>

      <div className="mb-8 rounded-2xl border border-border bg-card p-5 text-sm leading-relaxed text-muted">
        <strong className="text-foreground">요약</strong>
        <br />
        이 사이트가 제공하는 문제는 실제 대학수학능력시험(수능) 기출문제 원문이 아니라, 공개적으로
        알려진 수능 출제 경향과 문항 유형을 참고하여 새로 만든 연습문제입니다.
      </div>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제1조 (목적)
        </h2>
        <p className="text-sm leading-relaxed">
          이 약관은 &quot;수능잼&quot;(이하 &quot;사이트&quot;)이 제공하는 서비스의 이용과 관련하여
          사이트와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제2조 (서비스의 내용)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>매일 새롭게 제공되는 영어·수학 수능 유형 연습문제(각 5문항)와 정답·해설 제공</li>
          <li>문제를 풀고 즉시 정답 여부와 해설을 확인할 수 있는 학습 도구 제공</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제3조 (서비스의 성격 — 연습문제이며 실제 기출문제가 아님)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>
            사이트에서 제공하는 모든 문제, 지문, 선택지, 해설은 한국교육과정평가원이 발표한
            실제 대학수학능력시험 기출문제 원문이 아니며, 공개적으로 알려진 출제 경향(문항
            유형, 난이도 구성 등)을 참고하여 자체적으로 새로 제작한 연습문제입니다.
          </li>
          <li>
            사이트의 문제는 실전 감각을 익히기 위한 참고 자료이며, 실제 수능 성적이나 결과를
            보장하지 않습니다.
          </li>
          <li>
            사이트는 매일 문제를 새로 추가하며, 문제의 난이도나 구성은 예고 없이 변경될 수
            있습니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제4조 (이용자의 의무)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>이용자는 사이트를 관계 법령과 이 약관이 정하는 바에 따라 이용해야 합니다.</li>
          <li>
            사이트를 통해 얻은 문제·해설을 상업적으로 무단 도용하거나 타인에게 피해를 주는
            방식으로 사용해서는 안 됩니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제5조 (지식재산권)
        </h2>
        <p className="text-sm leading-relaxed">
          사이트가 자체적으로 작성한 문제, 지문, 해설, 디자인에 대한 권리는 사이트 운영자에게
          있습니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제6조 (면책조항)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>
            사이트는 천재지변, 서비스 설비의 장애 등 불가항력으로 인해 서비스를 제공할 수 없는
            경우 책임이 면제됩니다.
          </li>
          <li>
            사이트는 무료로 제공되는 서비스와 관련하여 관련 법령에 특별한 규정이 없는 한 책임을
            지지 않습니다.
          </li>
          <li>
            사이트가 제공하는 연습문제는 실제 수능 문제와 다를 수 있으며, 이를 이용해 발생한
            결과(예: 시험 성적)에 대해 책임을 지지 않습니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제7조 (약관의 변경)
        </h2>
        <p className="text-sm leading-relaxed">
          사이트는 필요한 경우 관련 법령을 위배하지 않는 범위 내에서 이 약관을 변경할 수 있으며,
          변경 시 사이트를 통해 공지합니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">제8조 (문의)</h2>
        <p className="text-sm leading-relaxed">
          약관 관련 문의사항은 아래 이메일로 문의해주시기 바랍니다.
        </p>
        <p className="mt-2 text-sm text-muted">goldgarden9620419@gmail.com</p>
      </section>

      <footer className="mt-8 border-t border-border pt-6 text-xs text-muted">
        <Link href="/" className="hover:text-accent">
          ← 메인으로 돌아가기
        </Link>
      </footer>
    </div>
  );
}
