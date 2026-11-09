# -*- coding: utf-8 -*-
"""분류(계정과목) 기억 회귀 테스트 (2026-11-09 사용자 요청).

'지금 실행'마다 같은 거래의 분류를 다시 묻던 문제:
① 청구번호가 달마다 바뀌는 표기도 숫자를 뺀 느슨한 일치로 알아보고
② 확인필요 파일의 처리 입력은 확인 완료(B2)·입력 서명과 무관하게
   수확한다 (app.py가 폴더의 파일을 전부 읽음 — 여기선 로더가
   미확인 파일에서도 읽히는지를 고정).
"""
from datetime import date

from openpyxl import load_workbook

import bank_classifier
import excel_report
from common import BANK_REFLECT_OK


def _tx(name, out=100000.0):
    return {"거래일": date(2026, 11, 9), "은행": "우리은행",
            "계좌": "220351", "적요": "인터넷", "기재내용·상대방": name,
            "출금액": out, "입금액": 0.0, "내부이체": False,
            "자동분류": "", "반영상태": BANK_REFLECT_OK}


def _rules(**extra):
    rules = {"rules": [], "사용자분류": [
        {"이름": "SKB6486358411 통신요금", "분류": "통신비"}]}
    rules.update(extra)
    return rules


def test_번호가_바뀐_거래도_기억한_분류로_인식():
    rules = _rules()
    row = _tx("SKB6486999999 통신요금")          # 청구번호만 다름
    bank_classifier.classify_rows([row], rules)
    assert row["자동분류"] == "통신비"


def test_숫자만_남는_짧은_이름은_느슨한_일치_금지():
    rules = {"rules": [], "사용자분류": [
        {"이름": "7008", "분류": "급여"}]}       # 글자 없이 숫자뿐
    row = _tx("KB9999 FBS출금")
    bank_classifier.classify_rows([row], rules)
    assert row["자동분류"] != "급여"             # 과잉 일치하지 않는다


def test_apply_custom_names도_느슨한_일치():
    rules = _rules()
    row = _tx("SKB6486999999 통신요금")
    assert bank_classifier.apply_custom_names([row], rules) == 1
    assert row["자동분류"] == "통신비"


def test_미확인_파일에서도_처리_입력을_읽는다(tmp_path):
    """B2가 '아니오'여도(입력 서명이 달라져도) 적어둔 분류는 수확 대상."""
    issues = [{"구분": excel_report.ISSUE_UNPLANNED, "팀명": "",
               "은행": "우리은행", "내용": "하나주식회사 쇼라스 인터넷",
               "금액": 5390000}]
    out = excel_report.create_issue_workbook(
        issues, tmp_path / "확인필요_test.xlsx",
        week_key="2026-W46", signature="sig")
    wb = load_workbook(out)
    ws = wb["확인필요"]
    ws.cell(row=5, column=9, value="지급수수료")   # I5: 처리에 직접 입력
    assert wb["안내"]["B2"].value == "아니오"      # 확인 완료 아님
    wb.save(out)
    got = excel_report.load_unplanned_classifications(out)
    assert got == [{"이름": "하나주식회사 쇼라스 인터넷",
                    "분류": "지급수수료"}]
