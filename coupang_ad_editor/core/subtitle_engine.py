# -*- coding: utf-8 -*-
"""자동 자막 + 강조 자막 (ASS / SRT).

- 음성 전체를 그대로 넣지 않고 짧은 청크(한 줄 8~16자, 최대 2줄)로 나눈다.
- Word Timestamp 기준으로 출력 타임라인에 정렬한다.
- 소구점/특징/혜택 키워드는 색·크기 강조(ASS 오버라이드 태그).
- 1080x1920 기준 Safe Zone(MarginV)을 지킨다.
"""
import re

from utils import config

# 강조 대상 일반 혜택 키워드
_BENEFIT_WORDS = ["간편", "편해", "편리", "저렴", "가성비", "튼튼", "빠르",
                  "쉽게", "한번에", "깔끔", "절약", "해결", "만족", "강력"]

_MAX_LINE = 16
_MIN_LINE = 8


def _ass_time(t: float) -> str:
    t = max(t, 0.0)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _srt_time(t: float) -> str:
    t = max(t, 0.0)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _emphasis_tokens(product: dict) -> list:
    tokens = list(_BENEFIT_WORDS)
    for key in ("selling_points", "features"):
        for part in re.split(r"[,\n·/;\s]+", product.get(key, "") or ""):
            part = part.strip()
            if len(part) >= 2 and part not in tokens:
                tokens.append(part)
    # 긴 토큰을 먼저 매칭
    return sorted(tokens, key=len, reverse=True)


def _apply_emphasis(text: str, tokens: list, scale: int) -> str:
    """강조 키워드에 ASS 오버라이드 태그(노란색·확대·볼드)를 감싼다."""
    tag_open = ("{\\c&H00E1FF&\\b1\\fscx%d\\fscy%d}" % (scale, scale))
    tag_close = "{\\r}"
    result = text
    for tok in tokens:
        if tok in result and tag_open not in result.split(tok)[0][-40:]:
            result = result.replace(tok, f"{tag_open}{tok}{tag_close}", 1)
    return result


def _chunk_clip(clip: dict) -> list:
    """클립의 단어들을 8~16자 청크로 나눈다.

    반환: [{"start": out_time, "end": out_time, "text": str}]
    """
    offset = clip["out_start"] - clip["src_start"]
    words = clip.get("words") or []
    chunks = []

    if not words:
        # 단어 타임스탬프가 없으면 문장 단위로 균등 분할
        text = clip["text"]
        parts = [text[i:i + _MAX_LINE] for i in range(0, len(text), _MAX_LINE)]
        dur = clip["out_end"] - clip["out_start"]
        step = dur / max(len(parts), 1)
        for i, part in enumerate(parts):
            chunks.append({
                "start": clip["out_start"] + i * step,
                "end": clip["out_start"] + (i + 1) * step,
                "text": part.strip(),
            })
        return [c for c in chunks if c["text"]]

    cur_words, cur_len = [], 0
    for w in words:
        token = w["word"].strip()
        if cur_words and cur_len + len(token) + 1 > _MAX_LINE:
            chunks.append({
                "start": cur_words[0]["start"] + offset,
                "end": cur_words[-1]["end"] + offset,
                "text": " ".join(x["word"] for x in cur_words),
            })
            cur_words, cur_len = [], 0
        cur_words.append(w)
        cur_len += len(token) + (1 if cur_len else 0)
    if cur_words:
        chunks.append({
            "start": cur_words[0]["start"] + offset,
            "end": cur_words[-1]["end"] + offset,
            "text": " ".join(x["word"] for x in cur_words),
        })

    # 너무 짧은 마지막 청크(<8자)는 앞 청크와 합치기 (2줄 허용)
    merged = []
    for c in chunks:
        if merged and len(c["text"]) < _MIN_LINE and \
                len(merged[-1]["text"]) + len(c["text"]) <= _MAX_LINE * 2:
            merged[-1]["text"] += "\\N" + c["text"]
            merged[-1]["end"] = c["end"]
        else:
            merged.append(dict(c))

    # 표시 최소 시간 보정 + 다음 청크 시작 전까지 유지
    for i, c in enumerate(merged):
        nxt = merged[i + 1]["start"] if i + 1 < len(merged) else clip["out_end"]
        c["end"] = max(min(nxt - 0.02, c["end"] + 0.35), c["start"] + 0.5)
    return merged


