"use client";

import { motion } from "motion/react";
import { Mascot } from "./Mascot";
import { daysSinceKst } from "@/lib/date";

const PRACTICE_START_DATE = "2026-07-01";

export function Hero({ blogUrl }: { blogUrl: string }) {
  const day = daysSinceKst(PRACTICE_START_DATE);

  return (
    <section className="relative flex min-h-[100dvh] flex-col items-center justify-center px-6 text-center">
      <Mascot />
      <motion.span
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mb-6 rounded-full border border-white/12 bg-white/[0.07] px-4 py-1.5 text-xs font-medium uppercase tracking-[0.2em] text-foreground-muted"
      >
        새벽 기상 실천{" "}
        <span className="font-semibold text-accent">{day}일째</span>
      </motion.span>

      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-3xl font-serif text-4xl leading-tight font-semibold text-foreground sm:text-6xl lg:text-7xl"
      >
        <span className="block">확언 한 줄로,</span>
        <span className="block text-accent">정말 인생이 바뀔까</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="mt-6 max-w-xl text-lg leading-relaxed text-foreground-muted"
      >
        새벽 기상과 확언으로 삶을 바꾼 실제 경험을 기록합니다. 부자의 습관과
        마인드셋을 함께 나눠요.
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
          이야기 읽으러 가기
        </motion.a>
        <a
          href="#pillars"
          className="cursor-pointer rounded-full border border-white/18 px-8 py-3.5 text-base font-medium text-foreground transition-colors hover:bg-white/[0.07]"
        >
          어떤 이야기인지 보기
        </a>
      </motion.div>
    </section>
  );
}
