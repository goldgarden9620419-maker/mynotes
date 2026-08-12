import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import * as C from "./catalogs.js";
import * as P from "./prompts.js";

/* ───────────────────────── 초기 상태 (섹션 23 기본값) ───────────────────────── */
const DEFAULTS = {
  started: false,
  step: 0,
  visited: [],
  nanoCompare: null,
  gen: { productRef: "", modelRef: "", storyJobId: "", storyUrl: "", storyVidUrl: "" },
  library: [],
  project: {
    name: "", purpose: "제품 인지도", platforms: ["Instagram Reels", "TikTok"], ratio: "9:16",
    length: "10초", style: "Instagram Lifestyle", colorMood: "Warm Beige"
  },
  global: { lightDir: "Camera Left → Right", lightTemp: "Warm", lens: "35mm", camHeight: "Eye Level", frame: "Medium Shot" },
  model: {
    gender: "여성", ethnicity: "한국인 / 동아시아인", age: "30대 초반", face: "계란형",
    skin: "웜 아이보리", eyes: "자연스러운 아몬드형", iris: "다크 브라운",
    hairLen: "중간 길이", hairStyle: "자연스러운 웨이브", hairColor: "소프트 블랙",
    views: ["정면", "왼쪽 45도", "오른쪽 45도", "상반신", "전신"], lock: true
  },
  product: { name: "", usp: "", scale: "한 손 소형", img: null, shot: "Hero Product", angle: "Front", position: "중앙", bg: "Warm Beige", effects: ["없음"], lock: true },
  location: { places: ["프리미엄 주방"], interior: "Minimal Korean", time: "Morning", light: "Soft Window Light", lens: "35mm", camHeight: "Eye Level" },
  scenes: [],
  sceneSeq: 1,
  composer: {
    timeline: [], orderMode: "현재 순서", flow: "원테이크 연결", transitions: {}, bridges: {},
    adStyle: "Smooth Premium", colorGrade: "Warm Premium",
    sound: "Music", musicMood: "Premium Minimal", sfx: [],
    captions: [], captionText: {}, cta: "제품 알아보기", ctaCustom: "",
    partners: { enabled: true, link: "", tags: "" }
  },
  post: null // POST_DEFAULTS는 로드 시 mergePost()로 채워진다 (postprod.jsx)
};

const STORAGE_KEY = "aiadstudio:v1";

// 제습기 프로젝트 시드 — 최초 1회 자동 등록 (Claude 채팅에서 만든 결과물)
const SEED = {
  version: "dehumidifier-v4",
  places: ["프리미엄 주방", "럭셔리 욕실"],
  productRef: "6f63e2aa-9c8f-45f6-b394-59344e66082d",
  modelRef: "fee509dd-1e87-4178-b11c-81d14e9b95fb",
  storyJobId: "37617416-69c1-4936-b5c6-4706671a3a2a",
  library: [
    { id: "d55bd41a-25dd-40cb-926a-438408d33093", name: "씬1 습기 고민 훅" },
    { id: "0c54d120-7dba-4ce8-b579-77263cca8460", name: "씬2 제품 소개" },
    { id: "8d433c56-5a7f-41f1-a9aa-37fa994b7222", name: "씬3 욕실 거울" },
    { id: "8d80a06e-4718-466a-8a41-a557b94484f4", name: "씬4 히어로 마무리" },
    { id: "a8174c3a-4909-4991-b70c-e9e8cd7493ec", name: "주방 사용 컷" },
    { id: "00d304aa-b597-4bef-9a7c-731554350d4f", name: "뽀송한 일상" }
  ]
};
const SEED_UUID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
function applySeed(st) {
  const gen = { ...st.gen };
  // 잘린/불완전한 ID는 항상 올바른 시드 값으로 복구 (매 로드마다 검사)
  if (!gen.productRef || !SEED_UUID_RE.test(gen.productRef)) gen.productRef = SEED.productRef;
  if (!gen.modelRef || !SEED_UUID_RE.test(gen.modelRef)) gen.modelRef = SEED.modelRef;
  if (!gen.storyJobId || !SEED_UUID_RE.test(gen.storyJobId)) gen.storyJobId = SEED.storyJobId;
  if (st.seeded === SEED.version) return { ...st, gen };
  const lib = Array.isArray(st.library) ? [...st.library] : [];
  SEED.library.forEach((it) => { if (!lib.some((x) => x.id === it.id)) lib.push(it); });
  const loc = { ...st.location };
  const places = Array.isArray(loc.places) ? [...loc.places] : [];
  SEED.places.forEach((pl) => { if (!places.includes(pl)) places.push(pl); });
  loc.places = places;
  return { ...st, library: lib, gen, location: loc, seeded: SEED.version };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const s = JSON.parse(raw);
      if (s.project && s.project.platform && !Array.isArray(s.project.platforms)) s.project.platforms = [s.project.platform];
      if (s.location && s.location.place && !Array.isArray(s.location.places)) s.location.places = [s.location.place];
      return applySeed({ ...DEFAULTS, ...s, project: { ...DEFAULTS.project, ...s.project }, global: { ...DEFAULTS.global, ...s.global }, model: { ...DEFAULTS.model, ...s.model }, product: { ...DEFAULTS.product, ...s.product }, location: { ...DEFAULTS.location, ...s.location }, composer: { ...DEFAULTS.composer, ...s.composer }, gen: { ...DEFAULTS.gen, ...(s.gen || {}) }, library: Array.isArray(s.library) ? s.library : [], post: mergePost(s.post) });
    }
  } catch (e) {}
  return applySeed({ ...DEFAULTS, post: mergePost(null) });
}

const STEPS = ["프로젝트 설정", "제품", "AI 모델", "장소", "개별 Scene", "스토리보드", "Scene Composer", "최종 Export", "후반 작업"];
const STEP_KEYS = ["PROJECT", "PRODUCT", "MODEL", "LOCATION", "SCENES", "STORY", "COMPOSER", "EXPORT", "POST"];

/* ───────────────────────── 공용 컴포넌트 ───────────────────────── */
/* confirm() 팝업이 차단되는 환경이 있어, 위험 동작은 두 번 클릭 방식으로 확인한다 */
function ArmedButton({ label, armedLabel, className, onRun, disabled }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = setTimeout(() => setArmed(false), 5000);
    return () => clearTimeout(t);
  }, [armed]);
  return (
    <button className={(className || "") + (armed ? " armed" : "")} disabled={disabled}
      onClick={() => { if (armed) { setArmed(false); onRun(); } else setArmed(true); }}>
      {armed ? (armedLabel || "⚠ 한 번 더 클릭하면 실행됩니다") : label}
    </button>
  );
}

function CopyBtn({ text, label = "복사", small }) {
  const [done, setDone] = useState(false);
  return (
    <button className={"copy-btn" + (done ? " done" : "") + (small ? " small" : "")}
      onClick={() => {
        const fb = () => {
          const ta = document.createElement("textarea");
          ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
          document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); setDone(true); setTimeout(() => setDone(false), 1200); } catch (e) {}
          document.body.removeChild(ta);
        };
        if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1200); }).catch(fb);
        else fb();
      }}>{done ? "복사됨 ✓" : label}</button>
  );
}

function Options({ title, list, value, onChange, multi, rec, custom = true, cols }) {
  const [cv, setCv] = useState("");
  const isSel = (kr) => multi ? (value || []).includes(kr) : value === kr;
  const knownKrs = list.map((x) => x.kr);
  const customActive = multi
    ? (value || []).some((v) => !knownKrs.includes(v))
    : (value && !knownKrs.includes(value));
  return (
    <div className="opt-group">
      <div className="opt-title">{title}{multi && <span className="multi-tag">복수 선택</span>}</div>
      <div className={"opt-grid" + (cols ? " cols-" + cols : "")}>
        {list.map((opt) => (
          <button key={opt.kr} className={"opt" + (isSel(opt.kr) ? " sel" : "")}
            onClick={() => {
              if (multi) {
                const cur = value || [];
                onChange(cur.includes(opt.kr) ? cur.filter((x) => x !== opt.kr) : [...cur, opt.kr]);
              } else onChange(opt.kr);
            }}>
            {opt.disp || opt.kr}
            {opt.sub && <span className="opt-desc">{opt.sub}</span>}
          </button>
        ))}
      </div>
      {custom && (
        <div className="custom-row">
          <input value={cv} onChange={(e) => setCv(e.target.value)} placeholder="직접 입력"
            onKeyDown={(e) => { if (e.key === "Enter" && cv.trim()) { multi ? onChange([...(value || []), cv.trim()]) : onChange(cv.trim()); setCv(""); } }} />
          <button onClick={() => { if (!cv.trim()) return; multi ? onChange([...(value || []), cv.trim()]) : onChange(cv.trim()); setCv(""); }}>적용</button>
          {customActive && <span className="custom-note">직접 입력값 사용 중: {multi ? (value || []).filter((v) => !knownKrs.includes(v)).join(", ") : value}</span>}
        </div>
      )}
    </div>
  );
}

function Toggle({ label, desc, value, onChange }) {
  return (
    <div className={"toggle-card" + (value ? " on" : "")} onClick={() => onChange(!value)} role="switch" aria-checked={value} tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onChange(!value); } }}>
      <div className="toggle-pill"><div className="toggle-knob" /></div>
      <div>
        <div className="toggle-label">{label} <span className="toggle-state">{value ? "ON" : "OFF"}</span></div>
        <div className="toggle-desc">{desc}</div>
      </div>
    </div>
  );
}

function PromptBox({ title, kr, en }) {
  const [lang, setLang] = useState("EN");
  const text = lang === "EN" ? en : kr;
  return (
    <div className="prompt-box">
      <div className="pb-head">
        <span className="pb-title">{title}</span>
        <div className="pb-tabs">
          {["EN", "KR"].map((l) => <button key={l} className={lang === l ? "active" : ""} onClick={() => setLang(l)}>{l}</button>)}
        </div>
        <CopyBtn text={text} small />
      </div>
      <textarea readOnly value={text} rows={Math.min(16, Math.max(4, text.split("\n").length + 1))} />
    </div>
  );
}

/* ───────── 힉스필드 직접 생성 (window.claude.mcp) — hf.js 공용 헬퍼 사용 ───────── */
import { hfReady, hfErrMsg, hfCall, hfWaitJob, isUuid, refMedias, badRefs, UUID_RE } from "./hf.js";
import { StepPost, mergePost, POST_DEFAULTS } from "./postprod.jsx";

