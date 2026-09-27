# -*- coding: utf-8 -*-
"""빈 데이터 유효성 검사(<dataValidations count="0"/>) 회귀 테스트.

2026-09-25 사용자 PC에서 확인필요 파일의 '확인필요' 시트가 Excel
'복구' 대화상자를 띄운 원인: 드롭다운 대상 행이 0건이라 셀 없는
DataValidation이 빈 요소로 저장됨. save_workbook이 이를 제거한다.
"""
import re
import zipfile

import excel_report


def _empty_validation_parts(path):
    bad = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.startswith("xl/worksheets/"):
                continue
            data = z.read(name)
            if (b'<dataValidations count="0"' in data
                    or re.search(rb"<dataValidations[^>]*/>", data)):
                bad.append(name)
    return bad


def test_드롭다운_대상_0건이어도_엑셀이_열_수_있는_파일(tmp_path):
    """계획없는출금만 있으면 처리 드롭다운 셀이 없다 — 빈 요소 금지."""
    issues = [{"구분": excel_report.ISSUE_UNPLANNED, "팀명": "",
               "내용": f"테스트 출금 {i}", "금액": 10000 + i}
              for i in range(3)]
    out = excel_report.create_issue_workbook(
        issues, tmp_path / "확인필요_test.xlsx",
        week_key="2026-W39", signature="sig")
    assert _empty_validation_parts(out) == []


def test_대상_행이_있으면_드롭다운은_유지(tmp_path):
    issues = [{"구분": "확인필요", "팀명": "건강사업팀",
               "내용": "지시 필요", "금액": 5000, "지시항목": "항목A"}]
    out = excel_report.create_issue_workbook(
        issues, tmp_path / "확인필요_test2.xlsx",
        week_key="2026-W39", signature="sig")
    assert _empty_validation_parts(out) == []
    with zipfile.ZipFile(out) as z:
        joined = b"".join(z.read(n) for n in z.namelist()
                          if n.startswith("xl/worksheets/"))
    m = re.search(rb'<dataValidations count="(\d+)"', joined)
    assert m and int(m.group(1)) >= 1        # 실제 드롭다운은 살아 있다
