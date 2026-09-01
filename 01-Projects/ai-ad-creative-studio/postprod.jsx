/* ───────────────────────── POST PRODUCTION (후반 작업) ─────────────────────────
   BGM → 한국어 대사 → AI Voice → Lip Sync → Audio Mix → Preview → Export
   실제 연동: Higgsfield MCP (generate_audio / generate_video / jobs_wait /
   media_upload / media_confirm / sandbox_exec). Mock 결과를 만들지 않는다 —
   연결이 없으면 "API 연결 필요"를 표시한다. */
import React, { useState } from "react";
import * as C from "./catalogs.js";
import * as P from "./prompts.js";
import { hfReady, hfErrMsg, hfCall, hfWaitJob, hfGenerate, isUuid } from "./hf.js";

/* ── 기본 상태 ── */
export const POST_DEFAULTS = {
  step: 1,
  bgm: { skip: false, mood: "세련된 광고", mediaId: "", track: "", volume: 35, fadeIn: true, fadeOut: true, origVol: 0, ducking: true },
  lines: {},            // sceneId -> { text, mode: "LIP"|"VO"|"NONE" }
  voice: { gender: "여성", age: "30대", style: "Natural", engine: "minimax", voiceId: "c25f78a0-714e-42af-8da3-a399cef94968", speed: 1.0, jobs: {}, mergedId: "", mergedUrl: "" },
  lip: { jobId: "", url: "" },
  mix: { voice: 100, bgm: 35, orig: 0, mixedId: "", mixedUrl: "" },
  final: { mediaId: "", url: "", info: null, capcutUrl: "" }
};
export function mergePost(p) {
  const d = JSON.parse(JSON.stringify(POST_DEFAULTS));
  if (!p) return d;
  return {
    ...d, ...p,
    bgm: { ...d.bgm, ...(p.bgm || {}) },
    lines: p.lines || {},
    voice: { ...d.voice, ...(p.voice || {}) },
    lip: { ...d.lip, ...(p.lip || {}) },
    mix: { ...d.mix, ...(p.mix || {}) },
    final: { ...d.final, ...(p.final || {}) }
  };
}

/* ── Voice 프리셋 (힉스필드 실측 preset voice id) ── */
const VOICES = {
  "여성": [
    { id: "c25f78a0-714e-42af-8da3-a399cef94968", name: "Hana", note: "차분·자연스러움 (추천)" },
    { id: "e9cfbbf0-4476-46be-b396-596eb774b165", name: "Chloe", note: "밝고 친근함" },
    { id: "41023a48-71ab-478a-bea7-c7b5a78f6b36", name: "Sienna", note: "세련·프리미엄" },
    { id: "375a3398-e3b4-4f91-845d-42181e352899", name: "Luna", note: "부드러움·감성" },
    { id: "caeba733-3c17-43db-863e-69c7025512cd", name: "Naomi", note: "내레이션" },
    { id: "ca83ca7f-c186-493d-bd69-0d765fa861b2", name: "Elena", note: "따뜻함" }
  ],
  "남성": [
    { id: "6b528d43-c056-4a2f-9d82-1591a7ba13b0", name: "John", note: "표준·신뢰감" },
    { id: "6f98d3dd-324f-4845-8c28-c1d1647a06cd", name: "Marcus", note: "저음·프리미엄" },
    { id: "f1373f24-3b96-433f-9a68-e595810ef608", name: "Kevin", note: "친근함" },
    { id: "95429266-c0ac-4137-a209-63b8812b0f23", name: "Julian", note: "내레이션" }
  ]
};
const VOICE_STYLES = [
  { k: "Natural", sub: "일상 대화처럼 자연스러움 — 기본 추천" },
  { k: "Friendly", sub: "친구에게 말하듯 밝고 친근함" },
  { k: "Warm", sub: "부드럽고 다정한 톤" },
  { k: "Professional", sub: "정돈되고 신뢰감 있는 톤" },
  { k: "Premium", sub: "차분하고 고급스러운 광고 톤" },
  { k: "Energetic", sub: "활기차고 힘 있는 톤 — 감정 표현 강함" },
  { k: "Calm", sub: "낮고 차분함 — 감성·힐링 영상용" },
  { k: "UGC", sub: "실사용 후기 느낌의 편한 말투" },
  { k: "Narration", sub: "다큐·설명형 내레이션 톤" }
];
const VOICE_AGES = ["20대", "30대", "40대", "50대"];
const BGM_MOODS = ["감성적", "밝고 경쾌함", "세련된 광고", "프리미엄", "미니멀", "따뜻함", "에너지", "시네마틱", "트렌디 숏폼", "직접 업로드"];
/* ── 분위기별 BGM 카탈로그 — Kevin MacLeod (incompetech.com), CC BY 4.0.
   모든 URL은 렌더 서버에서 다운로드 검증 완료. 상업용 사용 가능, 캡션에 출처 1줄 필요. ── */
const BGM_BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/";
const bt = (name, note) => ({ name, note, url: BGM_BASE + encodeURIComponent(name) + ".mp3" });
const BGM_LIB = {
  "감성적": [bt("Dreams Become Real", "잔잔한 피아노 — 차분한 감성"), bt("Tranquility", "평온하고 부드러움"), bt("Floating Cities", "서정적인 피아노"), bt("Immersed", "몽환적·잔잔함"), bt("Bright Wish", "맑고 희망적")],
  "밝고 경쾌함": [bt("Carefree", "통통 튀는 가벼운 리듬 (추천)"), bt("Life of Riley", "업비트 팝"), bt("Monkeys Spinning Monkeys", "숏폼에서 유명한 경쾌 트랙"), bt("Happy Alley", "발랄·장난기"), bt("Fluffing a Duck", "귀엽고 가벼움")],
  "세련된 광고": [bt("Airport Lounge", "스무스 라운지 재즈 (추천)"), bt("Smooth Lovin", "부드러운 그루브"), bt("Bossa Antigua", "보사노바 — 여유로움"), bt("Lobby Time", "호텔 로비 재즈"), bt("George Street Shuffle", "세련된 셔플 재즈")],
  "프리미엄": [bt("Deliberate Thought", "미니멀 일렉트로닉 피아노 (추천)"), bt("Inspired", "서정적·고급스러움"), bt("Impact Prelude", "웅장한 시작"), bt("Backbay Lounge", "고급 라운지"), bt("Tranquility", "차분한 프리미엄")],
  "미니멀": [bt("Deliberate Thought", "미니멀의 기준 (추천)"), bt("Thinking Music", "가벼운 미니멀"), bt("Wallpaper", "단정하고 산뜻함"), bt("Immersed", "여백 있는 앰비언트"), bt("Floating Cities", "잔잔한 피아노")],
  "따뜻함": [bt("Wholesome", "따뜻하고 친근함 (추천)"), bt("Carpe Diem", "포근한 어쿠스틱"), bt("Dreams Become Real", "잔잔한 감성"), bt("Vibing Over Venus", "따뜻한 스윙"), bt("Bright Wish", "맑고 다정함")],
  "에너지": [bt("Cut and Run", "빠르고 에너제틱"), bt("Electrodoodle", "일렉트로 팝 에너지"), bt("Upbeat Forever", "계속 올라가는 텐션"), bt("Pamgaea", "드라이브감"), bt("Rollin at 5", "그루브 있는 펑크")],
  "시네마틱": [bt("Prelude and Action", "영화 예고편 느낌"), bt("Impact Prelude", "웅장한 빌드업"), bt("Inspired", "감동적인 스코어"), bt("Floating Cities", "서정적 피아노"), bt("Dreams Become Real", "잔잔한 엔딩")],
  "트렌디 숏폼": [bt("Funk Game Loop", "펑키 루프 (추천)"), bt("Funkorama", "레트로 펑크"), bt("Electrodoodle", "일렉트로 그루브"), bt("Monkeys Spinning Monkeys", "밈으로 유명한 트랙"), bt("Daily Beetle", "가볍고 리드미컬")]
};
export function bgmCredit(track) { return track ? `Music: ${track} — Kevin MacLeod (incompetech.com), CC BY 4.0` : ""; }
const VOICE_DIRECTION = `자연스러운 한국어 일상 대화체로 말한다.
전문 광고 성우처럼 지나치게 또박또박 읽지 않는다.
친한 사람에게 직접 사용해 본 제품을 추천하듯 편안하게 이야기한다.
문장마다 자연스러운 억양 변화를 주고 쉼표에서는 짧게 호흡한다.
'…' 부분에서는 약 0.2~0.5초 자연스럽게 쉬어간다.
과장된 홈쇼핑 억양을 사용하지 않는다.
모든 문장을 같은 속도와 같은 높낮이로 읽지 않는다.
중요한 단어만 자연스럽게 강조한다.`;

/* ── Voice Direction → seed_audio 파라미터 매핑 (텍스트로 읽히지 않도록 파라미터로 전달) ── */
function voiceParams(voice) {
  const rate = Math.round((voice.speed - 1) * 50) - 8; // 기본을 살짝 느리게
  const expr = { Energetic: 6, Friendly: 4, Warm: 4, UGC: 4 }[voice.style] || 3;
  return { speech_rate: Math.max(-25, Math.min(25, rate)), expression_intensity: expr };
}

