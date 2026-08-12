# -*- coding: utf-8 -*-
"""TikTok 편집 전략.

Instagram과 동일 원본이라도 별도 EDL로 편집한다:
- 첫 1~2초 Hook을 더 강하게(짧게 치고 들어감)
- 빠른 컷 전환, 호흡 적극 제거(짧은 패딩)
- 큰 자막, 핵심 단어 강조, 짧고 명확한 CTA
"""
import os

from core import audio_engine, edit_planner, render_engine, subtitle_engine
from utils import config, file_utils


def build(source_path: str, segments: list, hook_seg: dict, product: dict,
          style: str, options: dict, out_dir: str, work_dir: str,
          has_audio: bool = True, out_filename: str = None,
          progress_cb=None) -> dict:
    """TikTok MP4 + SRT 생성. 반환: {"mp4", "srt", "edl"}"""
    cfg = config.PLATFORMS["tiktok"]

    # TikTok은 컷 속도를 한 단계 빠르게 (사용자가 명시하지 않았다면)
    tt_options = dict(options)
    if tt_options.get("cut_speed", "보통") == "보통":
        tt_options["cut_speed"] = "빠르게"

    edl = edit_planner.build_edl(segments, hook_seg, cfg, style, tt_options)

    endcard_image = tt_options.get("endcard_image")
    endcard_start = endcard_end = None
    if endcard_image:
        endcard_start = edl["total_duration"]
        endcard_end = endcard_start + config.ENDCARD_DURATION

    # 짧고 명확한 CTA
    cta_text = (tt_options.get("cta_text") or "쿠팡에서 확인").strip()
    if len(cta_text) > 12:
        cta_text = cta_text[:12]

    subs = subtitle_engine.build_subtitles(
        edl, cfg, product,
        {
            "endcard_start": endcard_start,
            "endcard_end": endcard_end,
            "cta_text": cta_text,
            "show_price": tt_options.get("show_price", False),
            "show_discount": tt_options.get("show_discount", False),
        },
    )
    ass_path = os.path.join(work_dir, "tiktok.ass")
    file_utils.write_text(ass_path, subs["ass"])

    srt_path = os.path.join(out_dir, "tiktok_subtitle.srt")
    file_utils.write_text(srt_path, subs["srt"])

    sfx_events = audio_engine.plan_sfx(
        edl, tt_options.get("sfx_enabled", False), work_dir, endcard_start)

    mp4_path = os.path.join(out_dir, out_filename or cfg["filename"])
    render_engine.render(
        source_path, edl, ass_path, mp4_path, cfg,
        has_audio=has_audio,
        bgm_path=tt_options.get("bgm_path"),
        sfx_events=sfx_events,
        endcard_image=endcard_image,
        progress_cb=progress_cb,
    )
    return {"mp4": mp4_path, "srt": srt_path, "edl": edl}
