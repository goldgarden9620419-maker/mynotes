# -*- coding: utf-8 -*-
"""CapCut(PC) 연동 내보내기.

AI 분석으로 만든 EDL(컷 목록)을 CapCut 프로젝트 초안(draft)으로 변환해
CapCut의 드래프트 폴더에 넣는다. CapCut을 열면 컷 편집이 끝난 타임라인이
프로젝트 목록에 나타나고, 자막/효과/BGM은 CapCut에서 마무리한다.

주의: CapCut 드래프트 포맷은 버전에 따라 달라질 수 있어(최신 버전은 암호화)
실험적 기능이다. 실패해도 클린 컷 MP4 + SRT 패키지는 항상 생성되므로
CapCut에 직접 불러와 편집하면 된다.
"""
import json
import os
import shutil
import time
import uuid


def _uid() -> str:
    return str(uuid.uuid4()).upper()


def _us(seconds: float) -> int:
    """초 → 마이크로초(µs)."""
    return int(round(seconds * 1_000_000))


def find_draft_root() -> str:
    """CapCut/剪映 PC의 드래프트 폴더를 찾는다. 없으면 None."""
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "CapCut", "User Data", "Projects",
                     "com.lveditor.draft"),
        os.path.join(local, "JianyingPro", "User Data", "Projects",
                     "com.lveditor.draft"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def _latest_template(root: str, exclude: str = None):
    """드래프트 루트에서 복제 템플릿으로 쓸 최신 드래프트 폴더를 찾는다."""
    best, best_mtime = None, -1
    try:
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if not os.path.isdir(full) or name == exclude:
                continue
            if not os.path.exists(os.path.join(full, "draft_content.json")):
                continue
            mtime = os.path.getmtime(full)
            if mtime > best_mtime:
                best, best_mtime = full, mtime
    except OSError:
        pass
    return best


def build_draft_content(video_path: str, video_info: dict, edl: dict) -> dict:
    """EDL → CapCut draft_content.json 딕셔너리."""
    width = int(video_info.get("width") or 1080)
    height = int(video_info.get("height") or 1920)
    src_duration_us = _us(float(video_info.get("duration") or 0.0))
    total_us = _us(edl["total_duration"])
    video_material_id = _uid()

    abs_path = os.path.abspath(video_path).replace("\\", "/")

    video_material = {
        "aigc_type": "none", "audio_fade": None, "cartoon_path": "",
        "category_id": "", "category_name": "local", "check_flag": 63487,
        "crop": {"lower_left_x": 0.0, "lower_left_y": 1.0,
                 "lower_right_x": 1.0, "lower_right_y": 1.0,
                 "upper_left_x": 0.0, "upper_left_y": 0.0,
                 "upper_right_x": 1.0, "upper_right_y": 0.0},
        "crop_ratio": "free", "crop_scale": 1.0,
        "duration": src_duration_us,
        "extra_type_option": 0, "formula_id": "", "freeze": None,
        "has_audio": bool(video_info.get("has_audio", True)),
        "height": height, "id": video_material_id,
        "intensifies_audio_path": "", "intensifies_path": "",
        "is_ai_generate_content": False, "is_copyright": False,
        "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
        "local_id": "", "local_material_id": "", "material_id": "",
        "material_name": os.path.basename(video_path), "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False,
                    "has_use_quick_eraser": False, "interactiveTime": [],
                    "path": "", "strokes": []},
        "media_path": "", "object_locked": None, "origin_material_id": "",
        "path": abs_path, "picture_from": "none",
        "picture_set_category_id": "", "picture_set_category_name": "",
        "request_id": "", "reverse_intensifies_path": "", "reverse_path": "",
        "smart_motion": None, "source": 0, "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0,
                   "time_range": {"duration": 0, "start": 0}},
        "team_id": "", "type": "video",
        "video_algorithm": {"algorithms": [], "complement_frame_config": None,
                            "deflicker": None, "gameplay_configs": [],
                            "motion_blur_config": None,
                            "noise_reduction": None, "path": "",
                            "quality_enhance": None, "time_range": None},
        "width": width,
    }

    speeds, canvases, sound_maps, segments = [], [], [], []
    for i, clip in enumerate(edl["clips"]):
        dur_us = _us(clip["src_end"] - clip["src_start"])
        speed_id, canvas_id, map_id = _uid(), _uid(), _uid()
        speeds.append({"curve_speed": None, "id": speed_id, "mode": 0,
                       "speed": 1.0, "type": "speed"})
        canvases.append({"album_image": "", "blur": 0.0, "color": "",
                         "id": canvas_id, "image": "", "image_id": "",
                         "image_name": "", "source_platform": 0,
                         "team_id": "", "type": "canvas_color"})
        sound_maps.append({"audio_channel_mapping": 0, "id": map_id,
                           "is_config_open": False, "type": ""})
        segments.append({
            "caption_info": None, "cartoon": False,
            "clip": {"alpha": 1.0,
                     "flip": {"horizontal": False, "vertical": False},
                     "rotation": 0.0, "scale": {"x": 1.0, "y": 1.0},
                     "transform": {"x": 0.0, "y": 0.0}},
            "common_keyframes": [], "enable_adjust": True,
            "enable_color_curves": True, "enable_color_match_adjust": False,
            "enable_color_wheels": True, "enable_lut": True,
            "enable_smart_color_adjust": False,
            "extra_material_refs": [speed_id, canvas_id, map_id],
            "group_id": "",
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
            "id": _uid(), "intensifies_audio": False,
            "is_placeholder": False, "is_tone_modify": False,
            "keyframe_refs": [], "last_nonzero_volume": 1.0,
            "material_id": video_material_id, "render_index": 0,
            "responsive_layout": {"enable": False, "horizontal_pos_layout": 0,
                                  "size_layout": 0, "target_follow": "",
                                  "vertical_pos_layout": 0},
            "reverse": False,
            "source_timerange": {"duration": dur_us,
                                 "start": _us(clip["src_start"])},
            "speed": 1.0,
            "target_timerange": {"duration": dur_us,
                                 "start": _us(clip["out_start"])},
            "template_id": "", "template_scene": "default",
            "track_attribute": 0, "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0},
            "visible": True, "volume": 1.0,
        })

    empty_material_lists = [
        "audio_balances", "audio_effects", "audio_fades", "audios", "beats",
        "chromas", "color_curves", "digital_humans", "drafts", "effects",
        "flowers", "green_screens", "handwrites", "hsl", "images",
        "log_color_wheels", "loudnesses", "manual_deformations", "masks",
        "material_animations", "material_colors", "multi_language_refs",
        "placeholders", "plugin_effects", "primary_color_wheels",
        "realtime_denoises", "shapes", "smart_crops", "smart_relights",
        "stickers", "tail_leaders", "text_templates", "texts", "time_marks",
        "transitions", "video_effects", "video_trackings",
        "vocal_beautifys", "vocal_separations",
    ]
    materials = {key: [] for key in empty_material_lists}
    materials.update({
        "canvases": canvases,
        "sound_channel_mappings": sound_maps,
        "speeds": speeds,
        "videos": [video_material],
    })

    now_us = int(time.time() * 1_000_000)
    return {
        "canvas_config": {"height": 1920, "ratio": "original", "width": 1080},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1, "attachment_info": [],
            "combination_max_index": 1, "export_range": None,
            "extract_audio_last_index": 1, "lyrics_recognition_id": "",
            "lyrics_sync": True, "lyrics_taskinfo": [],
            "maintrack_adsorb": True, "material_save_mode": 0,
            "original_sound_last_index": 1, "record_audio_last_index": 1,
            "sticker_max_index": 1, "subtitle_recognition_id": "",
            "subtitle_sync": True, "subtitle_taskinfo": [],
            "system_font_list": [], "video_mute": False,
            "zoom_info_params": None,
        },
        "cover": None, "create_time": now_us, "duration": total_us,
        "extra_info": None, "fps": 30.0,
        "free_render_index_mode_on": False, "group_container": None,
        "id": _uid(),
        "keyframe_graph_list": [],
        "keyframes": {"adjusts": [], "audios": [], "effects": [],
                      "filters": [], "handwrites": [], "stickers": [],
                      "texts": [], "videos": []},
        "last_modified_platform": {
            "app_id": 359289, "app_source": "cc", "app_version": "4.5.0",
            "device_id": "", "hard_disk_id": "", "mac_address": "",
            "os": "windows", "os_version": "10.0",
        },
        "materials": materials,
        "mutable_config": None, "name": "", "new_version": "110.0.0",
        "platform": {
            "app_id": 359289, "app_source": "cc", "app_version": "4.5.0",
            "device_id": "", "hard_disk_id": "", "mac_address": "",
            "os": "windows", "os_version": "10.0",
        },
        "relationships": [], "render_index_track_mode_on": True,
        "retouch_cover": None, "source": "default",
        "static_cover_image_path": "", "time_marks": None,
        "tracks": [{
            "attribute": 0, "flag": 0, "id": _uid(),
            "is_default_name": True, "name": "",
            "segments": segments, "type": "video",
        }],
        "update_time": now_us, "version": 360000,
    }


