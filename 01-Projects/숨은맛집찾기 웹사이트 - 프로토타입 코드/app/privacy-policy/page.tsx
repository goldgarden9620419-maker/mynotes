import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "개인정보처리방침 | 숨은맛집찾기",
};

export default function PrivacyPolicy() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-6 py-16">
      <Link href="/" className="mb-6 text-sm text-muted hover:text-accent">
        ← 메인으로 돌아가기
      </Link>
      <h1 className="mb-1 text-2xl font-bold">개인정보처리방침</h1>
      <p className="mb-8 text-sm text-muted">시행일: 2026-08-14 · 최종 수정일: 2026-08-14</p>

      <p className="mb-6 text-sm leading-relaxed">
        &quot;숨은맛집찾기&quot;(이하 &quot;사이트&quot;)는 이용자의 개인정보를 소중히 여기며, 관련
        법령을 준수하기 위해 다음과 같이 개인정보처리방침을 안내합니다.
      </p>

      <div className="mb-8 rounded-2xl border border-border bg-card p-5 text-sm leading-relaxed text-muted">
        <strong className="text-foreground">요약</strong>
        <br />
        이 사이트는 위치 정보를 <strong className="text-foreground">서버에 저장하지 않고</strong>,
        맛집 검색을 위해 브라우저에서 구글 Places API로 실시간 전송할 뿐입니다. 회원가입·로그인
        기능이 없어 이름, 연락처 등 개인 식별 정보를 수집하지 않습니다.
      </div>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          1. 수집하는 개인정보 항목
        </h2>
        <p className="mb-2 text-sm leading-relaxed">
          사이트는 회원가입 없이 이용 가능하며, 이용자가 직접 입력하는 개인정보(이름, 이메일 등)를
          수집하지 않습니다. 다만 서비스 이용 과정에서 아래 정보가 자동으로 생성되어 수집될 수
          있습니다.
        </p>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>방문 기록, 접속 IP, 쿠키, 접속 기기/브라우저 정보 (통계 서비스 이용 시)</li>
          <li>광고 게재를 위한 쿠키 및 광고 식별자 (Google 애드센스 등 광고 서비스 이용 시)</li>
          <li>
            현재 위치(GPS 좌표) — 근처 맛집을 찾기 위해 브라우저에서만 처리되며, 검색을 위해 Google
            Places API로 전송되고 사이트 서버에는 저장되지 않습니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          2. 개인정보의 이용 목적
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>현재 위치 기반 근처 맛집 검색 결과 제공</li>
          <li>서비스 이용 통계 분석 및 사용자 경험 개선</li>
          <li>맞춤형 광고 게재 (Google 애드센스 등 제3자 광고 서비스를 통해)</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          3. 제3자 서비스 (Google Places API, Google 애드센스)
        </h2>
        <ul className="ml-5 list-disc space-y-1 text-sm leading-relaxed">
          <li>
            맛집 이름, 별점, 리뷰 수, 사진 등 검색 결과 데이터는{" "}
            <strong className="text-foreground">Google Places API</strong>를 통해 제공받으며,
            해당 데이터의 수집·처리는 Google의 정책을 따릅니다.
          </li>
          <li>
            사이트는 Google 애드센스를 통해 광고를 게재할 수 있으며, Google 등 제3자 광고
            공급업체는 쿠키를 사용하여 맞춤형 광고를 제공할 수 있습니다.
          </li>
          <li>
            이용자는{" "}
            <a
              href="https://adssettings.google.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline"
            >
              Google 광고 설정
            </a>{" "}
            페이지에서 맞춤형 광고를 비활성화할 수 있습니다.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          4. 개인정보의 보유 및 이용 기간
        </h2>
        <p className="text-sm leading-relaxed">
          사이트는 별도로 개인정보를 저장하지 않으며, 통계·광고 서비스를 통해 수집되는 정보는 각
          서비스 제공업체(Google)의 정책에 따라 처리됩니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          5. 만 14세 미만 아동의 개인정보
        </h2>
        <p className="text-sm leading-relaxed">
          사이트는 만 14세 미만 아동을 대상으로 한 서비스가 아니며, 아동으로부터 고의로
          개인정보를 수집하지 않습니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">
          6. 개인정보처리방침의 변경
        </h2>
        <p className="text-sm leading-relaxed">
          이 개인정보처리방침은 법령·정책 또는 서비스 변경에 따라 수정될 수 있으며, 변경 시
          사이트를 통해 공지합니다.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 border-b border-border pb-2 text-base font-semibold">7. 문의</h2>
        <p className="text-sm leading-relaxed">
          개인정보 관련 문의사항은 아래 이메일로 문의해주시기 바랍니다.
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
