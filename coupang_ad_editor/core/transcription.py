# -*- coding: utf-8 -*-
"""faster-whisper 기반 한국어 음성 → 텍스트 변환 (Word Timestamp 포함)."""
import os

from utils import config, ffmpeg_utils

_MODELS = {}


def _load_model(size: str = None):
    size = size or config.WHISPER_MODEL
    if size not in _MODELS:
        from faster_whisper import WhisperModel
        _MODELS[size] = WhisperModel(
            size,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
    return _MODELS[size]


def transcribe(video_path: str, work_dir: str, progress_cb=None,
               model_size: str = None, initial_prompt: str = None) -> list:
    """영상에서 음성을 추출해 전사한다.

    model_size: None이면 기본(small). "medium"이면 느리지만 더 정확.
    initial_prompt: 제품명/특징 등 힌트 텍스트 — 제품 용어 오인식을 줄인다.
    반환: [{"start": float, "end": float, "text": str,
            "words": [{"start": float, "end": float, "word": str}]}]
    """
    wav_path = os.path.join(work_dir, "whisper_input.wav")
    ffmpeg_utils.extract_audio_wav(video_path, wav_path)

    model = _load_model(model_size)
    segments_iter, info = model.transcribe(
        wav_path,
        language=config.WHISPER_LANGUAGE,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5,
        initial_prompt=(initial_prompt or None),
    )

    total = getattr(info, "duration", 0.0) or 0.0
    results = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        words = []
        for w in (seg.words or []):
            token = (w.word or "").strip()
            if token:
                words.append(
                    {"start": round(w.start, 3), "end": round(w.end, 3),
                     "word": token}
                )
        results.append(
            {"start": round(seg.start, 3), "end": round(seg.end, 3),
             "text": text, "words": words}
        )
        if progress_cb and total:
            progress_cb(min(seg.end / total, 1.0))

    try:
        os.remove(wav_path)
    except OSError:
        pass
    return results


def to_transcript_text(segments: list) -> str:
    """common/transcript.txt 용 전체 대본."""
    lines = []
    for seg in segments:
        lines.append(f'[{seg["start"]:7.2f} ~ {seg["end"]:7.2f}] {seg["text"]}')
    return "\n".join(lines) + "\n"