/* 생성 버튼 한 줄 — kind: 'image' | 'video' */
function GenRow({ kind, label, getParams, savedUrl, onResult, disabled, disabledMsg }) {
  const [st, setSt] = useState(savedUrl ? { phase: "done", url: savedUrl } : { phase: "idle" });
  const run = async (extra) => {
    if (!hfReady()) { setSt({ phase: "error", msg: "힉스필드 연결을 사용할 수 없습니다 — claude.ai에서 Higgsfield 커넥터를 연결한 뒤 이 페이지를 새로고침해주세요." }); return; }
    try {
      setSt({ phase: "starting" });
      const params = { ...getParams(), ...(extra || {}) };
      const bad = badRefs(params);
      if (bad.length) { setSt({ phase: "error", msg: "참조 ID가 불완전합니다 (붙여넣을 때 잘린 것 같아요): " + bad.map((b) => '"' + b + '"').join(", ") + " — 전체 ID(8-4-4-4-12자리, 총 36자)를 다시 붙여넣어주세요." }); return; }
      const tool = kind === "video" ? "generate_video" : "generate_image";
      let p = await hfCall(tool, { params });
      // 힉스필드가 프리셋 추천을 돌려주면 자동으로 거절하고 원래 프롬프트로 1회 재요청
      if (p && p.notice && p.notice.data && p.notice.data.retry_literal_with) {
        p = await hfCall(tool, { params: { ...params, ...p.notice.data.retry_literal_with } });
      }
      if (p && p.unlim_choice) { setSt({ phase: "unlim", q: p.unlim_choice }); return; }
      const job = p && p.results && p.results[0];
      if (!job || !job.id) {
        const detail = p && (p.error && (p.error.message || p.error) || p.message || p.detail);
        throw new Error("작업 생성에 실패했습니다" + (detail ? ": " + (typeof detail === "string" ? detail : JSON.stringify(detail)).slice(0, 200) : " (응답: " + JSON.stringify(p || {}).slice(0, 200) + ")"));
      }
      setSt({ phase: "waiting", jobId: job.id });
      const done = await hfWaitJob(job.id);
      setSt({ phase: "done", url: done.result_url, jobId: job.id });
      if (onResult) onResult(job.id, done.result_url);
    } catch (e) {
      setSt({ phase: "error", msg: e && e.code ? hfErrMsg(e) : (e && e.message) || "알 수 없는 오류" });
    }
  };
  return (
    <div className="gen-row">
      <button className="primary small" disabled={disabled || st.phase === "starting" || st.phase === "waiting"} onClick={() => run()}>
        {st.phase === "starting" ? "요청 중…" : st.phase === "waiting" ? (kind === "video" ? "영상 생성 중… (3~5분)" : "이미지 생성 중… (1~3분)") : label}
      </button>
      {disabled && disabledMsg && <span className="gen-note">{disabledMsg}</span>}
      {st.phase === "unlim" && (
        <span className="gen-note">
          어떤 잔액으로 생성할까요?
          <button className="mini" onClick={() => run({ use_unlim: true })}>무료 생성 사용</button>
          <button className="mini" onClick={() => run({ use_unlim: false })}>크레딧 사용</button>
        </span>
      )}
      {st.phase === "done" && st.url && (
        <span className="gen-note ok">
          완료 ✓ <a href={st.url} target="_blank" rel="noreferrer">결과 열기</a>
          <CopyBtn text={st.url} label="URL 복사" small />
          {st.jobId && <span className="gen-id">job: {st.jobId.slice(0, 8)}…</span>}
          <button className="mini" onClick={() => run()}>다시 생성</button>
        </span>
      )}
      {st.phase === "error" && <span className="gen-note err">{st.msg} <button className="mini" onClick={() => run()}>재시도</button></span>}
    </div>
  );
}

/* 이미지 프롬프트 — GPT 이미지 2 기본. 나노바나나 비교 여부는 마지막(Export)에서 한 번만 묻는다 */
function ImagePrompt({ title, kr, en, gen }) {
  return (
    <>
      <PromptBox title={title + " · GPT 이미지 2 (기본)"} kr={kr} en={P.withGpt(en)} />
      {gen && (
        <GenRow kind="image" label={gen.label || "🎨 이미지 생성"} savedUrl={gen.savedUrl} onResult={gen.onResult}
          getParams={() => ({ model: "gpt_image_2", quality: "high", aspect_ratio: gen.ratio || "9:16", prompt: en, medias: refMedias(gen.refs) })} />
      )}
    </>
  );
}

function NavButtons({ S, set, onSave, onReset }) {
  return (
    <div className="nav-buttons">
      <button className="ghost" disabled={S.step === 0} onClick={() => set({ step: S.step - 1 })}>← 이전</button>
      <ArmedButton className="ghost" label="이 단계 초기화" armedLabel="⚠ 한 번 더 클릭하면 초기화" onRun={onReset} />
      <div className="spacer" />
      {S.step < STEPS.length - 1 && <button className="primary" onClick={() => { onSave(); set({ step: S.step + 1 }); }}>다음 →</button>}
    </div>
  );
}

/* ───────────────────────── STEP 화면들 ───────────────────────── */
function StepProject({ S, up, upG }) {
  return (
    <>
      <h2>프로젝트 설정</h2>
      <div className="field-row">
        <label>프로젝트명</label>
        <input className="text-field" value={S.project.name} onChange={(e) => up({ name: e.target.value })}
          placeholder="예: 쁘띠앤 오메가3 Instagram 광고" />
      </div>
      <Options title="광고 목적" list={C.PURPOSES} value={S.project.purpose} onChange={(v) => up({ purpose: v })} rec="제품 인지도" />
      <Options title="플랫폼 (복수 선택 — 선택한 플랫폼별로 맞춤 프롬프트가 생성됩니다)" list={C.PLATFORMS} value={S.project.platforms} onChange={(v) => up({ platforms: v })} multi rec="Instagram Reels" />
      <div className="opt-group">
        <div className="opt-title">영상 비율 — 플랫폼에 맞춰 자동 설정</div>
        <div className="opt-grid">
          {P.platformsOf(S).map((pf) => (
            <span key={pf} className="opt sel" style={{ cursor: "default" }}>{pf} → {P.ratioOfPlatform(pf)}</span>
          ))}
        </div>
        <div className="custom-note" style={{ marginTop: 6 }}>
          소스 촬영 비율: {P.sourceRatio(S)}{P.cropNote(S) ? " (비율이 다른 플랫폼은 중앙 크롭으로 납품 — 핵심 요소를 중앙에 배치하라는 지시가 프롬프트에 자동 포함됩니다)" : ""}
        </div>
      </div>
      <Options title="광고 길이" list={C.LENGTHS} value={S.project.length} onChange={(v) => up({ length: v })} rec="10초" />
      <Options title="광고 스타일" list={C.AD_STYLES} value={S.project.style} onChange={(v) => up({ style: v })} rec="Instagram Lifestyle" />
      <Options title="광고 컬러 무드" list={C.COLOR_MOODS} value={S.project.colorMood} onChange={(v) => up({ colorMood: v })} rec="Warm Beige" />
      <div className="section-divider">GLOBAL CAMERA &amp; LIGHT — 모든 Asset·Scene 프롬프트에 자동 적용</div>
      <Options title="LIGHT DIRECTION" list={C.LIGHT_DIRS} value={S.global.lightDir} onChange={(v) => upG({ lightDir: v })} rec="Camera Left → Right" custom={false} />
      <Options title="LIGHT TEMPERATURE" list={C.LIGHT_TEMPS} value={S.global.lightTemp} onChange={(v) => upG({ lightTemp: v })} custom={false} />
      <Options title="CAMERA (렌즈)" list={C.LENSES} value={S.global.lens} onChange={(v) => upG({ lens: v })} rec="35mm" custom={false} />
      <Options title="CAMERA HEIGHT" list={C.CAM_HEIGHTS} value={S.global.camHeight} onChange={(v) => upG({ camHeight: v })} custom={false} />
      <Options title="FRAME" list={C.FRAMES} value={S.global.frame} onChange={(v) => upG({ frame: v })} custom={false} />
    </>
  );
}

function StepModel({ S, set, up }) {
  const m = S.model;
  const prompt = P.buildModelPrompt(S);
  const gen = S.gen || {};
  return (
    <>
      <h2>AI 모델 빌더</h2>
      <Options title="성별" list={C.GENDERS} value={m.gender} onChange={(v) => up({ gender: v })} custom={false} />
      <Options title="인종적 외형" list={C.ETHNICITIES} value={m.ethnicity} onChange={(v) => up({ ethnicity: v })} rec="한국인 / 동아시아인" />
      <Options title="연령" list={C.AGES} value={m.age} onChange={(v) => up({ age: v })} rec="30대 초반" custom={false} />
      <Options title="얼굴형" list={C.FACES} value={m.face} onChange={(v) => up({ face: v })} rec="계란형" custom={false} />
      <Options title="피부톤" list={C.SKINS} value={m.skin} onChange={(v) => up({ skin: v })} rec="웜 아이보리" custom={false} />
      <Options title="눈" list={C.EYES} value={m.eyes} onChange={(v) => up({ eyes: v })} rec="자연스러운 아몬드형" custom={false} />
      <Options title="눈동자" list={C.IRISES} value={m.iris} onChange={(v) => up({ iris: v })} rec="다크 브라운" custom={false} />
      <Options title="헤어 길이" list={C.HAIR_LENGTHS} value={m.hairLen} onChange={(v) => up({ hairLen: v })} rec="중간 길이" custom={false} />
      <Options title="헤어스타일" list={C.HAIR_STYLES} value={m.hairStyle} onChange={(v) => up({ hairStyle: v })} rec="자연스러운 웨이브" custom={false} />
      <Options title="헤어 컬러" list={C.HAIR_COLORS} value={m.hairColor} onChange={(v) => up({ hairColor: v })} rec="소프트 블랙" custom={false} />
      <Options title="모델 이미지 타입" list={C.MODEL_VIEWS} value={m.views} onChange={(v) => up({ views: v })} multi custom={false} />
      <Toggle label="MODEL IDENTITY LOCK — 모델 얼굴 고정" value={m.lock} onChange={(v) => up({ lock: v })}
        desc="ON: 얼굴·나이·비율 고정 규칙과 Character Reference 사용 지시를 모든 모델 프롬프트에 자동 삽입합니다." />
      <div className="field-row">
        <label>캐릭터 시트 참조 ID (아래 생성 버튼 사용 시 자동 입력 — 채팅에서 만든 job id 붙여넣기도 가능)</label>
        <input className="text-field" value={gen.modelRef || ""} placeholder="전체 job ID 36자를 붙여넣으세요"
          onChange={(e) => set({ gen: { ...gen, modelRef: e.target.value.trim() } })} />
        {gen.modelRef && !isUuid(gen.modelRef) && <div className="gen-note err">ID가 불완전합니다 — 전체 36자(8-4-4-4-12)를 붙여넣어주세요</div>}
        {gen.modelRef && isUuid(gen.modelRef) && <div className="gen-note ok">형식 확인 ✓</div>}
      </div>
      <ImagePrompt title="MODEL PROMPT" kr={prompt.kr} en={prompt.en}
        gen={{ label: "🎨 캐릭터 시트 이미지 생성", refs: [], onResult: (jobId) => set({ gen: { ...S.gen, modelRef: jobId } }) }} />
    </>
  );
}

