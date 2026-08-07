"use client";

import { motion } from "motion/react";

const blobs = [
  { size: 520, top: "-10%", left: "8%", color: "var(--accent)", duration: 22 },
  { size: 420, top: "28%", left: "68%", color: "var(--accent-secondary)", duration: 26 },
  { size: 380, top: "68%", left: "18%", color: "var(--accent)", duration: 30 },
];

export function AmbientBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {blobs.map((blob, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full blur-3xl"
          style={{
            width: blob.size,
            height: blob.size,
            top: blob.top,
            left: blob.left,
            background: blob.color,
          }}
          animate={{
            x: [0, 40, -20, 0],
            y: [0, -30, 20, 0],
            opacity: [0.08, 0.16, 0.1, 0.08],
          }}
          transition={{
            duration: blob.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
