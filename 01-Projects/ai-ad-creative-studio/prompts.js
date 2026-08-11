// 프롬프트 조립 로직 — 상태 → 영문 프롬프트 + 한국어 설명
import {
  PURPOSES, PLATFORMS, LENGTHS, AD_STYLES, COLOR_MOODS,
  GENDERS, ETHNICITIES, AGES, FACES, SKINS, EYES, IRISES,
  HAIR_LENGTHS, HAIR_STYLES, HAIR_COLORS, MODEL_VIEWS,
  PRODUCT_TYPES, PRODUCT_SHOTS, PRODUCT_ANGLES, PRODUCT_POSITIONS, PRODUCT_BGS, PRODUCT_FX,
  PLACES, INTERIORS, TIMES, ENV_LIGHTS,
  LIGHT_DIRS, LIGHT_TEMPS, LENSES, CAM_HEIGHTS, FRAMES,
  SCENE_ROLES, MODEL_ACTIONS, PRODUCT_MOTIONS, CAMERA_MOTIONS,
  TRANSITIONS, BRIDGE_TYPES, EDIT_STYLES, COLOR_GRADES, SOUNDS, MUSIC_MOODS, SFX_LIST,
  CAPTION_TYPES, CTAS,
  IDENTITY_LOCK_EN, PRODUCT_LOCK_EN, VIDEO_NEG_EN, AI_AUTO_NOTE,
  PARTNERS_DISCLOSURE, PARTNERS_BASE_TAGS, PLATFORM_PROFILES, NO_TEXT_EN, PRODUCT_SCALES,
  PRESENT_STYLES, PRESENT_GAZES, PRESENT_GESTURES, PACKAGE_PRESERVE_EN
} from "./catalogs.js";

// 플랫폼 목록 (구버전 단일 platform 저장분 호환)
export function platformsOf(S) {
  const p = S.project.platforms;
  if (Array.isArray(p) && p.length) return p;
  if (S.project.platform) return [S.project.platform];
  return ["Instagram Reels"];
}
function platformsEn(S) {
  return platformsOf(S).map((p) => en(PLATFORMS, p)).join(" and ");
}

// 장소 목록 (구버전 단일 place 저장분 호환)
export function placesOf(S) {
  const l = S.location;
  if (Array.isArray(l.places) && l.places.length) return l.places;
  if (l.place) return [l.place];
  return ["프리미엄 주방"];
}
// 씬에 지정된 장소 (미지정이면 첫 번째 장소)
export function scenePlace(scene, S) {
  const list = placesOf(S);
  return scene.place && list.includes(scene.place) ? scene.place : list[0];
}

// 플랫폼 → 권장 비율 (프로필에 없으면 9:16)
export function ratioOfPlatform(platform) {
  return (PLATFORM_PROFILES[platform] || {}).ratio || "9:16";
}
// 소스 촬영 비율: 세로형(9:16) 플랫폼이 하나라도 있으면 9:16으로 찍고 나머지는 크롭
export function sourceRatio(S) {
  const ratios = platformsOf(S).map(ratioOfPlatform);
  return ratios.includes("9:16") ? "9:16" : (ratios[0] || "9:16");
}
// 비율이 섞여 있을 때 크롭 안전 안내
export function cropNote(S) {
  const ratios = [...new Set(platformsOf(S).map(ratioOfPlatform))];
  if (ratios.length <= 1) return "";
  const others = ratios.filter((r) => r !== sourceRatio(S));
  return ` Keep all key content (faces, product, captions) center-framed so the shot survives a crop to ${others.join(" / ")}.`;
}

// kr 값 → en 값 (직접 입력 값은 그대로 통과)
export function en(catalog, kr) {
  if (!kr) return "";
  const hit = catalog.find((c) => c.kr === kr);
  return hit ? hit.en : kr;
}

export function globalCameraEn(S) {
  return `Camera: ${en(LENSES, S.global.lens)}, ${en(CAM_HEIGHTS, S.global.camHeight)}, ${en(FRAMES, S.global.frame)}.`;
}
export function globalLightEn(S) {
  return `Lighting: ${en(LIGHT_DIRS, S.global.lightDir)}, ${en(LIGHT_TEMPS, S.global.lightTemp)}.`;
}
function styleMoodEn(S) {
  return `Ad style: ${en(AD_STYLES, S.project.style)}. Color mood: ${en(COLOR_MOODS, S.project.colorMood)}. Aspect ratio ${sourceRatio(S)}.` + cropNote(S);
}