def _patch_meta(draft_dir: str, draft_name: str, total_us: int, root: str):
    """복제한 템플릿의 draft_meta_info.json을 새 이름/경로로 갱신 (best-effort)."""
    meta_path = os.path.join(draft_dir, "draft_meta_info.json")
    if not os.path.exists(meta_path):
        return
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        updates = {
            "draft_name": draft_name,
            "draft_fold_path": draft_dir.replace("\\", "/"),
            "draft_root_path": root.replace("\\", "/"),
            "draft_id": _uid(),
            "tm_duration": total_us,
            "tm_draft_modified": int(time.time() * 1_000_000),
        }
        for key, value in updates.items():
            if key in meta:
                meta[key] = value
        # 견본(템플릿)에서 딸려온 미디어 목록 제거 — 이게 남아 있으면
        # CapCut이 프로젝트를 열 때 '미디어 연결(파일을 찾을 수 없음)'
        # 창을 띄운다. 우리 타임라인은 source.mp4만 쓰므로 비워도 안전.
        if "draft_materials" in meta:
            if isinstance(meta["draft_materials"], list):
                for group in meta["draft_materials"]:
                    if isinstance(group, dict) and isinstance(
                            group.get("value"), list):
                        group["value"] = []
            else:
                meta["draft_materials"] = []
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
    except (OSError, ValueError):
        pass


