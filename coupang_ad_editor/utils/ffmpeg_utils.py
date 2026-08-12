# -*- coding: utf-8 -*-
"""FFmpeg / FFprobe 실행 유틸.

- PATH에 ffmpeg가 있으면 그대로 사용
- 없으면 static-ffmpeg 패키지가 자동 다운로드한 실행파일 사용
- Windows 한글 경로 대응: subprocess에 리스트 인자로 전달
"""
import json
import os
import shutil
import subprocess

_FFMPEG = None
_FFPROBE = None


class FFmpegError(RuntimeError):
    pass


def _find_binaries():
    """(ffmpeg, ffprobe) 실행 파일 경로를 찾는다."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    try:
        from static_ffmpeg import run as _sf_run
        ffmpeg2, ffprobe2 = _sf_run.get_or_fetch_platform_executables_else_raise()
        return ffmpeg or ffmpeg2, ffprobe or ffprobe2
    except Exception as exc:  # noqa: BLE001
        raise FFmpegError(
            "FFmpeg를 찾을 수 없습니다. install.bat을 다시 실행하거나 "
            "https://ffmpeg.org 에서 설치 후 PATH에 등록해주세요.\n"
            f"(원인: {exc})"
        )


def get_ffmpeg() -> str:
    global _FFMPEG, _FFPROBE
    if _FFMPEG is None:
        _FFMPEG, _FFPROBE = _find_binaries()
    return _FFMPEG


def get_ffprobe() -> str:
    global _FFMPEG, _FFPROBE
    if _FFPROBE is None:
        _FFMPEG, _FFPROBE = _find_binaries()
    return _FFPROBE


def run_cmd(args, desc="ffmpeg 작업"):
    """명령을 실행하고 실패 시 stderr 마지막 부분을 담아 예외를 던진다."""
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        args, capture_output=True, creationflags=creationflags
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        tail = "\n".join(err.strip().splitlines()[-25:])
        raise FFmpegError(f"{desc} 실패 (exit {proc.returncode}):\n{tail}")
    return proc


def probe(path: str) -> dict:
    """ffprobe JSON 결과 전체."""
    proc = run_cmd(
        [
            get_ffprobe(), "-v", "error",
            "-print_format", "json",
            "-show_format", "-show_streams",
            path,
        ],
        desc="영상 정보 분석(ffprobe)",
    )
    return json.loads(proc.stdout.decode("utf-8", errors="replace"))


def _parse_fps(rate: str) -> float:
    try:
        if "/" in rate:
            num, den = rate.split("/")
            den = float(den)
            return round(float(num) / den, 2) if den else 0.0
        return round(float(rate), 2)
    except (ValueError, ZeroDivisionError):
        return 0.0


def media_info(path: str) -> dict:
    """길이/해상도/FPS/파일크기/오디오 유무를 담은 dict."""
    data = probe(path)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or (video or {}).get("duration") or 0.0)
    return {
        "path": path,
        "duration": duration,
        "width": int((video or {}).get("width") or 0),
        "height": int((video or {}).get("height") or 0),
        "fps": _parse_fps((video or {}).get("avg_frame_rate") or "0/1"),
        "size_bytes": int(fmt.get("size") or os.path.getsize(path)),
        "has_audio": audio is not None,
        "video_codec": (video or {}).get("codec_name", ""),
        "audio_codec": (audio or {}).get("codec_name", ""),
    }


def filter_path(path: str) -> str:
    """filter_complex 내부(ass=, subtitles=)에서 쓸 수 있게 경로를 이스케이프."""
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:").replace("'", "\\'")
    return p


def extract_audio_wav(video_path: str, wav_path: str, sample_rate: int = 16000):
    """Whisper 입력용 16kHz 모노 WAV 추출."""
    run_cmd(
        [
            get_ffmpeg(), "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", str(sample_rate),
            "-c:a", "pcm_s16le", wav_path,
        ],
        desc="오디오 추출",
    )
