# -*- coding: utf-8 -*-
"""은행 파일 자동 분류 테스트 (2026-11-27 사용자 요청).

은행별 폴더에 나눠 넣기 번거로움 — 03_은행거래내역 한 폴더에 넣으면
파일명 → 파일 상단 문구 → 계좌번호(이력 대조) 순서로 은행을 판별해
제 폴더로 옮긴다. 판별 실패분은 그대로 두고 확인필요로 알린다.
"""
from openpyxl import Workbook

import bank_loader


class _Cfg:
    def __init__(self, root, state):
        self._root, self.state_dir = root, state

    def folder(self, key):
        assert key == "bank_root"
        return self._root

    def bank_dir(self, bank):
        return self._root / bank


def _cfg(tmp_path):
    root = tmp_path / "03_은행거래내역"
    root.mkdir()
    return _Cfg(root, tmp_path)


def _xlsx(path, rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def test_파일명으로_판별해_이동(tmp_path):
    cfg = _cfg(tmp_path)
    _xlsx(cfg._root / "국민4577_20261127.xlsx", [["x"]])
    _xlsx(cfg._root / "NH거래내역.xlsx", [["x"]])
    moved, issues = bank_loader.sort_loose_bank_files(cfg)
    assert sorted(moved) == [("NH거래내역.xlsx", "농협"),
                             ("국민4577_20261127.xlsx", "국민은행")]
    assert (cfg._root / "국민은행" / "국민4577_20261127.xlsx").exists()
    assert (cfg._root / "농협" / "NH거래내역.xlsx").exists()
    assert not issues


def test_상단_문구로_판별(tmp_path):
    cfg = _cfg(tmp_path)
    _xlsx(cfg._root / "거래내역조회.xlsx", [
        ["우리은행 거래내역조회", None, None],
        ["조회기간: 2026-11-21 ~ 2026-11-27"],
        ["거래일자", "출금액", "입금액", "잔액", "내용"],
        ["2026-11-24", 1000, 0, 5000, "점심"],
    ])
    moved, issues = bank_loader.sort_loose_bank_files(cfg)
    assert moved == [("거래내역조회.xlsx", "우리은행")]
    assert not issues


def test_계좌번호를_이력과_대조해_판별(tmp_path):
    cfg = _cfg(tmp_path)
    (tmp_path / "bank_history.csv").write_text(
        "거래일시,거래일,은행,계좌,출금액,입금액,거래후잔액,적요,"
        "기재내용·상대방,취급점,자동분류,내부이체,원본파일\n"
        ",2026-11-20,농협,1006-301-569003,0,1000,1000,이자,,,,False,x\n",
        encoding="utf-8-sig")
    _xlsx(cfg._root / "거래내역.xlsx", [
        ["계좌번호: 1006-301-569003"],
        ["거래일자", "출금액", "입금액", "잔액", "내용"],
        ["2026-11-24", 1000, 0, 5000, "점심"],
    ])
    moved, issues = bank_loader.sort_loose_bank_files(
        cfg, bank_loader._known_accounts(cfg))
    assert moved == [("거래내역.xlsx", "농협")]
    assert not issues


def test_판별_실패는_그대로_두고_알린다(tmp_path):
    cfg = _cfg(tmp_path)
    _xlsx(cfg._root / "모르는파일.xlsx", [["무언가"], ["내용 없음"]])
    moved, issues = bank_loader.sort_loose_bank_files(cfg)
    assert not moved
    assert (cfg._root / "모르는파일.xlsx").exists()
    assert issues and issues[0]["구분"] == "은행 구분 불가"
    assert "모르는파일" in issues[0]["내용"]


def test_같은_이름_있으면_번호_붙여_보존(tmp_path):
    cfg = _cfg(tmp_path)
    (cfg._root / "국민은행").mkdir()
    _xlsx(cfg._root / "국민은행" / "국민_1127.xlsx", [["기존"]])
    _xlsx(cfg._root / "국민_1127.xlsx", [["새것"]])
    moved, _ = bank_loader.sort_loose_bank_files(cfg)
    assert moved == [("국민_1127.xlsx", "국민은행")]
    assert (cfg._root / "국민은행" / "국민_1127_1.xlsx").exists()
