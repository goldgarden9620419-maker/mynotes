# -*- coding: utf-8 -*-
"""백업·격리·임시폴더·지난자료 관리 (31번 항목)."""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


def backup_inputs(cfg, week_key: str,
                  input_files: list[Path]) -> Path | None:
    """실행 전 입력파일을 zip으로 백업한다."""
    backup_dir = cfg.folder("backup")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / f"입력백업_{week_key}_{stamp}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for path in input_files:
                path = Path(path)
                if path.exists():
                    z.write(path, arcname=f"{path.parent.name}/{path.name}")
        return zip_path
    except OSError:
        return None


def quarantine_file(cfg, path: Path, reason: str) -> Path | None:
    """손상파일을 06_확인필요/손상파일로 옮겨 격리한다."""
    path = Path(path)
    if not path.exists():
        return None
    target_dir = cfg.folder("review") / "손상파일"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = target_dir / f"{stamp}_{path.name}"
    try:
        shutil.move(str(path), str(target))
        (target_dir / f"{stamp}_{path.stem}_사유.txt").write_text(
            reason, encoding="utf-8")
        return target
    except OSError:
        return None


class TempWorkspace:
    """작업 중 임시폴더. 정상 완료 시에만 결과폴더로 옮긴다."""

    def __init__(self, cfg):
        self.output_dir = cfg.folder("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="._작업중_",
                                              dir=str(self.output_dir)))
        self.moved: list[Path] = []

    def path(self, filename: str) -> Path:
        return self.temp_dir / filename

    def commit(self, filenames: list[str], unique_fn) -> list[Path]:
        """임시폴더의 결과물을 결과폴더로 이동한다(덮어쓰기 금지)."""
        moved = []
        for name in filenames:
            src = self.temp_dir / name
            if not src.exists():
                continue
            dst = unique_fn(self.output_dir / name)
            shutil.move(str(src), str(dst))
            moved.append(dst)
        self.moved = moved
        self.cleanup()
        return moved

    def cleanup(self) -> None:
        """실패 시에도 호출: 임시파일 정리."""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except OSError:
            pass


_OUTPUT_PREFIXES = ("주간자금계획", "확인필요")


def _sweep_to_archive(src_dir, archive_dir, keep_names) -> int:
    """keep_names에 없는 결과 파일을 archive_dir로 옮긴다."""
    moved = 0
    if not src_dir.exists():
        return 0
    for path in src_dir.iterdir():
        if not path.is_file() or not path.name.startswith(_OUTPUT_PREFIXES):
            continue
        if path.name in keep_names:
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / path.name
        if target.exists():
            stamp = datetime.now().strftime("%H%M%S")
            target = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
        try:
            shutil.move(str(path), str(target))
            moved += 1
        except OSError:
            continue
    return moved


def archive_superseded_outputs(cfg, keep_output_names,
                               keep_review_names=()) -> int:
    """05_결과·06_확인필요에는 최신 실행 결과만 남긴다.

    이전 실행 파일은 지우지 않고 99_지난자료/지난결과로 이동한다
    (같은 주에 여러 번 실행해도 결과 폴더가 어지럽지 않도록).
    """
    archive_dir = cfg.folder("archive") / "지난결과"
    moved = _sweep_to_archive(cfg.folder("output"), archive_dir,
                              set(keep_output_names))
    moved += _sweep_to_archive(cfg.folder("review"), archive_dir,
                               set(keep_review_names))
    return moved


def archive_old_outputs(cfg, keep_days: int = 35) -> int:
    """오래된 결과물을 99_지난자료로 이동한다. 기존 결과물은 지우지 않는다."""
    output_dir = cfg.folder("output")
    archive_dir = cfg.folder("archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=keep_days)
    moved = 0
    if not output_dir.exists():
        return 0
    for path in output_dir.iterdir():
        if not path.is_file():
            continue
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                target = archive_dir / path.name
                if target.exists():
                    stamp = datetime.now().strftime("%H%M%S")
                    target = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
                shutil.move(str(path), str(target))
                moved += 1
        except OSError:
            continue
    return moved
