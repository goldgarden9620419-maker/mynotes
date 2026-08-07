"use client";

import { motion } from "motion/react";

export function Mascot() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="pointer-events-none absolute top-28 right-4 hidden select-none sm:block lg:top-32 lg:right-16"
      aria-hidden="true"
    >
      <motion.div
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg width="130" height="150" viewBox="0 0 140 150" fill="none">
          <defs>
            <linearGradient id="mascotGradient" x1="20" y1="34" x2="120" y2="124" gradientUnits="userSpaceOnUse">
              <stop stopColor="#5e6ad2" />
              <stop offset="1" stopColor="#7c3aed" />
            </linearGradient>
          </defs>

          <motion.ellipse
            cx="70"
            cy="132"
            rx="30"
            ry="7"
            fill="#5e6ad2"
            animate={{ opacity: [0.22, 0.1, 0.22], scaleX: [1, 0.85, 1] }}
            transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
          />

          <motion.path
            d="M70 20 C 78 4, 96 4, 100 18 C 88 22, 76 24, 70 20 Z"
            fill="#7c3aed"
            animate={{ rotate: [-6, 6, -6] }}
            transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
            style={{ transformOrigin: "70px 20px" }}
          />

          <rect x="20" y="34" width="100" height="90" rx="45" fill="url(#mascotGradient)" />

          <circle cx="46" cy="90" r="7" fill="#ffffff" opacity="0.18" />
          <circle cx="94" cy="90" r="7" fill="#ffffff" opacity="0.18" />

          <motion.g
            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
            transition={{
              duration: 4,
              repeat: Infinity,
              times: [0, 0.85, 0.9, 0.95, 1],
              ease: "easeInOut",
            }}
            style={{ transformOrigin: "70px 78px" }}
          >
            <circle cx="52" cy="78" r="7" fill="#0a0a0c" />
            <circle cx="88" cy="78" r="7" fill="#0a0a0c" />
            <circle cx="54" cy="76" r="2" fill="#ffffff" />
            <circle cx="90" cy="76" r="2" fill="#ffffff" />
          </motion.g>

          <path
            d="M58 96 Q70 106 82 96"
            stroke="#0a0a0c"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      </motion.div>
    </motion.div>
  );
}
