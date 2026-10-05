# -*- coding: utf-8 -*-
"""지난자료는 '옮긴 시점'부터 보관 기간을 센다.

shutil.move는 수정시각을 유지하므로, 오래된 파일이 지난자료로 옮겨지자마자
같은 실행의 purge_old_archive에서 삭제되던 버그(2026-10-05 재현)를 막는다.
"""
import os
import time
from datetime import date
from pathlib import Path

import backup_manager as bm


class _Cfg:
    def __init__(self, root: Path):
        self.root = root

    def folder(self, key: str) -> Path:
        return self.root / key

    def bank_dir(self, bank: str) -> Path:
        return self.root / "bank" / bank


def _old_file(path: Path, days: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    old = time.time() - days * 86400
    os.utime(path, (old, old))
    return path


def test_오래된_결과물은_옮긴_직후_삭제되지_않는다(tmp_path):
    cfg = _Cfg(tmp_path)
    _old_file(tmp_path / "output" / "주간자금계획_old.xlsx", 40)
    assert bm.archive_old_outputs(cfg) == 1
    assert bm.purge_old_archive(cfg, 14) == 0
    assert (tmp_path / "archive" / "주간자금계획_old.xlsx").exists()


def test_대체된_결과물도_옮긴_시점부터_보관한다(tmp_path):
    cfg = _Cfg(tmp_path)
    _old_file(tmp_path / "output" / "주간자금계획_이전.xlsx", 20)
    (tmp_path / "review").mkdir()
    assert bm.archive_superseded_outputs(cfg, set(), set()) == 1
    assert bm.purge_old_archive(cfg, 14) == 0
    assert (tmp_path / "archive" / "지난결과" / "주간자금계획_이전.xlsx").exists()


def test_보관기간이_지난_지난자료는_삭제한다(tmp_path):
    cfg = _Cfg(tmp_path)
    _old_file(tmp_path / "archive" / "지난결과" / "아주오래된.xlsx", 15)
    assert bm.purge_old_archive(cfg, 14) == 1


def test_대체된_은행파일도_옮긴_시점부터_보관한다(tmp_path):
    cfg = _Cfg(tmp_path)
    _old_file(tmp_path / "bank" / "국민" / "국민_0901.xls", 30)
    _old_file(tmp_path / "bank" / "국민" / "국민_0930.xls", 1)
    rows = [{"원본파일": "국민_0901.xls", "은행": "국민", "계좌": "0001",
             "거래일": date(2026, 9, 1)},
            {"원본파일": "국민_0930.xls", "은행": "국민", "계좌": "0001",
             "거래일": date(2026, 9, 30)}]
    assert bm.archive_superseded_bank_files(cfg, rows) == 1
    assert bm.purge_old_archive(cfg, 14) == 0
    assert (tmp_path / "archive" / "지난입력파일" / "국민"
            / "국민_0901.xls").exists()


def test_수정시각_갱신이_실패해도_이동은_성공으로_센다(tmp_path, monkeypatch):
    cfg = _Cfg(tmp_path)
    _old_file(tmp_path / "output" / "주간자금계획_old.xlsx", 40)

    def _fail(*a, **k):
        raise PermissionError("읽기 전용")
    monkeypatch.setattr(bm.os, "utime", _fail)
    assert bm.archive_old_outputs(cfg) == 1
    assert (tmp_path / "archive" / "주간자금계획_old.xlsx").exists()
