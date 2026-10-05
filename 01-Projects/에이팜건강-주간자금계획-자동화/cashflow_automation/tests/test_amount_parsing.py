# -*- coding: utf-8 -*-
"""회계식 금액 표기 해석과 '읽을 수 없는 금액' 처리 (진단 8번).

읽을 수 없는 금액을 조용히 0원으로 넘기지 않고, 경고 로그를 남기고
확인필요로 올려야 한다.
"""
import logging

import pytest

from bank_loader import load_bank_file
from common import is_unreadable_amount, parse_amount
from team_loader import _normalize_row, validate_row


@pytest.mark.parametrize("text, expected", [
    ("(1,000)", -1000.0),
    ("1,000-", -1000.0),
    ("₩1,000", 1000.0),
    ("△1,000", -1000.0),
    ("1,000원", 1000.0),
    ("-1,000", -1000.0),
    (" 2,500 ", 2500.0),
    (1000, 1000.0),
])
def test_회계식_금액_표기를_읽는다(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["abc", "nan", "inf", "1,0O0", "(1,000"])
def test_읽을수_없는_금액은_None_그리고_해석불가로_표시(text):
    assert parse_amount(text) is None
    assert is_unreadable_amount(text)


@pytest.mark.parametrize("text", [None, "", "  ", "-"])
def test_빈칸과_대시는_해석불가가_아니다(text):
    assert not is_unreadable_amount(text)


_HTML = """
<html><body><table>
<tr><th>거래일자</th><th>출금금액</th><th>입금금액</th>
    <th>거래후잔액</th><th>거래기록사항</th></tr>
<tr><td>2026-09-21</td><td>(5,000)</td><td>0</td>
    <td>1,000,000</td><td>정상행</td></tr>
<tr><td>2026-09-22</td><td>12만원</td><td>0</td>
    <td>988,000</td><td>이상행</td></tr>
</table></body></html>
"""


def test_은행_금액_해석불가는_0원이_아니라_확인필요(tmp_path, caplog):
    p = tmp_path / "우리은행 거래내역.xls"
    p.write_text(_HTML, encoding="cp949")
    with caplog.at_level(logging.WARNING, logger="cashflow"):
        rows, issues = load_bank_file(p, "우리은행")
    # 정상행은 회계식 음수 표기도 읽는다
    assert [r["적요"] or r["기재내용·상대방"] for r in rows] == ["정상행"]
    assert rows[0]["출금액"] == -5000.0
    # 이상행은 0원으로 반영되지 않고 확인필요로 올라간다
    bad = [i for i in issues if i["구분"] == "금액 해석 불가"]
    assert len(bad) == 1
    assert "12만원" in bad[0]["내용"]
    assert "금액 해석 불가" in caplog.text


def test_팀_금액_해석불가는_누락과_구분해_알린다(caplog):
    team = {"code": "S", "name": "영업"}
    with caplog.at_level(logging.WARNING, logger="cashflow"):
        row = _normalize_row({"예상금액": "12만원", "지급방법": "계좌송금"},
                             team, "영업.xlsx", 0.0, 3)
    assert row["예상금액"] is None
    assert "금액 해석 불가" in caplog.text
    problems = validate_row(row)
    assert "금액 해석 불가(12만원)" in problems
    assert "금액 누락 또는 0원" not in problems


_HTML_MASKED_BALANCE = """
<html><body><table>
<tr><th>거래일자</th><th>출금금액</th><th>입금금액</th>
    <th>거래후잔액</th><th>거래기록사항</th></tr>
<tr><td>2026-09-21</td><td>5,000</td><td>0</td>
    <td>*****</td><td>가</td></tr>
<tr><td>2026-09-22</td><td>0</td><td>7,000</td>
    <td>*****</td><td>나</td></tr>
</table></body></html>
"""


def test_잔액만_해석불가면_거래는_유지하고_파일당_한번_알린다(tmp_path, caplog):
    p = tmp_path / "우리은행 거래내역.xls"
    p.write_text(_HTML_MASKED_BALANCE, encoding="cp949")
    with caplog.at_level(logging.WARNING, logger="cashflow"):
        rows, issues = load_bank_file(p, "우리은행")
    assert [(r["출금액"], r["입금액"], r["거래후잔액"]) for r in rows] == \
        [(5000.0, 0.0, None), (0.0, 7000.0, None)]
    bad = [i for i in issues if i["구분"] == "잔액 해석 불가"]
    assert len(bad) == 1 and "2건" in bad[0]["내용"]
    assert "잔액 해석 불가" in caplog.text
    assert not any(k.startswith("_") for r in rows for k in r)
