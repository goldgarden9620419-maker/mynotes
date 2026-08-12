# -*- coding: utf-8 -*-
"""오디오: 효과음 합성 + BGM/덕킹 계획.

효과음은 외부 에셋 없이 numpy로 직접 합성한다(Whoosh/Pop/Click/Impact).
BGM 덕킹은 render_engine에서 ffmpeg sidechaincompress로 처리하며,
여기서는 효과음 이벤트 배치만 계획한다. 음성이 항상 최우선이다.
"""
import os
import wave

import numpy as np

SAMPLE_RATE = 48000


def _write_wav(path: str, samples: np.ndarray):
    data = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(data)


def synth_sfx(kind: str, path: str) -> str:
    """간단한 효과음을 합성해 WAV로 저장한다."""
    sr = SAMPLE_RATE
    rng = np.random.default_rng(7)
    kind = kind.lower()

    if kind == "whoosh":
        n = int(0.45 * sr)
        t = np.linspace(0, 1, n)
        noise = rng.standard_normal(n)
        sig = np.convolve(noise, np.ones(32) / 32, mode="same")
        sig *= np.sin(np.pi * t) ** 2 * 0.5
    elif kind == "pop":
        n = int(0.14 * sr)
        t = np.linspace(0, 0.14, n)
        freq = 600 - 350 * (t / 0.14)
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 30) * 0.7
    elif kind == "click":
        n = int(0.04 * sr)
        sig = rng.standard_normal(n) * np.exp(-np.linspace(0, 10, n)) * 0.5
    elif kind == "impact":
        n = int(0.4 * sr)
        t = np.linspace(0, 0.4, n)
        sig = (np.sin(2 * np.pi * 75 * t) * 0.8 +
               rng.standard_normal(n) * 0.15) * np.exp(-t * 8)
    else:
        raise ValueError(f"알 수 없는 효과음: {kind}")

    _write_wav(path, sig)
    return path


def plan_sfx(edl: dict, enabled: bool, work_dir: str,
             endcard_start: float = None) -> list:
    """효과음 이벤트 계획.

    Hook 시작(Whoosh), 첫 제품 등장(Pop), 엔드카드/CTA(Impact)에만
    절제해서 사용한다. 반환: [{"time": float, "path": str}]
    """
    if not enabled:
        return []
    os.makedirs(work_dir, exist_ok=True)
    events = []

    whoosh = synth_sfx("whoosh", os.path.join(work_dir, "sfx_whoosh.wav"))
    pop = synth_sfx("pop", os.path.join(work_dir, "sfx_pop.wav"))
    impact = synth_sfx("impact", os.path.join(work_dir, "sfx_impact.wav"))

    clips = edl["clips"]
    if clips:
        events.append({"time": max(clips[0]["out_start"], 0.0), "path": whoosh})
    for clip in clips:
        if clip["role"] == "PRODUCT":
            events.append({"time": clip["out_start"], "path": pop})
            break
    if endcard_start is not None:
        events.append({"time": endcard_start, "path": impact})
    return events
