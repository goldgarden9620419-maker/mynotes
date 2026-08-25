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

const title = "황금정원 — 새벽 기상과 확언으로 바꾼 삶을 기록하는 블로그";
const description =
  "새벽 기상, 확언, 자기암시로 삶을 바꾼 실제 경험을 기록하는 블로그 황금정원. 부자의 습관과 마인드셋을 나눕니다.";

export const metadata: Metadata = {
  metadataBase: new URL("https://landing.goldjade0419.com"),
  title,
  description,
  openGraph: {
    title,
    description,
    url: "https://landing.goldjade0419.com",
    siteName: "황금정원",
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
  },
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
