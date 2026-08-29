import Link from "next/link";
import QuizApp from "./components/QuizApp";
import InstallPrompt from "./components/InstallPrompt";
import AffirmationCard from "./components/AffirmationCard";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center px-4 pb-16 pt-4 sm:pt-10">
      <InstallPrompt />
      <div className="mb-4 flex max-w-md flex-col items-center text-center sm:mb-8">
        <span className="motion-safe:animate-pulse rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold text-accent sm:px-3 sm:text-xs">
          🔥 매일 새로운 5문제
        </span>
        <h1 className="text-balance mt-2 text-xl font-extrabold leading-snug tracking-tight sm:mt-4 sm:text-4xl">
          &ldquo;공부할 시간이 없다&rdquo;는
          <br />
          핑계, <span className="text-accent">오늘부로 끝.</span>
        </h1>
        <p className="mt-1.5 text-xs leading-relaxed text-muted sm:mt-3 sm:text-sm">
          버스에서, 쉬는 시간에, 잠들기 전 1~2분. 영어·수학 딱 5문제면 충분해요.
        </p>
      </div>

      <QuizApp />

      <div className="mt-10">
        <AffirmationCard />
      </div>

      <footer className="mt-16 flex flex-col items-center gap-2 text-center text-xs text-muted">
        <p>© 2026 수능잼(suneungjam.com) · 실제 기출문제가 아닌, 출제 경향을 참고해 새로 만든 연습문제입니다.</p>
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
