import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "이용약관 | 숨은맛집찾기",
};

export default function Terms() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 메인으로 돌아가기
      </Link>
      <h1 className="mb-1 text-2xl font-bold">이용약관</h1>
      <p className="mb-8 text-sm text-muted">시행일: 2026-08-14 · 최종 수정일: 2026-08-14</p>

      <div className="mb-8 rounded-2xl border border-border bg-card p-5 text-sm leading-relaxed text-muted">
        <strong className="text-foreground">요약</strong>
        <br />
        이 사이트가 제공하는 맛집 검색 결과(별점, 리뷰 수, 사진, 주소 등)는 Google Places API를
        통해 제공받은 정보이며, 정확성이나 최신성에 대해 사이트가 별도로 보증하지 않습니다.
      </div>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제1조 (목적)
        </h2>
        <p className="text-sm leading-relaxed">
          이 약관은 &quot;숨은맛집찾기&quot;(이하 &quot;사이트&quot;)이 제공하는 서비스의 이용과
          관련하여 사이트와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제2조 (서비스의 내용)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>이용자의 현재 위치, 인원 구성, 모임 성격, 음식 종류를 바탕으로 근처 맛집을 검색</li>
          <li>프랜차이즈 매장을 제외하고, 별점·리뷰 수 기준으로 우선순위를 정해 결과를 제공</li>
          <li>외부 지도 앱(카카오맵 등)으로 연결되는 길찾기 기능 제공</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제3조 (서비스의 성격 — 제3자 데이터 기반)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>
            검색 결과에 표시되는 상호명, 주소, 별점, 리뷰 수, 사진 등은{" "}
            <strong className="text-foreground">Google Places API</strong>가 제공하는 정보를
            그대로 보여주는 것이며, 사이트가 직접 검증하거나 수정하지 않습니다.
          </li>
          <li>
            영업시간 변경, 폐업, 정보 오류 등으로 실제와 다를 수 있으며, 사이트는 이에 대한 책임을
            지지 않습니다.
          </li>
          <li>
            길찾기 기능은 카카오맵 등 외부 애플리케이션으로 이용자를 연결하며, 해당 외부
            서비스에서 발생하는 문제에 대해서는 각 서비스 제공업체의 정책이 적용됩니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제4조 (이용자의 의무)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>이용자는 사이트를 관계 법령과 이 약관이 정하는 바에 따라 이용해야 합니다.</li>
          <li>사이트를 통해 얻은 정보를 상업적으로 무단 도용하거나 타인에게 피해를 주는 방식으로 사용해서는 안 됩니다.</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제5조 (지식재산권)
        </h2>
        <p className="text-sm leading-relaxed">
          사이트가 자체적으로 작성한 디자인, 필터링·추천 로직 등에 대한 권리는 사이트 운영자에게
          있습니다. 맛집 관련 정보(상호명, 별점, 리뷰, 사진 등)의 권리는 Google 및 각 정보
          제공자에게 있습니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          제6조 (면책조항)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>사이트는 천재지변, 서비스 설비의 장애 등 불가항력으로 인해 서비스를 제공할 수 없는 경우 책임이 면제됩니다.</li>
          <li>사이트는 무료로 제공되는 서비스와 관련하여 관련 법령에 특별한 규정이 없는 한 책임을 지지 않습니다.</li>
          <li>사이트가 제공하는 맛집 검색 결과의 정확성, 신뢰성에 대해 보증하지 않으며, 이를 이용해 발생한 손해(예: 잘못된 정보로 인한 방문 불편)에 대해 책임을 지지 않습니다.</li>
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
