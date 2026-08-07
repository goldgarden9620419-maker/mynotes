import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "WellLog — 건강한 하루를 기록하는 블로그",
  description:
    "건강·생활정보를 다루는 1인 블로그 프로젝트 WellLog. 12주간의 기록으로 신뢰할 수 있는 콘텐츠를 쌓아갑니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${inter.variable} ${lora.variable} h-full`}>
      <body className="min-h-full bg-bg-base font-sans text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
