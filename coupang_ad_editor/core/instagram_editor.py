# -*- coding: utf-8 -*-
"""Instagram Reels 편집 전략.

- 깔끔한 화면, 지나치게 빠르지 않은 컷, 읽기 쉬운 자막
- Safe Zone 고려, 자연스러운 BGM, UGC 스타일 유지
"""
import os

from core import audio_engine, edit_planner, render_engine, subtitle_engine
from utils import config, file_utils


def build(source_path: str, segments: list, hook_seg: dict, product: dict,
          style: str, options: dict, out_dir: str, work_dir: str,
          has_audio: bool = True, out_filename: str = None,
          progress_cb=None) -> dict:
    """Instagram Reels MP4 + SRT 생성. 반환: {"mp4", "srt", "edl"}"""
    cfg = config.PLATFORMS["instagram"]
    edl = edit_planner.build_edl(segments, hook_seg, cfg, style, options)

    endcard_image = options.get("endcard_image")
    endcard_start = endcard_end = None
    if endcard_image:
        endcard_start = edl["total_duration"]
        endcard_end = endcard_start + config.ENDCARD_DURATION

    subs = subtitle_engine.build_subtitles(
        edl, cfg, product,
        {
            "endcard_start": endcard_start,
            "endcard_end": endcard_end,
            "cta_text": options.get("cta_text"),
            "show_price": options.get("show_price", False),
            "show_discount": options.get("show_discount", False),
            "subtitles_enabled": options.get("subtitles_enabled", True),
        },
    )
    ass_path = os.path.join(work_dir, "instagram.ass")
    file_utils.write_text(ass_path, subs["ass"])

    srt_path = os.path.join(out_dir, "instagram_subtitle.srt")
    file_utils.write_text(srt_path, subs["srt"])

    sfx_events = audio_engine.plan_sfx(
        edl, options.get("sfx_enabled", False), work_dir, endcard_start)

    mp4_path = os.path.join(out_dir, out_filename or cfg["filename"])
    render_engine.render(
        source_path, edl, ass_path, mp4_path, cfg,
        has_audio=has_audio,
        bgm_path=options.get("bgm_path"),
        sfx_events=sfx_events,
        endcard_image=endcard_image,
        progress_cb=progress_cb,
    )
    return {"mp4": mp4_path, "srt": srt_path, "edl": edl}
