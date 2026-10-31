// promo2.html을 프레임 단위로 캡처해 mp4로 조립한다 (1080x1920, 30fps)
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import ffmpegPath from "ffmpeg-static";
import fs from "node:fs";
import path from "node:path";

const FPS = 30;
const DIR = path.dirname(new URL(import.meta.url).pathname);
const FRAMES = path.join(DIR, "frames2");

async function launch() {
  try {
    return await chromium.launch();
  } catch {
    // 설치된 브라우저 리비전이 playwright 기대 버전과 다를 때의 대비
    for (const p of [
      "/opt/pw-browsers/chromium",
      "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    ]) {
      if (fs.existsSync(p) && fs.statSync(p).isFile()) {
        return await chromium.launch({ executablePath: p });
      }
    }
    throw new Error("chromium을 찾지 못했습니다");
  }
}

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto("file://" + path.join(DIR, "promo2.html"));
await page.waitForFunction("window.READY === true", { timeout: 15000 });

const total = await page.evaluate("window.TOTAL");
const frameCount = Math.round((total / 1000) * FPS);
fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

console.log(`rendering ${frameCount} frames...`);
for (let i = 0; i < frameCount; i++) {
  await page.evaluate((t) => window.seek(t), (i * 1000) / FPS);
  await page.screenshot({ path: path.join(FRAMES, `f${String(i).padStart(4, "0")}.png`) });
  if (i % 100 === 0) console.log(`frame ${i}/${frameCount}`);
}
await browser.close();

console.log("encoding mp4...");
const out = path.join(DIR, "harubogo-promo2.mp4");
const r = spawnSync(
  ffmpegPath,
  ["-y", "-framerate", String(FPS), "-i", path.join(FRAMES, "f%04d.png"),
   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-movflags", "+faststart", out],
  { stdio: "inherit" }
);
if (r.status !== 0) throw new Error("ffmpeg failed");
console.log("done:", out);
