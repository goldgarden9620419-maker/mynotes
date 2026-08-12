# -*- coding: utf-8 -*-
"""원본 영상 메타데이터 분석."""
from utils import ffmpeg_utils, file_utils


def analyze(video_path: str) -> dict:
    """영상 길이/해상도/FPS/파일크기/오디오 유무를 반환."""
    info = ffmpeg_utils.media_info(video_path)
    info["summary"] = {
        "영상 길이": file_utils.human_duration(info["duration"]),
        "해상도": f'{info["width"]} x {info["height"]}',
        "FPS": f'{info["fps"]:.2f}',
        "파일 크기": file_utils.human_size(info["size_bytes"]),
        "오디오": "있음" if info["has_audio"] else "없음",
    }
    return info
