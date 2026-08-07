# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** WellLog
**Generated:** 2026-08-07 (manually curated — overrides the auto-generated default)
**Category:** Personal blog landing page (건강·생활정보, AdSense project)
**Brief:** 다크 무드, 글래스모피즘, 시네마틱 스크롤 애니메이션

---

## Global Rules

### Style Base

Blend of two ui-ux-pro-max styles:
- **Modern Dark (Cinema Mobile)** — deep near-black gradient, glassmorphism cards, ambient glow blobs, frosted blur nav
- **Parallax Storytelling** — scroll-driven section reveals, layered depth, cinematic transitions (implemented via Motion `whileInView` / `useScroll` instead of GSAP ScrollTrigger)

### Color Palette

| Role | Value | CSS Variable |
|------|-------|--------------|
| Background Deep | `#0F172A` | `--bg-deep` |
| Background Base | `#131A30` | `--bg-base` |
| Background Elevated | `#192134` | `--bg-elevated` |
| Glass Surface | `rgba(255,255,255,0.07)` | `--surface` |
| Foreground | `#FFFFFF` | `--foreground` |
| Foreground Muted | `#94A3B8` | `--foreground-muted` |
| Accent Primary (Indigo) | `#6366F1` | `--accent` |
| Accent Secondary (Violet) | `#7C3AED` | `--accent-secondary` |
| Accent Glow | `rgba(99,102,241,0.32)` | `--accent-glow` |
| Border | `rgba(255,255,255,0.12)` | `--border` |
| Destructive | `#DC2626` | `--destructive` |

**Notes (updated — brighter revision):** Moved off near-black onto a lighter slate-navy scale (`#0F172A → #131A30 → #192134`, Tailwind slate-900-ish) so the dark mode reads brighter while staying dark. Glass cards: `background: var(--surface)`, `backdrop-filter: blur(20px)`, `border: 1px solid var(--border)`, `border-radius: 16px`.

### Typography

- **Display / Hero Font:** Lora (serif) — warmth for a personal health & lifestyle brand
- **UI / Body Font:** Inter (sans) — cinematic precision, matches the "Modern Dark Cinema" pairing
- **Google Fonts:** `https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=Inter:wght@300;400;500;600;700&display=swap` (loaded via `next/font/google`, not a CSS import)
- **Scale:** Display 48–64px Lora 600, H2 28–32px Inter 600 (-0.5 tracking), Body 16px Inter 400, Label 12–13px Inter 500 uppercase (+1.2 tracking)

### Motion (via `motion/react`, not GSAP)

- Easing: `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out) for entrances
- Hero: staggered fade + rise on load
- Section reveals: `whileInView={{ opacity: 1, y: 0 }}` from `{ opacity: 0, y: 24 }`, `viewport={{ once: true, margin: "-100px" }}`
- Ambient background blobs: slow looping translate/opacity oscillation (indigo/violet, blurred, low opacity 0.08–0.15)
- Buttons/cards: `whileHover={{ scale: 1.02 }}`, `whileTap={{ scale: 0.98 }}`
- Respect `prefers-reduced-motion`

### Spacing

| Token | Value |
|-------|-------|
| `--space-xs` | `4px` |
| `--space-sm` | `8px` |
| `--space-md` | `16px` |
| `--space-lg` | `24px` |
| `--space-xl` | `32px` |
| `--space-2xl` | `48px` |
| `--space-3xl` | `64px` |

---

## Anti-Patterns (Do NOT Use)

- ❌ Pure black `#000000` background
- ❌ Emojis as icons — use inline SVG (Heroicons/Lucide-style)
- ❌ Missing `cursor-pointer` on clickable elements
- ❌ Text below 14px for body content
- ❌ Animating `width`/`height` directly — use `transform`/`opacity`
- ❌ Decorative-only animation with no meaning
- ❌ Low contrast text (below 4.5:1)

---

## Pre-Delivery Checklist

- [ ] No emojis used as icons (use SVG instead)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover/tap states with smooth transitions (150–300ms)
- [ ] Text contrast 4.5:1 minimum against dark backgrounds
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
