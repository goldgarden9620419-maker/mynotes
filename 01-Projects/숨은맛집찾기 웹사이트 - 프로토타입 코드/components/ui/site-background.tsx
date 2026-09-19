"use client";

import { motion } from "framer-motion";

export function SiteBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      {/* 도트 그리드 패턴 */}
      <div
        className="absolute inset-0 opacity-[0.35] [--dot:var(--border)] bg-[radial-gradient(var(--dot)_1px,transparent_1px)] bg-[size:28px_28px]"
      />

      {/* 은은하게 떠다니는 그라데이션 블롭들 */}
      <motion.div
        className="absolute -top-20 -left-24 h-[26rem] w-[26rem] rounded-full bg-orange-300/60 blur-[80px]"
        animate={{ x: [0, 50, 0], y: [0, 35, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-[28%] -right-28 h-[30rem] w-[30rem] rounded-full bg-amber-300/55 blur-[90px]"
        animate={{ x: [0, -40, 0], y: [0, 45, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut", delay: 2 }}
      />
      <motion.div
        className="absolute top-[65%] left-[10%] h-[26rem] w-[26rem] rounded-full bg-orange-400/40 blur-[85px]"
        animate={{ x: [0, 35, 0], y: [0, -30, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut", delay: 4 }}
      />
      <motion.div
        className="absolute bottom-[-10%] right-[15%] h-[22rem] w-[22rem] rounded-full bg-yellow-200/50 blur-[75px]"
        animate={{ x: [0, -30, 0], y: [0, -20, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      />

      {/* 위/아래 비네트로 대비 정리 */}
      <div className="absolute inset-0 bg-gradient-to-b from-background/0 via-transparent to-background/60" />
    </div>
  );
}
