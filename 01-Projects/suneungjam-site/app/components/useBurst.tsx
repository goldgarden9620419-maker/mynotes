"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * 정답 연출용 입자 효과. 화면 전체를 덮는 투명 캔버스에 그리고 클릭을 막지 않는다.
 * '동작 줄이기' 설정이면 아무것도 그리지 않는다. 입자가 모두 사라지면 그리기를 멈춘다.
 */

export type BurstKind = "correct" | "finish" | "perfect";

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  g: number;
  size: number;
  rot: number;
  vr: number;
  life: number;
  max: number;
  color: string;
  shape: "dot" | "star" | "rect";
};

const COLORS = ["#34d399", "#6ee7b7", "#fcd34d", "#60a5fa", "#f9a8d4"];
const GOLD = ["#fcd34d", "#fde68a", "#fbbf24"];

function reducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function star(ctx: CanvasRenderingContext2D, r: number) {
  ctx.beginPath();
  for (let i = 0; i < 5; i++) {
    const a = (i * 4 * Math.PI) / 5 - Math.PI / 2;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
}

export function useBurst() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const particles = useRef<Particle[]>([]);
  const raf = useRef(0);
  const last = useRef(0);

  const frame = useCallback((t: number) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      raf.current = 0;
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dt = last.current ? Math.min(t - last.current, 50) : 16;
    last.current = t;
    const k = dt / 16;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const dpr = canvas.width / window.innerWidth;
    const list = particles.current;
    let alive = 0;
    for (const p of list) {
      p.life += dt;
      if (p.life >= p.max) continue;
      alive++;
      p.vy += p.g * k;
      p.x += p.vx * k;
      p.y += p.vy * k;
      p.rot += p.vr * k;
      const u = p.life / p.max;
      const a = u < 0.1 ? u / 0.1 : u > 0.65 ? Math.max(0, (1 - u) / 0.35) : 1;
      ctx.save();
      ctx.globalAlpha = a;
      ctx.translate(p.x * dpr, p.y * dpr);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      const s = p.size * dpr;
      if (p.shape === "dot") {
        ctx.beginPath();
        ctx.arc(0, 0, s, 0, Math.PI * 2);
        ctx.fill();
      } else if (p.shape === "star") {
        star(ctx, s * 1.4);
      } else {
        ctx.fillRect(-s, -s * 0.5, s * 2, s);
      }
      ctx.restore();
    }
    particles.current = list.filter((p) => p.life < p.max);
    if (alive > 0) {
      raf.current = requestAnimationFrame(frame);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      raf.current = 0;
      last.current = 0;
    }
  }, []);

  const resize = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
  }, []);

  useEffect(() => {
    resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [resize]);

  const fire = useCallback(
    (kind: BurstKind, x?: number, y?: number) => {
      if (reducedMotion()) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      const out: Particle[] = [];
      if (kind === "correct") {
        const ox = x ?? w / 2;
        const oy = y ?? h / 2;
        for (let i = 0; i < 26; i++) {
          const ang = Math.random() * Math.PI * 2;
          const sp = Math.random() * 4.2 + 1.6;
          out.push({
            x: ox, y: oy,
            vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp - 2.4,
            g: 0.16, size: Math.random() * 3 + 2,
            rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.2,
            life: 0, max: 800 + Math.random() * 500,
            color: COLORS[(Math.random() * COLORS.length) | 0],
            shape: Math.random() < 0.4 ? "star" : "dot",
          });
        }
      } else {
        const n = kind === "perfect" ? 110 : 70;
        const palette = kind === "perfect" ? [...COLORS, ...GOLD, ...GOLD] : COLORS;
        for (let i = 0; i < n; i++) {
          out.push({
            x: Math.random() * w, y: -20 - Math.random() * h * 0.35,
            vx: (Math.random() - 0.5) * 2.2, vy: Math.random() * 2 + 1.6,
            g: 0.035, size: Math.random() * 3.5 + 2,
            rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.25,
            life: -Math.random() * 500, max: 2400 + Math.random() * 1200,
            color: palette[(Math.random() * palette.length) | 0],
            shape: (["rect", "rect", "star", "dot"] as const)[(Math.random() * 4) | 0],
          });
        }
      }
      particles.current.push(...out);
      if (!raf.current) raf.current = requestAnimationFrame(frame);
    },
    [frame],
  );

  const Canvas = (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-50 h-full w-full"
    />
  );

  return { fire, Canvas };
}