/* ── 한국어 대사 자동 생성 (로컬 — 프로젝트 데이터 재사용, 재입력 없음) ── */
const FILLERS = ["근데", "저도", "사실", "이게", "생각보다", "특히", "써보니까", "솔직히"];
function pick(arr, seed) { return arr[Math.abs(seed) % arr.length]; }
function prodName(S) { return (S.product.name || "이 제품").replace(/\s*\d+\s*(ml|g|개입|정)?\s*$/i, ""); }
function genLine(scene, S, seed) {
  const nm = prodName(S);
  const usp = (S.product.usp || "").split(/[,·/]/)[0].trim();
  const role = scene.role;
  const t = (arrs) => pick(arrs, seed + scene.id * 7);
  if (role === "Hook") return t([
    "아 요즘 습기… 다들 에어컨만 켜시죠?",
    "하… 집이 왜 이렇게 꿉꿉하지 싶을 때 있죠?",
    "요즘 집 안이… 좀 꿉꿉하지 않으세요?"
  ]);
  if (role === "Model Introduction" || role === "Intro") return t([
    "저도 그랬는데… 이거 하나 두니까 확 다르더라고요.",
    "음… 사실 저도 별 기대 없었거든요.",
    "저희 집도 진짜… 똑같았어요."
  ]);
  if (role === "Product Reveal" || role === "Product Detail") return t([
    `근데 ${nm} 써보니까… 생각보다 괜찮더라고요.`,
    `이게 ${nm}인데요… 하나 두니까 확 다르더라고요.`,
    `아, ${nm} 하나면 충분하더라고요.`
  ]);
  if (role === "Benefit" || role === "Usage") return t([
    usp ? `특히 ${usp}… 이게 진짜 체감돼요.` : "보세요, 거울 김서림까지… 싹 사라져요.",
    "그냥 켜두기만 하면 되니까… 신경 쓸 게 없어요.",
    usp ? `${usp}… 이 부분이 제일 마음에 들어요.` : "크기는 아담한데… 소리도 거의 안 나요."
  ]);
  if (role === "Emotional Moment" || role === "Lifestyle") return t([
    "와… 아침 공기가 달라진 게 느껴져요.",
    "이제 집에 오면… 뽀송한 냄새부터 나요.",
    "그 눅눅한 느낌이… 사라졌어요."
  ]);
  if (role === "Hero Shot" || role === "Brand Ending") return t([
    "아 진짜… 장마철엔 이게 최고예요.",
    "솔직히… 진작 살 걸 그랬어요.",
    "올여름은… 이걸로 버티려고요."
  ]);
  if (role === "CTA") return t([
    "궁금하면 프로필 링크에서 확인해보세요.",
    "링크는 프로필에 있어요.",
    "자세한 건 프로필 링크에서 보세요."
  ]);
  return t(["직접 써보니까, 이건 추천할 만해요.", "생각보다 괜찮아서 공유해요."]);
}
/* 한 번 누를 때마다 반드시 한 단계씩 짧아지는 축약 파이프라인 */
function shortenOnce(text) {
  let t = (text || "").trim();
  // ① 문장 앞 감탄사·군말 제거
  const lead = t.replace(/^(아+|음+…?|와|하…?|이게|근데|생각보다|사실|솔직히|그니까|저기)[,\s]+/, "");
  if (lead !== t && lead.length >= 4) return lead;
  // ② "…" 뒤의 핵심 절만 남기기
  const parts = t.split("…");
  if (parts.length > 1) {
    const tail = parts[parts.length - 1].trim().replace(/^[,\s]+/, "");
    if (tail.length >= 5) return tail;
  }
  // ③ 여러 문장이면 첫 문장만
  const sents = t.split(/(?<=[.!?])\s+/);
  if (sents.length > 1) return sents[0];
  // ④ 강조 부사 제거
  const adv = t.replace(/(계속|아직도|진짜|정말|이제|그냥|한번|확)\s+/, "");
  if (adv !== t) return adv;
  // ⑤ 앞 짧은 절(쉼표 앞) 제거
  const comma = t.replace(/^[^,]{2,12},\s*/, "");
  if (comma !== t && comma.length >= 5) return comma;
  return t;
}
/* 대사 변형 버튼 */
function transformLine(text, kind, scene, S, seed) {
  if (kind === "다시 생성") return genLine(scene, S, seed + 1);
  if (kind === "더 짧게") return shortenOnce(text);
  if (kind === "더 자연스럽게") {
    const INTJ = ["아 ", "음… ", "와 ", "하… "];
    if (!/^(아|음|와|하|어|진짜)/.test(text)) return pick(INTJ, seed) + text;
    if (!text.includes("…")) return text.replace(/,\s*/, "… ");
    if (!FILLERS.some((f) => text.includes(f))) return pick(FILLERS, seed) + " " + text;
    return text.replace(/합니다\.?/g, "해요.").replace(/입니다\.?/g, "이에요.");
  }
  if (kind === "더 강하게") return text.replace(/괜찮/g, "확실히 다르").replace(/좋아요/g, "진짜 좋아요").replace(/\.$/, "!");
  if (kind === "친근하게") return text.replace(/합니다\.?/g, "해요.").replace(/하세요/g, "해보세요").replace(/제공/g, "챙겨줘");
  if (kind === "전문적으로") return text.replace(/근데 /g, "").replace(/진짜 /g, "확실히 ").replace(/괜찮더라고요/g, "만족스러웠어요");
  if (kind === "감성적으로") return text.replace(/\.$/, "… 그 기분, 아시죠?");
  return text;
}
/* 예상 음성 길이 — Minimax 실측(16음절+… ≈ 3.9초) 기준 4.5음절/초 + '…' 쉼 */
export function estDur(text, speed) {
  const syl = ((text || "").match(/[가-힣]/g) || []).length + ((text || "").match(/[A-Za-z0-9]+/g) || []).length * 2;
  const pauses = ((text || "").match(/…/g) || []).length * 0.35 + ((text || "").match(/[,.]/g) || []).length * 0.12;
  return syl / (4.5 * (speed || 1)) + pauses + 0.25;
}
/* 영상 길이에 맞게 자동 축약 */
function autoShorten(text, maxSec, speed, scene, S, seed) {
  let t = text, guard = 0;
  while (estDur(t, speed) > maxSec && guard < 4) { t = transformLine(t, "더 짧게", scene, S, seed); guard++; if (t === text) break; text = t; }
  return t;
}
/* Scene 자동 분류 — LIP / VO / NONE */
export function classifyScene(scene) {
  if (["Hero Shot", "Brand Ending"].includes(scene.role)) return "NONE";
  if ((scene.assets || []).includes("MODEL")) return "LIP";
  return "VO";
}

/* ───────── Provider Adapter 구조 (§21) — 특정 서비스 종속 최소화 ─────────
   API Key는 클라이언트에 없다 — 모든 호출은 뷰어의 claude.ai Higgsfield 커넥터
   (window.claude.mcp)를 통해 승인·인증된다. */
const VOICE_ENGINES = [
  { k: "minimax", label: "Minimax", sub: "한국어 억양이 가장 자연스러움 (추천 기본)" },
  { k: "elevenlabs", label: "ElevenLabs", sub: "감정 표현·호흡이 풍부함" },
  { k: "seed_speech", label: "Seed Speech", sub: "빠르고 깔끔한 발음" },
  { k: "seed_audio", label: "Seed Audio", sub: "속도·감정 세부 조절 가능" }
];
export const VoiceProvider = {
  getVoices: (gender) => VOICES[gender] || VOICES["여성"],
  async generateVoice(text, voice) {
    const engine = voice.engine || "minimax";
    const params = engine === "seed_audio"
      ? { model: "seed_audio", voice_type: "preset", voice_id: voice.voiceId, ...voiceParams(voice), prompt: text }
      : { model: "text2speech_v2", variant: engine, voice_type: "preset", voice_id: voice.voiceId, prompt: text,
          ...(engine === "minimax" ? { speed: voice.speed || 1 } : {}) };
    const p = await hfGenerate("generate_audio", params);
    const job = p && p.results && p.results[0];
    if (!job || !job.id) throw new Error("음성 작업 생성 실패: " + JSON.stringify(p || {}).slice(0, 160));
    const done = await hfWaitJob(job.id);
    return { jobId: job.id, url: done.result_url };
  },
  previewVoice(text, voice) { return this.generateVoice(text, voice); }
};
export const LipSyncProvider = {
  async generateLipSync({ prompt, duration, imageRefs, audioId, videoRef }) {
    const medias = [
      ...(videoRef ? [{ value: videoRef, role: "video_references" }] : []),
      ...imageRefs.map((v) => ({ value: v, role: "image_references" })),
      { value: audioId, role: "audio" }
    ];
    const p = await hfGenerate("generate_video", {
      model: "seedance_2_0", mode: "std", resolution: "1080p", aspect_ratio: "9:16",
      duration, generate_audio: false, medias, prompt
    });
    if (p && p.unlim_choice) return { unlim: p.unlim_choice };
    const job = p && p.results && p.results[0];
    if (!job || !job.id) throw new Error("립싱크 작업 생성 실패: " + JSON.stringify(p || {}).slice(0, 160));
    return { jobId: job.id };
  },
  getStatus: (jobId) => hfCall("jobs_wait", { jobs: [{ index: 0, job_id: jobId }], timeout_seconds: 15 }),
  getResult: (jobId) => hfWaitJob(jobId)
};
export const RenderProvider = {
  async upload(filename, contentType) {
    const p = await hfCall("media_upload", { filename, content_type: contentType });
    const u = p && p.uploads && p.uploads[0];
    if (!u || !u.upload_url) throw new Error("업로드 URL 발급 실패");
    return u; // { upload_url, media_id, url }
  },
  async run(command) {
    const p = await hfCall("sandbox_exec", { command, timeout_seconds: 120 });
    if (!p || p.exit_code !== 0) throw new Error("렌더 서버 오류: " + ((p && (p.stderr || p.stdout)) || "").slice(-300));
    return p.stdout || "";
  },
  confirm: (mediaId, type) => hfCall("media_confirm", { type, media_id: mediaId })
};

