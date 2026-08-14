import Link from "next/link";
import Hero07 from "@/components/ui/hero-07";
import { Features } from "@/components/blocks/features-2";
import MatjipFinder from "./components/MatjipFinder";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center">
      <div className="w-full">
        <Hero07
          tagline="프랜차이즈는 빼고, 진짜 근처 로컬 맛집만"
          title="당신 근처에 있는, 아직 아무도 모르는 맛집."
          description="현재 위치, 인원수, 모임 성격, 먹고 싶은 음식만 알려주시면 진짜 숨은 맛집을 바로 찾아드려요."
          landscapeImage="/hero-food.jpg"
          landscapeAlt="따뜻한 조명 아래 정갈하게 차려진 맛집 한상"
          animation="none"
          primaryCTA={{ ctaEnabled: true, text: "숨은 맛집 찾아보기", link: "#finder", variant: "default" }}
        />
      </div>

      <Features />

      <div
        id="finder"
        className="flex w-full scroll-mt-8 flex-col items-center px-4 pb-16 pt-4 sm:pb-24"
      >
        <MatjipFinder />
      </div>

      <footer className="mb-16 flex flex-col items-center gap-2 text-center text-xs text-muted">
        <p>© 2026 숨은맛집찾기 · 위치 정보는 브라우저에서만 사용되며 저장되지 않습니다.</p>
        <div className="flex gap-4">
          <Link href="/privacy-policy" className="hover:text-accent hover:underline">
            개인정보처리방침
          </Link>
          <Link href="/terms" className="hover:text-accent hover:underline">
            이용약관
          </Link>
        </div>
      </footer>
    </div>
  );
}