function StepProduct({ S, set, up }) {
  const p = S.product;
  const gen = S.gen || {};
  const fileRef = useRef(null);
  const prompt = P.buildProductPrompt(S);
  const onFile = (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, 480 / Math.max(img.width, img.height));
        const cv = document.createElement("canvas");
        cv.width = Math.round(img.width * scale); cv.height = Math.round(img.height * scale);
        cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
        up({ img: cv.toDataURL("image/jpeg", 0.85) });
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  };
  return (
    <>
      <h2>제품 빌더</h2>
      <div className="field-row">
        <label>제품명</label>
        <input className="text-field" value={p.name} onChange={(e) => up({ name: e.target.value })} placeholder="예: 쁘띠앤 오메가3" />
      </div>
      <div className="field-row">
        <label>소구점 / 핵심 특징 (연출·캡션에 자동 반영 — 화면 텍스트로는 넣지 않습니다)</label>
        <input className="text-field" value={p.usp || ""} onChange={(e) => up({ usp: e.target.value })} placeholder="예: 이카리딘 7%, 독일산 원료, 온 가족용 3개입" />
      </div>
      <div className="upload-zone" onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files[0]); }}>
        <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => { onFile(e.target.files[0]); e.target.value = ""; }} />
        {p.img
          ? <div className="upload-preview"><img src={p.img} alt="제품 참조 이미지" /><span>업로드됨 — 클릭해서 교체</span></div>
          : <div><strong>제품 사진 (미리보기·프롬프트 문구용)</strong><br /><span>여기 올린 사진은 브라우저에만 저장됩니다. 실제 생성에 쓰려면 아래 "힉스필드 제품 참조 ID"에 media_id를 넣어주세요 (Claude 채팅의 힉스필드 업로드 창으로 사진을 올리면 ID를 받을 수 있습니다)</span></div>}
      </div>
      {p.img && <button className="ghost" style={{ marginBottom: 14 }} onClick={() => up({ img: null })}>사진 제거</button>}
      <Options title="제품 촬영 스타일" list={C.PRODUCT_SHOTS} value={p.shot} onChange={(v) => up({ shot: v })} rec="Hero Product" custom={false} />
      <Options title="제품 각도" list={C.PRODUCT_ANGLES} value={p.angle} onChange={(v) => up({ angle: v })} rec="Front" custom={false} />
      <Options title="실제 크기감 (AI가 크기를 틀리게 그리는 것 방지)" list={C.PRODUCT_SCALES} value={p.scale || "한 손 소형"} onChange={(v) => up({ scale: v })} custom={false} />
      <Options title="제품 위치" list={C.PRODUCT_POSITIONS} value={p.position} onChange={(v) => up({ position: v })} rec="중앙" custom={false} />
      <Options title="제품 배경" list={C.PRODUCT_BGS} value={p.bg} onChange={(v) => up({ bg: v })} custom={false} />
      <Options title="연출 요소" list={C.PRODUCT_FX} value={p.effects} onChange={(v) => up({ effects: v })} multi custom={false} />
      <Toggle label="PRODUCT REFERENCE LOCK — 제품 디자인 고정" value={p.lock} onChange={(v) => up({ lock: v })}
        desc="ON: 패키지·로고·라벨·타이포그래피·비율 절대 변경 금지 규칙을 모든 제품 프롬프트에 자동 삽입합니다." />
      <div className="field-row">
        <label>⭐ 힉스필드 제품 참조 ID — 실제 생성에 쓰이는 값 (채팅의 힉스필드 업로드 창으로 사진을 올리고 받은 media_id를 붙여넣으세요. 이게 있어야 라벨이 원본 그대로 나옵니다)</label>
        <input className="text-field" value={gen.productRef || ""} placeholder="전체 media_id 36자를 붙여넣으세요"
          onChange={(e) => set({ gen: { ...gen, productRef: e.target.value.trim() } })} />
        {gen.productRef && !isUuid(gen.productRef) && <div className="gen-note err">ID가 불완전합니다 — 전체 36자(8-4-4-4-12)를 붙여넣어주세요</div>}
        {gen.productRef && isUuid(gen.productRef) && <div className="gen-note ok">형식 확인 ✓</div>}
      </div>
      <ImagePrompt title="PRODUCT PROMPT" kr={prompt.kr} en={prompt.en}
        gen={{ label: "🎨 제품 이미지 생성", refs: [gen.productRef] }} />
    </>
  );
}

function StepLocation({ S, up }) {
  const l = S.location;
  const places = P.placesOf(S);
  return (
    <>
      <h2>장소 빌더</h2>
      <div className="banner">EMPTY ENVIRONMENT ONLY — NO MODEL · NO PRODUCT · NO BRAND · NO TEXT</div>
      <Options title="장소 (복수 선택 — 장소별 프롬프트가 각각 생성되고, 씬마다 어느 장소인지 고를 수 있습니다)" list={C.PLACES} value={places} onChange={(v) => up({ places: v })} multi />
      <Options title="인테리어 스타일" list={C.INTERIORS} value={l.interior} onChange={(v) => up({ interior: v })} rec="Minimal Korean" custom={false} />
      <Options title="시간" list={C.TIMES} value={l.time} onChange={(v) => up({ time: v })} rec="Morning" custom={false} />
      <Options title="조명" list={C.ENV_LIGHTS} value={l.light} onChange={(v) => up({ light: v })} rec="Soft Window Light" custom={false} />
      <Options title="렌즈" list={C.LOC_LENSES} value={l.lens} onChange={(v) => up({ lens: v })} rec="35mm" custom={false} />
      <Options title="카메라 높이" list={C.LOC_CAM_HEIGHTS} value={l.camHeight} onChange={(v) => up({ camHeight: v })} custom={false} />
      {places.map((pl) => {
        const pr = P.buildLocationPrompt(S, pl);
        return <ImagePrompt key={pl} title={"LOCATION PROMPT — " + C.disp(C.PLACES, pl)} kr={pr.kr} en={pr.en} />;
      })}
    </>
  );
}

function SceneCard({ scene, S, set, idx }) {
  const [showImg, setShowImg] = useState(false);
  const [showVid, setShowVid] = useState(false);
  const upScene = (patch) => set({ scenes: S.scenes.map((sc) => sc.id === scene.id ? { ...sc, ...patch } : sc) });
  const imgP = showImg ? P.buildSceneImagePrompt(scene, S) : null;
  const vidP = showVid ? P.buildSceneVideoPrompt(scene, S) : null;
  return (
    <div className="scene-card">
      <div className="scene-head">
        <span className="scene-num">SCENE {String(idx + 1).padStart(2, "0")}</span>
        <input className="scene-name" value={scene.name} placeholder="씬 이름 (예: 습기 고민 훅, 욕실 거울 김서림)" onChange={(e) => upScene({ name: e.target.value })} />
        <button className="mini danger" onClick={() => {
          set({
            scenes: S.scenes.filter((sc) => sc.id !== scene.id),
            composer: { ...S.composer, timeline: S.composer.timeline.filter((id) => id !== scene.id) }
          });
        }}>삭제</button>
        <button className="mini" onClick={() => {
          const copy = { ...scene, id: S.sceneSeq, name: scene.name + " (복제)" };
          set({ scenes: [...S.scenes, copy], sceneSeq: S.sceneSeq + 1 });
        }}>복제</button>
      </div>
      <Options title="Scene 역할" list={C.SCENE_ROLES} value={scene.role} onChange={(v) => upScene({ role: v })} custom={false} cols={4} />
      <Options title="사용 Asset" list={C.SCENE_ASSETS} value={scene.assets} onChange={(v) => upScene({ assets: v })} multi custom={false} cols={4} />
      {scene.assets.includes("MODEL") && <>
        <Options title="소개 스타일 (말하는 톤)" list={C.PRESENT_STYLES} value={scene.presentStyle || "친구에게 추천하듯"} onChange={(v) => upScene({ presentStyle: v })} custom={false} />
        <Options title="시선 처리" list={C.PRESENT_GAZES} value={scene.gaze || "카메라 정면 응시"} onChange={(v) => upScene({ gaze: v })} custom={false} />
        <Options title="소개 제스처" list={C.PRESENT_GESTURES} value={scene.gesture || "제품 들어 보여주기"} onChange={(v) => upScene({ gesture: v })} custom={false} />
      </>}
      {scene.assets.includes("LOCATION") && P.placesOf(S).length > 1 && (
        <Options title="이 씬의 장소" list={P.placesOf(S).map((pl) => ({ kr: pl, en: pl, disp: C.disp(C.PLACES, pl) }))}
          value={P.scenePlace(scene, S)} onChange={(v) => upScene({ place: v })} custom={false} />
      )}
      {scene.assets.includes("PRODUCT") && <Options title="제품 동작" list={C.PRODUCT_MOTIONS} value={scene.productMotion} onChange={(v) => upScene({ productMotion: v })} custom={false} cols={4} />}
      <Options title="카메라 움직임" list={C.CAMERA_MOTIONS} value={scene.cameraMotion} onChange={(v) => upScene({ cameraMotion: v })} custom={false} cols={4} />
      <Options title="Scene 길이" list={C.SCENE_DURATIONS} value={scene.duration + "초"} onChange={(v) => upScene({ duration: parseFloat(v) || 2 })} cols={4} />
      <div className="scene-actions">
        <button className="primary small" onClick={() => setShowImg(!showImg)}>{showImg ? "IMAGE PROMPT 닫기" : "IMAGE PROMPT 생성"}</button>
        <button className="primary small" onClick={() => setShowVid(!showVid)}>{showVid ? "VIDEO PROMPT 닫기" : "VIDEO PROMPT 생성"}</button>
      </div>
      {(() => {
        const lib = S.library || [];
        const current = lib.find((it) => it.id === scene.imgJobId);
        const available = lib.filter((it) => !S.scenes.some((sc) => sc.id !== scene.id && sc.imgJobId === it.id));
        if (!lib.length && !scene.imgJobId) return null;
        return (
          <div className="opt-group" style={{ marginTop: 4 }}>
            <div className="opt-title">이 씬의 이미지 선택 {current ? "— " + current.name + " 연결됨 ✓" : scene.imgJobId && isUuid(scene.imgJobId) ? "— 직접 입력 ID 연결됨 ✓" : ""}</div>
            <div className="opt-grid">
              {available.map((it) => (
                <button key={it.id} className={"opt" + (scene.imgJobId === it.id ? " sel" : "")}
                  onClick={() => upScene({ imgJobId: scene.imgJobId === it.id ? "" : it.id, imgUrl: "" })}>
                  {it.name}
                </button>
              ))}
              {scene.imgJobId && <button className="mini" onClick={() => upScene({ imgJobId: "", imgUrl: "" })}>선택 해제</button>}
            </div>
            {scene.imgJobId && !isUuid(scene.imgJobId) && <div className="gen-note err">연결된 ID가 불완전합니다</div>}
          </div>
        );
      })()}
      {imgP && <ImagePrompt title={"SCENE " + (idx + 1) + " IMAGE PROMPT"} kr={imgP.kr} en={imgP.en}
        gen={{
          label: "🎨 이미지 생성",
          refs: [scene.assets.includes("MODEL") ? (S.gen || {}).modelRef : "", scene.assets.includes("PRODUCT") ? (S.gen || {}).productRef : ""],
          savedUrl: scene.imgUrl,
          onResult: (jobId, url) => upScene({ imgJobId: jobId, imgUrl: url })
        }} />}
      {vidP && <>
        <PromptBox title={"SCENE " + (idx + 1) + " VIDEO PROMPT"} kr={vidP.kr} en={vidP.en} />
        <GenRow kind="video" label="🎬 영상 생성 (씬 이미지 → Seedance)"
          disabled={!isUuid(scene.imgJobId)} disabledMsg={scene.imgJobId ? (isUuid(scene.imgJobId) ? "" : "연결된 ID가 불완전합니다") : "먼저 위에서 이미지를 생성하거나 기존 job ID를 연결하세요"}
          savedUrl={scene.vidUrl}
          onResult={(jobId, url) => upScene({ vidJobId: jobId, vidUrl: url })}
          getParams={() => ({
            model: "seedance_2_0", mode: "std", resolution: "1080p", aspect_ratio: "9:16",
            duration: Math.max(4, Math.round(parseFloat(scene.duration) || 4)), generate_audio: false,
            medias: [{ value: scene.imgJobId, role: "start_image" }],
            prompt: P.buildSceneVideoPrompt(scene, S).en
          })} />
      </>}
    </div>
  );
}