export function modelSummaryEn(S) {
  const m = S.model;
  return `a ${en(AGES, m.age)} ${en(ETHNICITIES, m.ethnicity)} ${en(GENDERS, m.gender)} commercial model with ${en(FACES, m.face)}, ${en(SKINS, m.skin)}, ${en(EYES, m.eyes)} with ${en(IRISES, m.iris)}, ${en(HAIR_LENGTHS, m.hairLen)} ${en(HAIR_STYLES, m.hairStyle)} in ${en(HAIR_COLORS, m.hairColor)}`;
}
export function modelSummaryKr(S) {
  const m = S.model;
  return `${m.age} ${m.ethnicity} ${m.gender} · ${m.face} · ${m.skin} · ${m.eyes}(${m.iris}) · ${m.hairLen} ${m.hairStyle}(${m.hairColor})`;
}

export function buildModelPrompt(S) {
  const views = S.model.views.length ? S.model.views.map((v) => en(MODEL_VIEWS, v)).join(", ") : "front-facing view";
  const enTxt = [
    `Ultra-photorealistic commercial photograph of ${modelSummaryEn(S)}.`,
    `Views to generate: ${views}.`,
    `Realistic skin texture with visible pores, natural facial asymmetry, individual hair strands. No plastic skin, no beauty-filter look.`,
    styleMoodEn(S),
    globalCameraEn(S),
    globalLightEn(S),
    S.model.lock ? IDENTITY_LOCK_EN : "",
    NO_TEXT_EN
  ].filter(Boolean).join("\n\n");
  const krTxt = `AI 모델 생성 프롬프트 — ${modelSummaryKr(S)} / 이미지 타입: ${S.model.views.join(", ") || "정면"} / 스타일 ${S.project.style} / ${sourceRatio(S)}${S.model.lock ? " / 얼굴 고정(IDENTITY LOCK) 포함" : ""}`;
  return { kr: krTxt, en: enTxt };
}

// 크기감 절 — 지정 안 함이면 빈 문자열
export function productScaleClause(S) {
  const e = en(PRODUCT_SCALES, S.product.scale);
  return e ? ` True physical scale: the product is ${e} — never render it larger or smaller than real life.` : "";
}
// 소구점 절 — 화면 텍스트가 아니라 연출로 표현하도록 강제
export function productUspClause(S) {
  const u = (S.product.usp || "").trim();
  return u ? ` Key selling points to express VISUALLY through the scene (never as on-screen text): ${u}.` : "";
}

// 모든 제품 등장 프롬프트에 기본 포함되는 실사진 참조 절 (힉스필드용)
export function productRefClause(S) {
  const name = S.product.name || "the product";
  return S.product.img
    ? `Use the uploaded real photo of ${name} as the absolute product reference in Higgsfield. Reproduce its design exactly — shape, packaging, logo, label, typography, and colors — with zero alteration.`
    : `[제품 사진 미업로드 — 힉스필드 생성 시 실제 ${name} 사진을 반드시 참조 이미지로 첨부하세요.] Use the real photo of ${name} as the absolute product reference; reproduce its design exactly with zero alteration.`;
}

export function buildProductPrompt(S) {
  const p = S.product;
  const name = p.name || "the product";
  const fx = p.effects.filter((e) => e !== "없음");
  const ref = productRefClause(S);
  const enTxt = [
    `${ref}`,
    `Product: ${name}. Shot style: ${en(PRODUCT_SHOTS, p.shot)}, ${en(PRODUCT_ANGLES, p.angle)}, ${en(PRODUCT_POSITIONS, p.position)} against a ${en(PRODUCT_BGS, p.bg)}.` + productScaleClause(S) + productUspClause(S),
    fx.length ? `Styling elements: ${fx.map((e) => en(PRODUCT_FX, e)).join(", ")}.` : `No added styling elements — clean product-only shot.`,
    styleMoodEn(S),
    globalCameraEn(S),
    globalLightEn(S),
    p.lock ? PRODUCT_LOCK_EN : "",
    NO_TEXT_EN
  ].filter(Boolean).join("\n\n");
  const krTxt = `제품 프롬프트 — ${name} / ${p.shot} · ${p.angle} · ${p.position} · 배경 ${p.bg}${fx.length ? " / 연출: " + fx.join(", ") : ""}${p.lock ? " / 제품 디자인 고정(REFERENCE LOCK) 포함" : ""}`;
  return { kr: krTxt, en: enTxt };
}

export function buildLocationPrompt(S, place) {
  const l = S.location;
  const pl = place || placesOf(S)[0];
  const enTxt = [
    `EMPTY ENVIRONMENT ONLY. No model, no person, no product, no brand, no text anywhere in the frame.`,
    `Location: ${en(PLACES, pl)}, ${en(INTERIORS, l.interior)}, at ${en(TIMES, l.time)}, lit by ${en(ENV_LIGHTS, l.light)}.`,
    `Location camera: ${en(LENSES, l.lens)}, ${en(CAM_HEIGHTS, l.camHeight)}.`,
    styleMoodEn(S),
    globalLightEn(S),
    NO_TEXT_EN
  ].join("\n\n");
  const krTxt = `장소 프롬프트 — ${pl} / ${l.interior} / ${l.time} / ${l.light} (모델·제품·브랜드·텍스트 없는 빈 환경 컷)`;
  return { kr: krTxt, en: enTxt };
}

