"use client";

import { motion } from "motion/react";

export function Hero({ blogUrl }: { blogUrl: string }) {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <motion.span
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mb-6 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium uppercase tracking-[0.2em] text-foreground-muted"
      >
        매일 밤 3시간, 12주의 기록
      </motion.span>

      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-3xl font-serif text-5xl leading-tight font-semibold text-foreground sm:text-6xl lg:text-7xl"
      >
        건강한 하루를 기록하는 곳,{" "}
        <span className="bg-gradient-to-r from-accent to-accent-secondary bg-clip-text text-transparent">
          WellLog
        </span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="mt-6 max-w-xl text-lg leading-relaxed text-foreground-muted"
      >
        건강·생활정보를 다루는 1인 블로그 프로젝트입니다. 검증된 정보를
        하나씩, 꾸준히 쌓아가고 있어요.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
      >
        <motion.a
          href={blogUrl}
          target="_blank"
          rel="noopener noreferrer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="cursor-pointer rounded-full bg-accent px-8 py-3.5 text-base font-medium text-white shadow-[0_0_40px_-8px_var(--accent-glow)] transition-colors hover:bg-accent/90"
        >
          블로그 방문하기
        </motion.a>
        <a
          href="#pillars"
          className="cursor-pointer rounded-full border border-white/15 px-8 py-3.5 text-base font-medium text-foreground transition-colors hover:bg-white/5"
        >
          어떤 이야기인지 보기
        </a>
      </motion.div>

      <motion.div
        animate={{ y: [0, 8, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-10 flex flex-col items-center gap-2 text-foreground-muted"
      >
        <span className="text-xs tracking-[0.2em] uppercase">Scroll</span>
        <svg width="16" height="24" viewBox="0 0 16 24" fill="none" aria-hidden="true">
          <rect x="1" y="1" width="14" height="22" rx="7" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="8" cy="7" r="1.5" fill="currentColor" />
        </svg>
      </motion.div>
    </section>
  );
}