const UUID_ANY_RE = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;
// 프롬프트를 분석해 어떤 장면인지 한글로 요약한다
function promptGist(p) {
  const t = (p || "").replace(/\s+/g, " ");
  if (/character (reference )?sheet/i.test(t)) return "모델 캐릭터 시트";
  if (/single .*canvas|scenes arranged|panels? arranged/i.test(t)) {
    const n = t.match(/(\d+)\s*(supplied|distinct|reference)?\s*scenes/i);
    return "스토리보드" + (n ? ` (${n[1]}씬 합본)` : "");
  }
  if (/BATHROOM MIRROR.*DIRECTIONAL|DIRECTIONAL CLEARING/i.test(t)) return "욕실 거울 씬 — 제습기 쪽부터 걷힘";
  if (/BATHROOM MIRROR|bathroom/i.test(t)) return "욕실 거울 씬";
  if (/HERO shot|closing HERO|hero/i.test(t)) return "히어로 마무리 씬";
  if (/humidity|damp laundry|troubled|fogged window/i.test(t)) return "습기 고민 훅 씬";
  if (/storyboard/i.test(t)) return "광고 씬 이미지";
  if (/mid-presentation|presenting|holding .*(up|toward).*(camera|lens)/i.test(t)) return "제품 소개 씬";
  if (/product (reference|photo|shot)|키비주얼|팩샷/i.test(t)) return "제품 컷";
  const kr = t.match(/[가-힣][^.]{5,50}/);
  if (kr) return kr[0].slice(0, 45);
  return "기타 이미지 — " + t.slice(0, 40) + "…";
}
function fmtDate(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
// 프로젝트 제품명 → 영문 프롬프트에서 그 제품을 찾는 힌트
const PRODUCT_HINTS = [
  [/제습/, /dehumidif/i],
  [/모기|벅스|기피/, /spray|repellent|bugsnet|icaridin/i],
  [/오메가/, /omega|softgel|capsule/i],
  [/효소/, /효소|enzyme|sachet|stick-?pack/i]
];
function isRelatedToProduct(promptText, productName) {
  const hint = PRODUCT_HINTS.find(([kr]) => kr.test(productName || ""));
  if (!hint) return true; // 제품을 특정할 수 없으면 필터하지 않음
  return hint[1].test(promptText || "") || (productName && (promptText || "").includes(productName));
}
function LibraryManager({ S, set }) {
  const [name, setName] = useState("");
  const [jid, setJid] = useState("");
  const [pick, setPick] = useState({ open: false, loading: false, items: [], err: "" });
  const [showAll, setShowAll] = useState(false);
  const lib = S.library || [];
  const usedBy = (id) => S.scenes.find((sc) => sc.imgJobId === id);
  const add = () => {
    if (!isUuid(jid)) return;
    if (lib.some((it) => it.id === jid.trim())) { setName(""); setJid(""); return; }
    set({ library: [...lib, { id: jid.trim(), name: name.trim() || ("이미지 " + (lib.length + 1)) }] });
    setName(""); setJid("");
  };
  const openPick = async () => {
    if (pick.open) { setPick({ ...pick, open: false }); return; }
    if (!hfReady()) { setPick({ open: true, loading: false, items: [], err: "힉스필드 연결이 없어 목록을 불러올 수 없습니다 — ID를 직접 붙여넣어주세요." }); return; }
    setPick({ open: true, loading: true, items: [], err: "" });
    try {
      const p = await hfCall("show_generations", { type: "image", size: 24 });
      const items = ((p && p.items) || [])
        .filter((it) => it.status === "completed" && it.type === "image")
        .map((it) => {
          const pr = (it.params && it.params.prompt) || "";
          const gist = promptGist(pr);
          return {
            id: it.id,
            url: it.results && it.results.rawUrl,
            gist,
            isScene: /씬/.test(gist),
            related: isRelatedToProduct(pr, S.product.name),
            model: it.model,
            at: fmtDate(it.createdAt)
          };
        });
      setPick({ open: true, loading: false, items, err: items.length ? "" : "완료된 이미지 생성 기록이 없습니다." });
    } catch (e) {
      setPick({ open: true, loading: false, items: [], err: hfErrMsg(e) });
    }
  };
  return (
    <div className="lib-box">
      <div className="opt-title">씬 이미지 라이브러리 — 만들어둔 이미지 job ID를 등록해두면 씬 카드에서 클릭으로 선택할 수 있습니다 (이미 배정된 이미지는 다른 씬 목록에서 숨겨집니다)</div>
      <div className="custom-row">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="이름 (예: 씬2 제품 소개)" style={{ width: 170 }} />
        <input value={jid} onFocus={() => { if (!pick.open && !jid) openPick(); }} onChange={(e) => {
          const v = e.target.value;
          const m = v.match(UUID_ANY_RE); // 붙여넣은 문장 속에서 UUID만 자동 추출
          setJid(m ? m[0] : v.trim());
        }} placeholder="클릭하면 내 이미지 목록이 열립니다" style={{ width: 280, fontFamily: "ui-monospace, monospace", fontSize: 11 }} />
        <button onClick={openPick}>{pick.open ? "목록 닫기" : "📋 목록에서 선택"}</button>
        <button onClick={add} disabled={!isUuid(jid)}>{isUuid(jid) ? "등록" : "ID 불완전"}</button>
      </div>
      {pick.open && (
        <div className="lib-pick">
          {pick.loading && <div className="gen-note">내 이미지 생성 기록 불러오는 중…</div>}
          {pick.err && <div className="gen-note err">{pick.err}</div>}
          {!pick.loading && !pick.err && (
            <div className="lib-pick-filter">
              <span className="gen-note">{showAll ? "전체 이미지 표시 중" : (S.product.name ? `"${S.product.name}" 관련 씬만 표시 중` : "씬 이미지만 표시 중")}</span>
              <button className="mini" onClick={() => setShowAll(!showAll)}>{showAll ? "관련 씬만 보기" : "전체 보기"}</button>
            </div>
          )}
          {!pick.loading && pick.items.filter((it) => showAll || (it.isScene && it.related)).map((it) => {
            const registered = lib.some((x) => x.id === it.id);
            const selected = jid === it.id;
            return (
              <div key={it.id} className={"lib-pick-row" + (selected ? " sel" : "") + (registered ? " reg" : "")}>
                <span className="lib-pick-gist">{it.gist || "(프롬프트 없음)"}</span>
                {it.at && <span className="lib-pick-date">{it.at}</span>}
                <span className="lib-id">{it.id.slice(0, 8)}…</span>
                {it.url && <a className="mini btn-link" href={it.url} target="_blank" rel="noreferrer">보기</a>}
                {registered
                  ? <span className="lib-pick-regmark">등록됨 ✓</span>
                  : <button className="mini" onClick={() => { setJid(it.id); }}>{selected ? "✓ 선택됨" : "선택"}</button>}
              </div>
            );
          })}
          {!pick.loading && !pick.err && pick.items.filter((it) => showAll || (it.isScene && it.related)).length === 0 && <div className="gen-note">관련 씬이 없습니다 — [전체 보기]로 전환해보세요.</div>}
          {!pick.loading && !pick.err && <div className="gen-note">[선택] → 이름 입력 → [등록] 순서로 추가하세요. 어떤 이미지인지 헷갈리면 [보기]로 새 탭에서 확인.</div>}
        </div>
      )}
      {lib.length > 0 && (
        <div className="lib-list">
          {lib.map((it) => {
            const u = usedBy(it.id);
            return (
              <span key={it.id} className={"lib-item" + (u ? " used" : "")}>
                {it.name}
                <span className="lib-id">{it.id.slice(0, 8)}…</span>
                {u && <span className="lib-used">→ {u.name}</span>}
                <button className="mini danger" title="라이브러리에서 삭제" onClick={() => set({ library: lib.filter((x) => x.id !== it.id) })}>×</button>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// 추천 6씬 구성 (합계 15초) — 제습기 프로젝트용. 라이브러리에 있는 이미지는 자동 연결.
const PRESET_6 = [
  { name: "습기 고민 훅", role: "Hook", assets: ["MODEL"], duration: 2.5, cameraMotion: "Slow Push-In", place: "프리미엄 주방", imgJobId: "d55bd41a-25dd-40cb-926a-438408d33093" },
  { name: "제품 소개", role: "Product Reveal", assets: ["MODEL", "PRODUCT"], duration: 2.5, cameraMotion: "Slow Push-In", place: "프리미엄 주방", imgJobId: "0c54d120-7dba-4ce8-b579-77263cca8460" },
  { name: "주방 사용 컷", role: "Usage", assets: ["PRODUCT", "LOCATION"], duration: 2, cameraMotion: "Macro Tracking", place: "프리미엄 주방", imgJobId: "a8174c3a-4909-4991-b70c-e9e8cd7493ec" },
  { name: "욕실 거울 김서림", role: "Benefit", assets: ["MODEL", "PRODUCT", "LOCATION"], duration: 3, cameraMotion: "Pan Right", place: "럭셔리 욕실", imgJobId: "8d433c56-5a7f-41f1-a9aa-37fa994b7222" },
  { name: "뽀송한 일상", role: "Emotional Moment", assets: ["MODEL"], duration: 2.5, cameraMotion: "Slow Pull-Out", place: "프리미엄 주방", imgJobId: "00d304aa-b597-4bef-9a7c-731554350d4f" },
  { name: "히어로 마무리", role: "Hero Shot", assets: ["MODEL", "PRODUCT"], duration: 2.5, cameraMotion: "Slow Pull-Out", place: "프리미엄 주방", imgJobId: "8d80a06e-4718-466a-8a41-a557b94484f4" }
];
// 역할별 권장 가중치(초) — 효과를 보여주는 Benefit 씬에 가장 큰 비중
const ROLE_W = { "Hook": 2.5, "Intro": 2, "Lifestyle": 2.5, "Model Introduction": 2.5, "Product Reveal": 2.5, "Product Detail": 2.5, "Ingredient": 2, "Benefit": 3, "Usage": 2, "Emotional Moment": 2.5, "Hero Shot": 2.5, "CTA": 2, "Brand Ending": 2 };
// 15초 안에서 역할 비중대로 씬 길이를 배분 (0.5초 단위, 씬당 1.5~5초)
function recommendDurations(scenes) {
  if (!scenes.length) return [];
  const target = Math.min(15, scenes.length * 5);
  const w = scenes.map((sc) => ROLE_W[sc.role] || 2.5);
  const sum = w.reduce((a, b) => a + b, 0);
  const durs = w.map((x) => Math.max(1.5, Math.min(5, Math.round(((x / sum) * target) * 2) / 2)));
  let guard = 30;
  while (guard--) {
    const total = durs.reduce((a, b) => a + b, 0);
    const diff = Math.round((target - total) * 2) / 2;
    if (Math.abs(diff) < 0.5) break;
    if (diff > 0) { const i = durs.findIndex((d) => d < 5); if (i < 0) break; durs[i] += 0.5; }
    else { const i = durs.findIndex((d) => d > 1.5); if (i < 0) break; durs[i] -= 0.5; }
  }
  return durs;
}
function analyzeComposition(S) {
  // 실제 영상에 들어가는 순서(6단계 타임라인) 기준으로 판정
  const rows0 = P.timelineRows(S);
  const scenes = rows0.length ? rows0.map((r) => r.scene) : S.scenes;
  const total = scenes.reduce((a, sc) => a + (parseFloat(sc.duration) || 0), 0);
  const rows = [];
  rows.push([total <= 15.01, `총 길이 ${total.toFixed(1)}초 / 최대 15초` + (total > 15.01 ? " — 초과분은 영상에서 잘립니다" : " ✓")]);
  rows.push([total >= 9 || scenes.length === 0, total < 9 ? `총 ${total.toFixed(1)}초 — 9초 미만은 광고 정보를 담기 빠듯합니다` : "숏폼 권장 범위(9~15초) ✓"]);
  rows.push([scenes.length >= 3 && scenes.length <= 7, `씬 ${scenes.length}개` + (scenes.length > 7 ? " — 너무 많아 씬당 시간이 부족합니다" : scenes.length < 3 ? " — 훅·제품·마무리 최소 3씬 권장" : " ✓")]);
  scenes.forEach((sc, i) => {
    const d = parseFloat(sc.duration) || 0;
    if (d < 1.5) rows.push([false, `씬${i + 1} ${sc.name || ""} ${d}초 — 1.5초 미만은 화면이 읽히기 전에 지나갑니다`]);
    if (d > 5) rows.push([false, `씬${i + 1} ${sc.name || ""} ${d}초 — 5초 초과는 숏폼에서 지루해집니다`]);
  });
  if (scenes.length) {
    rows.push([scenes[0].role === "Hook", scenes[0].role === "Hook" ? "첫 씬 Hook ✓" : "첫 씬이 Hook이 아닙니다 — 첫 1초 이탈률에 영향"]);
    const last = scenes[scenes.length - 1].role;
    rows.push([["Hero Shot", "CTA", "Brand Ending"].includes(last), ["Hero Shot", "CTA", "Brand Ending"].includes(last) ? "마지막 씬 마무리형 ✓" : "마지막 씬은 Hero Shot/CTA/Brand Ending 권장"]);
  }
  return { rows, total };
}
function StepScenes({ S, set }) {
  const [check, setCheck] = useState(null);
  const rec = recommendDurations(S.scenes);
  const recTotal = rec.reduce((a, b) => a + b, 0);
  const recDiffers = S.scenes.some((sc, i) => Math.abs((parseFloat(sc.duration) || 0) - rec[i]) >= 0.25);
  const applyRec = () => {
    set({ scenes: S.scenes.map((sc, i) => ({ ...sc, duration: rec[i] })) });
    setCheck(null);
    setTimeout(() => setCheck("done"), 0);
  };
  const addScene = () => {
    const id = S.sceneSeq;
    const sc = {
      id, name: "Scene " + String(id).padStart(2, "0"), role: "Model Introduction",
      assets: ["MODEL", "PRODUCT"], presentStyle: "친구에게 추천하듯", gaze: "카메라 정면 응시", gesture: "제품 들어 보여주기", productMotion: "Static",
      cameraMotion: "Slow Push-In", duration: 2
    };
    set({ scenes: [...S.scenes, sc], sceneSeq: id + 1, composer: { ...S.composer, timeline: [...S.composer.timeline, id] } });
  };
  const applyPreset6 = () => {
    const scenes = PRESET_6.map((p, i) => ({
      id: i + 1, name: p.name, role: p.role, assets: p.assets,
      presentStyle: "친구에게 추천하듯", gaze: "카메라 정면 응시", gesture: "제품 들어 보여주기", productMotion: "Static",
      cameraMotion: p.cameraMotion, duration: p.duration, place: p.place,
      imgJobId: p.imgJobId && (S.library || []).some((x) => x.id === p.imgJobId) ? p.imgJobId : (p.imgJobId || "")
    }));
    set({
      scenes, sceneSeq: 7,
      composer: { ...S.composer, timeline: scenes.map((sc) => sc.id) },
      post: { ...mergePost(S.post), lines: {} } // 씬이 바뀌었으니 대사도 초기화
    });
  };
  return (
    <>
      <h2>개별 Scene 빌더</h2>
      <LibraryManager S={S} set={set} />
      <div className="gen-row" style={{ margin: "10px 0" }}>
        <button className="primary" onClick={addScene}>+ Scene 추가</button>
        <ArmedButton className="primary small" label="🎬 추천 6씬 구성 불러오기 (15초)"
          armedLabel={S.scenes.length ? "⚠ 현재 씬 " + S.scenes.length + "개가 교체됩니다 — 한 번 더 클릭" : "한 번 더 클릭하면 6씬이 만들어집니다"}
          onRun={applyPreset6} />
        <button className="primary small" disabled={!S.scenes.length} onClick={() => setCheck(analyzeComposition(S))}>⏱ 구성 길이 확인</button>
      </div>
      {check && check !== "done" && (
        <div className="lib-box" style={{ marginBottom: 10 }}>
          <div className="opt-title">구성 진단</div>
          {check.rows.map(([ok, label], i) => (
            <div key={i} className={"gen-note" + (ok ? " ok" : " err")} style={{ display: "block", margin: "3px 0" }}>{ok ? "☑" : "⚠"} {label}</div>
          ))}
          {recDiffers && (
            <div className="gen-row" style={{ marginTop: 8 }}>
              <button className="primary small" onClick={applyRec}>✨ 추천 길이 바로 적용 (합계 {recTotal.toFixed(1)}초)</button>
              <span className="gen-note">{S.scenes.map((sc, i) => `${sc.name || "씬" + (i + 1)} ${rec[i]}초`).join(" · ")}</span>
            </div>
          )}
          {!recDiffers && <div className="gen-note ok" style={{ display: "block", marginTop: 6 }}>현재 길이가 추천 배분과 일치합니다 ✓</div>}
        </div>
      )}
      {check === "done" && (
        <div className="gen-note ok" style={{ display: "block", margin: "0 0 10px" }}>추천 길이 적용 완료 ✓ — 각 씬 카드의 Scene 길이가 갱신되었습니다. [⏱ 구성 길이 확인]으로 다시 진단할 수 있습니다.</div>
      )}
      <div style={{ height: 4 }} />
      {S.scenes.length === 0 && <div className="empty">아직 Scene이 없습니다. "Scene 추가"로 시작하세요.</div>}
      {S.scenes.map((sc, i) => <SceneCard key={sc.id} scene={sc} S={S} set={set} idx={i} />)}
    </>
  );
}

const ROLE_PRIORITY = {
  "AI 추천 광고 구조": ["Hook", "Intro", "Lifestyle", "Model Introduction", "Product Reveal", "Product Detail", "Ingredient", "Benefit", "Usage", "Emotional Moment", "Hero Shot", "CTA", "Brand Ending"],
  "제품 중심": ["Product Reveal", "Product Detail", "Ingredient", "Hook", "Benefit", "Usage", "Hero Shot", "Model Introduction", "Lifestyle", "Intro", "Emotional Moment", "CTA", "Brand Ending"],
  "모델 중심": ["Hook", "Model Introduction", "Lifestyle", "Usage", "Emotional Moment", "Product Reveal", "Benefit", "Product Detail", "Ingredient", "Hero Shot", "CTA", "Brand Ending"],
  "Story 중심": ["Hook", "Intro", "Lifestyle", "Emotional Moment", "Model Introduction", "Usage", "Benefit", "Product Reveal", "Product Detail", "Ingredient", "Hero Shot", "CTA", "Brand Ending"],
  "TikTok Fast Cut": ["Hook", "Product Reveal", "Benefit", "Usage", "Hero Shot", "CTA", "Intro", "Lifestyle", "Model Introduction", "Product Detail", "Ingredient", "Emotional Moment", "Brand Ending"],
  "Premium Commercial": ["Intro", "Lifestyle", "Model Introduction", "Product Reveal", "Product Detail", "Benefit", "Emotional Moment", "Hero Shot", "Brand Ending", "Hook", "Ingredient", "Usage", "CTA"]
};

function StepStoryboard({ S, set }) {
  const rows = P.timelineRows(S);
  const gen = S.gen || {};
  const move = (i, dir) => {
    const t = [...S.composer.timeline];
    const j = i + dir;
    if (j < 0 || j >= t.length) return;
    [t[i], t[j]] = [t[j], t[i]];
    set({ composer: { ...S.composer, timeline: t } });
  };
  if (rows.length < 2) {
    return <>
      <h2>스토리보드</h2>
      <div className="empty">개별 Scene 단계에서 씬을 2개 이상 만들면, 모든 씬을 한 캔버스에 배치한 스토리보드를 생성할 수 있습니다.</div>
      <div className="gen-note" style={{ marginTop: 10 }}>스토리보드는 다음 단계(Scene Composer)에서 "자연스럽게 이어지는 하나의 영상"을 만드는 기준이 됩니다.</div>
    </>;
  }
  const sb = P.buildStoryboardPrompt(S);
  return <>
    <h2>스토리보드</h2>
    <div className="banner">모든 씬을 한 캔버스에 배치한 스토리보드를 먼저 만들고, 다음 단계에서 이 스토리보드를 기준으로 하나의 영상을 제작합니다. 동일 제품·인물·의상·배경 아이덴티티 유지 · 분할선 없이 이어지는 하나의 키비주얼 · 텍스트 생성 금지.</div>
    <div className="opt-title">씬 순서 (스토리보드 패널 순서 = 영상 순서)</div>
    <div className="timeline">
      {rows.map((r, i) => (
        <div className="tl-scene" key={r.scene.id}>
          <span className="tl-time">{P.fmtT(r.start)}–{P.fmtT(r.end)}</span>
          <span className="tl-name">{String(i + 1).padStart(2, "0")} {r.scene.name}</span>
          <span className="tl-role">{C.disp(C.SCENE_ROLES, r.scene.role)}</span>
          <span className="tl-move">
            <button className="mini" disabled={i === 0} onClick={() => move(i, -1)}>▲</button>
            <button className="mini" disabled={i === rows.length - 1} onClick={() => move(i, 1)}>▼</button>
          </span>
        </div>
      ))}
    </div>
    {sb.refs.length > 0
      ? <div className="gen-note ok">씬 이미지 {sb.refs.length}장이 모두 연결되어 있어 — 스토리보드는 씬 이미지들을 순서대로 참조해 충실히 재현합니다 (권장 방식 ✓)</div>
      : <div className="gen-note">일부 씬에 이미지가 연결되지 않아 씬 설정 텍스트만으로 그립니다 — 5단계에서 씬마다 이미지를 연결하면 스토리보드 품질이 훨씬 좋아집니다.</div>}
    <PromptBox title={"스토리보드 이미지 프롬프트 (씬 " + sb.count + "개 → 한 캔버스)"} kr={sb.kr} en={P.withGpt(sb.en)} />
    <GenRow kind="image" label="🎨 스토리보드 이미지 생성"
      savedUrl={gen.storyUrl}
      onResult={(jobId, url) => set({ gen: { ...S.gen, storyJobId: jobId, storyUrl: url } })}
      getParams={() => ({ model: "gpt_image_2", quality: "high", aspect_ratio: "9:16", prompt: sb.en,
        medias: sb.refs.length ? refMedias(sb.refs) : refMedias([gen.modelRef, gen.productRef]) })} />
    <div className="field-row" style={{ marginTop: 14 }}>
      <label>또는 기존 스토리보드 job ID 연결 (채팅에서 이미 만든 스토리보드를 그대로 쓸 때)</label>
      <input className="text-field" value={gen.storyJobId || ""} placeholder="전체 job ID 36자를 붙여넣으세요"
        onChange={(e) => set({ gen: { ...S.gen, storyJobId: e.target.value.trim() } })} />
      {gen.storyJobId && !isUuid(gen.storyJobId) && <div className="gen-note err">ID가 불완전합니다 — 전체 36자(8-4-4-4-12)를 붙여넣어주세요</div>}
    </div>
    {gen.storyJobId && <div className="gen-note ok">스토리보드 연결됨 ✓ — 다음 단계(Scene Composer)에서 멀티샷 영상을 생성하세요.</div>}
  </>;
}

function StepComposer({ S, set }) {
  const c = S.composer;
  const upC = (patch) => set({ composer: { ...c, ...patch } });
  const rows = P.timelineRows(S);
  const inTimeline = new Set(c.timeline);
  const [output, setOutput] = useState(null);

  const move = (i, dir) => {
    const t = [...c.timeline];
    const j = i + dir;
    if (j < 0 || j >= t.length) return;
    [t[i], t[j]] = [t[j], t[i]];
    upC({ timeline: t });
  };
  const applyOrder = (mode) => {
    if (mode === "현재 순서") { upC({ orderMode: mode }); return; }
    const pri = ROLE_PRIORITY[mode] || [];
    const sorted = [...c.timeline].sort((a, b) => {
      const ra = S.scenes.find((s) => s.id === a)?.role, rb = S.scenes.find((s) => s.id === b)?.role;
      return (pri.indexOf(ra) === -1 ? 99 : pri.indexOf(ra)) - (pri.indexOf(rb) === -1 ? 99 : pri.indexOf(rb));
    });
    upC({ orderMode: mode, timeline: sorted });
  };

  return (
    <>
      <h2>🎬 Scene Composer</h2>
      <div className="opt-title">Timeline에 포함할 Scene 선택</div>
      <div className="opt-grid cols-3" style={{ marginBottom: 16 }}>
        {S.scenes.map((sc) => (
          <button key={sc.id} className={"opt" + (inTimeline.has(sc.id) ? " sel" : "")}
            onClick={() => upC({ timeline: inTimeline.has(sc.id) ? c.timeline.filter((id) => id !== sc.id) : [...c.timeline, sc.id] })}>
            {sc.name} <span className="opt-sub">{C.disp(C.SCENE_ROLES, sc.role)}</span>
          </button>
        ))}
        {S.scenes.length === 0 && <div className="empty">개별 Scene 단계에서 Scene을 먼저 만들어주세요.</div>}
      </div>

      <Options title="SCENE ORDER MODE" list={C.ORDER_MODES} value={c.orderMode} onChange={applyOrder} custom={false} cols={4} />

      <div className="opt-title">Composer Timeline (순서 변경 · 전환 · 브릿지)</div>
      <div className="timeline">
        {rows.map((r, i) => (
          <React.Fragment key={r.scene.id}>
            <div className="tl-scene">
              <span className="tl-time">{P.fmtT(r.start)}–{P.fmtT(r.end)}</span>
              <span className="tl-name">{String(i + 1).padStart(2, "0")} {r.scene.name}</span>
              <span className="tl-role">{C.disp(C.SCENE_ROLES, r.scene.role)}</span>
              <span className="tl-move">
                <button className="mini" disabled={i === 0} onClick={() => move(i, -1)}>▲</button>
                <button className="mini" disabled={i === rows.length - 1} onClick={() => move(i, 1)}>▼</button>
              </span>
            </div>
            {i < rows.length - 1 && (
              <div className="tl-gap">
                <select value={c.transitions[i] || ((c.flow || "원테이크 연결") === "원테이크 연결" ? "Motion Match" : "AI Auto")} onChange={(e) => upC({ transitions: { ...c.transitions, [i]: e.target.value } })}>
                  {C.TRANSITIONS.map((t) => <option key={t.kr} value={t.kr}>{t.disp || t.kr}</option>)}
                </select>
                {!c.transitions[i] && <span className="tl-note">{(c.flow || "원테이크 연결") === "원테이크 연결" ? "원테이크 연결감 기본값 — 움직임을 이어받는 모션 매치" : "이전 씬 끝/다음 씬 시작을 비교해 가장 튀지 않는 전환을 선택"}</span>}
                {c.bridges[i]
                  ? <span className="bridge-tag">
                      BRIDGE:
                      <select value={c.bridges[i].type} onChange={(e) => upC({ bridges: { ...c.bridges, [i]: { ...c.bridges[i], type: e.target.value } } })}>
                        {C.BRIDGE_TYPES.map((b) => <option key={b.kr} value={b.kr}>{b.disp || b.kr}</option>)}
                      </select>
                      <select value={c.bridges[i].dur} onChange={(e) => upC({ bridges: { ...c.bridges, [i]: { ...c.bridges[i], dur: e.target.value } } })}>
                        {C.BRIDGE_DURS.map((b) => <option key={b.kr} value={b.en}>{b.kr}</option>)}
                      </select>
                      <button className="mini danger" onClick={() => { const b = { ...c.bridges }; delete b[i]; upC({ bridges: b }); }}>제거</button>
                    </span>
                  : <button className="mini" onClick={() => upC({ bridges: { ...c.bridges, [i]: { type: "Product Macro", dur: "0.5" } } })}>+ BRIDGE</button>}
              </div>
            )}
          </React.Fragment>
        ))}
        {rows.length === 0 && <div className="empty">위에서 Scene을 Timeline에 추가하세요.</div>}
        {rows.length > 0 && <div className="tl-total">총 길이: {rows[rows.length - 1].end.toFixed(1)}초 (목표: {S.project.length})</div>}
      </div>

      <div className="section-divider">씬 연결 방식</div>
      <Options title="촬영 연결감 — 씬과 씬이 어떻게 이어질지" list={C.FLOW_MODES} value={c.flow || "원테이크 연결"} onChange={(v) => upC({ flow: v })} custom={false} cols={2} />
      {(c.flow || "원테이크 연결") === "원테이크 연결" && <div className="gen-note" style={{ marginBottom: 10 }}>멀티샷 영상 프롬프트에 "한 번에 촬영한 것처럼 카메라·동작이 씬 경계를 넘어 흐르듯 이어지게" 지시가 자동으로 들어갑니다. 씬 사이 전환 기본값도 모션 매치로 바뀝니다. 씬 장소가 2곳 이상이면 공간 이동 규칙(모델이 직접 걸어서 이동 + 문틀·어깨가 화면을 잠깐 가리는 순간에 공간 전환)도 자동으로 추가됩니다.</div>}

      <div className="section-divider">FINAL AD STYLE</div>
      <Options title="편집 스타일" list={C.EDIT_STYLES} value={c.adStyle} onChange={(v) => upC({ adStyle: v })} custom={false} cols={3} />
      <Options title="Color Grade" list={C.COLOR_GRADES} value={c.colorGrade} onChange={(v) => upC({ colorGrade: v })} custom={false} cols={4} />

      <div className="section-divider">AUDIO BUILDER</div>
      <Options title="Sound" list={C.SOUNDS} value={c.sound} onChange={(v) => upC({ sound: v })} custom={false} cols={3} />
      {c.sound !== "없음" && <>
        <Options title="Music Mood" list={C.MUSIC_MOODS} value={c.musicMood} onChange={(v) => upC({ musicMood: v })} custom={false} cols={3} />
        <Options title="SFX" list={C.SFX_LIST} value={c.sfx} onChange={(v) => upC({ sfx: v })} multi custom={false} cols={3} />
      </>}

      <div className="section-divider">TEXT &amp; CTA</div>
      <Options title="광고 자막 사용" list={C.CAPTION_TYPES} value={c.captions} onChange={(v) => upC({ captions: v.filter((x) => x !== "없음") })} multi custom={false} cols={4} />
      {c.captions.map((cap) => (
        <div className="field-row" key={cap}>
          <label>{C.disp(C.CAPTION_TYPES, cap)} 문구</label>
          <input className="text-field" value={c.captionText[cap] || ""} placeholder={C.disp(C.CAPTION_TYPES, cap) + " 문구를 직접 입력"}
            onChange={(e) => upC({ captionText: { ...c.captionText, [cap]: e.target.value } })} />
        </div>
      ))}
      <Options title="CTA" list={C.CTAS} value={c.cta} onChange={(v) => upC({ cta: v })} />

      <div className="section-divider">쿠팡파트너스 게시물 캡션</div>
      <Toggle label="대가성 고지 문구 포함 (필수)" value={(c.partners || {}).enabled !== false}
        onChange={(v) => upC({ partners: { ...c.partners, enabled: v } })}
        desc={'"' + "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다." + '" — 공정위 표시광고법상 수익형 게시물에 반드시 포함해야 하며, 미표기 시 파트너스 제재 대상입니다.'} />
      <div className="field-row">
        <label>링크 안내 문구 (비우면 기본 문구 사용)</label>
        <input className="text-field" value={(c.partners || {}).link || ""} placeholder="예: 제품 링크는 프로필에서 확인하세요 👇"
          onChange={(e) => upC({ partners: { ...c.partners, link: e.target.value } })} />
      </div>
      <div className="field-row">
        <label>추가 해시태그 (쉼표/공백 구분 — 기본 태그에 더해집니다)</label>
        <input className="text-field" value={(c.partners || {}).tags || ""} placeholder="예: 모기기피제, 여름캠핑, 육아템"
          onChange={(e) => upC({ partners: { ...c.partners, tags: e.target.value } })} />
      </div>
      {P.platformsOf(S).map((pf) => {
        const cap = P.buildSnsCaption(S, pf);
        const note = (C.PLATFORM_PROFILES[pf] || {}).captionNote || "";
        return <PromptBox key={pf} title={"SNS 캡션 — " + pf + (note ? " (" + note + ")" : "")} kr={cap} en={cap} />;
      })}

      <div className="section-divider">멀티샷 영상 — 6단계 스토리보드를 하나의 영상으로 (Seedance 2.0)</div>
      {(() => {
        const gen = S.gen || {};
        if (!gen.storyJobId) return <div className="empty">먼저 6단계(스토리보드)에서 스토리보드 이미지를 생성해주세요. 그 스토리보드를 기준으로 씬이 순서대로 이어지는 하나의 영상을 만듭니다.</div>;
        const sbv = P.buildStoryboardVideoPrompt(S);
        return <>
          {gen.storyUrl && <div className="gen-note ok" style={{ marginBottom: 10 }}>스토리보드 준비됨 ✓ <a href={gen.storyUrl} target="_blank" rel="noreferrer">스토리보드 보기</a></div>}
          <PromptBox title={"멀티샷 영상 프롬프트 (" + sbv.duration.toFixed(1) + "초 · Scene 1 → Scene " + sbv.count + ")"} kr={sbv.kr} en={sbv.en} />
          <GenRow kind="video" label="🎬 멀티샷 영상 생성 (스토리보드 → Seedance 2.0)"
            savedUrl={gen.storyVidUrl}
            onResult={(jobId, url) => set({ gen: { ...S.gen, storyVidUrl: url } })}
            getParams={() => ({
              model: "seedance_2_0", mode: "std", resolution: "1080p", aspect_ratio: "9:16",
              duration: Math.min(15, Math.max(4, Math.round(sbv.duration))), generate_audio: false,
              medias: refMedias([gen.storyJobId, gen.productRef], "image_references"),
              prompt: sbv.en
            })} />
        </>;
      })()}

      <div style={{ height: 14 }} />
      <button className="primary big" onClick={() => setOutput(P.buildMasterPrompts(S))}>최종 광고 프롬프트 생성</button>

      {output && <>
        <PromptBox title="1. MASTER EDITING PROMPT" kr="전체 편집 지시 — 씬 보호·연속성·편집 스타일" en={output.master} />
        <PromptBox title="2. SCENE-BY-SCENE PROMPT" kr="타임라인 순서대로 각 씬의 영상 프롬프트" en={output.sceneBlock || "(씬 없음)"} />
        <PromptBox title="3. TRANSITION PROMPT" kr="씬 사이 전환 지시" en={output.transBlock} />
        <PromptBox title="4. BRIDGE SCENE PROMPTS" kr="브릿지 인서트 프롬프트" en={output.bridgeBlock} />
        <PromptBox title="5. COLOR GRADING INSTRUCTIONS" kr="색보정 통일 지시" en={output.colorBlock} />
        <PromptBox title="6. AUDIO INSTRUCTIONS" kr="음악·SFX 지시" en={output.audioBlock} />
        {output.platformMasters.map((pm, i) => (
          <PromptBox key={pm.platform} title={"7-" + (i + 1) + ". FINAL MASTER VIDEO PROMPT — " + pm.platform}
            kr={pm.platform + " 전용 최적화(안전영역·페이싱·톤)가 붙은 최종 통합 프롬프트"} en={pm.en} />
        ))}
        <PromptBox title="8. NEGATIVE / PROTECTION PROMPT" kr="모델·제품 보호 및 금지 규칙" en={output.protection} />
      </>}
    </>
  );
}

function StepExport({ S, set }) {
  const rows = P.timelineRows(S);
  const total = rows.length ? rows[rows.length - 1].end : 0;
  const checks = P.continuityChecks(S);
  const mp = P.buildModelPrompt(S), pp = P.buildProductPrompt(S);
  const locPrompts = P.placesOf(S).map((pl) => ({ place: pl, p: P.buildLocationPrompt(S, pl) }));
  const master = P.buildMasterPrompts(S);
  const bridgeEntries = Object.entries(S.composer.bridges);
  const platforms = P.platformsOf(S);
  const captions = platforms.map((pf) => ({ platform: pf, text: P.buildSnsCaption(S, pf) }));
  const allText = [
    "■ " + (S.project.name || "무제 프로젝트"),
    "\n── MODEL PROMPT ──\n" + mp.en,
    "\n── PRODUCT PROMPT ──\n" + pp.en,
    ...locPrompts.map((x) => "\n── LOCATION PROMPT (" + x.place + ") ──\n" + x.p.en),
    ...rows.map((r, i) => "\n── SCENE " + (i + 1) + " IMAGE ──\n" + P.buildSceneImagePrompt(r.scene, S).en + "\n\n── SCENE " + (i + 1) + " VIDEO ──\n" + P.buildSceneVideoPrompt(r.scene, S).en),
    "\n── BRIDGES ──\n" + master.bridgeBlock,
    ...master.platformMasters.map((pm) => "\n── MASTER VIDEO PROMPT (" + pm.platform + ") ──\n" + pm.en),
    "\n── PROTECTION ──\n" + master.protection,
    ...captions.map((cp) => "\n── SNS 캡션 (" + cp.platform + ") ──\n" + cp.text)
  ].join("\n");

  const summary = [
    ["PROJECT NAME", S.project.name || "-"], ["PLATFORM", P.platformsOf(S).join(" + ")], ["FORMAT", P.platformsOf(S).map((pf) => pf + " " + P.ratioOfPlatform(pf)).join(" · ") + " (소스 " + P.sourceRatio(S) + ")"],
    ["TOTAL LENGTH", total.toFixed(1) + "초 (목표 " + S.project.length + ")"], ["AD STYLE", C.disp(C.AD_STYLES, S.project.style)],
    ["MODEL", P.modelSummaryKr(S) + (S.model.lock ? " · LOCK ON" : "")],
    ["PRODUCT", (S.product.name || "-") + (S.product.lock ? " · LOCK ON" : "") + (S.product.img ? " · 사진 있음" : " · 사진 없음")],
    ["LOCATION", P.placesOf(S).map((pl) => C.disp(C.PLACES, pl)).join(" + ") + " · " + C.disp(C.INTERIORS, S.location.interior) + " · " + C.disp(C.TIMES, S.location.time)],
    ["GLOBAL CAMERA", S.global.lens + " · " + C.disp(C.CAM_HEIGHTS, S.global.camHeight) + " · " + C.disp(C.FRAMES, S.global.frame)],
    ["GLOBAL LIGHT", C.disp(C.LIGHT_DIRS, S.global.lightDir) + " · " + C.disp(C.LIGHT_TEMPS, S.global.lightTemp)],
    ["COLOR MOOD", C.disp(C.COLOR_MOODS, S.project.colorMood) + " / Grade: " + C.disp(C.COLOR_GRADES, S.composer.colorGrade)],
    ["SCENE LIST", rows.map((r, i) => (i + 1) + ". " + r.scene.name + " (" + C.disp(C.SCENE_ROLES, r.scene.role) + ")").join("  ·  ") || "-"],
    ["AUDIO", C.disp(C.SOUNDS, S.composer.sound) + (S.composer.sound !== "없음" ? " · " + C.disp(C.MUSIC_MOODS, S.composer.musicMood) : "")],
    ["COPY", S.composer.captions.map((x) => C.disp(C.CAPTION_TYPES, x)).join(", ") || "-"],
    ["CTA", S.composer.cta === "직접 입력" ? S.composer.ctaCustom : S.composer.cta],
    ["ENDING", rows.length ? C.disp(C.SCENE_ROLES, rows[rows.length - 1].scene.role) : "-"],
    ["파트너스 고지", (S.composer.partners || {}).enabled !== false ? "포함됨 ✓" : "⚠ 미포함"]
  ];

  return (
    <>
      <h2>최종 Export</h2>
      <div className="banner" style={{ lineHeight: 1.7 }}>
        <strong>쿠팡파트너스 승인 준비 체크</strong><br />
        ① 파트너스 가입 후 <b>내 인스타그램/틱톡 채널 URL을 파트너스에 등록</b>했는지 확인 (등록 안 된 채널의 수익은 인정되지 않습니다)<br />
        ② 모든 수익형 게시물에 <b>대가성 고지 문구</b> 포함 — 아래 SNS 캡션에 자동으로 들어갑니다<br />
        ③ 최종 승인은 가입 후 <b>일정 누적 매출(현행 기준 15만원 이상) 발생 시</b> 이뤄집니다 — 정확한 최신 기준은 쿠팡파트너스 공지사항에서 확인하세요<br />
        ④ 링크는 영상 자체에 넣을 수 없으므로 <b>프로필 링크/링크트리</b>에 넣고 캡션에서 유도하세요
      </div>
      <div className="section-divider">CONTINUITY CHECKER</div>
      <div className="check-list">
        {checks.map(([label, ok, warn]) => (
          <div key={label} className={"check" + (ok ? " ok" : " warn")}>
            <span className="check-mark">{ok ? "☑" : "⚠"}</span>
            <span>{label}</span>
            {!ok && <span className="check-warn">{warn}</span>}
          </div>
        ))}
      </div>

      <div className="section-divider">PROJECT SUMMARY</div>
      <table className="summary-table"><tbody>
        {summary.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v}</td></tr>)}
      </tbody></table>

      <div className="section-divider">MASTER TIMELINE</div>
      <div className="timeline">
        {rows.map((r, i) => (
          <div className="tl-scene" key={r.scene.id}>
            <span className="tl-time">{P.fmtT(r.start)}–{P.fmtT(r.end)}</span>
            <span className="tl-name">SCENE {String(i + 1).padStart(2, "0")} — {r.scene.name}</span>
            <span className="tl-role">{C.disp(C.SCENE_ROLES, r.scene.role)}</span>
          </div>
        ))}
        {rows.length === 0 && <div className="empty">Composer에서 Timeline을 구성하세요.</div>}
      </div>

      <div className="section-divider">COPY PROMPTS</div>
      {S.nanoCompare === null && (
        <div className="compare-ask" style={{ marginBottom: 12 }}>
          <span>이미지 프롬프트는 GPT 이미지 2 기본으로 준비됐습니다. 나노바나나(Pro) 비교 버전도 함께 받을까요? (한글 라벨 재현력 비교에 유용)</span>
          <button className="primary small" onClick={() => set({ nanoCompare: true })}>네, 비교 버전도 받기</button>
          <button className="mini" onClick={() => set({ nanoCompare: false })}>아니요, GPT만</button>
        </div>
      )}
      {S.nanoCompare === false && (
        <div className="compare-ask muted" style={{ marginBottom: 12 }}>GPT 이미지 2만 사용합니다. <button className="mini" onClick={() => set({ nanoCompare: true })}>나노바나나 비교 버전도 받기</button></div>
      )}
      <div className="copy-list">
        <div className="copy-row"><span>MODEL PROMPT (GPT 이미지 2)</span><CopyBtn text={P.withGpt(mp.en)} label="COPY" /></div>
        <div className="copy-row"><span>PRODUCT PROMPT (GPT 이미지 2)</span><CopyBtn text={P.withGpt(pp.en)} label="COPY" /></div>
        {locPrompts.map((x) => (
          <div className="copy-row" key={"loc-" + x.place}><span>LOCATION PROMPT — {C.disp(C.PLACES, x.place)} (GPT 이미지 2)</span><CopyBtn text={P.withGpt(x.p.en)} label="COPY" /></div>
        ))}
        {rows.map((r, i) => (
          <React.Fragment key={r.scene.id}>
            <div className="copy-row"><span>SCENE {i + 1} IMAGE PROMPT — {r.scene.name} (GPT 이미지 2)</span><CopyBtn text={P.withGpt(P.buildSceneImagePrompt(r.scene, S).en)} label="COPY" /></div>
            <div className="copy-row"><span>SCENE {i + 1} VIDEO PROMPT — {r.scene.name}</span><CopyBtn text={P.buildSceneVideoPrompt(r.scene, S).en} label="COPY" /></div>
          </React.Fragment>
        ))}
        {bridgeEntries.length > 0 && <div className="copy-row"><span>BRIDGE PROMPTS ({bridgeEntries.length}개)</span><CopyBtn text={master.bridgeBlock} label="COPY" /></div>}
        {master.platformMasters.map((pm) => (
          <div className="copy-row" key={"m-" + pm.platform}><span>MASTER VIDEO PROMPT — {pm.platform}</span><CopyBtn text={pm.en} label="COPY" /></div>
        ))}
        {captions.map((cp) => (
          <div className="copy-row" key={"c-" + cp.platform}><span>SNS 캡션 — {cp.platform} (대가성 고지 포함)</span><CopyBtn text={cp.text} label="COPY" /></div>
        ))}
        {S.nanoCompare === true && <>
          <div className="copy-row"><span>MODEL PROMPT (나노바나나 비교)</span><CopyBtn text={P.withNano(mp.en)} label="COPY" /></div>
          <div className="copy-row"><span>PRODUCT PROMPT (나노바나나 비교)</span><CopyBtn text={P.withNano(pp.en)} label="COPY" /></div>
          {locPrompts.map((x) => (
            <div className="copy-row" key={"nloc-" + x.place}><span>LOCATION PROMPT — {C.disp(C.PLACES, x.place)} (나노바나나 비교)</span><CopyBtn text={P.withNano(x.p.en)} label="COPY" /></div>
          ))}
          {rows.map((r, i) => (
            <div className="copy-row" key={"nsc-" + r.scene.id}><span>SCENE {i + 1} IMAGE PROMPT — {r.scene.name} (나노바나나 비교)</span><CopyBtn text={P.withNano(P.buildSceneImagePrompt(r.scene, S).en)} label="COPY" /></div>
          ))}
        </>}
        <div className="copy-row all"><span>COPY ALL — 프로젝트 전체 프롬프트</span><CopyBtn text={allText} label="COPY ALL" /></div>
      </div>

      <div className="section-divider">POST PRODUCTION — 광고 후반 작업</div>
      <div className="banner" style={{ lineHeight: 1.7 }}>
        영상이 완성되었다면 이제 <b>BGM → 한국어 대사 → AI Voice → Lip Sync → Audio Mix → Preview → MP4 다운로드</b>까지 이어서 진행하세요.
        <div style={{ marginTop: 8 }}>
          <button className="primary small" onClick={() => set({ step: 8, post: { ...mergePost(S.post), step: 1 } })}>▶ 후반 작업 시작 (9단계)</button>
        </div>
      </div>
    </>
  );
}

/* ───────────────────────── Summary Panel ───────────────────────── */
function SummaryPanel({ S }) {
  const rows = P.timelineRows(S);
  const total = rows.length ? rows[rows.length - 1].end : 0;
  const items = [
    ["프로젝트", S.project.name || "무제"],
    ["플랫폼", P.platformsOf(S).join("+") + " · " + P.sourceRatio(S)],
    ["스타일", C.disp(C.AD_STYLES, S.project.style)],
    ["컬러", C.disp(C.COLOR_MOODS, S.project.colorMood)],
    ["모델", S.model.age + " " + S.model.ethnicity + (S.model.lock ? " 🔒" : "")],
    ["제품", (S.product.name || "미입력") + (S.product.lock ? " 🔒" : "") + (S.product.img ? " 📷" : "")],
    ["장소", P.placesOf(S).map((pl) => C.disp(C.PLACES, pl)).join(" + ")],
    ["카메라", S.global.lens + " · " + C.disp(C.FRAMES, S.global.frame)],
    ["조명", C.disp(C.LIGHT_DIRS, S.global.lightDir)],
    ["Scene", S.scenes.length + "개 · Timeline " + rows.length + "개"],
    ["총 길이", total.toFixed(1) + "초 / " + S.project.length]
  ];
  return (
    <aside className="summary-panel">
      <div className="sp-title">SUMMARY</div>
      {items.map(([k, v]) => <div className="sp-row" key={k}><span>{k}</span><strong>{v}</strong></div>)}
    </aside>
  );
}

/* ───────────────────────── App ───────────────────────── */
function App() {
  const [S, setS] = useState(loadState);
  const SRef = useRef(S);
  SRef.current = S;
  useEffect(() => {
    const t = setTimeout(() => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(S)); } catch (e) {} }, 400);
    return () => clearTimeout(t);
  }, [S]);
  useEffect(() => {
    const flush = () => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(SRef.current)); } catch (e) {} };
    window.addEventListener("beforeunload", flush);
    document.addEventListener("visibilitychange", flush);
    return () => { window.removeEventListener("beforeunload", flush); document.removeEventListener("visibilitychange", flush); };
  }, []);

  const set = (patch) => setS((s) => ({ ...s, ...patch }));
  const markVisited = () => setS((s) => s.visited.includes(s.step) ? s : { ...s, visited: [...s.visited, s.step] });
  const resetStep = () => {
    const key = ["project", "product", "model", "location", "scenes", "storyboard", "composer", null, "post"][S.step];
    if (key === "post") { set({ post: mergePost(null) }); return; }
    if (key === "storyboard") { set({ gen: { ...S.gen, storyJobId: "", storyUrl: "", storyVidUrl: "" } }); return; }
    if (!key) return;
    if (key === "scenes") set({ scenes: [], sceneSeq: 1, composer: { ...S.composer, timeline: [] } });
    else if (key === "project") set({ project: { ...DEFAULTS.project }, global: { ...DEFAULTS.global } });
    else set({ [key]: JSON.parse(JSON.stringify(DEFAULTS[key])) });
  };

  if (!S.started) {
    return (
      <div className="landing">
        <div className="landing-mark">{["#E0994A", "#4FA6AE", "#9BAE5C", "#B98AC7", "#D97A66"].map((c) => <span key={c} style={{ background: c }} />)}</div>
        <h1>AI AD CREATIVE STUDIO</h1>
        <p>제품 · 모델 · 장소를 각각 설계하고<br />Scene별 이미지와 영상을 제작한 뒤<br />하나의 완성된 광고 프롬프트로 연결하세요.</p>
        <button className="primary big" onClick={() => set({ started: true, step: 0 })}>새 광고 프로젝트 시작</button>
      </div>
    );
  }

  const stepProps = { S, set };
  const done = (i) => S.visited.includes(i);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand" onClick={() => set({ started: false })} title="첫 화면으로">AI AD CREATIVE STUDIO</div>
        <input className="proj-name" value={S.project.name} placeholder="프로젝트명 입력…"
          onChange={(e) => set({ project: { ...S.project, name: e.target.value } })} />
        <div className="progress-dots">
          {STEP_KEYS.map((k, i) => (
            <span key={k} className={"dot-item" + (done(i) ? " done" : "") + (S.step === i ? " now" : "")} onClick={() => set({ step: i })}>
              <span className="dot" />{k}
            </span>
          ))}
        </div>
        <ArmedButton className="ghost danger" label="전체 초기화" armedLabel="⚠ 전체 삭제 — 한 번 더 클릭"
          onRun={() => { localStorage.removeItem(STORAGE_KEY); setS(applySeed({ ...JSON.parse(JSON.stringify(DEFAULTS)), post: mergePost(null), started: true })); }} />
      </header>

      <div className="layout">
        <nav className="stepnav">
          {STEPS.map((label, i) => (
            <button key={label} className={"step-link" + (S.step === i ? " active" : "") + (done(i) ? " done" : "")} onClick={() => set({ step: i })}>
              <span className="step-idx">{i + 1}</span>{label}
            </button>
          ))}
        </nav>

        <main className="content">
          {S.step === 0 && <StepProject S={S} up={(p) => set({ project: { ...S.project, ...p } })} upG={(p) => set({ global: { ...S.global, ...p } })} />}
          {S.step === 1 && <StepProduct S={S} set={set} up={(p) => set({ product: { ...S.product, ...p } })} />}
          {S.step === 2 && <StepModel S={S} set={set} up={(p) => set({ model: { ...S.model, ...p } })} />}
          {S.step === 3 && <StepLocation S={S} up={(p) => set({ location: { ...S.location, ...p } })} />}
          {S.step === 4 && <StepScenes {...stepProps} />}
          {S.step === 5 && <StepStoryboard S={S} set={set} />}
          {S.step === 6 && <StepComposer {...stepProps} />}
          {S.step === 7 && <StepExport S={S} set={set} />}
          {S.step === 8 && <StepPost S={S} set={set} />}
          <NavButtons S={S} set={set} onSave={markVisited} onReset={resetStep} />
        </main>

        <SummaryPanel S={S} />
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
