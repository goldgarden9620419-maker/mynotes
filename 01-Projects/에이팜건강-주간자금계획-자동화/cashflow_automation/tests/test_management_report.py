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
            {"일자": date(2026, 10, 14), "구분": "경영지원팀",
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
    # ② 4주(28일) 일별 표: 반영률 셀 참조 + 지출 SUMIFS + 시작잔액 연결
    assert "$F$12" in str(ws["C14"].value)
    assert "SUMIFS" in str(ws["D14"].value)
    assert "$E$47" in str(ws["D14"].value)      # 지출 표 구간 참조
    assert str(ws["E14"].value).startswith("=$H$13")
    assert ws["A41"].value.date() == date(2026, 10, 18)  # 28일째
    assert str(ws["C42"].value).startswith("=MIN(E14:E41")
    # 실행일(월 9/21)~차주 금요일(10/2) 구간이 하나의 붉은 상자 (격자 아님)
    def _side(cell, name):
        s = getattr(cell.border, name, None)
        return s.style if s is not None else None
    assert _side(ws["A14"], "top") == "medium"
    assert _side(ws["A14"], "left") == "medium"
    assert _side(ws["F25"], "bottom") == "medium"
    assert _side(ws["F25"], "right") == "medium"
    assert _side(ws["C17"], "left") != "medium"
    assert _side(ws["A26"], "left") != "medium"   # 구간 밖은 없음
    # ③ 4주 지출예정 표: 항목·합계 (10/14 건도 포함)
    assert ws["A47"].value is not None and ws["E47"].value == 500000
    assert ws["D48"].value == "대외비 급여·인건비(대외비)"
    assert "SUM(" in str(ws["E141"].value)
    assert ws.auto_filter.ref == "A46:F140"   # 지급일별 필터
    # ④ 필요 추가 입금: 목표잔액 셀 참조 MAX 수식 (80/90/100 3행)
    assert ws["A146"].value == 0.8 and ws["A148"].value == 1.0
    assert "MAX(0,$B$144" in str(ws["E146"].value)
    # ⑤ 전달 메모 수식
    memo = str(ws["A152"].value)
    assert memo.startswith("=IF(") and "건강사업팀" in memo
    wb.close()


def test_정기지출_체크_시트(tmp_path):
    rep = _report()
    rep["meta"]["run_date"] = date(2026, 9, 21)
    rep["recurring_check"] = [
        {"예정일": date(2026, 9, 23), "항목": "농협카드",
         "예상금액": 6_066_502, "관리상태": "제외",
         "팀제출일": date(2026, 9, 23), "팀제출금액": 10_000_000.0,
         "누락": False, "판정": "팀 계획 반영"},
        {"예정일": date(2026, 9, 25), "항목": "SKB",
         "예상금액": 220_000, "관리상태": "제외",
         "팀제출일": None, "팀제출금액": None,
         "누락": True, "판정": "누락 의심 — 팀 재제출 요청"},
    ]
    out = tmp_path / "주간자금계획_경영보고_check.xlsx"
    mr.create_management_workbook(rep, out)
    assert mr.verify_management_workbook(out)

    wb = load_workbook(out)
    ws = wb[mr.CHECK_SHEET]
    assert "누락 의심 1건" in str(ws["A3"].value)
    assert ws["C6"].value == "농협카드" and "있음" in str(ws["F6"].value)
    assert ws["C7"].value == "SKB" and ws["F7"].value == "없음"
    assert "누락 의심" in str(ws["G7"].value)
    assert str(ws["A7"].fill.start_color.rgb).endswith("FFC7CE")  # 붉은 행
    assert ws.auto_filter.ref.startswith("A5:G")
    wb.close()
