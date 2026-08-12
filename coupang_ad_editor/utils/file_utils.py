# -*- coding: utf-8 -*-
"""파일/폴더 유틸. 한글 파일명과 Windows 경로를 안전하게 처리한다."""
import os
import re
import shutil
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ROOT = os.path.join(BASE_DIR, "output")


def sanitize_name(name: str, default: str = "project") -> str:
    """폴더명으로 안전한 문자열로 변환(한글 유지, 특수문자 제거)."""
    name = (name or "").strip()
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    name = name.strip("._")
    return name[:60] or default


def project_dirs(project_name: str) -> dict:
    """output/프로젝트명/ 하위 폴더 구조 생성 후 경로 dict 반환."""
    safe = sanitize_name(project_name)
    root = os.path.join(OUTPUT_ROOT, safe)
    dirs = {
        "root": root,
        "instagram": os.path.join(root, "instagram"),
        "tiktok": os.path.join(root, "tiktok"),
        "common": os.path.join(root, "common"),
        "work": os.path.join(root, "_work"),  # 임시 작업 폴더
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    return dirs


def save_uploaded(uploaded_file, dest_dir: str, prefix: str = "") -> str:
    """Streamlit UploadedFile을 디스크에 저장하고 경로 반환."""
    os.makedirs(dest_dir, exist_ok=True)
    name = sanitize_name(os.path.splitext(uploaded_file.name)[0], "file")
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    path = os.path.join(dest_dir, f"{prefix}{name}{ext}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def write_text(path: str, text: str, bom: bool = True):
    """텍스트 저장. 기본은 utf-8-sig(BOM) → Windows 메모장/플레이어 한글 호환."""
    encoding = "utf-8-sig" if bom else "utf-8"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(text)


def make_temp_dir(prefix: str = "cae_") -> str:
    return tempfile.mkdtemp(prefix=prefix)


def cleanup_dir(path: str):
    """임시 폴더 삭제(실패해도 무시)."""
    if path and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def human_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}분 {s}초" if m else f"{s}초"