// 프레젠터 연출 값 (구버전 씬 저장분은 기본값 폴백)
function presenterOf(scene) {
  return {
    style: en(PRESENT_STYLES, scene.presentStyle || "친구에게 추천하듯"),
    gaze: en(PRESENT_GAZES, scene.gaze || "카메라 정면 응시"),
    gesture: en(PRESENT_GESTURES, scene.gesture || "제품 들어 보여주기")
  };
}

export function buildSceneImagePrompt(scene, S) {
  const use = (a) => scene.assets.includes(a);
  const sec = [];
  sec.push(`[SUBJECT]\nScene "${scene.name}" (${en(SCENE_ROLES, scene.role)}) for a ${en(PURPOSES, S.project.purpose)} ad for ${platformsEn(S)}.`);
  if (use("MODEL")) sec.push(`[IDENTITY]\nThe model is ${modelSummaryEn(S)}.${S.model.lock ? "\n" + IDENTITY_LOCK_EN : ""}`);
  if (use("PRODUCT")) sec.push(`[PRODUCT REFERENCE]\nProduct: ${S.product.name || "the product"}.\n${productRefClause(S)}${productScaleClause(S)}${productUspClause(S)}${S.product.lock ? "\n" + PRODUCT_LOCK_EN : ""}`);
  if (use("LOCATION")) sec.push(`[LOCATION]\n${en(PLACES, scenePlace(scene, S))}, ${en(INTERIORS, S.location.interior)}, ${en(TIMES, S.location.time)}, ${en(ENV_LIGHTS, S.location.light)}.`);
  if (use("PROP")) sec.push(`[PROP]\nSupporting props consistent with the scene, no brand or text on props.`);
  if (use("MODEL")) {
    const pr = presenterOf(scene);
    sec.push(`[POSE / ACTION]\nThe model is mid-presentation: ${pr.gesture}, ${pr.gaze}, ${pr.style}. Natural warm expression, mouth slightly open as if speaking.${use("PRODUCT") ? ` Product: ${en(PRODUCT_MOTIONS, scene.productMotion)} (frozen at its most photogenic moment for the still).` : ""}`);
  } else {
    sec.push(`[POSE / ACTION]\n${use("PRODUCT") ? `Product: ${en(PRODUCT_MOTIONS, scene.productMotion)} (frozen at its most photogenic moment for the still).` : "Clean composition without a model."}`);
  }
  sec.push(`[COMPOSITION]\n${en(FRAMES, S.global.frame)}, subject placed with intentional negative space for ${sourceRatio(S)}.`);
  sec.push(`[CAMERA]\n${globalCameraEn(S)}`);
  sec.push(`[LIGHT]\n${globalLightEn(S)}`);
  sec.push(`[COLOR]\n${en(COLOR_MOODS, S.project.colorMood)}, consistent with the whole campaign.`);
  sec.push(`[MATERIAL]\nRealistic material rendering — skin, fabric, glass, liquid, and packaging behave like their real physical materials.`);
  sec.push(`[REALISM]\nUltra-photorealistic commercial photography, full-frame camera look, shallow natural depth of field, no illustration or CGI look.`);
  sec.push(`[FORMAT]\nAspect ratio ${sourceRatio(S)}, high resolution, ad-ready still frame.${cropNote(S)}`);
  sec.push(`[CONSISTENCY RULES]\nMatch light direction (${en(LIGHT_DIRS, S.global.lightDir)}), light temperature (${en(LIGHT_TEMPS, S.global.lightTemp)}), camera height, lens characteristics, perspective, shadow direction, and color grading with every other scene in this project.`);
  sec.push(`[NEGATIVE INSTRUCTIONS]\n${NO_TEXT_EN}\nNo distorted anatomy, no plastic skin, no product redesign.`);
  const krTxt = `씬 이미지 프롬프트 — ${scene.name} (${scene.role}) / 사용 Asset: ${scene.assets.join(", ") || "-"} / ${sourceRatio(S)}`;
  return { kr: krTxt, en: sec.join("\n\n") };
}

