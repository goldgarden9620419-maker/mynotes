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
