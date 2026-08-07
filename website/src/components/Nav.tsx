"use client";

import { motion } from "motion/react";

export function Nav({ blogUrl }: { blogUrl: string }) {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4"
    >
      <div className="flex w-full max-w-5xl items-center justify-between rounded-full border border-white/10 bg-bg-base/80 px-5 py-3 shadow-[0_8px_32px_rgba(0,0,0,0.35)] backdrop-blur-xl">
        <span className="font-serif text-lg font-semibold tracking-tight text-foreground">
          WellLog
        </span>
        <a
          href={blogUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="cursor-pointer rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          블로그 방문하기
        </a>
      </div>
    </motion.header>
  );
}