export function buildSceneVideoPrompt(scene, S) {
  const use = (a) => scene.assets.includes(a);
  const d = parseFloat(scene.duration) || 2;
  const t1 = Math.round(d * 0.3 * 10) / 10, t2 = Math.round(d * 0.8 * 10) / 10;
  const sec = [];
  sec.push(`[SUBJECT]\nScene "${scene.name}" (${en(SCENE_ROLES, scene.role)}), ${d} seconds, ${sourceRatio(S)}.${cropNote(S)}`);
  sec.push(`[STARTING STATE]\nThe frame opens exactly on the approved scene image: ${use("MODEL") ? "model in position, " : ""}${use("PRODUCT") ? "product clearly visible, " : ""}composition already settled.`);
  if (use("MODEL")) {
    const pr = presenterOf(scene);
    sec.push(`[SUBJECT MOTION — PRESENTER]\n0.0–${t1} sec: she settles naturally and begins speaking, ${pr.style}. ${t1}–${t2} sec: while talking, she is ${pr.gesture}, ${pr.gaze}. ${t2}–${d} sec: she finishes her line with a warm closing expression and holds.\nRealistic natural speaking mouth movements throughout (dialogue/voiceover will be added in post — no exaggerated lip movement). Relaxed, natural hand gestures like a real presenter.`);
  }
  if (use("PRODUCT")) sec.push(`[PRODUCT REFERENCE]\n${productRefClause(S)}${productScaleClause(S)} Preserve the product's shape, label, colors, and details exactly throughout every frame of the video.`);
  if (use("PRODUCT")) sec.push(`[PRODUCT MOTION]\nThe product is ${en(PRODUCT_MOTIONS, scene.productMotion)} throughout, label always readable, packaging never deforming.`);
  sec.push(`[CAMERA MOTION]\n${en(CAMERA_MOTIONS, scene.cameraMotion)} across the full ${d} seconds, evenly paced, no sudden speed changes.`);
  sec.push(`[LIGHTING]\n${en(ENV_LIGHTS, S.location.light)} stays constant, ${en(LIGHT_DIRS, S.global.lightDir)}, ${en(LIGHT_TEMPS, S.global.lightTemp)}, no flicker.`);
  sec.push(`[ENVIRONMENT MOTION]\nOnly ambient elements move subtly (light, fabric, plants, particles). The environment structure never changes.`);
  sec.push(`[PHYSICS]\nNatural weight and momentum. Hair, fabric, and liquid obey real physics.`);
  sec.push(`[FOCUS]\nFocus locked on ${use("PRODUCT") ? "the product label" : "the model's face"}; background holds its depth of field.`);
  sec.push(`[TIMING]\n0.0–${t1} sec: establish. ${t1}–${t2} sec: main action. ${t2}–${d} sec: settle and hold for the cut.`);
  sec.push(`[ENDING STATE]\nMotion resolves cleanly; final frame is stable and usable as a transition-out point.`);
  sec.push(`[CONSISTENCY]\n${use("MODEL") && S.model.lock ? "Model identity locked — same woman, no drift. " : ""}${use("PRODUCT") && S.product.lock ? "Product design locked — no packaging or label changes. " : ""}Match the project's global camera, light direction, and color grade.`);
  sec.push(`[NEGATIVE INSTRUCTIONS]\n${VIDEO_NEG_EN}`);
  const krTxt = `씬 영상 프롬프트 — ${scene.name} / ${d}초 / 카메라 ${scene.cameraMotion}${use("MODEL") ? " / 모델: " + scene.modelAction : ""}${use("PRODUCT") ? " / 제품: " + scene.productMotion : ""}`;
  return { kr: krTxt, en: sec.join("\n\n") };
}

export function buildBridgePrompt(bridge, prevScene, nextScene, S) {
  const enTxt = [
    `BRIDGE SCENE (${bridge.dur} seconds): ${en(BRIDGE_TYPES, bridge.type)} connecting "${prevScene ? prevScene.name : "previous scene"}" to "${nextScene ? nextScene.name : "next scene"}".`,
    `Build the bridge from elements shared by the previous scene's END FRAME and the next scene's START FRAME. Compare and match: COLOR, LIGHT, MOTION, OBJECT, CAMERA DIRECTION.`,
    prevScene ? `Previous scene ends with: ${en(CAMERA_MOTIONS, prevScene.cameraMotion)}, role ${en(SCENE_ROLES, prevScene.role)}.` : "",
    nextScene ? `Next scene begins with: ${en(CAMERA_MOTIONS, nextScene.cameraMotion)}, role ${en(SCENE_ROLES, nextScene.role)}.` : "",
    `Keep the project's ${en(COLOR_MOODS, S.project.colorMood)}, ${en(LIGHT_DIRS, S.global.lightDir)}, and ${en(LIGHT_TEMPS, S.global.lightTemp)} identical on both ends so the insert is invisible as an edit.`,
    `If the product appears: ${productRefClause(S)}` + (S.product.lock ? " " + PRODUCT_LOCK_EN : ""),
    VIDEO_NEG_EN
  ].filter(Boolean).join("\n\n");
  const krTxt = `브릿지 — ${bridge.type} / ${bridge.dur}초 / ${prevScene ? prevScene.name : "?"} → ${nextScene ? nextScene.name : "?"}`;
  return { kr: krTxt, en: enTxt };
}

export function orderedScenes(S) {
  return S.composer.timeline.map((id) => S.scenes.find((sc) => sc.id === id)).filter(Boolean);
}

