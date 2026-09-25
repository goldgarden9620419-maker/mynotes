import Link from "next/link";
import QuizApp from "./components/QuizApp";
import InstallPrompt from "./components/InstallPrompt";
import AffirmationCard from "./components/AffirmationCard";

const steps = [
  {
    title: "1. 오늘의 문제 풀기",
    body: "영어 5문제, 수학 5문제가 매일 새벽 새로 올라와요. 정답을 맞히면 자동으로 다음 문제로 넘어가서, 끊기지 않고 짧은 시간에 몰아서 풀 수 있어요.",
  },
  {
    title: "2. 틀리면 그 자리에서 해설 확인",
    body: "오답이 나오면 바로 그 문제 아래에 해설이 펼쳐져요. 영어는 지문에 나온 어려운 단어 뜻을, 수학은 풀이에 쓰인 핵심 개념을 함께 보여줘서 왜 틀렸는지 바로 이해할 수 있어요.",
  },
  {
    title: "3. 오답만 모아 복습·PDF 저장",
    body: "틀린 문제는 자동으로 저장돼서, '복습' 페이지에서 오늘 틀린 문제만 모아 다시 보거나 PDF로 인쇄해 노트처럼 들고 다니며 볼 수 있어요.",
  },
];

const faqs = [
  {
    q: "실제 수능 기출문제인가요?",
    a: "아니요. 평가원 기출문제 원문을 그대로 가져오지 않아요. 실제 수능 출제 패턴(문항 유형·난이도)을 참고해서 AI가 매일 새로운 문제를 만들어요.",
  },
  {
    q: "문제는 하루에 몇 개씩 나오나요?",
    a: "매일 새벽 영어 5문제(어법·빈칸추론·순서·문장삽입·주제)와 수학 5문제(수열·미분·적분·확률과통계·삼각함수), 총 10문제가 새로 추가돼요.",
  },
  {
    q: "틀린 문제는 어떻게 다시 볼 수 있나요?",
    a: "문제를 풀다 틀리면 그 문제가 자동으로 저장돼요. 화면 하단이나 결과 화면의 '복습' 버튼을 누르면 오늘 틀린 문제만 모아서 보여주고, PDF로 인쇄도 할 수 있어요.",
  },
  {
    q: "로그인이 필요한가요?",
    a: "아니요. 로그인 없이 바로 풀 수 있어요. 오답 기록은 서버가 아니라 브라우저에만 임시로 저장되기 때문에, 다른 기기나 브라우저에서는 이어지지 않아요.",
  },
];

export default function Home() {
  return (
    <div className="flex min-h-dvh w-full flex-1 flex-col items-center justify-center gap-5 px-4 py-6 sm:gap-8 sm:py-10">
      <InstallPrompt />
      <div className="flex max-w-md flex-col items-center text-center">
        <span className="motion-safe:animate-pulse rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-accent sm:px-4 sm:text-sm">
          🔥 매일 새로운 5문제
        </span>
        <h1 className="text-balance mt-3 text-2xl font-extrabold leading-snug tracking-tight sm:mt-4 sm:text-4xl">
          &ldquo;공부할 시간이 없다&rdquo;는
          <br />
          핑계, <span className="text-accent">오늘부로 끝.</span>
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted sm:mt-3 sm:text-base">
          버스에서, 쉬는 시간에, 잠들기 전 1~2분. 영어·수학 딱 5문제면 충분해요.
        </p>
      </div>

      <QuizApp />

      <AffirmationCard />

      <section className="w-full max-w-2xl px-4 pb-4 pt-6">
        <h2 className="mb-6 text-center text-lg font-bold sm:text-xl">이용 방법</h2>
        <div className="flex flex-col gap-4">
          {steps.map((s) => (
            <div key={s.title} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="mb-1.5 font-semibold">{s.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="w-full max-w-2xl px-4 pb-6">
        <h2 className="mb-6 text-center text-lg font-bold sm:text-xl">자주 묻는 질문</h2>
        <div className="flex flex-col gap-3">
          {faqs.map((f) => (
            <details
              key={f.q}
              className="group rounded-2xl border border-border bg-card p-5 open:pb-5"
            >
              <summary className="cursor-pointer list-none font-medium marker:content-none">
                <span className="flex items-center justify-between gap-3">
                  {f.q}
                  <span className="text-muted transition-transform group-open:rotate-45">+</span>
                </span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <footer className="flex flex-col items-center gap-2 text-center text-xs text-muted">
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
