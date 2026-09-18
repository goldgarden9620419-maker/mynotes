# -*- coding: utf-8 -*-
"""입금 예측·4주 일별·13주 주별 계획 테스트."""
from datetime import date, timedelta

from bank_classifier import CLASS_ONLINE_SALES
from common import PAY_METHOD_TRANSFER
from forecast_engine import (
    STATE_OK, STATE_SHORTAGE, analyze_recurring, build_daily_plan,
    build_forecast, build_weekly_plan, weekday_online_averages,
)

BASE = date(2026, 9, 21)  # 월요일


def _online_history(weeks: int = 12, daily_amount: float = 1000000.0):
    """매주 월~금 동일 금액이 입금된 이력."""
    rows = []
    for w in range(1, weeks + 1):
        monday = BASE - timedelta(weeks=w)
        for i in range(5):  # 월~금
            d = monday + timedelta(days=i)
            rows.append({"거래일": d, "거래일시": None, "은행": "농협",
                         "계좌": "1", "입금액": daily_amount, "출금액": 0.0,
                         "거래후잔액": None, "적요": "입금",
                         "기재내용·상대방": "네이버페이",
                         "자동분류": CLASS_ONLINE_SALES, "내부이체": False,
                         "현금유출입": daily_amount, "원본파일": "h",
                         "반영상태": "정상반영", "row_order": 0})
    return rows


def _plan(due: date, amount: float, method=PAY_METHOD_TRANSFER) -> dict:
    return {"자금계획 반영일": due, "지급예정일": due, "예상금액": amount,
            "지급방법": method, "반영상태": "정상반영"}


def test_요일별_평균():
    avg = weekday_online_averages(_online_history(), BASE)
    assert round(avg[0]) == 1000000  # 월요일 (가중 평균, 균일 데이터면 동일)
    assert round(avg[4]) == 1000000  # 금요일
    assert avg[5] == 0               # 토요일


def test_4주_잔액_계산():
    avg = {i: (1000000.0 if i < 5 else 0.0) for i in range(7)}
    plans = [_plan(BASE + timedelta(days=2), 500000.0)]
    daily = build_daily_plan(plans, BASE, opening_balance=10000000.0,
                             weekday_avg=avg, rate=0.8, adjustments=[])
    assert len(daily) == 28
    # 1일차(월): 기초 1000만 + 입금 80만 = 1080만
    assert daily[0]["기초잔액"] == 10000000
    assert daily[0]["온라인 예상입금"] == 800000
    assert daily[0]["기말잔액"] == 10800000
    # 3일차(수): 지출 50만 반영
    assert daily[2]["팀별 송금예정"] == 500000
    assert daily[2]["기말잔액"] == daily[1]["기말잔액"] + 800000 - 500000
    # 잔액 연결성: 다음 날 기초 = 전날 기말
    for prev, cur in zip(daily, daily[1:]):
        assert cur["기초잔액"] == prev["기말잔액"]
    assert all(r["상태"] == STATE_OK for r in daily)


def test_자금부족_표시():
    avg = {i: 0.0 for i in range(7)}
    plans = [_plan(BASE + timedelta(days=1), 2000000.0)]
    daily = build_daily_plan(plans, BASE, opening_balance=1000000.0,
                             weekday_avg=avg, rate=0.8, adjustments=[])
    assert daily[1]["기말잔액"] == -1000000
    assert daily[1]["상태"] == STATE_SHORTAGE


def test_13주_잔액_계산():
    avg = {i: (1000000.0 if i < 5 else 0.0) for i in range(7)}
    plans = [_plan(BASE + timedelta(days=2), 500000.0),
             _plan(BASE + timedelta(weeks=6), 700000.0)]  # 7주차
    daily = build_daily_plan(plans, BASE, opening_balance=10000000.0,
                             weekday_avg=avg, rate=0.8, adjustments=[])
    weekly = build_weekly_plan(plans, BASE, daily, avg, 0.8, [], [])
    assert len(weekly) == 13
    # 1주차: 입금 5일*80만=400만, 지출 50만
    assert weekly[0]["예상입금"] == 4000000
    assert weekly[0]["송금예정"] == 500000
    # 1~4주는 일별 합산과 일치
    assert weekly[3]["기말잔액"] == daily[-1]["기말잔액"]
    # 7주차에 미래 지출 반영
    assert weekly[6]["송금예정"] == 700000
    # 주별 잔액 연결성
    closing = weekly[0]["기말잔액"]
    for w in weekly[1:]:
        assert abs((closing + w["순현금흐름"]) - w["기말잔액"]) < 1
        closing = w["기말잔액"]


def test_입금_반영률_변경():
    history = _online_history()
    result = build_forecast([], BASE, 10000000.0, history, [], [],
                            rates=[0.6, 0.7, 0.8, 0.9, 1.0],
                            default_rate=0.8)
    scenarios = result["rate_scenarios"]
    assert set(scenarios) == {0.6, 0.7, 0.8, 0.9, 1.0}
    # 반영률이 높을수록 입금·기말잔액이 커진다
    assert scenarios[0.6]["4주 온라인입금"] < scenarios[1.0]["4주 온라인입금"]
    assert scenarios[0.6]["4주 기말잔액"] < scenarios[1.0]["4주 기말잔액"]
    assert scenarios[0.6]["13주 기말잔액"] < scenarios[1.0]["13주 기말잔액"]
    # 80%: 4주 20영업일 * 100만 * 0.8 = 1600만
    assert abs(scenarios[0.8]["4주 온라인입금"] - 16000000) < 1
    assert result["scenario"]["안내"]


def test_정기지출_분석():
    rows = []
    for m in range(1, 7):  # 3~8월 매월 25일 출금
        d = date(2026, 3, 25) + timedelta(days=0)
        d = date(2026, 2 + m, 25)
        rows.append({"거래일": d, "거래일시": None, "은행": "우리은행",
                     "계좌": "1", "입금액": 0.0, "출금액": 450000.0,
                     "거래후잔액": None, "적요": "보험",
                     "기재내용·상대방": "한화생명", "자동분류": "보험료",
                     "내부이체": False, "현금유출입": -450000.0,
                     "원본파일": "h", "반영상태": "정상반영", "row_order": 0})
    items = analyze_recurring(rows, BASE, lookback_months=6, min_months=4)
    assert len(items) == 1
    item = items[0]
    assert item["발생개월수"] >= 4
    assert item["평균 월지출"] == 450000
    assert item["대표 지급일"] == 25
    assert item["신뢰도"] in ("상", "중", "하")
    # 2개월만 반복되면 정기지출이 아니다
    few = rows[:2]
    assert analyze_recurring(few, BASE) == []