export function timelineRows(S) {
  const list = orderedScenes(S);
  let t = 0;
  return list.map((sc) => {
    const d = parseFloat(sc.duration) || 2;
    const row = { scene: sc, start: t, end: t + d };
    t += d;
    return row;
  });
}
export function fmtT(sec) {
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return `${String(m).padStart(2, "0")}:${s.toFixed(1).padStart(4, "0")}`;
}

export function buildMasterPrompts(S) {
  const rows = timelineRows(S);
  const total = rows.length ? rows[rows.length - 1].end : 0;
  const c = S.composer;

  const master = [
    `Create one seamless commercial using the supplied source scene videos.`,
    `Treat every supplied scene as protected source footage.`,
    S.model.lock ? `Preserve the exact model identity.\nPreserve facial structure, skin tone, age and hairstyle.` : "",
    S.product.lock ? `Preserve the exact product packaging, logo, label, typography, colors and proportions.` : "",
    `Do not redesign supplied assets.`,
    `Arrange all scenes according to the approved timeline.`,
    `Maintain visual continuity between scenes. Match motion direction whenever possible.`,
    `Match: camera direction, camera speed, camera height, perspective, exposure, white balance, contrast, color grading, light direction, shadow direction.`,
    `Use motivated transitions. Avoid decorative or excessive effects.`,
    `The final result must look like all scenes were intentionally directed and filmed for one unified advertising campaign.`,
    PACKAGE_PRESERVE_EN,
    `Editing style: ${en(EDIT_STYLES, c.adStyle)}. Color grade: ${en(COLOR_GRADES, c.colorGrade)}. Total length: ${total.toFixed(1)} seconds, source ratio ${sourceRatio(S)}, for ${platformsEn(S)}.`
  ].filter(Boolean).join("\n");

  const sceneBlock = rows.map((r, i) => {
    const p = buildSceneVideoPrompt(r.scene, S);
    return `━━━ SCENE ${String(i + 1).padStart(2, "0")} — ${r.scene.name} [${fmtT(r.start)}–${fmtT(r.end)}] ━━━\n${p.en}`;
  }).join("\n\n");

  const transBlock = rows.slice(0, -1).map((r, i) => {
    const tr = c.transitions[i] || "AI Auto";
    const next = rows[i + 1];
    return `${r.scene.name} → ${next.scene.name}: ${en(TRANSITIONS, tr)}${tr === "AI Auto" ? "\n" + AI_AUTO_NOTE : ""}`;
  }).join("\n\n") || "(전환 설정 없음 — 씬이 2개 이상일 때 생성됩니다)";

  const bridgeBlock = Object.entries(c.bridges).map(([gap, b]) => {
    const i = parseInt(gap, 10);
    const prev = rows[i] ? rows[i].scene : null;
    const next = rows[i + 1] ? rows[i + 1].scene : null;
    return buildBridgePrompt(b, prev, next, S).en;
  }).join("\n\n━━━━━━━━\n\n") || "(브릿지 없음)";

  const colorBlock = `Apply one unified color grade to every scene: ${en(COLOR_GRADES, c.colorGrade)}, built on the campaign color mood (${en(COLOR_MOODS, S.project.colorMood)}). Match exposure, white balance (${en(LIGHT_TEMPS, S.global.lightTemp)}), contrast and saturation across all cuts so no scene looks like it came from a different shoot.`;

  const audioParts = [`Sound design: ${en(SOUNDS, c.sound)}.`];
  if (c.sound !== "없음") {
    audioParts.push(`Music mood: ${en(MUSIC_MOODS, c.musicMood)}.`);
    if (c.sfx.length) audioParts.push(`Sound effects: ${c.sfx.map((s) => en(SFX_LIST, s)).join(", ")} — placed on matching visual beats only.`);
    audioParts.push(`Audio levels support the visuals; music ducks under any voice; no jarring volume jumps.`);
  }
  const audioBlock = audioParts.join("\n");

  const capLines = c.captions.filter((x) => x !== "없음").map((cap) => {
    const custom = (c.captionText[cap] || "").trim();
    return `- ${cap}${custom ? `: "${custom}"` : ""}`;
  });
  const ctaText = c.cta === "직접 입력" ? c.ctaCustom : c.cta;
  const copyBlock = capLines.length || ctaText
    ? `On-screen text plan:\n${capLines.join("\n")}${ctaText ? `\n- CTA: "${ctaText}"` : ""}\nKeep captions short, high-contrast, and inside platform-safe margins for ${platformsEn(S)}.`
    : "(자막/CTA 미사용)";

  const finalMaster = [
    master,
    ``,
    `── TIMELINE ──`,
    rows.map((r, i) => `${fmtT(r.start)}–${fmtT(r.end)}  SCENE ${String(i + 1).padStart(2, "0")} — ${r.scene.name} (${en(SCENE_ROLES, r.scene.role)})`).join("\n") || "(타임라인 비어 있음)",
    ``,
    `── TRANSITIONS ──`,
    transBlock,
    ``,
    `── COLOR ──`,
    colorBlock,
    ``,
    `── AUDIO ──`,
    audioBlock,
    ``,
    `── TEXT & CTA ──`,
    copyBlock
  ].join("\n");

  const protection = [
    S.model.lock ? IDENTITY_LOCK_EN : "",
    S.product.lock ? PRODUCT_LOCK_EN : "",
    PACKAGE_PRESERVE_EN,
    VIDEO_NEG_EN
  ].filter(Boolean).join("\n\n");

  // 선택한 각 플랫폼별 최종 마스터 프롬프트 (공통 마스터 + 플랫폼 최적화 블록)
  const platformMasters = platformsOf(S).map((p) => {
    const prof = PLATFORM_PROFILES[p];
    const dr = ratioOfPlatform(p);
    return {
      platform: p,
      ratio: dr,
      en: finalMaster + `\n\n── DELIVERY FORMAT ──\nDeliver this cut in ${dr} for ${p}.` + (dr !== sourceRatio(S) ? ` Center-crop from the ${sourceRatio(S)} source; keep faces, product, and captions fully inside the ${dr} crop.` : "") + (prof ? `\n\n── ${p.toUpperCase()} 전용 최적화 ──\n${prof.editEn}` : "")
    };
  });

  return {
    master, sceneBlock, transBlock, bridgeBlock, colorBlock, audioBlock, finalMaster, protection,
    copyBlock, total, platformMasters
  };
}

