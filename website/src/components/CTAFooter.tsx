"use client";

import { motion } from "motion/react";
import { Mascot } from "./Mascot";
import { Reveal } from "./Reveal";

export function CTAFooter({ blogUrl }: { blogUrl: string }) {
  return (
    <footer className="relative px-6 py-32">
      <Mascot pose="heart" size={100} delay={0.2} className="top-6 right-4 lg:top-10 lg:right-24" />
      <Reveal className="mx-auto flex max-w-2xl flex-col items-center rounded-3xl border border-white/12 bg-white/[0.07] px-8 py-16 text-center backdrop-blur-xl">
        <h2 className="font-serif text-3xl font-semibold text-foreground sm:text-4xl">
          지금부터 함께 지켜봐 주세요
        </h2>
        <p className="mt-4 max-w-md text-foreground-muted">
          12주 후 결과가 어떻게 될지, 블로그에서 실시간으로 확인할 수 있어요.
        </p>
        <motion.a
          href={blogUrl}
          target="_blank"
          rel="noopener noreferrer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="mt-8 cursor-pointer rounded-full bg-accent px-8 py-3.5 text-base font-medium text-white shadow-[0_0_40px_-8px_var(--accent-glow)] transition-colors hover:bg-accent/90"
        >
          블로그 방문하기
        </motion.a>
        <p className="mt-10 text-xs text-foreground-muted">
          © 2026 WellLog. 건강·생활정보를 기록합니다.
        </p>
      </Reveal>
    </footer>
  );
}
