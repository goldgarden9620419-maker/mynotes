"use client";

import { motion } from "framer-motion";
import MatjipFinder from "./components/MatjipFinder";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center bg-background px-4 py-16 sm:py-24">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-10 flex flex-col items-center text-center"
      >
        <span className="mb-3 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted">
          내 위치 기반 맛집 추천
        </span>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          숨은맛집찾기
        </h1>
        <p className="mt-3 max-w-md text-sm text-muted sm:text-base">
          프랜차이즈는 빼고, 지금 내 위치 근처의 진짜 숨은 맛집만 찾아드려요.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="flex w-full flex-col items-center"
      >
        <MatjipFinder />
      </motion.div>

      <footer className="mt-16 text-center text-xs text-muted">
        © 2026 숨은맛집찾기 · 위치 정보는 브라우저에서만 사용되며 저장되지 않습니다.
      </footer>
    </div>
  );
}
