# -*- coding: utf-8 -*-
"""처리 선택 기억·미리 채움 회귀 테스트 (2026-11-23 사용자 요청).

"처리는 내가 하고, 반복해서 나타나는 항목이면 지난 선택을 자동으로
채워주고 확인만 받자" — 확인필요(당일차이 유지/보류, 정기지출누락
계획반영)와 주간대조(②안 나간 돈 ③계획에 없는 지출 확인 ▼)의 선택을
action_memory.json에 기억했다가 다음 파일에 연두색으로 미리 채운다.
"""
from datetime import date

from openpyxl import load_workbook

import action_memory
import excel_report
import weekly_reconcile
from excel_report import (ACTION_HOLD, ACTION_INCLUDE, ACTION_KEEP,
                          ACTION_SKIP, ISSUE_INTRADAY,
                          ISSUE_RECURRING_MISSING, ISSUE_UNPLANNED)

GREEN = action_memory.PREFILL_FILL


def test_기억_저장_불러오기_왕복(tmp_path):
    mem = {}
    n = action_memory.remember(
        mem, [(ISSUE_INTRADAY, "네이버 광고비 1,234원", ACTION_HOLD)])
    assert n == 1
    # 금액·숫자가 달라져도 같은 항목으로 찾는다
    assert action_memory.lookup(mem, ISSUE_INTRADAY,
                                "네이버 광고비 99,999원") == ACTION_HOLD
    p = tmp_path / "action_memory.json"
    action_memory.save(p, mem)
    again = action_memory.load(p)
    assert action_memory.lookup(again, ISSUE_INTRADAY,
                                "네이버 광고비 7,700원") == ACTION_HOLD
    # 기본값으로 되돌린 선택이 기억을 덮는다 (다음부터 미리 안 채움)
    action_memory.remember(again, [(ISSUE_INTRADAY, "네이버 광고비 7,700원",
                                    ACTION_KEEP)])
    assert action_memory.lookup(again, ISSUE_INTRADAY,
                                "네이버 광고비 7,700원") == ACTION_KEEP


def _issues():
    return [
        {"구분": ISSUE_UNPLANNED, "팀명": "", "은행": "우리은행",
         "내용": "SKB 통신요금", "금액": 85621},
        {"구분": ISSUE_INTRADAY, "팀명": "경영", "내용": "당일 차이 네이버",
         "금액": 10000, "당일지시": True, "요청ID": "경영-001"},
        {"구분": ISSUE_RECURRING_MISSING, "팀명": "", "은행": "국민은행",
         "내용": "사회보험 정기지출", "금액": 300000},
    ]


def test_확인필요_반복항목은_지난선택_미리채움(tmp_path):
    mem = {}
    action_memory.remember(mem, [
        (ISSUE_INTRADAY, "당일 차이 네이버", ACTION_HOLD),
        (ISSUE_RECURRING_MISSING, "사회보험 정기지출", ACTION_INCLUDE)])
    out = excel_report.create_issue_workbook(
        _issues(), tmp_path / "확인필요_test.xlsx",
        week_key="2026-W48", signature="sig", remembered=mem)
    wb = load_workbook(out)
    ws = wb["확인필요"]
    cell = ws.cell(row=6, column=9)          # 당일차이 행(6행)의 처리
    assert cell.value == ACTION_HOLD
    assert str(cell.fill.start_color.rgb).endswith(GREEN)
    miss = wb["정기지출누락"]
    mcell = miss.cell(row=5, column=9)
    assert mcell.value == ACTION_INCLUDE
    assert str(mcell.fill.start_color.rgb).endswith(GREEN)


def test_기억없으면_기본값_노란칸_그대로(tmp_path):
    out = excel_report.create_issue_workbook(
        _issues(), tmp_path / "확인필요_test.xlsx",
        week_key="2026-W48", signature="sig", remembered={})
    wb = load_workbook(out)
    cell = wb["확인필요"].cell(row=6, column=9)
    assert cell.value == ACTION_KEEP
    assert not str(cell.fill.start_color.rgb).endswith(GREEN)


def test_확인필요_처리선택_수확(tmp_path):
    mem = {}
    action_memory.remember(mem, [
        (ISSUE_INTRADAY, "당일 차이 네이버", ACTION_HOLD)])
    out = excel_report.create_issue_workbook(
        _issues(), tmp_path / "확인필요_test.xlsx",
        week_key="2026-W48", signature="sig", remembered=mem)
    got = excel_report.load_action_entries(out)
    kinds = {(k, a) for k, _n, a in got}
    assert (ISSUE_INTRADAY, ACTION_HOLD) in kinds        # 미리 채운 값
    assert (ISSUE_RECURRING_MISSING, ACTION_SKIP) in kinds  # 기본값도 수확
    assert all(k != ISSUE_UNPLANNED for k, _n, _a in got)   # 분류기억 담당


def test_주간대조_확인칸_미리채움과_수확(tmp_path):
    mem = {}
    action_memory.remember(mem, [
        (weekly_reconcile.RECON_KIND_UNPAID, "비즈콘",
         "다음 주 지급(이월)")])
    from common import MATCH_NOT_FOUND, MATCH_UNPLANNED
    data = {
        "기간": (date(2026, 11, 21), date(2026, 11, 27)),
        "실행일": date(2026, 11, 27), "은행기준일": date(2026, 11, 27),
        "계좌": [], "계획지출": 0, "실제출금": 0,
        "일치": 0, "완료내역": [],
        "차이내역": [
            {"대조결과": MATCH_NOT_FOUND, "팀명": "물류", "거래처": "비즈콘",
             "지급예정일": date(2026, 11, 25), "예정금액": 500},
            {"대조결과": MATCH_UNPLANNED, "거래처": "이체 수수료",
             "실제출금일": date(2026, 11, 24), "실제금액": 300,
             "은행": "우리은행"},
        ],
        "차이건수": {},
    }
    out = weekly_reconcile.write_reconcile_workbook(
        data, tmp_path / "주간대조_test.xlsx", remembered=mem)
    ws = load_workbook(out)["대조결과"]
    col = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    r2 = next(r for r, v in enumerate(col, start=1)
              if v and str(v).startswith("②")) + 2
    cell = ws.cell(row=r2, column=5)
    assert cell.value == "다음 주 지급(이월)"           # 미리 채움
    assert str(cell.fill.start_color.rgb).endswith(GREEN)
    got = weekly_reconcile.load_reconcile_actions(
        tmp_path / "주간대조_test.xlsx")
    assert (weekly_reconcile.RECON_KIND_UNPAID, "비즈콘",
            "다음 주 지급(이월)") in got
