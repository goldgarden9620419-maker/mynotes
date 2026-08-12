# -*- coding: utf-8 -*-
"""전역 설정값.

플랫폼별 렌더링/편집 파라미터, 광고 구조, 스타일 정의를 한 곳에 모은다.
환경변수로 Whisper 모델 크기 등을 바꿀 수 있다.
"""
import os

# ---------------------------------------------------------------------------
# Whisper (faster-whisper)
# ---------------------------------------------------------------------------
WHISPER_MODEL = os.environ.get("CAE_WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("CAE_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.environ.get("CAE_WHISPER_COMPUTE", "int8")
WHISPER_LANGUAGE = "ko"

# ---------------------------------------------------------------------------
# 공통 출력 사양
# ---------------------------------------------------------------------------
OUT_WIDTH = 1080
OUT_HEIGHT = 1920
OUT_FPS = 30
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
AUDIO_SAMPLE_RATE = 48000
CRF = "20"
PRESET = "medium"

# 한글 자막 기본 폰트 (Windows 기본 탑재)
SUBTITLE_FONT = os.environ.get("CAE_SUBTITLE_FONT", "Malgun Gothic")

# 엔드카드(제품 이미지 + CTA) 길이(초)
ENDCARD_DURATION = 2.5

# ---------------------------------------------------------------------------
# 플랫폼별 편집 파라미터
# ---------------------------------------------------------------------------
PLATFORMS = {
    "instagram": {
        "key": "instagram",
        "label": "Instagram Reels",
        "filename": "instagram_reels.mp4",
        "target_duration": 32.0,   # 목표 총 길이(초)
        "min_duration": 15.0,
        "clip_pad": 0.18,          # 컷 앞뒤 여유(초) — 자연스러운 호흡 유지
        "max_clip_len": 6.0,       # 한 컷 최대 길이
        "hook_max_len": 3.5,       # Hook 컷 최대 길이
        "zoom_threshold": 4.0,     # 이 길이 이상 컷에 미세 punch-in
        "subtitle_fontsize": 62,
        "subtitle_margin_v": 460,  # 하단 UI Safe Zone(px, 1920 기준)
        "emphasis_scale": 118,     # 강조 자막 확대 비율(%)
        "bgm_volume": 0.30,
        "tempo": "normal",
    },
    "tiktok": {
        "key": "tiktok",
        "label": "TikTok",
        "filename": "tiktok.mp4",
        "target_duration": 24.0,
        "min_duration": 10.0,
        "clip_pad": 0.08,          # 호흡 적극 제거 → 짧은 패딩
        "max_clip_len": 4.0,
        "hook_max_len": 2.2,       # 첫 1~2초 Hook을 더 강하게
        "zoom_threshold": 2.6,
        "subtitle_fontsize": 76,   # 큰 자막
        "subtitle_margin_v": 500,
        "emphasis_scale": 128,
        "bgm_volume": 0.35,
        "tempo": "fast",
    },
}

# ---------------------------------------------------------------------------
# 광고 구조 / 역할
# ---------------------------------------------------------------------------
ROLES = [
    "HOOK", "PROBLEM", "EMPATHY", "PRODUCT", "BENEFIT", "FEATURE",
    "PROOF", "DEMO", "OFFER", "CTA", "UNNECESSARY", "NG",
]

# 광고 재구성 시 역할 배치 순서 (HOOK 다음 ~ CTA 이전)
AD_STRUCTURE = ["PROBLEM", "EMPATHY", "PRODUCT", "FEATURE", "DEMO",
                "BENEFIT", "PROOF", "OFFER"]

# 역할별 최대 사용 컷 수
ROLE_CLIP_LIMITS = {
    "PROBLEM": 1, "EMPATHY": 1, "PRODUCT": 2, "FEATURE": 2,
    "DEMO": 2, "BENEFIT": 2, "PROOF": 1, "OFFER": 1,
}

# ---------------------------------------------------------------------------
# 광고 스타일
# ---------------------------------------------------------------------------
AD_STYLES = [
    "UGC 후기형",
    "문제 해결형",
    "제품 시연형",
    "정보 전달형",
    "감성형",
    "강한 퍼포먼스 광고형",
]

# 스타일별 Hook 점수 가중치 (없는 항목은 1.0)
STYLE_HOOK_WEIGHTS = {
    "UGC 후기형":        {"curiosity": 1.0, "problem": 1.0, "benefit": 1.1, "proof": 1.3},
    "문제 해결형":       {"problem": 1.5, "benefit": 1.2},
    "제품 시연형":       {"visual": 1.4, "benefit": 1.1},
    "정보 전달형":       {"curiosity": 1.2, "benefit": 1.1},
    "감성형":            {"curiosity": 1.1, "retention": 1.2},
    "강한 퍼포먼스 광고형": {"benefit": 1.3, "curiosity": 1.2, "problem": 1.2},
}

# 스타일별 템포 배율 (1.0보다 작으면 컷을 더 짧게)
STYLE_TEMPO = {
    "UGC 후기형": 1.0,
    "문제 해결형": 0.95,
    "제품 시연형": 1.0,
    "정보 전달형": 1.05,
    "감성형": 1.1,
    "강한 퍼포먼스 광고형": 0.85,
}

# ---------------------------------------------------------------------------
# CTA 프리셋
# ---------------------------------------------------------------------------
CTA_PRESETS = [
    "제품 확인하기",
    "프로필 링크에서 확인",
    "자세히 보기",
    "지금 확인해보세요",
    "쿠팡에서 확인",
]

# 허위/과장 광고 방지: 자동 생성 문구에서 금지되는 표현(사용자가 직접 입력한 경우는 제외)
BANNED_AUTO_PHRASES = [
    "오늘만", "마감 임박", "품절 임박", "단 하루", "최저가 보장",
    "100% 효과", "부작용 없음", "즉시 완치", "무조건",
]

# 효과음 종류
SFX_KINDS = ["Whoosh", "Pop", "Click", "Impact"]
