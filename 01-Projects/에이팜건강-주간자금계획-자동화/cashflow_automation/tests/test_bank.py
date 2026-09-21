# -*- coding: utf-8 -*-
"""은행 거래 표준화·중복 제거·자동분류 테스트."""
from datetime import date, datetime

from bank_classifier import (
    CLASS_INTERNAL, CLASS_ONLINE_SALES, CLASS_REVIEW, DEFAULT_RULES,
    classify_rows,
)
from bank_loader import load_bank_file, summarize_balances
from common import BANK_REFLECT_DUPLICATE, BANK_REFLECT_OK, CONF_CAT_PAYROLL
from duplicate_checker import merge_with_history, remove_duplicates
from tests.conftest import kb_tx, nh_tx, write_bank_csv


def _tx(bank="농협", d=date(2026, 9, 15), dt=None, out_amt=0.0, in_amt=0.0,
        balance=1000000.0, desc="", memo="", src="a.csv", order=1) -> dict:
    return {"거래일시": dt, "거래일": d, "은행": bank, "계좌": "123",
            "출금액": out_amt, "입금액": in_amt, "거래후잔액": balance,
            "적요": desc, "기재내용·상대방": memo, "취급점": "",
            "자동분류": "", "내부이체": False, "정기지출후보": False,
            "현금유출입": in_amt - out_amt, "원본파일": src,
            "반영상태": BANK_REFLECT_OK, "row_order": order}


def test_은행파일_표준화(tmp_path):
    path = write_bank_csv(tmp_path / "농협.csv", "농협", [
        nh_tx(date(2026, 9, 15), "09:10:11", out_amt=300000,
              balance=52000000, desc="이체", memo="사무용품(주)"),
        nh_tx(date(2026, 9, 16), "10:00:00", in_amt=1000000,
              balance=53000000, desc="입금", memo="네이버페이"),
    ])
    rows, issues = load_bank_file(path, "농협")
    assert len(rows) == 2
    assert rows[0]["거래일"] == date(2026, 9, 15)
    assert rows[0]["거래일시"] == datetime(2026, 9, 15, 9, 10, 11)
    assert rows[0]["출금액"] == 300000
    assert rows[0]["거래후잔액"] == 52000000
    assert rows[1]["입금액"] == 1000000
    assert not issues


def test_은행거래_중복_제외():
    a = _tx(src="지난주.csv", dt=datetime(2026, 9, 15, 9, 0, 0))
    b = _tx(src="이번주.csv", dt=datetime(2026, 9, 15, 9, 0, 0), order=2)
    kept, dups = remove_duplicates([dict(a, 출금액=500000.0),
                                    dict(b, 출금액=500000.0)])
    assert len(kept) == 1
    assert len(dups) == 1
    assert dups[0]["반영상태"] == BANK_REFLECT_DUPLICATE
    assert dups[0]["현금유출입"] == 0


def test_거래일시가_다르면_중복이_아니다():
    a = _tx(dt=datetime(2026, 9, 15, 9, 0, 0), out_amt=100000.0)
    b = _tx(dt=datetime(2026, 9, 15, 15, 0, 0), out_amt=100000.0, order=2)
    kept, dups = remove_duplicates([a, b])
    assert len(kept) == 2
    assert not dups


def test_내부이체는_반대편_거래가_있어야_표시():
    w = dict(_tx(bank="우리은행", out_amt=5000000.0, memo="(주)에이팜건강"),
             계좌="220351")
    d = dict(_tx(bank="국민은행", in_amt=5000000.0, memo="에이팜건강"),
             계좌="169124")
    issues = classify_rows([w, d], DEFAULT_RULES)
    for row in (w, d):
        assert row["자동분류"] == CLASS_INTERNAL
        assert row["내부이체"] is True
        assert row["현금유출입"] == 0
    assert not issues


def test_회사명이_붙은_외부지급은_내부이체가_아니다():
    """네이버 광고비 충전 가상계좌는 계좌명에 광고주(회사)명이 붙는다.

    2026-09-21 실사용에서 발견: '국민네이버 apha'·'국민네이버 에이팜건'
    출금이 내부이체로 오분류되어 총 시작잔액이 계좌별 출발 잔액 합과
    2,508,000원 어긋났다. 반대편 입금이 우리 계좌에 없으면 외부 지급이다.
    """
    rows = [
        dict(_tx(bank="우리은행", out_amt=2178000.0,
                 memo="국민네이버 apha"), 계좌="220351"),
        dict(_tx(bank="우리은행", out_amt=330000.0,
                 memo="국민네이버 에이팜건"), 계좌="220351", order=2),
    ]
    classify_rows(rows, DEFAULT_RULES)
    for row in rows:
        assert row["내부이체"] is False
        assert row["자동분류"] != CLASS_INTERNAL
    assert rows[0]["현금유출입"] == -2178000.0


def test_이력의_잘못된_내부이체_표시를_짝_재판정으로_되돌린다():
    stale = dict(_tx(bank="우리은행", out_amt=330000.0,
                     memo="국민네이버 에이팜건"), 계좌="220351")
    stale["자동분류"] = CLASS_INTERNAL
    stale["내부이체"] = True
    stale["현금유출입"] = 0.0
    from bank_classifier import mark_internal_transfers
    mark_internal_transfers([stale], DEFAULT_RULES)
    assert stale["내부이체"] is False
    assert stale["자동분류"] == ""
    assert stale["현금유출입"] == -330000.0


def test_월말_TOP출금_급여_분류():
    row = _tx(bank="국민은행", d=date(2026, 9, 25), out_amt=10000000.0,
              desc="TOP출금")
    classify_rows([row], DEFAULT_RULES)
    assert row["자동분류"] == CONF_CAT_PAYROLL


def test_월말아닌_TOP출금_확인필요():
    row = _tx(bank="국민은행", d=date(2026, 9, 10), out_amt=3000000.0,
              desc="TOP출금")
    issues = classify_rows([row], DEFAULT_RULES)
    assert row["자동분류"] == CLASS_REVIEW
    assert issues and issues[0]["구분"] == "수동 대조 필요"


def test_키워드_자동분류():
    사회보험 = _tx(bank="우리은행", out_amt=450000.0, memo="사회보험료")
    카드 = _tx(bank="우리은행", out_amt=1100000.0, memo="우리카드결제대금")
    온라인 = _tx(bank="농협", in_amt=900000.0, memo="스마트스토어")
    classify_rows([사회보험, 카드, 온라인], DEFAULT_RULES)
    assert 사회보험["자동분류"] == "4대보험"
    assert 카드["자동분류"] == "우리카드 결제"
    assert 온라인["자동분류"] == CLASS_ONLINE_SALES


def test_잔액_요약():
    rows = [
        _tx(bank="농협", d=date(2026, 9, 15), balance=52000000.0),
        _tx(bank="농협", d=date(2026, 9, 16), balance=53000000.0, order=2),
        _tx(bank="국민은행", d=date(2026, 9, 16), balance=8900000.0),
    ]
    balances, total = summarize_balances(rows)
    assert balances[("농협", "123")] == 53000000
    assert total == 53000000 + 8900000


def test_이력_병합은_중복을_만들지_않는다():
    old = _tx(dt=datetime(2026, 9, 15, 9, 0, 0), out_amt=100000.0)
    new = dict(old)
    merged = merge_with_history([new], [old])
    assert len(merged) == 1
