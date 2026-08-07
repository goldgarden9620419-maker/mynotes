"use client";

import { motion } from "motion/react";

type MascotPose = "leaf" | "wave" | "flag" | "heart" | "note";

export function Mascot({
  className = "top-28 right-4 lg:top-32 lg:right-16",
  size = 130,
  pose = "leaf",
  delay = 0.6,
}: {
  className?: string;
  size?: number;
  pose?: MascotPose;
  delay?: number;
}) {
  const gradientId = `mascotGradient-${pose}`;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`pointer-events-none absolute hidden select-none sm:block ${className}`}
      aria-hidden="true"
    >
      <motion.div
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg width={size} height={size} viewBox="0 0 140 150" fill="none">
          <defs>
            <linearGradient id={gradientId} x1="20" y1="34" x2="120" y2="124" gradientUnits="userSpaceOnUse">
              <stop stopColor="#6366f1" />
              <stop offset="1" stopColor="#7c3aed" />
            </linearGradient>
          </defs>

          <motion.ellipse
            cx="70"
            cy="132"
            rx="30"
            ry="7"
            fill="#6366f1"
            animate={{ opacity: [0.22, 0.1, 0.22], scaleX: [1, 0.85, 1] }}
            transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
          />

          {pose === "leaf" && (
            <motion.path
              d="M70 20 C 78 4, 96 4, 100 18 C 88 22, 76 24, 70 20 Z"
              fill="#7c3aed"
              animate={{ rotate: [-6, 6, -6] }}
              transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
              style={{ transformOrigin: "70px 20px" }}
            />
          )}

          {pose === "flag" && (
            <motion.g
              animate={{ rotate: [-5, 5, -5] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              style={{ transformOrigin: "70px 30px" }}
            >
              <line x1="70" y1="30" x2="70" y2="4" stroke="#94a3b8" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M70 5 L70 19 L92 12 Z" fill="#7c3aed" />
            </motion.g>
          )}

          {pose === "note" && (
            <motion.g
              animate={{ y: [0, -3, 0], rotate: [-3, 3, -3] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
              style={{ transformOrigin: "75px 15px" }}
            >
              <rect x="56" y="11" width="36" height="7" rx="3.5" fill="#94a3b8" transform="rotate(-28 75 15)" />
              <path d="M90 8 L98 11 L90 15 Z" fill="#7c3aed" transform="rotate(-28 75 15)" />
            </motion.g>
          )}

          {pose === "heart" && (
            <motion.path
              d="M100 6 C97 0 88 0 87 8 C86 0 77 0 74 6 C71 14 87 26 87 26 C87 26 103 14 100 6 Z"
              fill="#f472b6"
              animate={{ scale: [1, 1.15, 1], y: [0, -4, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              style={{ transformOrigin: "87px 13px" }}
            />
          )}

          <rect x="20" y="34" width="100" height="90" rx="45" fill={`url(#${gradientId})`} />

          {pose === "wave" && (
            <motion.ellipse
              cx="128"
              cy="42"
              rx="9"
              ry="15"
              fill={`url(#${gradientId})`}
              animate={{ rotate: [0, -25, 5, -25, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 0.6, ease: "easeInOut" }}
              style={{ transformOrigin: "118px 55px" }}
            />
          )}

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
