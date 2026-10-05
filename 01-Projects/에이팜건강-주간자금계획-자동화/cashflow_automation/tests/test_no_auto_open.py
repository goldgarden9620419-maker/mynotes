# -*- coding: utf-8 -*-
"""테스트 실행 중 결과 파일(Excel)이 실제로 열리지 않아야 한다.

conftest의 autouse fixture(_no_auto_open)를 지키는 테스트다 —
fixture가 빠지면 진짜 os.startfile이 남아 있어 실패한다.
"""
import os


def test_테스트중에는_파일을_열지_않는다():
    assert getattr(os.startfile, "__name__", "") == "_no_startfile"