def export_draft(video_path: str, video_info: dict, edl: dict,
                 draft_name: str, fallback_dir: str) -> dict:
    """CapCut 드래프트 생성.

    반환: {"ok": bool, "installed": bool, "path": str, "message": str}
    installed=True면 CapCut 드래프트 폴더에 직접 설치됨.
    """
    content = build_draft_content(video_path, video_info, edl)
    total_us = content["duration"]
    root = find_draft_root()

    if root:
        target = os.path.join(root, draft_name)
        n = 2
        while os.path.exists(target):
            target = os.path.join(root, f"{draft_name}_{n}")
            n += 1
        template = _latest_template(root)
        try:
            if template:
                shutil.copytree(template, target)
                # 템플릿의 콘텐츠/커버는 제거하고 우리 것으로 교체
                for extra in ("draft_cover.jpg", "draft_cover.png"):
                    extra_path = os.path.join(target, extra)
                    if os.path.exists(extra_path):
                        os.remove(extra_path)
            else:
                os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "draft_content.json"), "w",
                      encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False)
            _patch_meta(target, os.path.basename(target), total_us, root)
            return {
                "ok": True, "installed": True, "path": target,
                "message": (f'CapCut 프로젝트 "{os.path.basename(target)}" 생성 완료! '
                            "CapCut을 열면 프로젝트 목록에 나타납니다. "
                            "(안 보이면 CapCut 재시작 → 그래도 없으면 아래 "
                            "클린 컷 MP4를 CapCut으로 불러오세요)"),
            }
        except OSError as exc:
            pass  # 아래 fallback으로 진행

    # CapCut 미설치 또는 실패 → output 폴더에 저장
    os.makedirs(fallback_dir, exist_ok=True)
    target = os.path.join(fallback_dir, draft_name)
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "draft_content.json"), "w",
              encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False)
    return {
        "ok": True, "installed": False, "path": target,
        "message": ("CapCut 드래프트 폴더를 찾지 못해 output 폴더에 저장했습니다. "
                    "CapCut(PC버전)이 설치되어 있다면 이 폴더를 "
                    "내 문서가 아닌 CapCut 드래프트 폴더로 복사하거나, "
                    "아래 클린 컷 MP4를 CapCut으로 불러와 편집하세요."),
    }
