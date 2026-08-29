import Link from "next/link";
import QuizApp from "./components/QuizApp";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center px-4 pb-16 pt-12 sm:pt-16">
      <div className="mb-8 flex max-w-md flex-col items-center text-center">
        <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-accent">
          매일 새로운 5문제
        </span>
        <h1 className="mt-4 text-2xl font-bold leading-snug sm:text-3xl">
          짬 나는 시간에,
          <br />딱 5문제만.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          버스에서, 쉬는 시간에, 잠들기 전에 — 영어·수학 수능 유형 문제를 1~2분이면 풀 수 있어요.
          맞히면 바로 다음 문제로, 틀리면 그 자리에서 해설을 확인하세요.
        </p>
      </div>

      <QuizApp />

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
