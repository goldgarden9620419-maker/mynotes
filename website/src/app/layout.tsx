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
    "건강·생활정보를 다루는 1인 블로그 WellLog. 직접 겪고 쓴 이야기를 나눕니다.",
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