/* ── sandbox 스크립트 빌더 ── */
function shQ(u) { return "'" + String(u).replace(/'/g, "'\\''") + "'"; }
function buildVoiceMergeCmd(plan, uploadUrl) {
  // plan: { total, scenes: [{url, start, slot}] }
  const dl = plan.scenes.map((s, i) => `curl -sf -o v${i}.wav ${shQ(s.url)}`).join(" && ");
  return `cd /home/user && ${dl} && python3 - <<'PYEOF'
import subprocess, json
plan = json.loads(r'''${JSON.stringify(plan)}''')
def dur(f):
    o = subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_format',f])
    return float(json.loads(o)['format']['duration'])
n = len(plan['scenes'])
segs = []
for i, sc in enumerate(plan['scenes']):
    subprocess.check_call(['ffmpeg','-loglevel','error','-y','-i',f'v{i}.wav','-af',
      "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse", f'c{i}.wav'])
    d = dur(f'c{i}.wav')
    slot = max(0.5, sc['slot'] - 0.15)
    if d > slot:
        tempo = min(1.28, d / slot)
        subprocess.check_call(['ffmpeg','-loglevel','error','-y','-i',f'c{i}.wav','-af',f'atempo={tempo:.4f}',f't{i}.wav'])
    else:
        subprocess.check_call(['cp',f'c{i}.wav',f't{i}.wav'])
    segs.append((sc['start'] + 0.1, dur(f't{i}.wav')))
delays = [int(s[0]*1000) for s in segs]
fc = ''.join(f'[{i}]adelay={delays[i]}|{delays[i]}[a{i}];' for i in range(n))
fc += ''.join(f'[a{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0,alimiter=limit=0.95,apad=whole_dur={plan["total"]},atrim=0:{plan["total"]}'
cmd = ['ffmpeg','-loglevel','error','-y']
for i in range(n): cmd += ['-i', f't{i}.wav']
cmd += ['-filter_complex', fc, '-ar','44100','-ac','2','merged.wav']
subprocess.check_call(cmd)
print('PLACEMENT', json.dumps([{'start': round(s[0],2), 'dur': round(s[1],2)} for s in segs]))
PYEOF
curl -sf -X PUT -H "Content-Type: audio/wav" --data-binary @merged.wav ${shQ(uploadUrl)} -o /dev/null -w 'UPLOAD %{http_code}\\n'`;
}
function buildMixCmd(opts, uploadUrl) {
  // opts: { voiceUrl, bgmUrl?, videoUrl?, total, voiceVol, bgmVol, origVol, fadeIn, fadeOut, ducking }
  const T = opts.total, vv = opts.voiceVol / 100, bv = opts.bgmVol / 100, ov = opts.origVol / 100;
  const parts = [`cd /home/user`, `curl -sf -o voice.wav ${shQ(opts.voiceUrl)}`];
  const duck = !!(opts.bgmUrl && opts.ducking);
  // 덕킹 시 [v]가 사이드체인 입력으로 소비되므로 asplit으로 믹스용/사이드체인용을 분리
  let inputs = `-i voice.wav`;
  let chains = [duck ? `[0:a]volume=${vv.toFixed(2)},asplit=2[v][vsc]` : `[0:a]volume=${vv.toFixed(2)}[v]`];
  let mixIn = ["[v]"], idx = 1;
  if (opts.bgmUrl) {
    parts.push(`curl -sf -o bgm.audio ${shQ(opts.bgmUrl)}`);
    inputs += ` -stream_loop -1 -i bgm.audio`;
    let b = `[${idx}:a]atrim=0:${T},volume=${bv.toFixed(2)}`;
    if (opts.fadeIn) b += `,afade=t=in:d=1.2`;
    if (opts.fadeOut) b += `,afade=t=out:st=${Math.max(0, T - 1.6).toFixed(1)}:d=1.6`;
    b += `[b0]`;
    chains.push(b);
    if (duck) { chains.push(`[b0][vsc]sidechaincompress=threshold=0.02:ratio=10:attack=40:release=450[bd]`); mixIn.push("[bd]"); }
    else mixIn.push("[b0]");
    idx++;
  }
  if (opts.videoUrl && ov > 0.01) {
    parts.push(`curl -sf -o src.mp4 ${shQ(opts.videoUrl)}`);
    parts.push(`(ffmpeg -loglevel error -y -i src.mp4 -vn -map 0:a:0 orig.wav) || ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t ${T} orig.wav`);
    inputs += ` -i orig.wav`;
    chains.push(`[${idx}:a]volume=${ov.toFixed(2)}[o]`);
    mixIn.push("[o]");
    idx++;
  }
  const fc = chains.join(";") + ";" + mixIn.join("") + `amix=inputs=${mixIn.length}:normalize=0,alimiter=limit=0.95,apad=whole_dur=${T},atrim=0:${T}`;
  parts.push(`ffmpeg -loglevel error -y ${inputs} -filter_complex "${fc}" -ar 44100 -ac 2 mix.wav`);
  parts.push(`curl -sf -X PUT -H "Content-Type: audio/wav" --data-binary @mix.wav ${shQ(uploadUrl)} -o /dev/null -w 'UPLOAD %{http_code}\\n'`);
  return parts.join(" && ");
}
/* STEP 2 대사를 씬 타이밍에 맞춰 자막(ASS)으로 — 캡컷 없이 자막 번인 */
function buildAss(rows, total, lineOf) {
  const t = (s) => {
    const cs = Math.max(0, Math.round(s * 100));
    const h = Math.floor(cs / 360000), m = Math.floor(cs / 6000) % 60, sec = Math.floor(cs / 100) % 60, c = cs % 100;
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}.${String(c).padStart(2, "0")}`;
  };
  const evs = rows.map((r) => {
    const ln = lineOf(r.scene);
    if (!(ln.text || "").trim() || ln.mode === "NONE") return null;
    const st = r.start + 0.1, en = Math.min(r.end, total) - 0.05;
    if (en <= st) return null;
    const text = ln.text.replace(/[\r\n]+/g, " ").replace(/[{}]/g, "").replace(/ASSEOF/g, "");
    return `Dialogue: 0,${t(st)},${t(en)},Cap,${text}`;
  }).filter(Boolean);
  if (!evs.length) return "";
  return [
    "[Script Info]", "PlayResX: 1080", "PlayResY: 1920", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
    "Style: Cap,Noto Sans KR,62,&H00FFFFFF,&H99000000,&H00000000,1,4,0,8,60,60,620", "",
    "[Events]", "Format: Layer, Start, End, Style, Text",
    ...evs
  ].join("\n");
}
/* 캡컷용 SRT 자막 — 씬 타이밍 그대로 */
function buildSrt(rows, total, lineOf) {
  const t = (s) => {
    const ms = Math.max(0, Math.round(s * 1000));
    const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60, mm = ms % 1000;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")},${String(mm).padStart(3, "0")}`;
  };
  let i = 0;
  const blocks = rows.map((r) => {
    const ln = lineOf(r.scene);
    if (!(ln.text || "").trim() || ln.mode === "NONE") return null;
    const st = r.start + 0.1, en = Math.min(r.end, total) - 0.05;
    if (en <= st) return null;
    i += 1;
    return `${i}\n${t(st)} --> ${t(en)}\n${ln.text.replace(/[\r\n]+/g, " ")}`;
  }).filter(Boolean);
  return blocks.join("\n\n") + "\n";
}
/* 캡컷 편집 패키지 — 영상·음성·BGM·SRT·캡션을 ZIP으로.
   heredoc은 && 체인으로 이으면 종료 마커가 깨지므로 set -e + 줄 단위로 실행한다. */
function buildCapcutCmd(opts, uploadUrl) {
  const body = (s) => {
    s = String(s || "").replace(/SRTEOF|CAPEOF/g, "");
    return s.endsWith("\n") ? s : s + "\n";
  };
  const lines = ["set -e", "cd /home/user", "rm -rf pkg && mkdir pkg"];
  lines.push(`curl -sf -o pkg/video_no_subs.mp4 ${shQ(opts.videoUrl)}`);
  if (opts.voiceUrl) lines.push(`curl -sf -o pkg/voice_track.wav ${shQ(opts.voiceUrl)}`);
  if (opts.bgmUrl) {
    lines.push(`curl -sfL -o bgm_src.audio ${shQ(opts.bgmUrl)}`);
    lines.push(`ffmpeg -loglevel error -y -i bgm_src.audio -t ${opts.total} -af "afade=t=out:st=${Math.max(0, opts.total - 1.6).toFixed(1)}:d=1.6" pkg/bgm_${Math.round(opts.total)}s.mp3`);
  }
  lines.push(`cat > pkg/subtitles.srt <<'SRTEOF'\n${body(opts.srt)}SRTEOF`);
  lines.push(`cat > pkg/caption_instagram.txt <<'CAPEOF'\n${body(opts.capIg)}CAPEOF`);
  lines.push(`cat > pkg/caption_tiktok.txt <<'CAPEOF'\n${body(opts.capTt)}CAPEOF`);
  lines.push(`cd pkg && zip -q -r ../capcut_package.zip . && cd ..`);
  lines.push(`curl -sf -X PUT -H "Content-Type: application/zip" --data-binary @capcut_package.zip ${shQ(uploadUrl)} -o /dev/null -w 'UPLOAD %{http_code}\n'`);
  return lines.join("\n");
}
function buildMuxCmd(videoUrl, audioUrl, uploadUrl, ass) {
  const subPart = ass
    ? ` && curl -sfL -o NotoSansKR.ttf 'https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf' && cat > subs.ass <<'ASSEOF'
${ass}
ASSEOF
`
    : " && ";
  const vopts = ass ? `-vf "ass=subs.ass:fontsdir=." -c:v libx264 -preset veryfast -crf 19` : `-c:v copy`;
  return `cd /home/user && curl -sf -o video.mp4 ${shQ(videoUrl)} && curl -sf -o mix.wav ${shQ(audioUrl)}${subPart}ffmpeg -loglevel error -y -i video.mp4 -i mix.wav -map 0:v:0 -map 1:a:0 ${vopts} -c:a aac -b:a 192k -shortest final.mp4 && ffprobe -v quiet -print_format json -show_format -show_streams final.mp4 | python3 -c "import sys,json; d=json.load(sys.stdin); f=d['format']; v=[s for s in d['streams'] if s['codec_type']=='video'][0]; print('INFO', json.dumps({'duration': round(float(f['duration']),1), 'size_mb': round(int(f['size'])/1048576,1), 'w': v['width'], 'h': v['height'], 'vcodec': v['codec_name']}))" && curl -sf -X PUT -H "Content-Type: video/mp4" --data-binary @final.mp4 ${shQ(uploadUrl)} -o /dev/null -w 'UPLOAD %{http_code}\\n'`;
}

/* ── 공용 UI 조각 ── */
function ApiGate({ children }) {
  if (hfReady()) return children;
  return (
    <div className="pp-api-warn">
      <strong>API 연결 필요</strong> — 이 기능은 claude.ai의 Higgsfield 커넥터로 실행됩니다. 결과를 흉내 내지 않습니다.
      <details><summary>API 설정 방법</summary>
        <ol>
          <li>claude.ai → 설정 → 커넥터에서 <b>Higgsfield</b>를 연결</li>
          <li>이 페이지를 새로고침하고 상단 권한 요청을 허용</li>
        </ol>
      </details>
    </div>
  );
}
function Busy({ st }) {
  if (!st || st.phase === "idle") return null;
  if (st.phase === "error") return <div className="gen-note pp-busy err">{st.msg}</div>;
  if (st.phase === "done") return st.msg ? <div className="gen-note pp-busy ok">{st.msg}</div> : null;
  return <div className="gen-note pp-busy">{st.msg} {st.pct != null && <b>{st.pct}%</b>}</div>;
}
function Slider({ label, value, onChange, min = 0, max = 100, step = 1, suffix = "%" }) {
  return (
    <div className="pp-slider">
      <label>{label}</label>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} />
      <span>{value}{suffix}</span>
    </div>
  );
}

