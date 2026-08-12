# -*- coding: utf-8 -*-
"""FFmpeg 렌더링 엔진.

EDL → 1080x1920 세로 영상 렌더링을 단일 filter_complex 그래프로 수행한다.
- 컷 트림/concat, 커버 스케일+센터 크롭, 미세 punch-in Zoom
- ASS 자막 번인 (한글 폰트)
- 엔드카드(제품 이미지 + CTA)
- 효과음(adelay + amix), BGM 루프 + sidechaincompress 덕킹(음성 최우선)
- H.264 / AAC / 30fps / faststart
"""
import os

from utils import config, ffmpeg_utils


def _afmt() -> str:
    return ("aresample=%d,aformat=sample_fmts=fltp:channel_layouts=stereo"
            % config.AUDIO_SAMPLE_RATE)


def _scale_crop(zoom: float) -> str:
    """커버 스케일 + 센터 크롭. zoom>1이면 미세 punch-in."""
    w = int(config.OUT_WIDTH * zoom) // 2 * 2
    h = int(config.OUT_HEIGHT * zoom) // 2 * 2
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={config.OUT_WIDTH}:{config.OUT_HEIGHT},"
            f"fps={config.OUT_FPS},setsar=1,format=yuv420p")


def render(source_path: str, edl: dict, ass_path: str, out_path: str,
           platform_cfg: dict, has_audio: bool = True,
           bgm_path: str = None, sfx_events: list = None,
           endcard_image: str = None, endcard_duration: float = None,
           progress_cb=None) -> str:
    """EDL을 최종 MP4로 렌더링한다."""
    sfx_events = sfx_events or []
    clips = edl["clips"]
    if not clips:
        raise ValueError("렌더링할 컷이 없습니다. 분석 결과를 확인해주세요.")

    inputs = ["-y", "-i", source_path]
    idx = 1

    endcard_idx = None
    if endcard_image:
        endcard_duration = endcard_duration or config.ENDCARD_DURATION
        inputs += ["-loop", "1", "-t", f"{endcard_duration:.2f}",
                   "-i", endcard_image]
        endcard_idx = idx
        idx += 1

    sfx_idx = []
    for ev in sfx_events:
        inputs += ["-i", ev["path"]]
        sfx_idx.append(idx)
        idx += 1

    bgm_idx = None
    if bgm_path:
        inputs += ["-stream_loop", "-1", "-i", bgm_path]
        bgm_idx = idx
        idx += 1

    parts = []
    concat_refs = []

    # --- 컷별 트림 ---
    for i, clip in enumerate(clips):
        a, b = clip["src_start"], clip["src_end"]
        parts.append(
            f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,"
            f"{_scale_crop(clip['zoom'])}[v{i}]"
        )
        if has_audio:
            parts.append(
                f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,"
                f"{_afmt()}[a{i}]"
            )
        else:
            dur = b - a
            parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate="
                f"{config.AUDIO_SAMPLE_RATE},atrim=0:{dur:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )
        concat_refs.append(f"[v{i}][a{i}]")

    # --- 엔드카드 ---
    if endcard_idx is not None:
        parts.append(
            f"[{endcard_idx}:v]scale={config.OUT_WIDTH}:{config.OUT_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={config.OUT_WIDTH}:{config.OUT_HEIGHT}:"
            f"(ow-iw)/2:(oh-ih)/2:color=0x101010,"
            f"fps={config.OUT_FPS},setsar=1,format=yuv420p[vend]"
        )
        parts.append(
            f"anullsrc=channel_layout=stereo:sample_rate="
            f"{config.AUDIO_SAMPLE_RATE},atrim=0:{endcard_duration:.3f},"
            f"asetpts=PTS-STARTPTS[aend]"
        )
        concat_refs.append("[vend][aend]")

    n = len(concat_refs)
    parts.append("".join(concat_refs) + f"concat=n={n}:v=1:a=1[vcat][acat]")

    # --- 자막 번인 ---
    ass_escaped = ffmpeg_utils.filter_path(ass_path)
    parts.append(f"[vcat]ass='{ass_escaped}'[vsub]")

    # --- 효과음 믹스 ---
    audio_label = "[acat]"
    if sfx_idx:
        mix_refs = [audio_label]
        for j, in_idx in enumerate(sfx_idx):
            delay_ms = max(int(sfx_events[j]["time"] * 1000), 0)
            parts.append(
                f"[{in_idx}:a]adelay={delay_ms}:all=1,{_afmt()},"
                f"volume=0.55[sfx{j}]"
            )
            mix_refs.append(f"[sfx{j}]")
        parts.append(
            "".join(mix_refs) +
            f"amix=inputs={len(mix_refs)}:duration=first:"
            f"dropout_transition=0:normalize=0[amix]"
        )
        audio_label = "[amix]"

    # --- BGM + 덕킹 (음성 최우선) ---
    if bgm_idx is not None:
        vol = platform_cfg.get("bgm_volume", 0.3)
        parts.append(f"{audio_label}asplit=2[voice][sc]")
        parts.append(f"[{bgm_idx}:a]{_afmt()},volume={vol}[bgraw]")
        parts.append(
            "[bgraw][sc]sidechaincompress=threshold=0.05:ratio=10:"
            "attack=20:release=400[bduck]"
        )
        parts.append(
            "[voice][bduck]amix=inputs=2:duration=first:"
            "dropout_transition=0:normalize=0[afin]"
        )
        audio_label = "[afin]"

    filter_complex = ";".join(parts)

    cmd = [ffmpeg_utils.get_ffmpeg()] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[vsub]", "-map", audio_label,
        "-c:v", config.VIDEO_CODEC, "-preset", config.PRESET,
        "-crf", config.CRF, "-pix_fmt", "yuv420p",
        "-c:a", config.AUDIO_CODEC, "-b:a", config.AUDIO_BITRATE,
        "-ar", str(config.AUDIO_SAMPLE_RATE),
        "-movflags", "+faststart",
        "-shortest",
        out_path,
    ]

    if progress_cb:
        progress_cb(0.1)
    ffmpeg_utils.run_cmd(cmd, desc=f'{platform_cfg["label"]} 렌더링')
    if progress_cb:
        progress_cb(1.0)

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise RuntimeError(f"렌더링 결과 파일이 비정상입니다: {out_path}")
    return out_path
