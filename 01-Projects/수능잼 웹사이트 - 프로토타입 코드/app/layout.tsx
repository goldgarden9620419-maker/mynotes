import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "수능잼 | 짬 나는 시간에 보는 수능 한 문제",
  description:
    "버스에서, 이동 중에, 짬날 때 1~2분이면 끝나는 영어·수학 수능 유형 문제. 정답을 맞히면 다음 문제로, 틀리면 바로 해설을 확인하세요.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full flex flex-col font-sans">
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6636318203503169"
          crossOrigin="anonymous"
          strategy="beforeInteractive"
        />
        {children}
      </body>
    </html>
  );
}
