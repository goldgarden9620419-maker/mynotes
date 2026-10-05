# -*- coding: utf-8 -*-
"""테스트 실행 중 결과 파일(Excel)이 실제로 열리지 않아야 한다.

conftest의 autouse fixture(_no_auto_open)를 지키는 테스트다 —
fixture가 빠지면 실제 _open_file이 os.startfile을 불러 실패한다.
"""
import os

import app


def test_테스트중에는_파일을_열지_않는다(monkeypatch, tmp_path):
    opened = []
    monkeypatch.setattr(os, "startfile", opened.append, raising=False)
    app._open_file(tmp_path / "확인필요.xlsx")
    assert opened == []
