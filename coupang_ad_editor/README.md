# 🎬 쿠팡 제품 광고 자동 제작 시스템

쿠팡 제품 홍보용 원본 MP4 하나를 넣으면 AI가 자동으로 분석·편집해서
**Instagram Reels용**과 **TikTok용** 광고 영상을 **각각 별도의 편집 전략으로**
만들어주는 GUI 프로그램입니다. 코딩을 몰라도 사용할 수 있습니다.

## 주요 기능

- **Whisper(faster-whisper) 한국어 음성 인식** — Word Timestamp 활용
- **NG 자동 제거** — 침묵 / 버벅임 / 반복 촬영 / "다시 할게요" 등 자동 탐지
- **광고 관점 분석** — 발화를 HOOK / PROBLEM / PRODUCT / BENEFIT / CTA 등으로 분류
- **광고 구조 재구성** — 좋은 장면이 뒤에 있어도 앞으로 이동 (Hook → 문제 → 제품 → 장점 → CTA)
- **Hook 후보 3개+ 자동 선정** — Curiosity / Problem / Benefit / Retention 등 100점 평가
- **자동 자막 + 강조 자막** — ASS 기반, 한 줄 8~16자, 핵심 키워드 색/크기 강조, Safe Zone 준수
- **BGM 업로드 + 자동 덕킹** — 대사가 있을 때 BGM 볼륨 자동 감소 (음성 최우선)
- **효과음** — Whoosh / Pop / Impact 자동 합성 (ON/OFF)
- **자동 Zoom** — 긴 컷에 100→105→110% 미세 punch-in
- **플랫폼별 별도 편집** — TikTok은 더 강한 Hook·빠른 컷·큰 자막
- **게시글 문구 + 해시태그** — 플랫폼 성격에 맞게 각각 생성
- **A/B 테스트** — Hook을 다르게 한 A/B/C 버전 제작
- **허위 광고 방지** — 입력하지 않은 효능/가격/할인 정보는 생성하지 않음

## 설치 (Windows)

1. [Python 3.11+](https://www.python.org/downloads/) 설치
   (설치 시 **"Add python.exe to PATH"** 체크 필수)
2. `install.bat` 더블클릭 → 자동으로 가상환경 + 라이브러리 설치
3. FFmpeg는 최초 실행 시 자동 다운로드됩니다 (별도 설치 불필요)

## 실행

`run.bat` 더블클릭 → 브라우저에서 GUI가 열립니다.

## 사용 순서

1. 제작 대상 선택 (Instagram + TikTok / Instagram만 / TikTok만)
2. 광고 스타일 선택 또는 **"AI에게 전부 맡기기"** ON
3. 제품 정보 입력 (제품명 필수)
4. 제품 이미지 업로드 (JPG/PNG/WEBP, 여러 장 가능 — 엔드카드에 사용)
5. 원본 MP4 업로드 → 길이/해상도/FPS/크기/오디오 자동 표시
6. **1단계: AI 분석** — 음성 인식, NG 제거, Hook 후보/소구점 확인
7. **2단계: 렌더링** — 플랫폼별 MP4 생성
8. 결과 화면에서 미리보기 + MP4 다운로드

## 출력 구조

```
output/
    제품명/
        instagram/
            instagram_reels.mp4
            instagram_caption.txt
            instagram_subtitle.srt
        tiktok/
            tiktok.mp4
            tiktok_caption.txt
            tiktok_subtitle.srt
        common/
            transcript.txt
            edit_decisions.json
            analysis.json
            editing_log.txt
```

## 출력 사양

- 1080x1920 (9:16), H.264 + AAC, 30fps, faststart
- Instagram: 목표 ~32초, 자연스러운 컷, 읽기 쉬운 자막
- TikTok: 목표 ~24초, 첫 1~2초 강한 Hook, 빠른 컷, 큰 자막

## 자주 묻는 질문

**Q. Whisper 모델이 너무 느려요/무거워요**
환경변수 `CAE_WHISPER_MODEL`을 `base` 또는 `tiny`로 설정하면 빨라집니다.
GPU(CUDA)가 있다면 `CAE_WHISPER_DEVICE=cuda`로 설정하세요.

**Q. 한글 자막 폰트를 바꾸고 싶어요**
환경변수 `CAE_SUBTITLE_FONT`에 설치된 폰트 이름을 지정하세요
(기본: Malgun Gothic).

**Q. 오디오 없는 영상도 되나요?**
됩니다. 다만 음성 분석 기반 편집(NG 제거, 자막)은 건너뜁니다.

## 프로젝트 구조

```
coupang_ad_editor/
    app.py                  # Streamlit GUI
    core/
        video_analyzer.py   # 영상 메타데이터 분석
        transcription.py    # faster-whisper 음성 인식
        ng_detector.py      # NG/침묵/반복 탐지
        ad_analyzer.py      # 광고 관점 역할 분류 + 소구점
        hook_analyzer.py    # Hook 후보 선정/점수
        edit_planner.py     # 광고 구조 재구성(EDL)
        instagram_editor.py # Instagram 편집 전략
        tiktok_editor.py    # TikTok 편집 전략
        subtitle_engine.py  # ASS/SRT 자막 + 강조
        audio_engine.py     # 효과음 합성 + 오디오 계획
        render_engine.py    # FFmpeg 렌더링
        caption_generator.py# 게시글 문구/해시태그
    utils/
        ffmpeg_utils.py
        config.py
        file_utils.py
    output/
    requirements.txt
    install.bat
    run.bat
```
