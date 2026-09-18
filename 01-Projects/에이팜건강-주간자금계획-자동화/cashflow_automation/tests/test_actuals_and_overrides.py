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


def test_정기지출분석_수정_수확_반영(tmp_path):
    """결과 파일의 분류·성격 수정이 기준파일 정기지출분류로 흘러간다."""
    from openpyxl import Workbook

    # 사용자가 편집한 라이브 결과물 흉내
    live = tmp_path / "주간자금계획_라이브_20260921_0910.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "정기지출분석"
    for c, h in enumerate(["은행", "정기지출명", "분류"], start=1):
        ws.cell(row=5, column=c, value=h)
    ws.cell(row=5, column=11, value="성격")
    ws.cell(row=6, column=2, value="기업콜마비앤에이치")
    ws.cell(row=6, column=3, value="외상대 지급")      # 사용자가 입력
    ws.cell(row=6, column=11, value="변동")            # 사용자가 입력
    ws.cell(row=7, column=2, value="세이브더칠드런")
    ws.cell(row=7, column=3, value="성격확인필요")      # 미입력 → 무시
    wb.save(live)
    wb.close()

    edits = fe.harvest_recurring_edits(live)
    assert edits["기업콜마비앤에이치"] == {"분류": "외상대 지급", "성격": "변동"}
    assert "세이브더칠드런" not in edits

    # 기준파일에 반영 → 다음 실행의 오버라이드로 적용
    base = tmp_path / "기준.xlsx"
    wb = Workbook()
    wb.active.title = "카드결제기준"
    wb.save(base)
    wb.close()
    assert fe.update_override_sheet(base, edits) >= 1
    ov = fe.load_recurring_overrides(base)
    items = [{"정기지출명": "기업콜마비앤에이치", "분류": ""}]
    fe.apply_recurring_overrides(items, ov)
    assert items[0]["분류"] == "외상대 지급"
    assert items[0]["성격"] == "변동"
    # 같은 값 재수확은 변경 0건 (사용자 수정 보존)
    assert fe.update_override_sheet(base, edits) == 0


def test_계좌별_시나리오_인출_우선순위():
    """우리은행 부족분은 농협→국민 순으로 이체해 채운다."""
    daily = [{"일자": date(2026, 9, 21), "요일": "월", "실적": False,
              "온라인 예상입금": 0.0, "확정·기타입금": 0.0,
              "팀별 송금예정": 0.0, "카드결제": 0.0, "자동이체": 0.0,
              "기타지출": 300.0}]
    balances = {("우리은행", "W"): 100.0, ("농협", "N"): 150.0,
                ("국민은행", "K"): 1000.0}
    sc = fe.build_account_scenario(daily, balances, [])
    assert sc["accounts"][0] == ("우리은행", "W")
    row = sc["rows"][0]
    # 부족 200 = 농협 150 + 국민 50
    assert row["이체"] == {("농협", "N"): 150.0, ("국민은행", "K"): 50.0}
    assert round(row["잔액"][("우리은행", "W")]) == 0
    assert round(row["잔액"][("농협", "N")]) == 0
    assert round(row["잔액"][("국민은행", "K")]) == 950
    assert row["비고"] == ""

    # 전 계좌 소진 시 부족 경고
    daily2 = [dict(daily[0], 기타지출=2000.0)]
    sc2 = fe.build_account_scenario(daily2, balances, [])
    assert "부족" in sc2["rows"][0]["비고"]


def test_금주일별_시나리오_생성():
    base = date(2026, 9, 21)  # 월요일
    fc = fe.build_forecast([], base, 1_000_000, [], [], [], [0.8, 0.9], 0.8)
    days = fc["rate_scenarios"][0.9]["금주일별"]
    assert len(days) == 5
    assert days[0][0] == base and days[-1][0] == date(2026, 9, 25)