/* ───────────────────────── 메인 컴포넌트 ───────────────────────── */
const PP_STEPS = ["BGM", "한국어 대사", "AI Voice", "Lip Sync", "Audio Mix", "Preview", "Export"];
export function StepPost({ S, set }) {
  const post = mergePost(S.post);
  const setPost = (patch) => set({ post: { ...post, ...patch } });
  const rows = P.timelineRows(S);
  const total = rows.length ? Math.min(15, rows[rows.length - 1].end) : 0;
  const gen = S.gen || {};
  const hasVideo = !!(gen.storyVidUrl || post.lip.url);
  const baseVideoUrl = post.lip.url || gen.storyVidUrl || "";

  // 완료 판정 (§1 — 단계별 완료 시각 표시)
  const lineOf = (sc) => { const ln = post.lines[sc.id] || {}; return { text: ln.text || "", mode: ln.mode || classifyScene(sc) }; };
  const spokenScenes = rows.map((r) => r.scene).filter((sc) => lineOf(sc).mode !== "NONE");
  const doneMap = {
    1: post.bgm.skip || /^https?:\/\//.test(post.bgm.mediaId),
    2: rows.length > 0 && spokenScenes.every((sc) => (lineOf(sc).text || "").trim().length > 0),
    3: !!post.voice.mergedId,
    4: !!post.lip.url,
    5: !!post.mix.mixedId,
    6: !!post.mix.mixedId && !!post.lip.url,
    7: !!post.final.url || !!post.final.capcutUrl
  };

  return (
    <>
      <h2>POST PRODUCTION <span className="pp-sub">광고 후반 작업</span></h2>
      {!rows.length && <div className="empty">먼저 5~7단계에서 Scene과 타임라인, 멀티샷 영상을 만들어주세요. 기존 데이터는 삭제되지 않습니다.</div>}
      <div className="pp-steps">
        {PP_STEPS.map((label, i) => {
          const n = i + 1;
          return (
            <button key={label} className={"pp-step" + (post.step === n ? " now" : "") + (doneMap[n] ? " done" : "")} onClick={() => setPost({ step: n })}>
              <span className="pp-idx">{doneMap[n] ? "✓" : n}</span>STEP {n}. {label}
            </button>
          );
        })}
      </div>
      {post.step === 1 && <PPBgm post={post} setPost={setPost} />}
      {post.step === 2 && <PPScript S={S} post={post} setPost={setPost} rows={rows} />}
      {post.step === 3 && <PPVoice S={S} post={post} setPost={setPost} rows={rows} total={total} />}
      {post.step === 4 && <PPLip S={S} post={post} setPost={setPost} rows={rows} total={total} />}
      {post.step === 5 && <PPMix S={S} post={post} setPost={setPost} total={total} baseVideoUrl={baseVideoUrl} />}
      {post.step === 6 && <PPPreview S={S} post={post} setPost={setPost} rows={rows} total={total} baseVideoUrl={baseVideoUrl} />}
      {post.step === 7 && <PPExport S={S} post={post} setPost={setPost} rows={rows} total={total} baseVideoUrl={baseVideoUrl} />}
      <div className="nav-buttons">
        <button className="ghost" disabled={post.step === 1} onClick={() => setPost({ step: post.step - 1 })}>← 이전 단계</button>
        <div className="spacer" />
        {post.step < 7
          ? <button className="primary" onClick={() => setPost({ step: post.step + 1 })}>다음 단계 →</button>
          : <span className={"pp-finish" + (doneMap[7] ? " ok" : "")}>
              {doneMap[7] ? "🎉 후반 작업 완료 — 최종 파일을 다운로드해서 업로드하면 끝!" : "마지막 단계입니다 — FINAL RENDER 또는 캡컷 편집 패키지로 마무리하세요"}
            </span>}
      </div>
    </>
  );
}

