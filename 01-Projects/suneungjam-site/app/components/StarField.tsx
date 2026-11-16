"use client";

import { useEffect, useRef } from "react";

/** 은은하게 깜빡이는 별 배경. 내용 뒤에 깔리고, '동작 줄이기'이거나 탭이 숨겨지면 멈춘다. */
export default function StarField() {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const lowEnd = (navigator.hardwareConcurrency || 4) <= 2;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);

    let stars: { x: number; y: number; r: number; p: number; s: number }[] = [];
    let raf = 0;
    let lastDraw = 0;

    function init() {
      if (!canvas) return;
      canvas.width = Math.floor(window.innerWidth * dpr);
      canvas.height = Math.floor(window.innerHeight * dpr);
      const n = lowEnd ? 22 : Math.min(60, Math.floor(window.innerWidth / 10));
      stars = Array.from({ length: n }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: (Math.random() * 1.1 + 0.4) * dpr,
        p: Math.random() * Math.PI * 2,
        s: Math.random() * 0.8 + 0.3,
      }));
    }

    function draw(t: number) {
      if (!canvas || !ctx) return;
      if (!document.hidden && t - lastDraw > 40) {
        lastDraw = t;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (const s of stars) {
          const a = reduce ? 0.3 : 0.16 + 0.3 * (0.5 + 0.5 * Math.sin((t / 1000) * s.s + s.p));
          ctx.fillStyle = `rgba(210,240,230,${a.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      if (!reduce) raf = requestAnimationFrame(draw);
    }

    init();
    raf = requestAnimationFrame(draw);
    window.addEventListener("resize", init);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", init);
    };
  }, []);

  return <canvas ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 h-full w-full" />;
}