def build_subtitles(edl: dict, platform_cfg: dict, product: dict,
                    options: dict = None) -> dict:
    """EDL로부터 ASS와 SRT 텍스트를 생성한다.

    options:
      endcard_start / endcard_end: 엔드카드 구간(출력 타임라인)
      cta_text, show_price, show_discount
    반환: {"ass": str, "srt": str}
    """
    options = options or {}
    fontsize = platform_cfg["subtitle_fontsize"]
    margin_v = platform_cfg["subtitle_margin_v"]
    scale = platform_cfg["emphasis_scale"]
    font = config.SUBTITLE_FONT
    tokens = _emphasis_tokens(product)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {config.OUT_WIDTH}
PlayResY: {config.OUT_HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{fontsize},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,1,0,0,0,100,100,0,0,1,5,0,2,60,60,{margin_v},1
Style: Title,{font},{int(fontsize * 0.85)},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,1,0,0,0,100,100,0,0,1,4,0,8,60,60,220,1
Style: Big,{font},{int(fontsize * 1.35)},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,1,0,0,0,100,100,0,0,1,6,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    srt_items = []

    all_chunks = []
    product_shown = False
    for clip in edl["clips"]:
        chunks = _chunk_clip(clip)
        all_chunks.extend(chunks)

        # 제품명 노출: 첫 PRODUCT 컷과 CTA 컷에만 자연스럽게 표시
        name = (product.get("name") or "").strip()
        if name and clip["role"] == "PRODUCT" and not product_shown:
            events.append(
                f"Dialogue: 1,{_ass_time(clip['out_start'])},"
                f"{_ass_time(min(clip['out_end'], clip['out_start'] + 3.0))},"
                f"Title,,0,0,0,,{name}"
            )
            product_shown = True

    for chunk in all_chunks:
        text = _apply_emphasis(chunk["text"], tokens, scale)
        events.append(
            f"Dialogue: 0,{_ass_time(chunk['start'])},{_ass_time(chunk['end'])},"
            f"Default,,0,0,0,,{text}"
        )
        srt_items.append(chunk)

    # 엔드카드: 제품명 + CTA (+ 가격/할인 옵션)
    ec_start = options.get("endcard_start")
    ec_end = options.get("endcard_end")
    if ec_start is not None and ec_end is not None:
        name = (product.get("name") or "").strip()
        cta = (options.get("cta_text") or "제품 확인하기").strip()
        if name:
            events.append(
                f"Dialogue: 1,{_ass_time(ec_start)},{_ass_time(ec_end)},"
                f"Title,,0,0,0,,{name}"
            )
        events.append(
            f"Dialogue: 1,{_ass_time(ec_start)},{_ass_time(ec_end)},"
            f"Big,,0,0,0,,{{\\c&H00E1FF&}}{cta}"
        )
        price_lines = []
        if options.get("show_price") and (product.get("price") or "").strip():
            price_lines.append(product["price"].strip())
        if options.get("show_discount") and (product.get("discount") or "").strip():
            price_lines.append(product["discount"].strip())
        if price_lines:
            events.append(
                f"Dialogue: 1,{_ass_time(ec_start)},{_ass_time(ec_end)},"
                f"Default,,0,0,0,,{' / '.join(price_lines)}"
            )
        srt_items.append({"start": ec_start, "end": ec_end, "text": cta})

    ass_text = header + "\n".join(events) + "\n"

    srt_lines = []
    for i, item in enumerate(sorted(srt_items, key=lambda x: x["start"]), 1):
        text = item["text"].replace("\\N", "\n")
        srt_lines.append(
            f"{i}\n{_srt_time(item['start'])} --> {_srt_time(item['end'])}\n{text}\n"
        )
    return {"ass": ass_text, "srt": "\n".join(srt_lines)}