// 쿠팡파트너스용 SNS 게시물 캡션 — platform 인자를 주면 그 플랫폼 톤에 맞춰 조정
export function buildSnsCaption(S, platform) {
  const c = S.composer;
  const pt = c.partners || {};
  const prof = platform ? PLATFORM_PROFILES[platform] : null;
  const tiktok = prof && prof.tone === "tiktok";
  const hook = (c.captionText["Hook"] || "").trim() ||
    (tiktok ? `${S.product.name || "이거"} 아직도 모름? 🦟` : `요즘 여름 필수템, ${S.product.name || "이 제품"} 써봤어요`);
  const benefit = (c.captionText["Key Benefit"] || "").trim() || (S.product.usp || "").trim();
  const slogan = (c.captionText["Brand Slogan"] || "").trim();
  const ctaText = c.cta === "직접 입력" ? c.ctaCustom : ((c.captionText["CTA"] || "").trim() || c.cta);
  const linkLine = (pt.link || "").trim() || (tiktok ? "링크는 프로필에 👆" : "제품 링크는 프로필에서 확인하세요 👇");
  const customTags = (pt.tags || "").split(/[,#\s]+/).map((t) => t.trim()).filter(Boolean);
  const nameTag = (S.product.name || "").replace(/[\s()+·]/g, "").slice(0, 12);
  const maxTags = prof ? prof.tagCount : 10;
  const tags = [...new Set([...customTags, ...(nameTag ? [nameTag] : []), ...PARTNERS_BASE_TAGS])]
    .slice(0, Math.max(maxTags, 2))
    .map((t) => "#" + t).join(" ");
  const lines = [hook];
  if (benefit && !tiktok) lines.push(benefit);
  if (benefit && tiktok) lines.push(benefit.split(/[,.]/)[0]);
  if (slogan && !tiktok) lines.push(slogan);
  lines.push("", linkLine + (ctaText && !tiktok ? ` (${ctaText})` : ""), "", tags);
  if (pt.enabled !== false) lines.push("", PARTNERS_DISCLOSURE);
  return lines.join("\n");
}

// CONTINUITY CHECKER — [label, ok, warnMsg]
export function continuityChecks(S) {
  const rows = timelineRows(S);
  const total = rows.length ? rows[rows.length - 1].end : 0;
  const c = S.composer;
  const flashy = rows.slice(0, -1).filter((_, i) => ["Whip Pan", "Flash", "Push", "Mask"].includes(c.transitions[i])).length;
  const prodTime = rows.filter((r) => r.scene.assets.includes("PRODUCT")).reduce((a, r) => a + (r.end - r.start), 0);
  const opposite = rows.slice(0, -1).some((r, i) => {
    const a = r.scene.cameraMotion, b = rows[i + 1].scene.cameraMotion;
    return (a === "Pan Left" && b === "Pan Right") || (a === "Pan Right" && b === "Pan Left") ||
      (a === "Orbit Left" && b === "Orbit Right") || (a === "Orbit Right" && b === "Orbit Left");
  });
  const lastRole = rows.length ? rows[rows.length - 1].scene.role : null;
  const hasCTA = c.captions.includes("CTA") || !!(c.cta && c.cta !== "없음");
  return [
    ["모델 얼굴 일관성", S.model.lock, "MODEL IDENTITY LOCK이 꺼져 있습니다"],
    ["모델 나이 일관성", S.model.lock, "IDENTITY LOCK을 켜면 나이 고정 규칙이 포함됩니다"],
    ["헤어 일관성", S.model.lock, "IDENTITY LOCK을 켜면 헤어 고정 규칙이 포함됩니다"],
    ["제품 패키지 유지", S.product.lock, "PRODUCT REFERENCE LOCK이 꺼져 있습니다"],
    ["로고 유지", S.product.lock, "PRODUCT REFERENCE LOCK이 꺼져 있습니다"],
    ["제품 텍스트 유지", S.product.lock, "PRODUCT REFERENCE LOCK이 꺼져 있습니다"],
    ["제품 비율 유지", !!S.product.img || S.product.lock, "제품 사진이 없으면 비율이 흔들릴 수 있습니다 — 사진 업로드 권장"],
    ["카메라 방향", !opposite, "인접 씬의 카메라가 반대 방향(팬/오빗)입니다 — 방향을 맞추거나 브릿지를 넣으세요"],
    ["움직임 방향", !opposite, "인접 씬 움직임 방향이 충돌합니다"],
    ["조명 방향", !!S.global.lightDir, "공통 광원 방향이 비어 있습니다"],
    ["색감 통일", !!c.colorGrade, "Color Grade가 선택되지 않았습니다"],
    ["Transition 과다 여부", flashy <= Math.max(1, Math.floor(rows.length / 3)), `화려한 전환(${flashy}개)이 많습니다 — Clean/Match 계열 권장`],
    ["Story Flow", rows.length > 0 && rows[0].scene.role === "Hook", "첫 씬이 Hook이 아닙니다 — 첫 1초 이탈률에 영향"],
    ["제품 노출 시간", total === 0 || prodTime >= total * 0.3, `제품 등장 시간이 전체의 ${total ? Math.round((prodTime / total) * 100) : 0}%입니다 (30% 이상 권장)`],
    ["CTA 확인", hasCTA, "CTA가 설정되지 않았습니다"],
    ["Ending 확인", ["CTA", "Brand Ending", "Hero Shot"].includes(lastRole), "마지막 씬은 Hero Shot / CTA / Brand Ending 권장"],
    ["쿠팡파트너스 대가성 고지", (c.partners || {}).enabled !== false, "수익용 게시물에는 '쿠팡 파트너스 활동…' 고지 문구가 법적으로 필수입니다 — Composer에서 켜세요"]
  ];
}

// 이미지 생성 모델 헤더 — GPT 이미지 2 기본, 나노바나나는 비교 승인 시
export const GPT_MODEL_HEADER = `[GENERATION MODEL]
Generate this image with GPT Image 2 (gpt_image_2, quality: high, 2K/4K direct output) — the default model for this project.`;
export const NANO_MODEL_HEADER = `[COMPARISON GENERATION — NANO BANANA PRO]
Generate the SAME prompt again with Nano Banana Pro (nano_banana_pro, 1K output — upscale to 4K after selection).
Purpose: side-by-side comparison with the GPT Image 2 result. Compare Korean label typography fidelity, product accuracy, and overall commercial quality, then keep the better one.`;
export function withGpt(enTxt) { return GPT_MODEL_HEADER + "\n\n" + enTxt; }
export function withNano(enTxt) { return NANO_MODEL_HEADER + "\n\n" + enTxt; }

// 씬 한 줄 요약 (스토리보드 패널 설명용)
function sceneBriefEn(scene, S) {
  const use = (a) => scene.assets.includes(a);
  const parts = [];
  if (use("MODEL")) {
    const pr = presenterOf(scene);
    parts.push(`the model is ${pr.gesture}, ${pr.gaze}`);
  }
  if (use("PRODUCT")) parts.push(`the product is ${en(PRODUCT_MOTIONS, scene.productMotion)}`);
  if (use("LOCATION")) parts.push(`set in ${en(PLACES, scenePlace(scene, S))}`);
  return parts.join("; ") || "clean product-focused composition";
}

// 스토리보드 이미지 — 하나의 캔버스에 여러 씬을 패널로 배치하되 이음새 없이 하나의 키비주얼처럼
export function buildStoryboardPrompt(S) {
  const rows = timelineRows(S);
  const list = rows.length ? rows.map((r) => r.scene) : S.scenes;
  const n = Math.max(list.length, 1);
  const sceneLines = list.map((sc, i) => `Scene ${i + 1} — ${en(SCENE_ROLES, sc.role)}: ${sceneBriefEn(sc, S)}.`).join("\n");
  const enTxt = [
    `Create ONE single ${sourceRatio(S)} canvas that contains ${n} distinct scenes arranged like a clean advertising storyboard.`,
    `Each scene occupies its own clearly readable zone, but the zones blend into each other seamlessly — no hard divider lines, no frames, no borders — so the whole canvas reads as ONE continuous premium ad key visual.`,
    `Every scene shows the SAME product, the SAME woman with identical facial identity, the SAME outfit, and the SAME background mood and design identity — perfect consistency across all scenes.`,
    sceneLines,
    productRefClause(S) + productScaleClause(S),
    S.model.lock ? IDENTITY_LOCK_EN : "",
    `Ad style: ${en(AD_STYLES, S.project.style)}. Color mood: ${en(COLOR_MOODS, S.project.colorMood)}. ${globalLightEn(S)}`,
    NO_TEXT_EN
  ].filter(Boolean).join("\n\n");
  const krTxt = `스토리보드 이미지 — 씬 ${n}개를 한 캔버스에 이음새 없이 배치 / 동일 제품·인물·의상·배경 아이덴티티 유지 / ${sourceRatio(S)}`;
  return { kr: krTxt, en: enTxt, count: n };
}

// 스토리보드 → 멀티샷 영상 (모든 씬을 하나의 영상으로)
export function buildStoryboardVideoPrompt(S) {
  const rows = timelineRows(S);
  const list = rows.length ? rows.map((r) => r.scene) : S.scenes;
  const n = Math.max(list.length, 1);
  const total = rows.length ? rows[rows.length - 1].end : list.reduce((a, sc) => a + (parseFloat(sc.duration) || 2), 0);
  const c = S.composer;
  const oneTake = (c.flow || "원테이크 연결") === "원테이크 연결";
  const defTrans = oneTake ? "Motion Match" : "AI Auto";
  const sceneLines = list.map((sc, i) => {
    const d = parseFloat(sc.duration) || 2;
    return `Scene ${i + 1} (${d}s, ${en(SCENE_ROLES, sc.role)}): ${sceneBriefEn(sc, S)}; camera: ${en(CAMERA_MOTIONS, sc.cameraMotion)}.`;
  }).join("\n");
  const transLines = list.slice(0, -1).map((sc, i) => `Scene ${i + 1} → Scene ${i + 2}: ${en(TRANSITIONS, c.transitions[i] || defTrans)}`).join("\n");
  const flowClause = oneTake
    ? `SEAMLESS ONE-TAKE FLOW — The finished video must feel like ONE continuously filmed take, not a sequence of separate clips. Carry the camera's momentum and the model's movement across every scene boundary: end each scene with a motion (a camera move, a turn of the body, a hand gesture, drifting steam or light) that flows directly into the opening motion of the next scene. Use motion-matched and camera-matched transitions instead of hard cuts. Lighting, color and energy keep flowing without any visible jump — a viewer should feel the camera traveled naturally from Scene 1 to Scene ${n} in a single filming session, with no abrupt scene change and no frozen moment between scenes.`
    : `CLEAN CUT EDITING — Separate the scenes with clean, confident cuts. Each cut lands exactly on the scene boundary; keep pacing crisp and readable.`;
  const placesUsed = [...new Set(list.map((sc) => scenePlace(sc, S)))].filter(Boolean);
  const roomClause = oneTake && placesUsed.length > 1
    ? `ROOM CHANGES — CRITICAL: The video moves between different rooms. A room change must NEVER look like a teleport or a hard cut. Every room change is motivated by the model physically walking: she turns and walks toward a doorway, the camera follows behind or beside her, and for a brief moment a foreground element (a doorframe, a wall edge, her shoulder) naturally fills and wipes the frame — during that moment of occlusion the new room is revealed as the camera clears the doorway. The walk, the occlusion wipe and the reveal happen as one continuous camera move.`
    : "";
  const enTxt = [
    `Using Higgsfield Seedance 2.0, create one naturally flowing video from the supplied storyboard image with realistic camera work and natural movement.`,
    `The storyboard contains ${n} panels. Recognize each panel as ONE independent scene and produce the video strictly in order: the video progresses naturally Scene 1 → Scene ${n}.`,
    `Preserve each scene's composition and directorial intent as much as possible. Never composite two panels into the same frame — at any moment the video shows the content of exactly one scene (a brief transitional camera move between scenes is allowed).`,
    flowClause,
    roomClause,
    `Product, person, background, color grading, lighting, and design stay perfectly consistent across all scenes. Never change or distort the original storyboard's composition and details.`,
    `Total length ${total.toFixed(1)} seconds, aspect ratio 9:16 vertical.`,
    sceneLines,
    transLines ? `Transitions:\n${transLines}` : "",
    productRefClause(S) + ` Preserve the product's shape, label, colors, and details exactly throughout every frame of the video.`,
    PACKAGE_PRESERVE_EN,
    VIDEO_NEG_EN
  ].filter(Boolean).join("\n\n");
  const krTxt = `멀티샷 영상 — 스토리보드 ${n}개 씬을 순서대로 하나의 ${total.toFixed(1)}초 영상으로 / ${oneTake ? "원테이크처럼 흐르듯 연결" : "씬별 클린 컷 편집"} / 패키지 원본 문구·로고 보존, 새 텍스트 생성 금지`;
  return { kr: krTxt, en: enTxt, duration: total, count: n };
}
