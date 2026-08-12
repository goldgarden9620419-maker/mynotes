# -*- coding: utf-8 -*-
"""쿠팡 제품 광고 자동 제작 시스템 — Streamlit GUI.

원본 MP4 하나로 Instagram Reels / TikTok 광고 영상을 각각 자동 제작한다.
실행: streamlit run app.py  (또는 run.bat)
"""
import json
import os
import traceback

import streamlit as st

from core import (ad_analyzer, caption_generator, hook_analyzer,
                  instagram_editor, ng_detector, product_scraper,
                  tiktok_editor, transcription, video_analyzer)
from utils import config, file_utils

st.set_page_config(
    page_title="쿠팡 광고 자동 제작", page_icon="🎬", layout="wide")

VERSION_SUFFIX = ["A", "B", "C"]


# ---------------------------------------------------------------------------
# 세션 상태
# ---------------------------------------------------------------------------
def _init_state():
    defaults = {
        "analysis": None,       # 1단계(AI 분석) 결과
        "results": None,        # 2단계(렌더링) 결과
        "video_path": None,
        "video_key": None,
        "work_dir": None,
        "scraped_images": [],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


_init_state()


def _persist_upload(uploaded, subdir: str) -> str:
    """업로드 파일을 세션 작업 폴더에 저장."""
    if st.session_state["work_dir"] is None:
        st.session_state["work_dir"] = file_utils.make_temp_dir()
    dest = os.path.join(st.session_state["work_dir"], subdir)
    return file_utils.save_uploaded(uploaded, dest)


# ---------------------------------------------------------------------------
# 헤더 + 사용자 모드
# ---------------------------------------------------------------------------
st.title("🎬 쿠팡 제품 광고 자동 제작 시스템")
st.caption("원본 MP4 → AI 분석/NG 컷 → 광고 구조 재구성 → "
           "Instagram Reels + TikTok 광고 영상 자동 렌더링")

top1, top2, top3 = st.columns([1.2, 1, 1])
with top1:
    mode = st.radio(
        "제작 대상",
        ["Instagram + TikTok 모두 제작", "Instagram만 제작", "TikTok만 제작"],
        horizontal=False,
    )
with top2:
    style = st.selectbox("광고 스타일", config.AD_STYLES, index=0)
with top3:
    auto_mode = st.toggle("🤖 AI에게 전부 맡기기 (자동 모드)", value=True,
                          help="광고 스타일·Hook·소구점·길이·컷 템포·자막·Zoom·CTA를 AI가 자동 결정합니다.")
    ab_count = st.selectbox("A/B 테스트 버전 수", [1, 2, 3], index=0,
                            help="Hook을 다르게 한 버전을 여러 개 만듭니다. (A=1순위, B=2순위, C=3순위 Hook)")

platforms = []
if "Instagram" in mode and "TikTok" in mode:
    platforms = ["instagram", "tiktok"]
elif "Instagram" in mode:
    platforms = ["instagram"]
else:
    platforms = ["tiktok"]

st.divider()

# ---------------------------------------------------------------------------
# 1. 제품 정보 입력
# ---------------------------------------------------------------------------
st.header("1. 제품 정보")

# --- 쿠팡 URL 자동 채우기 (필드보다 위에 있어야 같은 실행에서 값이 반영됨) ---
u1, u2 = st.columns([3, 1])
with u1:
    st.text_input("쿠팡 상품 URL", key="p_url",
                  placeholder="https://www.coupang.com/vp/products/...")
with u2:
    st.write("")
    st.write("")
    fill_clicked = st.button("🔗 URL에서 자동 채우기", use_container_width=True)

if fill_clicked:
    url_value = (st.session_state.get("p_url") or "").strip()
    if not url_value:
        st.warning("먼저 쿠팡 상품 URL을 붙여넣어주세요.")
    else:
        if st.session_state["work_dir"] is None:
            st.session_state["work_dir"] = file_utils.make_temp_dir()
        with st.spinner("쿠팡에서 상품 정보를 가져오는 중..."):
            scraped = product_scraper.fetch_product_info(
                url_value,
                image_dir=os.path.join(st.session_state["work_dir"], "images"))
        if scraped["ok"]:
            if scraped["name"]:
                st.session_state["p_name"] = scraped["name"]
            if scraped["category"]:
                st.session_state["p_category"] = scraped["category"]
            if scraped["price"]:
                st.session_state["p_price"] = scraped["price"]
            if scraped["discount"]:
                st.session_state["p_discount"] = scraped["discount"]
            if scraped["image_path"] and \
                    scraped["image_path"] not in st.session_state["scraped_images"]:
                st.session_state["scraped_images"].append(scraped["image_path"])
            st.success(f'✅ {scraped["message"]} — 아래 칸을 확인하고 '
                       "특징/소구점 등은 직접 보완해주세요.")
        else:
            st.warning(f'⚠️ {scraped["message"]}')

c1, c2 = st.columns(2)
with c1:
    p_name = st.text_input("제품명 *", key="p_name",
                           placeholder="예: 접이식 미니 건조대")
    p_category = st.text_input("제품 카테고리", key="p_category",
                               placeholder="예: 생활/주방용품")
    p_features = st.text_area("제품 핵심 특징", height=90, key="p_features",
                              placeholder="쉼표 또는 줄바꿈으로 구분\n예: 원터치 접이식, 스테인리스 재질")
    p_selling = st.text_area("제품 핵심 소구점", height=90, key="p_selling",
                             placeholder="예: 좁은 공간 활용, 설치 3초, 가성비")
    p_target = st.text_input("타깃 고객", key="p_target",
                             placeholder="예: 자취생, 1인 가구")
with c2:
    p_price = st.text_input("제품 가격", key="p_price",
                            placeholder="예: 19,900원")
    p_discount = st.text_input("할인 정보", key="p_discount",
                               placeholder="예: 20% 할인 중")
    cta_choice = st.selectbox("CTA 문구", config.CTA_PRESETS + ["직접 입력"])
    cta_custom = ""
    if cta_choice == "직접 입력":
        cta_custom = st.text_input("CTA 직접 입력", placeholder="예: 지금 쿠팡에서 만나보세요")
p_url = st.session_state.get("p_url", "")

product = {
    "name": p_name, "category": p_category, "features": p_features,
    "selling_points": p_selling, "target": p_target, "price": p_price,
    "discount": p_discount,
    "cta": cta_custom if cta_choice == "직접 입력" else cta_choice,
    "url": p_url,
}

# ---------------------------------------------------------------------------
# 2. 제품 이미지 업로드
# ---------------------------------------------------------------------------
st.header("2. 제품 이미지")
image_files = st.file_uploader(
    "쿠팡 제품 사진 또는 직접 촬영 이미지 (여러 장 가능)",
    type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
image_paths = []
if image_files:
    cols = st.columns(min(len(image_files), 5))
    for i, img in enumerate(image_files):
        path = _persist_upload(img, "images")
        image_paths.append(path)
        with cols[i % len(cols)]:
            st.image(img, use_container_width=True)

# URL 자동 채우기로 받아온 쿠팡 대표 이미지
scraped_images = [p for p in st.session_state["scraped_images"]
                  if os.path.exists(p)]
if scraped_images:
    st.caption("🔗 쿠팡에서 자동으로 가져온 대표 이미지 (엔드카드에 사용됩니다)")
    cols = st.columns(min(len(scraped_images), 5))
    for i, path in enumerate(scraped_images):
        with cols[i % len(cols)]:
            st.image(path, use_container_width=True)
    image_paths.extend(scraped_images)

# ---------------------------------------------------------------------------
# 3. 원본 영상 업로드
# ---------------------------------------------------------------------------
st.header("3. 원본 영상 (MP4)")
video_file = st.file_uploader("촬영/제작한 원본 영상", type=["mp4"])
video_info = None
if video_file is not None:
    key = f"{video_file.name}-{video_file.size}"
    if st.session_state["video_key"] != key:
        st.session_state["video_path"] = _persist_upload(video_file, "video")
        st.session_state["video_key"] = key
        st.session_state["analysis"] = None
        st.session_state["results"] = None

    try:
        video_info = video_analyzer.analyze(st.session_state["video_path"])
        info_cols = st.columns(5)
        for col, (label, value) in zip(info_cols, video_info["summary"].items()):
            col.metric(label, value)
        if not video_info["has_audio"]:
            st.warning("⚠️ 이 영상에는 오디오가 없습니다. 음성 분석 없이 편집됩니다.")
        with st.expander("원본 영상 미리보기", expanded=False):
            st.video(video_file)
    except Exception as exc:  # noqa: BLE001
        st.error(f"영상 정보를 읽을 수 없습니다: {exc}")
        video_info = None

# ---------------------------------------------------------------------------
# 고급 모드 옵션
# ---------------------------------------------------------------------------
adv = {}
with st.expander("⚙️ 고급 모드 (직접 설정)", expanded=not auto_mode):
    a1, a2, a3 = st.columns(3)
    with a1:
        adv["use_duration"] = st.checkbox("영상 길이 직접 지정", value=False,
                                          disabled=auto_mode)
        adv["target_duration"] = st.slider("목표 길이(초)", 10, 60, 30,
                                           disabled=auto_mode or not adv["use_duration"])
        adv["cut_speed"] = st.select_slider("컷 속도", ["느리게", "보통", "빠르게"],
                                            value="보통", disabled=auto_mode)
        adv["subtitles_enabled"] = st.checkbox(
            "대사 자막 표시", value=True,
            help="음성 인식 오타가 거슬리면 끄세요. 직접 입력한 제품명/CTA/가격 자막은 유지됩니다.")
        adv["whisper_accuracy"] = st.select_slider(
            "음성 인식 정확도", ["표준(빠름)", "높음(느림)"], value="표준(빠름)",
            help="'높음'은 더 큰 AI 모델을 사용해 오타가 줄지만 분석이 몇 배 느려집니다. 최초 1회 모델 추가 다운로드(약 1.5GB).")
    with a2:
        adv["show_price"] = st.checkbox("가격 표시 ON", value=False)
        adv["show_discount"] = st.checkbox("할인율 표시 ON", value=False)
        adv["use_images"] = st.checkbox("제품 이미지 엔드카드 사용",
                                        value=bool(image_paths))
    with a3:
        adv["sfx_enabled"] = st.checkbox("효과음 사용 (Whoosh/Pop/Impact)",
                                         value=False)
        bgm_option = st.radio("BGM", ["BGM 없음", "BGM 직접 업로드"], horizontal=True)
        bgm_path = None
        if bgm_option == "BGM 직접 업로드":
            bgm_file = st.file_uploader("BGM (MP3)", type=["mp3"])
            if bgm_file is not None:
                bgm_path = _persist_upload(bgm_file, "bgm")
                st.caption("대사 구간에서는 자동으로 볼륨을 낮춥니다(덕킹). 음성이 항상 우선입니다.")

if auto_mode:
    adv["use_duration"] = False
    adv["cut_speed"] = "보통"
    adv["sfx_enabled"] = True
    adv["use_images"] = bool(image_paths)

st.divider()

# ---------------------------------------------------------------------------
# 4. 1단계: AI 분석
# ---------------------------------------------------------------------------
st.header("4. AI 분석")
analyze_disabled = video_info is None or not p_name.strip()
if analyze_disabled:
    st.info("제품명과 원본 영상을 먼저 입력/업로드해주세요.")

if st.button("🔍 1단계: AI 영상/음성 분석 시작", type="primary",
             disabled=analyze_disabled, use_container_width=True):
    try:
        with st.status("AI 분석 중...", expanded=True) as status:
            work_dir = st.session_state["work_dir"]
            video_path = st.session_state["video_path"]

            if video_info["has_audio"]:
                st.write("🎙️ Whisper 음성 → 텍스트 변환 중 (최초 실행 시 모델 다운로드)...")
                model_size = ("medium"
                              if adv.get("whisper_accuracy") == "높음(느림)"
                              else None)
                # 제품 정보를 힌트로 넣어 제품 용어 오인식을 줄인다
                hint = " ".join(
                    x.strip() for x in [product["name"], product["category"],
                                        product["features"],
                                        product["selling_points"]]
                    if x and x.strip())[:200]
                segments = transcription.transcribe(
                    video_path, work_dir,
                    model_size=model_size, initial_prompt=hint or None)
            else:
                segments = []

            st.write(f"✂️ NG/침묵/반복 발화 탐지 중... (발화 {len(segments)}개)")
            ng_result = ng_detector.detect(segments)

            st.write("📊 광고 관점 분석 (역할 분류 + 소구점)...")
            kept = ad_analyzer.classify(ng_result["kept"], product)
            selling_points = ad_analyzer.select_selling_points(product, kept)

            st.write("🪝 Hook 후보 선정 및 점수 평가...")
            hooks = hook_analyzer.score_candidates(kept, product, style)

            if not kept:
                status.update(label="분석 완료 (발화 없음)", state="error")
                st.error("사용할 수 있는 발화 구간이 없습니다. "
                         "오디오가 있는 영상인지 확인해주세요.")
            else:
                st.session_state["analysis"] = {
                    "video_path": video_path,
                    "video_info": video_info,
                    "segments_all": segments,
                    "ng_result": {k: v for k, v in ng_result.items()},
                    "kept": kept,
                    "selling_points": selling_points,
                    "hooks": hooks,
                    "style": style,
                }
                st.session_state["results"] = None
                status.update(label="✅ AI 분석 완료", state="complete")
    except Exception as exc:  # noqa: BLE001
        st.error(f"분석 중 오류가 발생했습니다: {exc}")
        st.code(traceback.format_exc())

analysis = st.session_state["analysis"]
selected_hook_idx = 0
if analysis:
    st.subheader("분석 결과")
    r1, r2, r3 = st.columns(3)
    r1.metric("유지된 발화", f'{len(analysis["kept"])}개')
    r2.metric("제거된 NG", f'{len(analysis["ng_result"]["removed"])}개')
    r3.metric("Hook 후보", f'{len(analysis["hooks"])}개')

    with st.expander("🪝 Hook 후보 및 점수 (100점 만점)", expanded=True):
        for i, hook in enumerate(analysis["hooks"]):
            score_text = " · ".join(
                f"{k.replace(' Score', '')} {v:.0f}"
                for k, v in hook["scores"].items())
            st.markdown(
                f'**{VERSION_SUFFIX[i] if i < 3 else i + 1}. '
                f'[{hook["label"]}] {hook["total"]:.0f}점** — “{hook["text"]}”')
            st.caption(score_text)
        if not auto_mode and len(analysis["hooks"]) > 1:
            selected_hook_idx = st.radio(
                "기본 Hook 선택 (A/B 버전은 이 순서 기준)",
                range(len(analysis["hooks"])),
                format_func=lambda i: f'{analysis["hooks"][i]["text"][:40]} '
                                      f'({analysis["hooks"][i]["total"]:.0f}점)',
            )

    if analysis["selling_points"]:
        with st.expander("💡 핵심 소구점 (최대 3개)"):
            for i, point in enumerate(analysis["selling_points"], 1):
                st.markdown(f"**소구점 {i}** — {point}")

    with st.expander("🗑️ 제거된 NG/불필요 구간"):
        for line in analysis["ng_result"]["log"]:
            st.text(line)

st.divider()

# ---------------------------------------------------------------------------
# 5. 2단계: 광고 영상 제작
# ---------------------------------------------------------------------------
st.header("5. 광고 영상 제작")

if st.button("🎬 2단계: Instagram / TikTok 광고 렌더링",
             type="primary", disabled=analysis is None,
             use_container_width=True):
    try:
        with st.status("광고 영상 제작 중...", expanded=True) as status:
            dirs = file_utils.project_dirs(p_name)
            kept = analysis["kept"]
            hooks = analysis["hooks"]
            selling_points = analysis["selling_points"]

            options = {
                "cut_speed": adv.get("cut_speed", "보통"),
                "show_price": adv.get("show_price", False),
                "show_discount": adv.get("show_discount", False),
                "subtitles_enabled": adv.get("subtitles_enabled", True),
                "sfx_enabled": adv.get("sfx_enabled", False),
                "bgm_path": bgm_path,
                "cta_text": product["cta"],
                "endcard_image": (image_paths[0]
                                  if adv.get("use_images") and image_paths
                                  else None),
            }
            if adv.get("use_duration"):
                options["target_duration"] = adv["target_duration"]

            versions = min(ab_count, len(hooks)) or 1
            hook_order = (list(range(len(hooks))) if auto_mode
                          else [selected_hook_idx] +
                          [i for i in range(len(hooks)) if i != selected_hook_idx])

            editors = {"instagram": instagram_editor, "tiktok": tiktok_editor}
            results = {"platforms": {}, "dirs": dirs}

            for platform in platforms:
                cfg = config.PLATFORMS[platform]
                out_dir = dirs[platform]
                results["platforms"][platform] = []
                for v in range(versions):
                    hook = hooks[hook_order[v % len(hook_order)]]
                    if versions > 1:
                        base, ext = os.path.splitext(cfg["filename"])
                        filename = f"{base}_{VERSION_SUFFIX[v]}{ext}"
                    else:
                        filename = cfg["filename"]
                    st.write(f'🎞️ {cfg["label"]} '
                             f'{"버전 " + VERSION_SUFFIX[v] if versions > 1 else ""} '
                             f'렌더링 중... (Hook: {hook["text"][:25]})')
                    built = editors[platform].build(
                        analysis["video_path"], kept, hook["segment"],
                        product, analysis["style"], options,
                        out_dir, dirs["work"],
                        has_audio=analysis["video_info"]["has_audio"],
                        out_filename=filename,
                    )
                    built["hook"] = hook
                    built["version"] = VERSION_SUFFIX[v] if versions > 1 else ""
                    results["platforms"][platform].append(built)

                # 플랫폼별 캡션/해시태그
                st.write(f'✍️ {cfg["label"]} 게시글 문구 작성 중...')
                best_hook_text = hooks[hook_order[0]]["text"]
                if platform == "instagram":
                    caption = caption_generator.instagram_caption(
                        product, selling_points, best_hook_text)
                    cap_path = os.path.join(out_dir, "instagram_caption.txt")
                else:
                    caption = caption_generator.tiktok_caption(
                        product, selling_points, best_hook_text)
                    cap_path = os.path.join(out_dir, "tiktok_caption.txt")
                file_utils.write_text(cap_path, caption)
                results["platforms"][platform + "_caption"] = caption

            # 공통 산출물 저장
            st.write("💾 분석 결과 저장 중 (transcript / analysis / EDL / 로그)...")
            common = dirs["common"]
            file_utils.write_text(
                os.path.join(common, "transcript.txt"),
                transcription.to_transcript_text(analysis["segments_all"]))

            analysis_json = {
                "product": product,
                "video_info": {k: v for k, v in analysis["video_info"].items()
                               if k != "summary"},
                "selling_points": selling_points,
                "hooks": [{"text": h["text"], "label": h["label"],
                           "total": h["total"], "scores": h["scores"]}
                          for h in hooks],
                "segments": [
                    {"start": s["start"], "end": s["end"], "text": s["text"],
                     "role": s.get("role"), "ad_score": s.get("ad_score")}
                    for s in kept],
                "removed_ng": [
                    {"start": s["start"], "end": s["end"], "text": s["text"],
                     "reason": s.get("ng_reason")}
                    for s in analysis["ng_result"]["removed"]],
                "summary": ad_analyzer.summarize(kept),
            }
            with open(os.path.join(common, "analysis.json"), "w",
                      encoding="utf-8") as f:
                json.dump(analysis_json, f, ensure_ascii=False, indent=2)

            edl_json = {
                platform: [b["edl"] for b in results["platforms"][platform]]
                for platform in platforms
            }
            with open(os.path.join(common, "edit_decisions.json"), "w",
                      encoding="utf-8") as f:
                json.dump(edl_json, f, ensure_ascii=False, indent=2)

            log_lines = list(analysis["ng_result"]["log"])
            for platform in platforms:
                for built in results["platforms"][platform]:
                    log_lines += built["edl"]["log"]
                    log_lines += built["edl"]["timeline"]
            file_utils.write_text(
                os.path.join(common, "editing_log.txt"), "\n".join(log_lines))

            # 임시 자막/효과음 파일 정리
            for name in os.listdir(dirs["work"]):
                try:
                    os.remove(os.path.join(dirs["work"], name))
                except OSError:
                    pass

            st.session_state["results"] = results
            status.update(label="✅ 광고 영상 제작 완료", state="complete")
    except Exception as exc:  # noqa: BLE001
        st.error(f"렌더링 중 오류가 발생했습니다: {exc}")
        st.code(traceback.format_exc())

# ---------------------------------------------------------------------------
# 6. 결과 화면
# ---------------------------------------------------------------------------
results = st.session_state["results"]
if results:
    st.header("6. 결과")
    st.success(f'출력 폴더: {results["dirs"]["root"]}')

    col_map = st.columns(len(platforms))
    for col, platform in zip(col_map, platforms):
        cfg = config.PLATFORMS[platform]
        with col:
            st.subheader(cfg["label"])
            for built in results["platforms"][platform]:
                label = f' (버전 {built["version"]})' if built["version"] else ""
                st.markdown(f'**Hook{label}:** “{built["hook"]["text"][:40]}”')
                st.video(built["mp4"])
                with open(built["mp4"], "rb") as f:
                    st.download_button(
                        f"⬇️ MP4 다운로드{label}",
                        f.read(),
                        file_name=os.path.basename(built["mp4"]),
                        mime="video/mp4",
                        key=f'dl_{platform}_{built["version"]}',
                        use_container_width=True,
                    )
            caption = results["platforms"].get(platform + "_caption", "")
            if caption:
                with st.expander(f"📝 {cfg['label']} 게시글 문구/해시태그"):
                    st.text(caption)
