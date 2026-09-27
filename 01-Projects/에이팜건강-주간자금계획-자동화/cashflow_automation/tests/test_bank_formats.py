# -*- coding: utf-8 -*-
"""은행 파일 형식 구분 없이 읽기 테스트 (2026-09-21 사용자 요청).

확장자와 실제 내용이 달라도(HTML 표를 .xls로, CSV를 .xlsx로,
스타일 XML이 깨진 xlsx 등) 내용을 판별해 읽어야 한다.
"""
import zipfile
from datetime import date, datetime

from bank_loader import load_bank_file
from file_validator import _bank_file_readable

_HTML = """
<html><body>
<table>
<tr><td>계좌번호: 1005-902-220351</td></tr>
<tr><th>거래일자</th><th>출금금액</th><th>입금금액</th>
    <th>거래후잔액</th><th>거래기록사항</th></tr>
<tr><td>2026-09-21</td><td>328,043</td><td>0</td>
    <td>11,620,094</td><td>SKB6452342048</td></tr>
<tr><td>2026-09-21</td><td>0</td><td>500,000</td>
    <td>12,120,094</td><td>네이버</td></tr>
</table></body></html>
"""

_CSV = ("거래일자,출금금액,입금금액,거래후잔액,거래기록사항\n"
        "2026-09-21,328043,0,11620094,SKB\n"
        "2026-09-22,0,700000,12320094,쿠팡\n")


def test_HTML표를_xls_확장자로_읽는다(tmp_path):
    p = tmp_path / "우리은행 거래내역.xls"        # 실제 내용은 HTML
    p.write_text(_HTML, encoding="cp949")
    rows, issues = load_bank_file(p, "우리은행")
    assert not [i for i in issues if i["구분"] == "손상된 파일"]
    assert len(rows) == 2
    assert rows[0]["거래일"] == date(2026, 9, 21)
    assert rows[0]["출금액"] == 328043
    assert rows[0]["거래후잔액"] == 11620094
    assert rows[1]["입금액"] == 500000
    assert "220351" in rows[0]["계좌"]
    assert _bank_file_readable(p)


def test_CSV내용을_xlsx_확장자로_읽는다(tmp_path):
    p = tmp_path / "국민은행 거래내역.xlsx"       # 실제 내용은 CSV
    p.write_text(_CSV, encoding="utf-8-sig")
    rows, issues = load_bank_file(p, "국민은행")
    assert not [i for i in issues if i["구분"] == "손상된 파일"]
    assert len(rows) == 2
    assert rows[1]["거래일"] == date(2026, 9, 22)
    assert rows[1]["입금액"] == 700000
    assert _bank_file_readable(p)


def test_스타일이_깨진_xlsx를_복구해_읽는다(tmp_path):
    from openpyxl import Workbook
    good = tmp_path / "good.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["거래일자", "출금금액", "입금금액", "거래후잔액", "내용"])
    ws.append([datetime(2026, 9, 21, 10, 0), 100000, 0, 900000, "테스트"])
    wb.save(good)
    wb.close()
    # styles.xml을 망가뜨린 사본 (은행 다운로드 파일에서 실제 발생)
    bad = tmp_path / "농협 거래내역.xlsx"
    with zipfile.ZipFile(good) as zin, \
            zipfile.ZipFile(bad, "w") as zout:
        for name in zin.namelist():
            zout.writestr(name, b"<broken" if name == "xl/styles.xml"
                          else zin.read(name))
    rows, issues = load_bank_file(bad, "농협")
    assert not [i for i in issues if i["구분"] == "손상된 파일"]
    assert len(rows) == 1
    # 서식이 사라져 날짜가 일련값(숫자)로 와도 날짜로 되살린다
    assert rows[0]["거래일"] == date(2026, 9, 21)
    assert rows[0]["출금액"] == 100000


def test_읽을수없는_파일은_손상으로_보고(tmp_path):
    p = tmp_path / "깨진파일.xls"
    p.write_bytes(b"\x00\x01\x02\x03\xff\xfe\x00\x99" * 10)
    rows, issues = load_bank_file(p, "우리은행")
    assert rows == []
    assert any(i["구분"] == "손상된 파일" for i in issues)
    assert not _bank_file_readable(p)


# ---------------------------------------------------------------------------
# 더존 내보내기 (2026-09-22 사용자 요청): 월/일·적요·입금액·출금액·잔액,
# 연도 없는 날짜, 전일잔액·합계 행, 계좌번호 없음(파일명 뒷자리로 구분)
# ---------------------------------------------------------------------------

def _더존_파일(path, d1, d2):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["월/일", "적요", "입금액", "출금액", "잔액"])
    ws.append([d1.strftime("%m-%d"), "전일잔액", "0", "0", "20147954"])
    ws.append([d2.strftime("%m-%d"), "KG이니시스", "750249", "0", "20898203"])
    ws.append([d2.strftime("%m-%d"), "METLIFE09002", "0", "4795900",
               "16102303"])
    ws.append(["합     계", "", "750249", "4795900", ""])
    wb.save(path)
    wb.close()


def test_더존_월일_양식을_읽고_파일명에서_계좌를_찾는다(tmp_path):
    from datetime import timedelta
    d1 = date.today() - timedelta(days=2)
    d2 = date.today() - timedelta(days=1)
    p = tmp_path / "국민 4577 20260922.xlsx"
    _더존_파일(p, d1, d2)
    rows, issues = load_bank_file(p, "국민")
    assert issues == []                      # 합계 행이 오류가 되면 안 된다
    assert len(rows) == 3                    # 전일잔액 포함, 합계 제외
    assert rows[0]["거래일"] == d1           # 연도 없는 월-일 보정
    assert rows[0]["입금액"] == 0 and rows[0]["거래후잔액"] == 20147954
    assert rows[1]["거래일"] == d2
    assert rows[2]["출금액"] == 4795900
    assert all(r["계좌"] == "4577" for r in rows)   # 날짜 토큰은 계좌가 아니다
    assert rows[1]["적요"] == "KG이니시스"   # 상대방 이름은 적요로 들어온다


def test_연도없는_날짜는_연말연초에도_맞게_보정한다():
    from bank_loader import _parse_month_day
    assert _parse_month_day("12-30", ref=date(2027, 1, 3)) == date(2026, 12, 30)
    assert _parse_month_day("01-02", ref=date(2027, 1, 3)) == date(2027, 1, 2)
    assert _parse_month_day("합 계") is None


def test_파일명_계좌_뒷자리를_은행원본_전체번호와_통일한다():
    from bank_loader import unify_account_labels
    rows = [{"은행": "국민", "계좌": "93401-01-154577"},
            {"은행": "국민", "계좌": "4577"},
            {"은행": "국민", "계좌": "169124"},
            {"은행": "농협", "계좌": "4577"}]
    unify_account_labels(rows)
    assert rows[1]["계좌"] == "93401-01-154577"   # 뒷자리 일치 → 같은 계좌
    assert rows[2]["계좌"] == "169124"            # 대응 없음 → 그대로
    assert rows[3]["계좌"] == "4577"              # 다른 은행은 건드리지 않음
