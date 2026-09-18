# -*- coding: utf-8 -*-
"""실적 반영(지난 날짜)·추정 중복 제외·정기지출분류 오버라이드 테스트."""
from datetime import date

import forecast_engine as fe


def _tx(d, in_amt=0.0, out_amt=0.0, cls="", internal=False):
    return {"거래일": d, "입금액": in_amt, "출금액": out_amt,
            "자동분류": cls, "내부이체": internal}


def test_지난날짜는_실적으로_채운다():
    base = date(2026, 9, 14)
    history = [
        _tx(date(2026, 9, 1), in_amt=1_000_000, cls="온라인매출입금"),
        _tx(date(2026, 9, 15), in_amt=300_000, cls="온라인매출입금"),
        _tx(date(2026, 9, 15), out_amt=100_000),
        _tx(date(2026, 9, 16), in_amt=50_000),
        _tx(date(2026, 9, 16), in_amt=999_999, internal=True),  # 제외
    ]
    fc = fe.build_forecast([], base, 1_000_000, history, [], [],
                           [0.8], 0.8)
    assert fc["actual_until"] == date(2026, 9, 16)
    # 시작잔액 = 현재잔액 - 실적 순증감(30만-10만+5만)
    assert round(fc["start_balance"]) == 1_000_000 - 250_000
    daily = {r["일자"]: r for r in fc["daily"]}
    d15 = daily[date(2026, 9, 15)]
    assert d15["실적"] is True
    assert d15["온라인 예상입금"] == 300_000
    assert d15["기타지출"] == 100_000
    d16 = daily[date(2026, 9, 16)]
    assert d16["확정·기타입금"] == 50_000
    # 실적 마지막 날 기말잔액이 현재잔액과 일치 (이중계산 없음)
    assert round(d16["기말잔액"]) == 1_000_000
    assert daily[date(2026, 9, 17)]["실적"] is False


def test_팀계획과_겹치는_자동초안_조정_제외():
    adjustments = [
        # 이름·금액·날짜가 모두 비슷 → 중복으로 제외
        {"일자": date(2026, 9, 21), "조정입금": 0.0, "조정지출": 223_019.0,
         "내용": "정기지출 추정(자동 초안): SKB 신뢰도 상"},
        # 금액은 거의 같지만 이름이 다름 → 우연 일치, 유지
        {"일자": date(2026, 9, 24), "조정입금": 0.0, "조정지출": 2_000_000.0,
         "내용": "정기지출 추정(자동 초안): 세이브더칠드런 신뢰도 중"},
        # 사용자가 직접 넣은 조정은 건드리지 않는다
        {"일자": date(2026, 9, 21), "조정입금": 0.0, "조정지출": 220_000.0,
         "내용": "수동 입력 지출"},
    ]
    plans = [
        {"자금계획 반영일": date(2026, 9, 21), "예상금액": 220_000.0,
         "거래처": "SK브로드밴드", "지출내용": "인터넷 요금"},
        {"자금계획 반영일": date(2026, 9, 21), "예상금액": 1_996_000.0,
         "거래처": "트라이앵글하모니", "지출내용": "용역비"},
    ]
    kept, skipped = fe.filter_duplicate_adjustments(adjustments, plans)
    assert len(skipped) == 1 and "SKB" in skipped[0]["내용"]
    assert {k["내용"] for k in kept} == {
        "정기지출 추정(자동 초안): 세이브더칠드런 신뢰도 중", "수동 입력 지출"}


def test_정기지출분류_시트_왕복(tmp_path):
    from openpyxl import Workbook, load_workbook
    p = tmp_path / "기준.xlsx"
    wb = Workbook()
    wb.active.title = "카드결제기준"
    wb.save(p)
    wb.close()

    items = [{"정기지출명": "콜마비앤에이치", "분류": "외상대"},
             {"정기지출명": "SKB", "분류": "통신비"}]
    fe.apply_recurring_overrides(items, fe.load_recurring_overrides(p))
    assert items[0]["성격"] == "변동"   # 분류에 '외상' 포함 → 기본 변동
    assert items[1]["성격"] == "정기"

    assert fe.ensure_recurring_override_sheet(p, items) == 2

    # 사용자가 SKB의 성격을 '제외'로 수정하면 다음 실행에 반영된다
    wb = load_workbook(p)
    ws = wb[fe.OVERRIDE_SHEET_NAME]
    for row in ws.iter_rows(min_row=2):
        if row[0].value == "SKB":
            row[2].value = "제외"
    wb.save(p)
    wb.close()

    fe.apply_recurring_overrides(items, fe.load_recurring_overrides(p))
    assert items[1]["성격"] == "제외"
    # 이미 있는 항목은 다시 추가하지 않는다 (사용자 수정 보존)
    assert fe.ensure_recurring_override_sheet(p, items) == 0
