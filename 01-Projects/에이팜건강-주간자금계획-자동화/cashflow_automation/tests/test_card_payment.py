# -*- coding: utf-8 -*-
"""카드 결제일 계산 테스트.

회사 확정 기준: 국민카드 결제일 15일(이용기간 전월 2일~당월 1일),
우리카드·농협카드 결제일 23일(이용기간 전월 10일~당월 9일).
"""
from datetime import date

from card_payment import CardPaymentCalculator, parse_period_spec


def test_이용기간_해석():
    assert parse_period_spec("전월 13일") == (-1, 13)
    assert parse_period_spec("전월 말일") == (-1, None)
    assert parse_period_spec("당월 12일") == (0, 12)
    assert parse_period_spec("전전월 25일") == (-2, 25)
    assert parse_period_spec("이상한값") is None


def test_카드결제일_계산_국민카드():
    calc = CardPaymentCalculator()
    # 결제일 15일, 이용기간 전월 2일 ~ 당월 1일
    assert calc.settlement_date(date(2026, 9, 1), "국민카드") \
        == date(2026, 9, 15)   # 9/1 사용 → 9/15 결제 (8/2~9/1 구간)
    assert calc.settlement_date(date(2026, 9, 2), "국민카드") \
        == date(2026, 10, 15)  # 9/2 사용 → 10/15 결제 (9/2~10/1 구간)
    assert calc.settlement_date(date(2026, 9, 23), "국민카드") \
        == date(2026, 10, 15)


def test_카드결제일_계산_우리카드():
    calc = CardPaymentCalculator()
    # 결제일 23일, 이용기간 전월 10일 ~ 당월 9일
    assert calc.settlement_date(date(2026, 9, 9), "우리카드") \
        == date(2026, 9, 23)   # 9/9 사용 → 9/23 결제 (8/10~9/9 구간)
    assert calc.settlement_date(date(2026, 9, 10), "우리카드") \
        == date(2026, 10, 23)
    assert calc.settlement_date(date(2026, 9, 23), "우리카드") \
        == date(2026, 10, 23)


def test_카드결제일_계산_농협카드():
    calc = CardPaymentCalculator()
    assert calc.settlement_date(date(2026, 9, 23), "농협카드") \
        == date(2026, 10, 23)
    assert calc.settlement_date(date(2026, 8, 15), "농협카드") \
        == date(2026, 9, 23)


def test_카드결제일_계산불가():
    calc = CardPaymentCalculator()
    assert calc.settlement_date(date(2026, 9, 10), "미등록카드") is None
    assert calc.settlement_date(None, "국민카드") is None
    # 사용여부 '미사용' 카드는 계산하지 않는다
    calc2 = CardPaymentCalculator([
        {"카드구분": "국민카드", "카드사": "KB", "결제일": 15,
         "이용기간 시작일": "전월 2일", "이용기간 종료일": "당월 1일",
         "출금계좌": "", "사용여부": "미사용"}])
    assert calc2.settlement_date(date(2026, 9, 1), "국민카드") is None


def test_기준파일에서_카드기준_읽기(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from make_templates import create_base_workbook
    path = create_base_workbook(tmp_path / "기준.xlsx")
    calc = CardPaymentCalculator.from_workbook(path)
    assert calc.settlement_date(date(2026, 9, 1), "국민카드") \
        == date(2026, 9, 15)
    assert calc.settlement_date(date(2026, 9, 23), "농협카드") \
        == date(2026, 10, 23)
