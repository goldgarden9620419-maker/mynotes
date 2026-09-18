# -*- coding: utf-8 -*-
"""카드 결제일 계산 테스트."""
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
    # 국민카드: 결제일 25일, 이용기간 전월 13일 ~ 당월 12일
    assert calc.settlement_date(date(2026, 9, 10), "국민카드") \
        == date(2026, 9, 25)
    assert calc.settlement_date(date(2026, 9, 23), "국민카드") \
        == date(2026, 10, 25)


def test_카드결제일_계산_우리카드_말일_경계():
    calc = CardPaymentCalculator()
    # 우리카드: 결제일 15일, 이용기간 전월 1일 ~ 전월 말일
    assert calc.settlement_date(date(2026, 8, 31), "우리카드") \
        == date(2026, 9, 15)
    assert calc.settlement_date(date(2026, 9, 1), "우리카드") \
        == date(2026, 10, 15)


def test_카드결제일_계산불가():
    calc = CardPaymentCalculator()
    assert calc.settlement_date(date(2026, 9, 10), "미등록카드") is None
    assert calc.settlement_date(None, "국민카드") is None
    # 사용여부 '미사용' 카드는 계산하지 않는다
    calc2 = CardPaymentCalculator([
        {"카드구분": "국민카드", "카드사": "KB", "결제일": 25,
         "이용기간 시작일": "전월 13일", "이용기간 종료일": "당월 12일",
         "출금계좌": "", "사용여부": "미사용"}])
    assert calc2.settlement_date(date(2026, 9, 10), "국민카드") is None


def test_기준파일에서_카드기준_읽기(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from make_templates import create_base_workbook
    path = create_base_workbook(tmp_path / "기준.xlsx")
    calc = CardPaymentCalculator.from_workbook(path)
    assert calc.settlement_date(date(2026, 9, 10), "국민카드") \
        == date(2026, 9, 25)
