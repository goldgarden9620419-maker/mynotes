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
          공감했다면, 함께 나눠주세요
        </h2>
        <p className="mt-4 max-w-md text-foreground-muted">
          내 이야기가 필요한 누군가에게 닿았으면 해요. 블로그에서 확인하고,
          마음에 닿으면 편하게 공유해주세요.
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
          © 2026 황금정원. 새벽 기상과 확언으로 만든 습관을 기록합니다.
        </p>
      </Reveal>
    </footer>
  );
}
