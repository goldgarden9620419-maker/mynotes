import type { Metadata } from "next";
import "./globals.css";
import { SiteBackground } from "@/components/ui/site-background";

export const metadata: Metadata = {
  title: "숨은맛집찾기 | 내 위치 기반 맛집 추천",
  description:
    "현재 위치, 인원수, 모임 성격, 먹고 싶은 음식을 입력하면 프랜차이즈를 뺀 근처 숨은 맛집을 찾아드려요.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full flex flex-col font-sans">
        <SiteBackground />
        {children}
      </body>
    </html>
  );
}