/* ── STEP 1. BGM ── */
function PPBgm({ post, setPost }) {
  const b = post.bgm;
  const up = (p) => setPost({ bgm: { ...b, ...p } });
  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 1 — BGM</div>
      <div className="opt-group">
        <div className="opt-title">분위기</div>
        <div className="opt-grid cols-5">
          {BGM_MOODS.map((m) => <button key={m} className={"opt" + (b.mood === m ? " sel" : "")} onClick={() => up({ mood: m })}>{m}</button>)}
        </div>
      </div>
      {b.mood !== "직접 업로드" && (
        <>
          <div className="gen-note">선택한 분위기에 맞는 검증된 무료 곡 5개입니다 (Kevin MacLeod · CC BY 4.0 — 상업용 사용 가능, 캡션에 출처 1줄만 넣으면 됩니다). <b>▶ 샘플 듣기</b>는 새 탭에서 재생됩니다.</div>
          <div className="bgm-tracks">
            {(BGM_LIB[b.mood] || []).map((t) => {
              const sel = b.mediaId === t.url;
              return (
                <div key={t.name + t.note} className={"bgm-track" + (sel ? " sel" : "")}>
                  <div className="bgm-track-info"><b>{t.name}</b><span>{t.note}</span></div>
                  <a className="mini btn-link" href={t.url} target="_blank" rel="noreferrer">▶ 샘플 듣기</a>
                  <button className={"mini" + (sel ? " on" : "")} onClick={() => up({ mediaId: t.url, track: t.name, skip: false })}>{sel ? "✓ 선택됨" : "이 곡 사용"}</button>
                </div>
              );
            })}
          </div>
          {b.track && b.mediaId && (
            <div className="gen-note ok">
              선택된 BGM: <b>{b.track}</b> — 믹싱 시 앞부분만 잘라 페이드·덕킹이 적용됩니다.
              <button className="mini" onClick={() => { try { navigator.clipboard.writeText(bgmCredit(b.track)); } catch (e) {} }}>캡션용 출처 복사</button>
              <span className="bgm-credit">{bgmCredit(b.track)}</span>
            </div>
          )}
        </>
      )}
      {b.mood === "직접 업로드" && (
        <>
          <div className="gen-note">가지고 있는 곡을 쓰려면: Claude 채팅에서 힉스필드 업로드 위젯으로 BGM 파일(mp3/wav)을 올린 뒤, 결과에 표시되는 <b>파일 URL(https://…)</b>을 붙여넣으세요.</div>
          <div className="field-row">
            <label>BGM 파일 URL</label>
            <input className="text-field" value={b.mediaId} placeholder="예: https://…cloudfront.net/…/bgm.mp3"
              onChange={(e) => up({ mediaId: e.target.value.trim(), track: "", skip: false })} />
          </div>
          {b.mediaId && !/^https?:\/\//.test(b.mediaId) && <div className="gen-note err">URL 형식이 아닙니다 — media ID가 아니라 https:// 로 시작하는 파일 URL을 붙여넣어주세요.</div>}
        </>
      )}
      <Slider label="BGM Volume" value={b.volume} onChange={(v) => up({ volume: v })} />
      <Slider label="Original Audio Volume" value={b.origVol} onChange={(v) => up({ origVol: v })} />
      <div className="pp-toggles">
        <label><input type="checkbox" checked={b.fadeIn} onChange={(e) => up({ fadeIn: e.target.checked })} /> Fade In</label>
        <label><input type="checkbox" checked={b.fadeOut} onChange={(e) => up({ fadeOut: e.target.checked })} /> Fade Out</label>
        <label><input type="checkbox" checked={b.ducking} onChange={(e) => up({ ducking: e.target.checked })} /> Auto Ducking (Voice 재생 중 BGM 자동 감쇠)</label>
        <label><input type="checkbox" checked={b.skip} onChange={(e) => up({ skip: e.target.checked })} /> BGM 없이 진행 (업로드/편집 앱에서 추가)</label>
      </div>
    </div>
  );
}

/* ── STEP 2. 한국어 대사 ── */
function PPScript({ S, post, setPost, rows }) {
  const [seed, setSeed] = useState(1);
  const lines = post.lines;
  const upLine = (id, patch) => setPost({ lines: { ...lines, [id]: { ...(lines[id] || {}), ...patch } } });
  const genAll = () => {
    const next = { ...lines };
    rows.forEach((r) => {
      const mode = (next[r.scene.id] && next[r.scene.id].mode) || classifyScene(r.scene);
      next[r.scene.id] = { mode, text: mode === "NONE" ? "" : genLine(r.scene, S, seed) };
    });
    setPost({ lines: next });
    setSeed(seed + 1);
  };
  const fitAll = () => {
    const next = { ...lines };
    rows.forEach((r) => {
      const ln = next[r.scene.id];
      if (ln && ln.text) next[r.scene.id] = { ...ln, text: autoShorten(ln.text, r.end - r.start - 0.2, post.voice.speed, r.scene, S, seed) };
    });
    setPost({ lines: next });
  };
  const fmt = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.round(t % 60)).padStart(2, "0")}`;
  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 2 — 한국어 광고 대사</div>
      <div className="gen-note">제품명·소구점·Scene 구성·길이는 프로젝트에서 자동으로 가져옵니다 — 다시 입력할 필요 없습니다. 홈쇼핑 톤이 아니라 실제 사용자가 말하는 톤으로 생성됩니다. "스토리보드 작성" 단계에서 이미 대사를 써두셨다면 여기 자동으로 채워져 있으니 확인·다듬기만 하면 됩니다.</div>
      <div className="gen-row">
        <button className="primary small" onClick={genAll}>🎬 AI 한국어 대사 생성</button>
        <button className="mini" onClick={fitAll}>영상 길이에 맞게 자동 축약</button>
      </div>
      {rows.map((r, i) => {
        const sc = r.scene;
        const raw = lines[sc.id] || {};
        const ln = { text: raw.text || "", mode: raw.mode || classifyScene(sc) };
        const slot = r.end - r.start;
        const est = estDur(ln.text, post.voice.speed);
        const fit = !ln.text || est <= slot;
        return (
          <div className="pp-scene" key={sc.id}>
            <div className="pp-scene-head">
              <b>SCENE {String(i + 1).padStart(2, "0")}</b>
              <span>{fmt(r.start)}~{fmt(r.end)} · {slot.toFixed(1)}s · {C.disp(C.SCENE_ROLES, sc.role)}</span>
              <span className="pp-modes">
                {["LIP", "VO", "NONE"].map((m) => (
                  <button key={m} className={"mini" + (ln.mode === m ? " on" : "")} onClick={() => upLine(sc.id, { mode: m })}>
                    {m === "LIP" ? "LIP SYNC" : m === "VO" ? "VOICE OVER" : "NO VOICE"}
                  </button>
                ))}
              </span>
            </div>
            {ln.mode !== "NONE" && (
              <>
                <textarea className="pp-line" rows={2} value={ln.text} placeholder="이 씬의 대사"
                  onChange={(e) => upLine(sc.id, { text: e.target.value })} />
                <div className="pp-line-tools">
                  {["다시 생성", "더 자연스럽게", "더 짧게", "더 강하게", "친근하게", "전문적으로", "감성적으로"].map((k) => (
                    <button key={k} className="mini" onClick={() => { upLine(sc.id, { text: transformLine(ln.text || genLine(sc, S, seed), k, sc, S, seed) }); setSeed(seed + 1); }}>{k}</button>
                  ))}
                  <span className={"pp-fit" + (fit ? " ok" : " warn")}>
                    영상 {slot.toFixed(1)}s · 예상 음성 {ln.text ? est.toFixed(1) : "0"}s · {fit ? "✓ 적합" : "⚠ 대사가 너무 깁니다"}
                  </span>
                </div>
              </>
            )}
            {ln.mode === "NONE" && <div className="gen-note">음성 없는 씬 — Hero Shot·로고·CTA 화면은 BGM만으로 더 효과적일 수 있습니다.</div>}
          </div>
        );
      })}
    </div>
  );
}

/* ── STEP 3. AI Voice ── */
function PPVoice({ S, post, setPost, rows, total }) {
  const v = post.voice;
  const upV = (p) => setPost({ voice: { ...v, ...p } });
  const [st, setSt] = useState({ phase: "idle" });
  const [pv, setPv] = useState({ phase: "idle" });
  const voices = VoiceProvider.getVoices(v.gender);
  const lineOf = (sc) => { const ln = post.lines[sc.id] || {}; return { text: ln.text || "", mode: ln.mode || classifyScene(sc) }; };
  const spoken = rows.filter((r) => { const ln = lineOf(r.scene); return ln.mode !== "NONE" && (ln.text || "").trim(); });

  const preview = async () => {
    const first = spoken[0];
    if (!first) { setPv({ phase: "error", msg: "먼저 STEP 2에서 대사를 만들어주세요." }); return; }
    try {
      setPv({ phase: "run", msg: "미리듣기 생성 중… (30초~1분)" });
      const r = await VoiceProvider.previewVoice(lineOf(first.scene).text, v);
      setPv({ phase: "done", msg: "", url: r.url });
    } catch (e) { setPv({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };
  const generateAll = async () => {
    try {
      const jobs = {};
      for (let i = 0; i < spoken.length; i++) {
        const r = spoken[i];
        setSt({ phase: "run", msg: `Scene ${i + 1}/${spoken.length} 음성 생성 중…`, pct: Math.round((i / (spoken.length + 1)) * 100) });
        const res = await VoiceProvider.generateVoice(lineOf(r.scene).text, v);
        jobs[r.scene.id] = res;
      }
      setSt({ phase: "run", msg: "음성을 타임라인에 배치하고 합치는 중… (렌더 서버)", pct: 90 });
      const up = await RenderProvider.upload("ad-voice-track.wav", "audio/wav");
      const plan = { total, scenes: spoken.map((r) => ({ url: jobs[r.scene.id].url, start: Math.min(r.start, total - 0.5), slot: Math.min(r.end, total) - r.start })) };
      const out = await RenderProvider.run(buildVoiceMergeCmd(plan, up.upload_url));
      if (!/UPLOAD 200/.test(out)) throw new Error("음성 트랙 업로드 실패: " + out.slice(-160));
      await RenderProvider.confirm(up.media_id, "audio");
      setPost({ voice: { ...v, jobs, mergedId: up.media_id, mergedUrl: up.url } });
      setSt({ phase: "done", msg: "Scene별 음성 생성 + 15초 통합 트랙 완성 ✓" });
    } catch (e) { setSt({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };

  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 3 — AI Voice</div>
      <div className="opt-group"><div className="opt-title">음성 엔진</div><div className="opt-grid cols-4">
        {VOICE_ENGINES.map((e) => <button key={e.k} className={"opt" + ((v.engine || "minimax") === e.k ? " sel" : "")} onClick={() => upV({ engine: e.k })}>{e.label}<span className="opt-desc">{e.sub}</span></button>)}
      </div></div>
      <div className="opt-group"><div className="opt-title">성별</div><div className="opt-grid cols-4">
        {["여성", "남성"].map((g) => <button key={g} className={"opt" + (v.gender === g ? " sel" : "")} onClick={() => upV({ gender: g, voiceId: VOICES[g][0].id })}>{g}</button>)}
      </div></div>
      <div className="opt-group"><div className="opt-title">연령대</div><div className="opt-grid cols-4">
        {VOICE_AGES.map((a) => <button key={a} className={"opt" + (v.age === a ? " sel" : "")} onClick={() => upV({ age: a })}>{a}</button>)}
      </div></div>
      <div className="opt-group"><div className="opt-title">Voice Style</div><div className="opt-grid cols-3">
        {VOICE_STYLES.map((s) => <button key={s.k} className={"opt" + (v.style === s.k ? " sel" : "")} onClick={() => upV({ style: s.k })}>{s.k}<span className="opt-desc">{s.sub}</span></button>)}
      </div></div>
      <div className="opt-group"><div className="opt-title">목소리</div><div className="opt-grid cols-3">
        {voices.map((vo) => <button key={vo.id} className={"opt" + (v.voiceId === vo.id ? " sel" : "")} onClick={() => upV({ voiceId: vo.id })}>{vo.name}<span className="opt-desc">{vo.note}</span></button>)}
      </div></div>
      <Slider label="Speed" value={v.speed} onChange={(x) => upV({ speed: x })} min={0.8} max={1.2} step={0.05} suffix="x" />
      <details className="pp-direction"><summary>Voice Direction (기본값 보기)</summary>
        <pre>{VOICE_DIRECTION}</pre>
        <div className="gen-note">이 디렉션은 음성 API에 텍스트로 읽히는 것이 아니라 속도·감정 파라미터와 대사의 '…'·쉼표로 반영됩니다.</div>
      </details>
      <ApiGate>
        <div className="gen-row">
          <button className="primary small" disabled={pv.phase === "run"} onClick={preview}>▶ Voice Preview (첫 씬 1개)</button>
          {pv.phase === "done" && pv.url && <span className="gen-note ok">완료 ✓ <a href={pv.url} target="_blank" rel="noreferrer">새 탭에서 듣기</a></span>}
        </div>
        <Busy st={pv} />
        <div className="gen-row">
          <button className="primary small" disabled={st.phase === "run" || !spoken.length} onClick={generateAll}>
            🎙 Scene별 Voice 생성 → 통합 트랙 만들기 ({spoken.length}개 씬)
          </button>
          {v.mergedUrl && <span className="gen-note ok">Voice 확정 ✓ <a href={v.mergedUrl} target="_blank" rel="noreferrer">트랙 듣기</a></span>}
        </div>
        <Busy st={st} />
      </ApiGate>
      <div className="gen-note">씬 음성이 씬 길이를 넘으면 무음 트림 → 안전 범위(최대 1.28배) 속도 보정 순서로 맞춥니다. 그래도 길면 STEP 2의 자동 축약을 사용하세요 — 과도한 배속보다 대사를 줄이는 것이 우선입니다.</div>
    </div>
  );
}

/* ── STEP 4. Lip Sync ── */
function PPLip({ S, post, setPost, rows, total }) {
  const [st, setSt] = useState({ phase: "idle" });
  const gen = S.gen || {};
  const lineOf = (sc) => { const ln = post.lines[sc.id] || {}; return { text: ln.text || "", mode: ln.mode || classifyScene(sc) }; };
  const canRun = post.voice.mergedId && gen.storyJobId;

  const buildPrompt = () => {
    const base = P.buildStoryboardVideoPrompt(S).en;
    const fmtRange = (r) => `${r.start.toFixed(1)}–${Math.min(r.end, total).toFixed(1)}s`;
    const syncLines = rows.map((r, i) => {
      const ln = lineOf(r.scene);
      if (ln.mode === "LIP") return `Scene ${i + 1} (${fmtRange(r)}): she speaks ON CAMERA — lip-sync her mouth precisely to the Korean audio in this window.`;
      if (ln.mode === "VO") return `Scene ${i + 1} (${fmtRange(r)}): VOICEOVER — the audio plays but she does NOT move her lips.`;
      return `Scene ${i + 1} (${fmtRange(r)}): NO VOICE — no speech in this window.`;
    }).join("\n");
    return [
      base,
      `AUDIO SYNC — The supplied ${total.toFixed(1)}-second Korean narration track drives the video. Sync exactly:\n${syncLines}\nWhen she speaks, mouth movements match the Korean syllables naturally, like unhurried everyday conversation — relaxed, not salesperson energy.`,
      `FACE PRESERVATION — Lip-sync must not change who she is. Keep identical: face shape, eyes, nose, skin, hairstyle, base expression, lighting, camera motion, background, outfit and the product. Modify only the minimal mouth region needed for speech; never regenerate her face into a different person.`,
      `ONLY ONE PHYSICAL PRODUCT — exactly ONE physical unit in every scene; any second appearance must only be a reflection inside mirror glass, never a duplicate standing in the room.`
    ].join("\n\n");
  };

  const buildResyncPrompt = () => {
    const fmtRange = (r) => `${r.start.toFixed(1)}–${Math.min(r.end, total).toFixed(1)}s`;
    const wins = rows.map((r, i) => {
      const m = lineOf(r.scene).mode;
      if (m === "NONE" || !(lineOf(r.scene).text || "").trim()) return `${fmtRange(r)} (Scene ${i + 1}): NO speech — her mouth stays closed in a natural soft smile.`;
      if (m === "VO") return `${fmtRange(r)} (Scene ${i + 1}): VOICEOVER — audio plays but she does NOT move her lips.`;
      return `${fmtRange(r)} (Scene ${i + 1}): she speaks ON CAMERA — mouth follows the audio precisely.`;
    }).join("\n");
    return [
      `PRECISE LIP-SYNC RE-PASS — The supplied reference VIDEO is the master. Reproduce it as closely as possible: the same scenes in the same order with the same timing, the same person with identical face and outfit, the same rooms, props, product placement, lighting, color grade and camera moves. Do NOT invent new shots, new angles, new rooms or new actions.`,
      `The ONLY thing to change: her mouth and jaw articulation must match the supplied Korean narration audio EXACTLY — lips open on syllable onsets, close on syllable ends, visible consonant/vowel shapes for Korean speech, and a fully CLOSED relaxed mouth whenever there is silence in the audio.`,
      `AUDIO SYNC WINDOWS:\n${wins}\nIf the audio line inside a window ends early, her mouth closes immediately and stays closed until the next window.`,
      `FACE PRESERVATION — identical face, hairstyle, expression baseline, lighting and identity as the reference video. Modify only the mouth region needed for speech; never turn her into a different person.`,
      `PRODUCT PRESERVATION — the product looks exactly like the reference photo, never deformed or re-spelled. Exactly ONE physical unit in every scene.`,
      `Do NOT add any NEW Korean or English text, numbers, subtitles, captions, logos, watermarks or UI overlays anywhere in the video.`,
      `Total length ${total.toFixed(1)} seconds, aspect ratio 9:16 vertical, photorealistic, natural everyday conversation energy.`
    ].join("\n\n");
  };
  const run = async (resync) => {
    try {
      setSt({ phase: "run", msg: (resync ? "입모양 정밀 재동기화 중… " : "립싱크 영상 생성 중… ") + "(3~6분)" });
      const r = await LipSyncProvider.generateLipSync({
        prompt: resync ? buildResyncPrompt() : buildPrompt(),
        duration: Math.min(15, Math.max(4, Math.round(total))),
        imageRefs: resync ? [gen.productRef].filter(isUuid) : [gen.storyJobId, gen.productRef].filter(isUuid),
        audioId: post.voice.mergedId,
        videoRef: resync ? post.lip.jobId : undefined
      });
      if (r.unlim) { setSt({ phase: "error", msg: "잔액 선택이 필요합니다 — 힉스필드 위젯/채팅에서 무료 생성 또는 크레딧을 선택 후 다시 시도해주세요." }); return; }
      const done = await LipSyncProvider.getResult(r.jobId);
      setPost({ lip: { jobId: r.jobId, url: done.result_url } });
      setSt({ phase: "done", msg: resync ? "입모양 재동기화 완성 ✓ — 미리보기에서 확인해주세요" : "립싱크 영상 완성 ✓" });
    } catch (e) { setSt({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };

  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 4 — Lip Sync</div>
      <div className="gen-note">AI가 씬을 자동 분류했습니다 — 모델이 말하는 씬만 립싱크하고, 나머지는 보이스오버/무음으로 둡니다. STEP 2에서 씬별로 직접 바꿀 수 있습니다.</div>
      <table className="pp-table"><tbody>
        {rows.map((r, i) => {
          const m = lineOf(r.scene).mode;
          return <tr key={r.scene.id}><td>SCENE {String(i + 1).padStart(2, "0")}</td><td>{C.disp(C.SCENE_ROLES, r.scene.role)}</td>
            <td className={"pp-mode-" + m}>{m === "LIP" ? "LIP SYNC ✓" : m === "VO" ? "VOICE OVER ✓" : "NO VOICE ✓"}</td></tr>;
        })}
      </tbody></table>
      <ApiGate>
        <div className="gen-row">
          <button className="primary small" disabled={!canRun || st.phase === "run"} onClick={() => run()}>
            💋 Lip Sync 영상 생성 (음성 트랙 기준)
          </button>
          {!canRun && <span className="gen-note">먼저 STEP 3에서 Voice 통합 트랙을 만들어주세요{gen.storyJobId ? "" : " (6단계 스토리보드도 필요)"}.</span>}
          {post.lip.url && <span className="gen-note ok">완성 ✓ <a href={post.lip.url} target="_blank" rel="noreferrer">▶ Lip Sync Preview</a>
            <button className="mini" onClick={() => run()}>다시 생성</button></span>}
        </div>
        {post.lip.jobId && (
          <div className="gen-row">
            <button className="primary small" disabled={!canRun || st.phase === "run"} onClick={() => run(true)}>🎯 입모양 정밀 재동기화 (현재 영상 기준)</button>
            <span className="gen-note">입모양이 음성과 안 맞을 때 — 위 영상을 그대로 참조로 고정하고 입 움직임만 음절 단위로 다시 맞춥니다.</span>
          </div>
        )}
        <Busy st={st} />
      </ApiGate>
      <div className="gen-note">참고: Seedance 2.0은 음성 트랙에 맞춰 영상 전체를 다시 생성하는 방식입니다. 입 주변만 잘라 수정하는 부분 편집은 지원되지 않아, 프롬프트의 FACE PRESERVATION 규칙으로 동일 인물·구도 유지를 강제합니다. 결과에서 얼굴이 달라졌다면 [다시 생성]을 눌러주세요.</div>
    </div>
  );
}

/* ── STEP 5. Audio Mix ── */
function PPMix({ S, post, setPost, total, baseVideoUrl }) {
  const m = post.mix, b = post.bgm;
  const upM = (p) => setPost({ mix: { ...m, ...p } });
  const [st, setSt] = useState({ phase: "idle" });
  const canRun = !!post.voice.mergedUrl;
  const run = async () => {
    try {
      setSt({ phase: "run", msg: "오디오 믹싱 중… (Voice + BGM" + (b.origVol > 0 ? " + Original" : "") + ")", pct: 30 });
      const up = await RenderProvider.upload("ad-audio-mix.wav", "audio/wav");
      const bgmUrl = !b.skip && /^https?:\/\//.test(b.mediaId) ? b.mediaId : "";
      const out = await RenderProvider.run(buildMixCmd({
        voiceUrl: post.voice.mergedUrl, bgmUrl, videoUrl: b.origVol > 0 ? baseVideoUrl : "",
        total, voiceVol: m.voice, bgmVol: b.volume, origVol: b.origVol,
        fadeIn: b.fadeIn, fadeOut: b.fadeOut, ducking: b.ducking
      }, up.upload_url));
      if (!/UPLOAD 200/.test(out)) throw new Error("믹스 업로드 실패: " + out.slice(-160));
      await RenderProvider.confirm(up.media_id, "audio");
      setPost({ mix: { ...m, mixedId: up.media_id, mixedUrl: up.url } });
      setSt({ phase: "done", msg: "오디오 믹스 완성 ✓ (클리핑 방지 리미터 적용)" });
    } catch (e) { setSt({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };
  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 5 — AUDIO MIXER</div>
      <Slider label="VOICE" value={m.voice} onChange={(v) => upM({ voice: v })} />
      <Slider label="BGM" value={b.volume} onChange={(v) => setPost({ bgm: { ...b, volume: v } })} />
      <Slider label="ORIGINAL AUDIO" value={b.origVol} onChange={(v) => setPost({ bgm: { ...b, origVol: v } })} />
      <div className="gen-note">Voice가 가장 명확하게 들리도록 믹싱하고, {b.ducking ? "Voice 구간에서 BGM을 자동으로 낮췄다가 (Auto Ducking) 대사가 끝나면 복원합니다." : "Auto Ducking이 꺼져 있습니다 (STEP 1)."} 최종 출력에는 리미터로 클리핑을 방지합니다. SFX 트랙은 현재 미지원입니다 — 필요하면 캡컷에서 추가하세요.</div>
      <ApiGate>
        <div className="gen-row">
          <button className="primary small" disabled={!canRun || st.phase === "run"} onClick={run}>🎚 오디오 믹스 생성</button>
          {!canRun && <span className="gen-note">먼저 STEP 3에서 Voice 트랙을 만들어주세요.</span>}
          {m.mixedUrl && <span className="gen-note ok">믹스 완성 ✓ <a href={m.mixedUrl} target="_blank" rel="noreferrer">들어보기</a></span>}
        </div>
        <Busy st={st} />
      </ApiGate>
      {!b.skip && b.mediaId && !/^https?:\/\//.test(b.mediaId) && <div className="gen-note err">STEP 1의 BGM URL 형식이 잘못되었습니다 — BGM 없이 믹싱됩니다.</div>}
    </div>
  );
}

/* ── STEP 6. Preview + 자동 검수 ── */
function PPPreview({ S, post, setPost, rows, total, baseVideoUrl }) {
  const lineOf = (sc) => { const ln = post.lines[sc.id] || {}; return { text: ln.text || "", mode: ln.mode || classifyScene(sc) }; };
  const checks = [];
  const add = (grp, ok, label, warn) => checks.push({ grp, ok, label, warn });
  add("VIDEO", rows.length > 0, "Scene 연결 정상", "타임라인이 비어 있습니다");
  add("VIDEO", !!baseVideoUrl, "영상 준비됨 (원본 해상도 1080×1920 유지)", "7단계 멀티샷 영상 또는 STEP 4 립싱크 영상이 필요합니다");
  add("VOICE", rows.every((r) => lineOf(r.scene).mode === "NONE" || (lineOf(r.scene).text || "").trim()), "대사 누락 없음", "빈 대사가 있는 씬이 있습니다");
  add("VOICE", rows.every((r) => { const ln = lineOf(r.scene); return ln.mode === "NONE" || !ln.text || estDur(ln.text, post.voice.speed) <= (r.end - r.start) + 0.6; }), "Scene Timing 정상 · 음성 잘림 없음", "씬 길이보다 긴 대사가 있습니다 — STEP 2 자동 축약 권장");
  add("LIP SYNC", !!post.lip.url, "입 모양·음성 동기화 영상 생성됨", "STEP 4를 실행하세요");
  add("LIP SYNC", true, "얼굴 변형 여부 — 미리보기에서 직접 확인 필요", "");
  add("AUDIO", !!post.mix.mixedId, "Voice 명료도 · Auto Ducking · 클리핑 방지 적용", "STEP 5 믹스를 만들어주세요");
  add("AUDIO", post.bgm.skip || /^https?:\/\//.test(post.bgm.mediaId), "BGM 설정 확인", "BGM 미설정 — STEP 1에서 건너뛰기를 체크하거나 파일 URL을 연결하세요");
  const firstLn = rows.length ? lineOf(rows[0].scene) : null;
  add("광고", rows.length > 0 && rows[0].scene.role === "Hook" && !!(firstLn && (firstLn.text || firstLn.mode === "NONE")), "첫 3초 Hook", "첫 씬을 Hook으로 설정하세요");
  add("광고", !!(S.product.usp || "").trim(), "핵심 소구점 전달", "1~2단계에서 제품 소구점을 입력하면 대사에 반영됩니다");
  add("광고", rows.some((r) => ["CTA", "Hero Shot", "Brand Ending"].includes(r.scene.role)) || (S.composer.cta || "").trim() !== "", "CTA 존재", "마지막 씬 역할 또는 CTA 문구를 설정하세요");
  const fails = checks.filter((c) => !c.ok);
  const fmt = (t) => t.toFixed(1) + "s";
  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 6 — PREVIEW · TIMELINE · 자동 검수</div>
      <div className="pp-timeline">
        {[
          ["VIDEO", rows.map((r) => ({ s: r.start, e: Math.min(r.end, total), on: true }))],
          ["VOICE", rows.map((r) => ({ s: r.start, e: Math.min(r.end, total), on: lineOf(r.scene).mode !== "NONE" && !!lineOf(r.scene).text }))],
          ["BGM", [{ s: 0, e: total, on: !post.bgm.skip && !!post.bgm.mediaId }]],
          ["LIP SYNC", rows.map((r) => ({ s: r.start, e: Math.min(r.end, total), on: lineOf(r.scene).mode === "LIP" }))]
        ].map(([name, segs]) => (
          <div className="pp-track" key={name}>
            <span className="pp-track-name">{name}</span>
            <div className="pp-track-bar">
              {segs.map((sg, i) => sg.on && total > 0 && (
                <span key={i} className="pp-seg" style={{ left: (sg.s / total * 100) + "%", width: (Math.max(0, sg.e - sg.s) / total * 100) + "%" }}
                  title={fmt(sg.s) + "–" + fmt(sg.e)} />
              ))}
            </div>
          </div>
        ))}
        <div className="gen-note">총 {total.toFixed(1)}초. 인페이지 재생은 보안 정책상 불가 — 미리보기는 새 탭에서 열립니다.</div>
      </div>
      <div className="gen-row">
        {post.lip.url && post.mix.mixedUrl
          ? <span className="gen-note">최종 화면+소리 합본은 STEP 7에서 렌더 후 재생됩니다. 지금은 개별 확인: <a href={post.lip.url} target="_blank" rel="noreferrer">▶ 영상(무음)</a> · <a href={post.mix.mixedUrl} target="_blank" rel="noreferrer">▶ 오디오 믹스</a></span>
          : <span className="gen-note">STEP 4(영상)와 STEP 5(오디오)를 완료하면 미리보기가 활성화됩니다.</span>}
      </div>
      <div className="section-divider">자동 검수</div>
      <div className="check-list">
        {checks.map((c, i) => (
          <div key={i} className={"check" + (c.ok ? " ok" : " warn")}>
            <span className="check-mark">{c.ok ? "☑" : "⚠"}</span> <b>{c.grp}</b> {c.label}
            {!c.ok && c.warn && <div className="check-warn">{c.warn}</div>}
          </div>
        ))}
      </div>
      {fails.length > 0 && <div className="gen-note err">렌더링 전에 {fails.length}개 항목을 확인하세요. 그대로 진행해도 되지만 결과 품질에 영향을 줄 수 있습니다.</div>}
    </div>
  );
}

/* ── STEP 7. Final Render + Export ── */
function PPExport({ S, post, setPost, rows, total, baseVideoUrl }) {
  const [st, setSt] = useState({ phase: "idle" });
  const lineOf = (sc) => { const ln = post.lines[sc.id] || {}; return { text: ln.text || "", mode: ln.mode || classifyScene(sc) }; };
  const hasSubLines = (rows || []).some((r) => { const ln = lineOf(r.scene); return ln.mode !== "NONE" && (ln.text || "").trim(); });
  const [burnSubs, setBurnSubs] = useState(true);
  const canRun = !!baseVideoUrl && !!post.mix.mixedUrl;
  const dateStr = () => { const d = new Date(); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`; };
  const fname = `${(prodName(S) || "AD").replace(/\s+/g, "_")}_AD_FINAL_${dateStr()}.mp4`;
  const run = async () => {
    try {
      setSt({ phase: "run", msg: "Preparing Video", pct: 10 });
      const up = await RenderProvider.upload(fname, "video/mp4");
      const ass = burnSubs && hasSubLines ? buildAss(rows, total, lineOf) : "";
      setSt({ phase: "run", msg: ass ? "Mixing Audio + 자막 번인 + Rendering" : "Mixing Audio + Rendering Video", pct: 45 });
      const out = await RenderProvider.run(buildMuxCmd(baseVideoUrl, post.mix.mixedUrl, up.upload_url, ass));
      setSt({ phase: "run", msg: "Encoding", pct: 90 });
      if (!/UPLOAD 200/.test(out)) throw new Error("최종 파일 업로드 실패: " + out.slice(-160));
      const infoMatch = out.match(/INFO (\{.*\})/);
      const info = infoMatch ? JSON.parse(infoMatch[1]) : null;
      await RenderProvider.confirm(up.media_id, "video");
      setPost({ final: { ...post.final, mediaId: up.media_id, url: up.url, info } });
      setSt({ phase: "done", msg: "Complete 100%" });
    } catch (e) { setSt({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };
  const [cst, setCst] = useState({ phase: "idle" });
  const capOf = (re) => {
    const pfs = P.platformsOf(S);
    const pf = pfs.find((p) => re.test(p)) || pfs[0] || "SNS";
    return P.buildSnsCaption(S, pf) + (post.bgm.track ? "\n" + bgmCredit(post.bgm.track) : "");
  };
  const runCapcut = async () => {
    try {
      setCst({ phase: "run", msg: "재료 수집 중 (영상·음성·BGM·자막)", pct: 15 });
      const up = await RenderProvider.upload("capcut_package.zip", "application/zip");
      const bgmUrl = !post.bgm.skip && /^https?:/.test(post.bgm.mediaId || "") ? post.bgm.mediaId : "";
      setCst({ phase: "run", msg: "ZIP 패키지 생성 중", pct: 55 });
      const out = await RenderProvider.run(buildCapcutCmd({
        videoUrl: baseVideoUrl, voiceUrl: post.voice.mergedUrl || "", bgmUrl, total,
        srt: buildSrt(rows, total, lineOf) || "1\n00:00:00,000 --> 00:00:01,000\n(대사 없음)\n",
        capIg: capOf(/insta/i), capTt: capOf(/tik ?tok|틱톡/i)
      }, up.upload_url));
      if (!/UPLOAD 200/.test(out)) throw new Error("패키지 업로드 실패: " + out.slice(-160));
      await RenderProvider.confirm(up.media_id, "file");
      setPost({ final: { ...post.final, capcutUrl: up.url } });
      setCst({ phase: "done", msg: "패키지 완성" });
    } catch (e) { setCst({ phase: "error", msg: e.code ? hfErrMsg(e) : e.message }); }
  };
  const f = post.final;
  return (
    <div className="pp-panel">
      <div className="section-divider">STEP 7 — FINAL RENDER & EXPORT</div>
      {hasSubLines && (
        <div className="pp-toggles">
          <label><input type="checkbox" checked={burnSubs} onChange={(e) => setBurnSubs(e.target.checked)} /> 자막 자동 입히기 — STEP 2 대사를 씬 타이밍에 맞춰 영상에 굽습니다 (캡컷 편집 불필요, 권장)</label>
        </div>
      )}
      <ApiGate>
        <div className="gen-row">
          <button className="primary" disabled={!canRun || st.phase === "run"} onClick={run}>🎞 FINAL RENDER{burnSubs && hasSubLines ? " (자막 포함)" : ""}</button>
          {!canRun && <span className="gen-note">영상(7단계 또는 STEP 4)과 오디오 믹스(STEP 5)가 먼저 필요합니다.</span>}
        </div>
        <Busy st={st} />
      </ApiGate>
      {f.url && (
        <div className="pp-final">
          <div className="pp-final-title">FINAL AD COMPLETE</div>
          <table className="pp-table"><tbody>
            <tr><td>Duration</td><td>{f.info ? f.info.duration + "s" : total.toFixed(1) + "s"}</td></tr>
            <tr><td>Resolution</td><td>{f.info ? f.info.w + " × " + f.info.h : "1080 × 1920"}</td></tr>
            <tr><td>Aspect Ratio</td><td>{P.sourceRatio(S)}</td></tr>
            <tr><td>File Size</td><td>{f.info ? f.info.size_mb + " MB" : "-"}</td></tr>
            <tr><td>Format</td><td>MP4 · {f.info ? f.info.vcodec.toUpperCase() : "H.264"} · AAC</td></tr>
            <tr><td>파일명(권장)</td><td>{fname}</td></tr>
          </tbody></table>
          <div className="gen-row">
            <a className="primary small btn-link" href={f.url} target="_blank" rel="noreferrer">▶ 최종 영상 재생</a>
            <a className="primary small btn-link" href={f.url} download={fname} target="_blank" rel="noreferrer">↓ MP4 다운로드</a>
            <span className="gen-note">다운로드 후 파일명을 위 권장 이름으로 저장하세요. 업로드 시 캡션에 쿠팡 파트너스 대가성 고지{post.bgm.track ? "와 BGM 출처(" + bgmCredit(post.bgm.track) + ")" : ""}를 꼭 포함하세요.</span>
          </div>
        </div>
      )}

      <div className="section-divider">📦 캡컷(CapCut) 편집 패키지 — 외부 편집용</div>
      <div className="gen-note">캡컷은 직접 연동(커넥터)이 지원되지 않아, 편집에 필요한 재료를 <b>ZIP 하나</b>로 묶어드립니다: 무자막 영상 + 음성 트랙 + {Math.round(total)}초로 잘라둔 BGM + 자막 SRT + 플랫폼별 캡션 2종.</div>
      <ApiGate>
        <div className="gen-row">
          <button className="primary" disabled={!baseVideoUrl || cst.phase === "run"} onClick={runCapcut}>📦 캡컷 편집 패키지 만들기</button>
          {!baseVideoUrl && <span className="gen-note">영상(7단계 멀티샷 또는 STEP 4 립싱크)이 먼저 필요합니다.</span>}
        </div>
        <Busy st={cst} />
      </ApiGate>
      {f.capcutUrl && (
        <div className="pp-scene">
          <div className="gen-row">
            <a className="primary small btn-link" href={f.capcutUrl} download="capcut_package.zip" target="_blank" rel="noreferrer">↓ capcut_package.zip 다운로드</a>
          </div>
          <div className="gen-note">
            <b>캡컷에서 가져오는 방법</b><br />
            ① ZIP 압축 해제 → 캡컷 새 프로젝트(9:16)에 <b>video_no_subs.mp4</b>를 타임라인에 올립니다.<br />
            ② 영상에 이미 음성·BGM이 믹스되어 있으면 그대로 쓰고, 오디오를 따로 다듬으려면 영상 음소거 후 <b>voice_track.wav</b>와 <b>bgm_*.mp3</b>를 오디오 트랙에 각각 올립니다.<br />
            ③ 자막: <b>캡컷 PC(데스크톱) 버전</b>에서 텍스트 → 로컬 자막 → <b>subtitles.srt</b> 가져오기 (모바일 앱은 SRT 가져오기 미지원 — PC에서 자막을 얹은 뒤 이어서 편집하세요).<br />
            ④ 업로드 시 <b>caption_instagram.txt / caption_tiktok.txt</b> 내용을 복사해 캡션으로 사용합니다 (쿠팡 파트너스 대가성 고지 포함됨).
          </div>
        </div>
      )}

      <div className="section-divider">업로드 캡션 (플랫폼별) — 복사하거나 파일로 저장</div>
      {P.platformsOf(S).map((pf) => {
        const cap = P.buildSnsCaption(S, pf) + (post.bgm.track ? "\n" + bgmCredit(post.bgm.track) : "");
        return (
          <div className="pp-scene" key={pf}>
            <div className="pp-scene-head"><b>{pf}</b>
              <span className="pp-modes">
                <button className="mini" onClick={() => { try { navigator.clipboard.writeText(cap); } catch (e) {} }}>복사</button>
                <button className="mini" onClick={async () => {
                  try {
                    if (window.claude && window.claude.downloads) await window.claude.downloads.save({ filename: "caption_" + pf.replace(/[^A-Za-z0-9]+/g, "_") + ".txt", data: cap });
                    else navigator.clipboard.writeText(cap);
                  } catch (e) {}
                }}>📥 파일 저장</button>
              </span>
            </div>
            <textarea className="pp-line" readOnly rows={7} value={cap} />
          </div>
        );
      })}
    </div>
  );
}
