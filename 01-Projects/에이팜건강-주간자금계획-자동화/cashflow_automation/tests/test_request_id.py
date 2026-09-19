# -*- coding: utf-8 -*-
"""요청ID 생성·중복·변경·취소·미확정 처리 테스트 (35번 항목)."""
from datetime import date

from common import (
    REFLECT_CANCELLED, REFLECT_DUPLICATE, REFLECT_OK, REFLECT_UNCONFIRMED,
)
from request_id import (
    decide_reflect_status, is_valid_request_id, make_request_id,
    parse_request_id, select_latest,
)
from team_loader import build_integrated_plan
from tests.conftest import team_row


def test_요청id_정상_생성():
    assert make_request_id("경영", date(2026, 9, 18), 1) == "경영-20260918-001"
    assert make_request_id("물류", "2026-09-18", 2) == "물류-20260918-002"
    assert make_request_id("데이터", 20260918, 15) == "데이터-20260918-015"
    # 구성요소 누락 시 빈 값
    assert make_request_id("", date(2026, 9, 18), 1) == ""
    assert make_request_id("연구", None, 1) == ""
    assert make_request_id("연구", date(2026, 9, 18), 0) == ""


def test_요청id_해석과_검증():
    parsed = parse_request_id("건강-20260918-001")
    assert parsed["team_code"] == "건강"
    assert parsed["team_name"] == "건강사업팀"
    assert parsed["reg_date"] == date(2026, 9, 18)
    assert parsed["serial"] == 1
    assert is_valid_request_id("CS-20260918-003")
    assert not is_valid_request_id("CS-2026-003")
    assert not is_valid_request_id("아무거나")


def test_요청id_중복_발견():
    r1 = team_row("물류", "물류팀", 1, date(2026, 9, 18), date(2026, 9, 23),
                  "한진", "택배", 100000, modified=date(2026, 9, 18))
    r2 = team_row("물류", "물류팀", 1, date(2026, 9, 18), date(2026, 9, 24),
                  "한진", "택배", 150000, modified=date(2026, 9, 19))
    selected, duplicates = select_latest([dict(r1), dict(r2)])
    assert len(selected) == 1
    assert len(duplicates) == 1
    assert duplicates[0]["반영상태"] == REFLECT_DUPLICATE


def test_변경건_최신자료_선택():
    old = team_row("CS", "CS팀", 1, date(2026, 9, 18), date(2026, 9, 22),
                   "콜센터", "상담수수료", 300000,
                   progress="신규", modified=date(2026, 9, 18))
    new = team_row("CS", "CS팀", 1, date(2026, 9, 18), date(2026, 9, 25),
                   "콜센터", "상담수수료", 350000,
                   progress="변경", modified=date(2026, 9, 21))
    selected, duplicates = select_latest([dict(old), dict(new)])
    winner = selected[0]
    assert winner["예상금액"] == 350000
    assert winner["지급예정일"] == date(2026, 9, 25)
    # 이전 금액은 합산되지 않는다
    assert sum(r["예상금액"] for r in selected) == 350000


def test_최종수정일_같으면_파일수정일로_선택():
    a = dict(team_row("연구", "연구팀", 1, date(2026, 9, 18),
                      date(2026, 9, 22), "시약사", "시약", 100000),
             file_mtime=100.0)
    b = dict(team_row("연구", "연구팀", 1, date(2026, 9, 18),
                      date(2026, 9, 22), "시약사", "시약", 90000),
             file_mtime=200.0)
    selected, _ = select_latest([a, b])
    assert selected[0]["예상금액"] == 90000


def test_취소건_제외():
    row = team_row("디자인", "디자인팀", 1, date(2026, 9, 18),
                   date(2026, 9, 23), "인쇄소", "리플렛", 200000,
                   progress="취소")
    assert decide_reflect_status(row) == REFLECT_CANCELLED
    plan = build_integrated_plan([dict(row, 원본파일="f.xlsx",
                                       file_mtime=0, row_order=1,
                                       confidential=False,
                                       반영상태="", 확인사항="",
                                       대외비구분="")])
    assert plan["countable"] == []
    # 기록은 유지된다
    assert any(r["반영상태"] == REFLECT_CANCELLED for r in plan["integrated"])


def test_미확정건_제외():
    row = team_row("건강", "건강사업팀", 1, date(2026, 9, 18),
                   date(2026, 9, 23), "광고사", "광고비", 400000,
                   confirmed="미확정")
    assert decide_reflect_status(row) == REFLECT_UNCONFIRMED
    확정 = dict(row, 확정여부="확정")
    assert decide_reflect_status(확정) == REFLECT_OK
