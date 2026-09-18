# -*- coding: utf-8 -*-
"""주간 자금 경영보고(대화형) 워크북 테스트."""
from datetime import date

from openpyxl import load_workbook

import management_report as mr


def _report():
    base = date(2026, 9, 21)  # 월요일
    daily = []
    for i in range(28):
        d = date.fromordinal(base.toordinal() + i)
        daily.append({"일자": d, "실적": False, "온라인 예상입금": 0.0,
                      "확정·기타입금": 100000.0 if i == 1 else 0.0,
                      "팀별 송금예정": 0.0, "카드결제": 0.0,
                      "자동이체": 0.0, "기타지출": 0.0})
    return {
        "meta": {"company": "(주)에이팜건강", "base_date": base,
                 "run_at": "2026-09-21 09:10:00"},
        "total_balance": 10_000_000,
        "balances": {("우리은행", "220351"): 4_000_000,
                     ("국민은행", "169124"): 6_000_000},
        "account_labels": {}, "account_last_dates": {},
        "forecast": {
            "daily": daily, "rate": 0.8, "actual_until": None,
            "start_balance": 10_000_000,
            "weekday_avg": {i: 1_000_000 if i < 5 else 0 for i in range(7)},
            "rate_scenarios": {
                0.8: {"4주 기말잔액": -5_000_000, "4주 최저잔액": -5_000_000,
                      "자금부족 예상일": date(2026, 10, 10)},
                0.9: {"4주 기말잔액": -2_000_000, "4주 최저잔액": -2_000_000,
                      "자금부족 예상일": date(2026, 10, 12)},
                1.0: {"4주 기말잔액": 1_000_000, "4주 최저잔액": 500_000,
                      "자금부족 예상일": None},
            },
        },
        "week_expenses": [
            {"일자": date(2026, 9, 22), "구분": "물류팀",
             "내용": "한진택배 택배비", "금액": 500_000,
             "지급방법": "계좌송금"},
            {"일자": date(2026, 9, 24), "구분": "경영지원팀",
             "내용": "대외비 급여·인건비(대외비)", "금액": 3_000_000,
             "지급방법": "계좌송금"},
        ],
        "stability_target": 0,
    }


def test_경영보고_생성과_수식(tmp_path):
    out = tmp_path / "주간자금계획_경영보고_test.xlsx"
    mr.create_management_workbook(_report(), out)
    assert mr.verify_management_workbook(out)

    wb = load_workbook(out)
    ws = wb["주간보고"]
    # ① 총잔액 합계 수식
    assert str(ws["C8"].value).startswith("=SUM(")
    # ② 일별 표: 미래일 입금은 반영률 셀 참조, 지출은 SUMIFS
    assert "$F$12" in str(ws["C14"].value)
    assert "SUMIFS" in str(ws["D14"].value)
    assert str(ws["E14"].value).startswith("=$H$13")   # 시작잔액 연결
    # ③ 지출 표: 항목·합계
    assert ws["A26"].value is not None and ws["E26"].value == 500000
    assert ws["D27"].value == "대외비 급여·인건비(대외비)"
    assert "SUM(" in str(ws["E89"].value)
    # ④ 필요 추가 입금: 목표잔액 셀 참조 MAX 수식 (80/90/100 3행)
    assert ws["A94"].value == 0.8 and ws["A96"].value == 1.0
    assert "MAX(0,$B$92" in str(ws["E94"].value)
    # ⑤ 전달 메모 수식
    memo = str(ws["A100"].value)
    assert memo.startswith("=IF(") and "건강사업팀" in memo
    wb.close()
