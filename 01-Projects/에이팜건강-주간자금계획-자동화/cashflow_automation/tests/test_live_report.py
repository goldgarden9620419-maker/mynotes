# -*- coding: utf-8 -*-
"""라이브 양식 채우기 테스트: 수식 보존 + 주차 날짜 재고정."""
from datetime import date, datetime, timedelta

from openpyxl import Workbook, load_workbook

from live_report import fill_live_workbook, verify_live_workbook

OLD_MONDAY = date(2026, 9, 14)
NEW_MONDAY = date(2026, 9, 21)

_DAILY_C = ("=INDEX('설정및분류'!$C$6:$C$12,WEEKDAY(A{r},2))*'요약'!$B$13")
_OLD_SUMIFS = ("=SUMIFS('4주일별계획'!$C$6:$C$33,'4주일별계획'!$A$6:$A$33,"
               "\">=\"&DATE(2026,9,14),'4주일별계획'!$A$6:$A$33,"
               "\"<=\"&DATE(2026,9,20))")


def _make_stub_template(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "요약"
    ws["B6"], ws["B13"] = 100, 0.8
    ws["B14"] = "='4주일별계획'!J33"
    ws["B15"] = "=MIN('4주일별계획'!J6:J33)"

    ws = wb.create_sheet("4주일별계획")
    for i in range(28):
        r = 6 + i
        ws.cell(row=r, column=1,
                value=datetime(2026, 9, 14) + timedelta(days=i))
        ws.cell(row=r, column=3, value=_DAILY_C.format(r=r))
        ws.cell(row=r, column=8, value=f"=C{r}+D{r}-E{r}-F{r}-G{r}")
        ws.cell(row=r, column=10, value=f"=I{r}+H{r}")

    ws = wb.create_sheet("13주주별계획")
    for w in range(13):
        r = 6 + w
        ws.cell(row=r, column=1, value=f"{w + 1}주차")
        if w < 4:
            for col in ("C", "D", "E", "F", "G"):
                ws[f"{col}{r}"] = _OLD_SUMIFS
        else:
            ws.cell(row=r, column=3,
                    value="=SUM('설정및분류'!$C$6:$C$12)*'요약'!$B$13")

    wb.create_sheet("정기지출분석")
    wb.create_sheet("계좌내역통합_RAW")
    ws = wb.create_sheet("설정및분류")
    for i in range(7):
        ws.cell(row=6 + i, column=3, value=0)
    wb.save(path)
    wb.close()


def _fake_report(base: date) -> dict:
    daily = []
    for i in range(28):
        d = base + timedelta(days=i)
        daily.append({"일자": d, "확정·기타입금": 0, "팀별 송금예정": 0,
                      "카드결제": 500000 if i == 3 else 0,
                      "자동이체": 0, "기타지출": 100000 if i == 0 else 0})
    weekly = [{"확정기타입금": 0, "송금예정": 0, "카드결제": 0,
               "자동이체": 0, "기타지출": 0} for _ in range(13)]
    weekly[5]["기타지출"] = 700000
    return {
        "meta": {"base_date": base},
        "forecast": {"weekday_avg": {i: 1000000 for i in range(5)},
                     "daily": daily, "weekly": weekly},
        "total_balance": 12345678,
        "history_stats": {"외부입금": 1, "외부출금": 2, "온라인입금": 3,
                          "주평균온라인": 4},
        "balances": {("국민은행", "596001-04-154577"): 12345678},
        "account_last_dates": {("국민은행", "596001-04-154577"):
                               base - timedelta(days=3)},
        "account_labels": {},
        "recurring": [{"은행": "우리은행", "정기지출명": "사회보험",
                       "분류": "4대보험", "발생개월수": 6, "거래건수": 6,
                       "평균 월지출": 100.0, "최소 월지출": 90.0,
                       "최대 월지출": 110.0, "대표 지급일": 10,
                       "신뢰도": "상"}],
        "bank_rows": [{"거래일": base - timedelta(days=3),
                       "거래일시": None, "은행": "국민은행",
                       "계좌": "596001-04-154577", "출금액": 0.0,
                       "입금액": 50000.0, "거래후잔액": 12345678.0,
                       "적요": "전자금융", "기재내용·상대방": "테스트",
                       "취급점": "", "자동분류": "", "내부이체": False,
                       "정기지출후보": False, "현금유출입": 50000.0,
                       "반영상태": "정상반영"}],
    }


def test_라이브양식_다음주로_재고정(tmp_path):
    template = tmp_path / "템플릿.xlsx"
    _make_stub_template(template)
    out = tmp_path / "결과.xlsx"
    fill_live_workbook(template, _fake_report(NEW_MONDAY), out)

    assert verify_live_workbook(out, NEW_MONDAY)
    wb = load_workbook(out)
    daily = wb["4주일별계획"]
    # 날짜가 새 주차로 이동
    assert daily["A6"].value.date() == NEW_MONDAY
    assert daily["A33"].value.date() == NEW_MONDAY + timedelta(days=27)
    # 반영률 수식은 그대로
    assert "INDEX" in daily["C6"].value and "$B$13" in daily["C6"].value
    # 지출 값 기록 (1일차 기타지출, 4일차 카드)
    assert daily["G6"].value == 100000
    assert daily["F9"].value == 500000
    weekly = wb["13주주별계획"]
    # 1주차 SUMIFS가 새 날짜로 재작성
    assert "DATE(2026,9,21)" in weekly["C6"].value
    assert "DATE(2026,9,27)" in weekly["C6"].value
    # 5주 이후 반영률 수식 유지 + 6주차 기타지출 값
    assert "$B$13" in weekly["C10"].value
    assert weekly["G11"].value == 700000
    summary = wb["요약"]
    assert summary["B6"].value == 12345678
    assert summary["B14"].value.startswith("=")  # 요약 수식 보존
    raw = wb["계좌내역통합_RAW"]
    assert raw["C2"].value == "국민은행"
    assert raw["F2"].value == 50000
    wb.close()


def test_라이브양식_검증은_이전주면_실패(tmp_path):
    template = tmp_path / "템플릿.xlsx"
    _make_stub_template(template)
    out = tmp_path / "결과.xlsx"
    fill_live_workbook(template, _fake_report(NEW_MONDAY), out)
    assert not verify_live_workbook(out, OLD_MONDAY)
