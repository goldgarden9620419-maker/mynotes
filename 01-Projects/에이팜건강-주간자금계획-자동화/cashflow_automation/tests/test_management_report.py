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
        "holidays": {date(2026, 9, 24): "추석 연휴",
                     date(2026, 9, 25): "추석"},
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
    # 반영률(F12)은 드롭다운으로 고른다 (60~100%)
    rate_dvs = [dv for dv in ws.data_validations.dataValidation
                if "80%" in str(dv.formula1)]
    assert rate_dvs and "F12" in str(rate_dvs[0].sqref)
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
    # ④ 필요 추가 입금: 금액은 좁은 B열을 피해 C~F열 (##### 방지)
    assert ws["A146"].value == 0.8 and ws["A148"].value == 1.0
    assert ws["B146"].value is None                # B열엔 금액 없음
    assert ws["C146"].value == -5_000_000          # 4주 기말잔액
    assert "MAX(0,$C$144" in str(ws["F146"].value)
    # ⑤ 전달 메모 수식
    memo = str(ws["A152"].value)
    assert memo.startswith("=IF(") and "건강사업팀" in memo
    # 공휴일 예상입금 0: 숨김 요일평균(G)이 0 → 입금 수식도 0
    assert ws["G17"].value == 0 and ws["G18"].value == 0    # 추석 9/24~25
    assert ws["G15"].value == 1_000_000                     # 평일은 평균
    # 주말·공휴일 일자는 붉은 글자 (9/24 추석=row17, 9/26 토=row19)
    assert str(ws["A17"].font.color.rgb).endswith("C00000")
    assert str(ws["B17"].font.color.rgb).endswith("C00000")
    assert str(ws["A19"].font.color.rgb).endswith("C00000")
    assert not str(ws["A15"].font.color.rgb                  # 화요일은 검정
                   if ws["A15"].font.color else "").endswith("C00000")
    # 인쇄: A4 세로 폭 맞춤 + 빈 지출행 숨김 (자료 2행 + 예비 3행만 표시)
    assert ws.page_setup.orientation == "portrait"
    assert int(ws.page_setup.fitToWidth or 0) == 1
    assert "$A$1" in str(ws.print_area) and "$F$" in str(ws.print_area)
    assert not ws.row_dimensions[49].hidden      # 예비행 (47+2건 뒤 3행)
    assert ws.row_dimensions[52].hidden          # 그 밖의 빈 행은 숨김
    assert ws.row_dimensions[140].hidden
    # ② 실행일(9/21)~차주 금요일(10/2)만 표시 — 이후 일자 행은 숨김
    assert not ws.row_dimensions[14].hidden      # 9/21 (실행일)
    assert not ws.row_dimensions[25].hidden      # 10/2 (차주 금요일)
    assert ws.row_dimensions[26].hidden          # 10/3부터 숨김
    assert ws.row_dimensions[41].hidden
    # ③ 창 밖 지급일 행 숨김: 9/22는 표시, 10/14는 숨김 (합계에는 포함)
    assert not ws.row_dimensions[47].hidden
    assert ws.row_dimensions[48].hidden
    wb.close()


def test_경영보고_실행일_기준_지난_일자_숨김(tmp_path):
    """주중(수 9/23) 실행이면 월·화 행이 숨고 창은 9/23~10/2."""
    rep = _report()
    rep["meta"]["run_date"] = date(2026, 9, 23)
    out = tmp_path / "주간자금계획_경영보고_midweek.xlsx"
    mr.create_management_workbook(rep, out)
    assert mr.verify_management_workbook(out)

    wb = load_workbook(out)
    ws = wb["주간보고"]
    assert ws.row_dimensions[14].hidden          # 9/21 (지난 일자)
    assert ws.row_dimensions[15].hidden          # 9/22
    assert not ws.row_dimensions[16].hidden      # 9/23 (실행일)
    assert not ws.row_dimensions[25].hidden      # 10/2 (차주 금요일)
    assert ws.row_dimensions[26].hidden          # 10/3부터 숨김
    # 붉은 상자도 실행일 행(16)에서 시작
    top = ws["A16"].border.top
    assert top is not None and top.style == "medium"
    # ③ 지난 지급일(9/22) 행도 숨김
    assert ws.row_dimensions[47].hidden
    assert ws.row_dimensions[48].hidden          # 10/14 (창 밖)
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
