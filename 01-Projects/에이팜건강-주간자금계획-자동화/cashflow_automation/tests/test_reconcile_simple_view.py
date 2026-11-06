# -*- coding: utf-8 -*-
"""주간대조 '대조결과' 단순 화면 회귀 테스트 (2026-11-06 사용자 요청).

차이내역 표가 복잡하다는 피드백 → 한 시트에서 ① 나간 돈(완료)
② 안 나간 돈(확인 ▼) ③ 계획에 없는 지출(확인 ▼) 세 칸만 보게 바꿈.
기간도 월~금 → 토~금으로 넓혀 자금계획 파일 기간과 맞춘다.
"""
from datetime import date

from openpyxl import load_workbook

import weekly_reconcile
from common import (MATCH_NOT_FOUND, MATCH_PAID, MATCH_PARTIAL,
                    MATCH_UNPLANNED, REFLECT_OK)


def _write(tmp_path):
    data = {
        "기간": (date(2026, 10, 31), date(2026, 11, 6)),
        "실행일": date(2026, 11, 6), "은행기준일": date(2026, 11, 6),
        "계좌": [], "계획지출": 1600, "실제출금": 500,
        "일치": 1,
        "완료내역": [
            {"대조결과": MATCH_PAID, "팀명": "경영", "거래처": "한화생명",
             "지급예정일": date(2026, 11, 5), "실제출금일": date(2026, 11, 5),
             "예정금액": 100, "실제금액": 100},
        ],
        "차이내역": [
            {"대조결과": MATCH_PARTIAL, "팀명": "경영", "거래처": "네이버",
             "지급예정일": date(2026, 11, 4), "실제출금일": date(2026, 11, 4),
             "예정금액": 1000, "실제금액": 400, "차이금액": -600},
            {"대조결과": MATCH_NOT_FOUND, "팀명": "물류", "거래처": "비즈콘",
             "지급예정일": date(2026, 11, 6), "예정금액": 500},
            {"대조결과": MATCH_UNPLANNED, "거래처": "이체 수수료",
             "실제출금일": date(2026, 11, 3), "실제금액": 300,
             "은행": "우리은행"},
        ],
        "차이건수": {},
    }
    out = weekly_reconcile.write_reconcile_workbook(
        data, tmp_path / "주간대조_test.xlsx")
    return load_workbook(out)


def _col_a(ws):
    return [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]


def _dv_for(ws, coord):
    for dv in ws.data_validations.dataValidation:
        if any(coord in str(rng) for rng in dv.sqref.ranges):
            return dv
    return None


def test_시트는_안내_대조결과_계좌별대조_순서(tmp_path):
    wb = _write(tmp_path)
    assert wb.sheetnames == ["안내", "대조결과", "계좌별대조"]


def test_나간돈에는_완료와_일부지급이_함께_비고로_표시(tmp_path):
    ws = _write(tmp_path)["대조결과"]
    col = _col_a(ws)
    sec = next(v for v in col if v and str(v).startswith("① 계획대로 나간 돈"))
    assert "2건" in sec                      # 지급완료 1 + 일부지급 1
    notes = [ws.cell(row=r, column=6).value or ""
             for r in range(1, ws.max_row + 1)]
    partial = next(n for n in notes if "일부만 나감" in n)
    assert "600" in partial                  # 남은 금액 안내


def test_안나간돈은_이월_취소_드롭다운(tmp_path):
    ws = _write(tmp_path)["대조결과"]
    col = _col_a(ws)
    sec_row = next(r for r, v in enumerate(col, start=1)
                   if v and str(v).startswith("② 계획했는데 안 나간 돈"))
    assert "1건" in col[sec_row - 1]
    dv = _dv_for(ws, f"E{sec_row + 2}")      # 머리글 다음 첫 자료 행
    assert dv is not None and dv.type == "list"
    assert "이월" in dv.formula1 and "취소" in dv.formula1
    assert dv.showInputMessage and dv.prompt


def test_계획에없는지출은_아는지출_드롭다운(tmp_path):
    ws = _write(tmp_path)["대조결과"]
    col = _col_a(ws)
    sec_row = next(r for r, v in enumerate(col, start=1)
                   if v and str(v).startswith("③ 계획에 없는 지출"))
    dv = _dv_for(ws, f"E{sec_row + 2}")
    assert dv is not None
    assert "모르는 지출" in dv.formula1
    assert dv.showInputMessage and dv.prompt


def test_대조기간은_토요일부터_금요일까지(tmp_path):
    """월~금 → 토~금: 주말 지급분이 계획 파일과 똑같이 잡힌다."""
    plans = [{"반영상태": REFLECT_OK, "팀명": "경영", "거래처": "주말지급",
              "지급예정일": date(2026, 10, 31), "예상금액": 700}]
    data = weekly_reconcile.build_reconcile_data(
        plans, [], {}, run_date=date(2026, 11, 6))
    assert data["기간"] == (date(2026, 10, 31), date(2026, 11, 6))
    assert any(r.get("거래처") == "주말지급"
               for r in data["차이내역"])      # 토요일 건이 대조에 포함
