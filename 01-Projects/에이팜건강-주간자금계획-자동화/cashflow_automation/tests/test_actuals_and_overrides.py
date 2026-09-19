# -*- coding: utf-8 -*-
"""실적 반영(지난 날짜)·추정 중복 제외·정기지출분류 오버라이드 테스트."""
from datetime import date

import forecast_engine as fe


def _tx(d, in_amt=0.0, out_amt=0.0, cls="", internal=False):
    return {"거래일": d, "입금액": in_amt, "출금액": out_amt,
            "자동분류": cls, "내부이체": internal}


def test_지난날짜는_실적으로_채운다():
    base = date(2026, 9, 14)
    history = [
        _tx(date(2026, 9, 1), in_amt=1_000_000, cls="온라인매출입금"),
        _tx(date(2026, 9, 15), in_amt=300_000, cls="온라인매출입금"),
        _tx(date(2026, 9, 15), out_amt=100_000),
        _tx(date(2026, 9, 16), in_amt=50_000),
        _tx(date(2026, 9, 16), in_amt=999_999, internal=True),  # 제외
    ]
    fc = fe.build_forecast([], base, 1_000_000, history, [], [],
                           [0.8], 0.8)
    assert fc["actual_until"] == date(2026, 9, 16)
    # 시작잔액 = 현재잔액 - 실적 순증감(30만-10만+5만)
    assert round(fc["start_balance"]) == 1_000_000 - 250_000
    daily = {r["일자"]: r for r in fc["daily"]}
    d15 = daily[date(2026, 9, 15)]
    assert d15["실적"] is True
    assert d15["온라인 예상입금"] == 300_000
    assert d15["기타지출"] == 100_000
    d16 = daily[date(2026, 9, 16)]
    assert d16["확정·기타입금"] == 50_000
    # 실적 마지막 날 기말잔액이 현재잔액과 일치 (이중계산 없음)
    assert round(d16["기말잔액"]) == 1_000_000
    assert daily[date(2026, 9, 17)]["실적"] is False


def test_팀계획과_겹치는_자동초안_조정_제외():
    adjustments = [
        # 이름·금액·날짜가 모두 비슷 → 중복으로 제외
        {"일자": date(2026, 9, 21), "조정입금": 0.0, "조정지출": 223_019.0,
         "내용": "정기지출 추정(자동 초안): SKB 신뢰도 상"},
        # 금액은 거의 같지만 이름이 다름 → 우연 일치, 유지
        {"일자": date(2026, 9, 24), "조정입금": 0.0, "조정지출": 2_000_000.0,
         "내용": "정기지출 추정(자동 초안): 세이브더칠드런 신뢰도 중"},
        # 사용자가 직접 넣은 조정은 건드리지 않는다
        {"일자": date(2026, 9, 21), "조정입금": 0.0, "조정지출": 220_000.0,
         "내용": "수동 입력 지출"},
    ]
    plans = [
        {"자금계획 반영일": date(2026, 9, 21), "예상금액": 220_000.0,
         "거래처": "SK브로드밴드", "지출내용": "인터넷 요금"},
        {"자금계획 반영일": date(2026, 9, 21), "예상금액": 1_996_000.0,
         "거래처": "트라이앵글하모니", "지출내용": "용역비"},
    ]
    kept, skipped = fe.filter_duplicate_adjustments(adjustments, plans)
    assert len(skipped) == 1 and "SKB" in skipped[0]["내용"]
    assert {k["내용"] for k in kept} == {
        "정기지출 추정(자동 초안): 세이브더칠드런 신뢰도 중", "수동 입력 지출"}


def test_정기지출분류_시트_왕복(tmp_path):
    from openpyxl import Workbook, load_workbook
    p = tmp_path / "기준.xlsx"
    wb = Workbook()
    wb.active.title = "카드결제기준"
    wb.save(p)
    wb.close()

    items = [{"정기지출명": "콜마비앤에이치", "분류": "외상대"},
             {"정기지출명": "SKB", "분류": "통신비"}]
    fe.apply_recurring_overrides(items, fe.load_recurring_overrides(p))
    assert items[0]["성격"] == "변동"   # 분류에 '외상' 포함 → 기본 변동
    assert items[1]["성격"] == "정기"

    assert fe.ensure_recurring_override_sheet(p, items) == 2

    # 사용자가 SKB의 성격을 '제외'로 수정하면 다음 실행에 반영된다
    wb = load_workbook(p)
    ws = wb[fe.OVERRIDE_SHEET_NAME]
    for row in ws.iter_rows(min_row=2):
        if row[0].value == "SKB":
            row[2].value = "제외"
    wb.save(p)
    wb.close()

    fe.apply_recurring_overrides(items, fe.load_recurring_overrides(p))
    assert items[1]["성격"] == "제외"
    # 이미 있는 항목은 다시 추가하지 않는다 (사용자 수정 보존)
    assert fe.ensure_recurring_override_sheet(p, items) == 0


def test_정기지출분석_수정_수확_반영(tmp_path):
    """결과 파일의 분류·성격 수정이 기준파일 정기지출분류로 흘러간다."""
    from openpyxl import Workbook

    # 사용자가 편집한 라이브 결과물 흉내
    live = tmp_path / "주간자금계획_라이브_20260921_0910.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "정기지출분석"
    for c, h in enumerate(["은행", "정기지출명", "분류"], start=1):
        ws.cell(row=5, column=c, value=h)
    ws.cell(row=5, column=11, value="성격")
    ws.cell(row=6, column=2, value="기업콜마비앤에이치")
    ws.cell(row=6, column=3, value="외상대 지급")      # 사용자가 입력
    ws.cell(row=6, column=11, value="변동")            # 사용자가 입력
    ws.cell(row=7, column=2, value="세이브더칠드런")
    ws.cell(row=7, column=3, value="성격확인필요")      # 미입력 → 무시
    wb.save(live)
    wb.close()

    edits = fe.harvest_recurring_edits(live)
    assert edits["기업콜마비앤에이치"] == {"분류": "외상대 지급", "성격": "변동"}
    assert "세이브더칠드런" not in edits

    # 기준파일에 반영 → 다음 실행의 오버라이드로 적용
    base = tmp_path / "기준.xlsx"
    wb = Workbook()
    wb.active.title = "카드결제기준"
    wb.save(base)
    wb.close()
    assert fe.update_override_sheet(base, edits) >= 1
    ov = fe.load_recurring_overrides(base)
    items = [{"정기지출명": "기업콜마비앤에이치", "분류": ""}]
    fe.apply_recurring_overrides(items, ov)
    assert items[0]["분류"] == "외상대 지급"
    assert items[0]["성격"] == "변동"
    # 같은 값 재수확은 변경 0건 (사용자 수정 보존)
    assert fe.update_override_sheet(base, edits) == 0


def test_정기지출분석_검토파일과_일괄변경_왕복(tmp_path):
    """별도 정기지출분석 검토 파일: 필터·드롭다운·K4 전체 일괄·N열
    분류별 일괄이 붙고, 수정이 수확돼 기준파일 정기지출분류로 흘러간다.
    우선순위: 전체 일괄 > 분류별 일괄 > 개별 행. '비정기'='변동'."""
    from openpyxl import load_workbook
    import excel_report as er

    assert er.recurring_review_name("확인필요_20260921_0910.xlsx") \
        == "정기지출분석_20260921_0910.xlsx"
    out = tmp_path / "정기지출분석_20260921_0910.xlsx"
    recurring = [
        {"은행": "우리은행", "정기지출명": "SKB", "분류": "통신비",
         "발생개월수": 6, "거래건수": 6, "평균 월지출": 220000.0,
         "대표 지급일": 25, "신뢰도": "상", "성격": "정기"},
        {"은행": "우리은행", "정기지출명": "KT", "분류": "통신비",
         "발생개월수": 6, "거래건수": 6, "평균 월지출": 90000.0,
         "대표 지급일": 26, "신뢰도": "상", "성격": "정기"},
        {"은행": "농협", "정기지출명": "코웨이", "분류": "렌탈료",
         "발생개월수": 6, "거래건수": 6, "평균 월지출": 113398.0,
         "대표 지급일": 28, "신뢰도": "상", "성격": "변동"},
    ]
    er.create_recurring_review_workbook(recurring, out, week_key="2026-W39")

    wb = load_workbook(out)
    ws = wb["정기지출분석"]
    # 머리글(5행) 필터 + K4 전체 일괄 + 분류별 일괄 블록(M·N열)
    assert ws.auto_filter.ref == "A5:K8"
    assert ws["K4"].value == "변경 안 함"
    # 성격 칸은 일괄 컨트롤과 수식으로 연결 (엑셀에서 즉시 반영되어 보임)
    assert str(ws["K6"].value).startswith("=IF($K$4")
    assert "MATCH($C6" in str(ws["K6"].value)
    assert '"비정기"' in str(ws["K8"].value)          # 변동은 비정기로 표시
    assert ws["M5"].value == "분류별 일괄"
    assert [ws[f"M{r}"].value for r in (6, 7)] == ["통신비", "렌탈료"]
    assert ws["N6"].value == "변경 안 함"
    # '적용할 성격' 선택지 안내 상자 (P열)
    assert ws["P5"].value == "적용할 성격 안내"
    guide = " ".join(str(ws[f"P{r}"].value) for r in range(6, 11))
    for word in ("변경 안 함", "정기 —", "비정기 —", "제외 —", "우선순위"):
        assert word in guide
    formulas = [str(dv.formula1) for dv in ws.data_validations.dataValidation]
    assert any("전체 비정기" in f for f in formulas)
    assert any("정기,비정기,제외" in f for f in formulas)
    # 개별 수정: SKB만 '비정기'로 직접 입력 (수식 대신 값)
    ws["K6"] = "비정기"
    wb.save(out)
    wb.close()
    edits = fe.harvest_recurring_edits(out)
    assert edits["SKB"]["성격"] == "변동"             # 비정기 → 내부 변동
    # 수식 그대로인 행은 '변경 없음'으로 읽힌다 (기준파일 값 유지)
    assert edits["KT"]["성격"] == ""

    # 분류별 일괄: 통신비 전체를 '제외' → 개별 값보다 우선
    wb = load_workbook(out)
    wb["정기지출분석"]["N6"] = "제외"
    wb.save(out)
    wb.close()
    edits = fe.harvest_recurring_edits(out)
    assert edits["SKB"]["성격"] == "제외"
    assert edits["KT"]["성격"] == "제외"
    assert edits["코웨이"]["성격"] == ""              # 다른 분류는 그대로

    # 전체 일괄(K4)은 분류별보다도 우선한다
    wb = load_workbook(out)
    wb["정기지출분석"]["K4"] = "전체 비정기"
    wb.save(out)
    wb.close()
    edits = fe.harvest_recurring_edits(out)
    assert all(e["성격"] == "변동" for e in edits.values())

    # 기준파일 반영 → 다음 오버라이드로 적용
    from openpyxl import Workbook
    base = tmp_path / "기준.xlsx"
    nb = Workbook()
    nb.active.title = "카드결제기준"
    nb.save(base)
    nb.close()
    assert fe.update_override_sheet(base, edits) >= 2
    fe.apply_recurring_overrides(recurring, fe.load_recurring_overrides(base))
    assert all(i["성격"] == "변동" for i in recurring)


def test_계좌별_시나리오_인출_우선순위():
    """우리은행 부족분은 농협→국민 순으로 이체해 채운다."""
    daily = [{"일자": date(2026, 9, 21), "요일": "월", "실적": False,
              "온라인 예상입금": 0.0, "확정·기타입금": 0.0,
              "팀별 송금예정": 0.0, "카드결제": 0.0, "자동이체": 0.0,
              "기타지출": 300.0}]
    balances = {("우리은행", "W"): 100.0, ("농협", "N"): 150.0,
                ("국민은행", "K"): 1000.0}
    sc = fe.build_account_scenario(daily, balances, [])
    assert sc["accounts"][0] == ("우리은행", "W")
    row = sc["rows"][0]
    # 부족 200 = 농협 150 + 국민 50
    assert row["이체"] == {("농협", "N"): 150.0, ("국민은행", "K"): 50.0}
    assert round(row["잔액"][("우리은행", "W")]) == 0
    assert round(row["잔액"][("농협", "N")]) == 0
    assert round(row["잔액"][("국민은행", "K")]) == 950
    assert row["비고"] == ""

    # 전 계좌 소진 시 부족 경고
    daily2 = [dict(daily[0], 기타지출=2000.0)]
    sc2 = fe.build_account_scenario(daily2, balances, [])
    assert "부족" in sc2["rows"][0]["비고"]


def test_에이팜_판별과_지출예정_수집():
    """㈜에이팜 관련만 골라내고 자사명(에이팜건강)은 제외한다."""
    assert fe.mentions_apalm("㈜에이팜")
    assert fe.mentions_apalm("", "에이팜 외상대 지급")
    assert not fe.mentions_apalm("(주)에이팜건강")
    assert not fe.mentions_apalm("에이팜 건강 급여")   # 공백 변형도 자사
    assert not fe.mentions_apalm("콜마비앤에이치")

    masked = [
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 23),
         "팀명": "경영지원팀", "거래처": "㈜에이팜", "지출내용": "외상대 지급",
         "예상금액": 5_000_000.0, "지급방법": "계좌송금"},
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 22),
         "팀명": "디자인팀", "거래처": "OO인쇄", "지출내용": "리플렛",
         "예상금액": 25_000.0, "지급방법": "법인카드"},
        # 대외비 집계행은 수집하지 않는다
        {"반영상태": "정상반영", "confidential": True,
         "자금계획 반영일": date(2026, 9, 23), "거래처": "㈜에이팜",
         "지출내용": "(대외비 집계)", "예상금액": 1.0},
    ]
    adjustments = [
        {"일자": date(2026, 9, 25), "조정입금": 0.0, "조정지출": 3_000_000.0,
         "내용": "정기지출 추정(자동 초안): ㈜에이팜 신뢰도 상"},
        {"일자": date(2026, 9, 25), "조정입금": 0.0, "조정지출": 100_000.0,
         "내용": "정기지출 추정(자동 초안): SKB 신뢰도 상"},
    ]
    rows = fe.collect_apalm_expenses(masked, adjustments)
    assert [(r["출처"], r["거래처"], r["반영"]) for r in rows] == [
        ("팀 지출계획", "㈜에이팜", "반영"),
        ("정기지출 추정", "㈜에이팜", "반영")]
    assert rows[0]["예상금액"] == 5_000_000.0
    assert rows[1]["예상금액"] == 3_000_000.0


def test_비고_에이팜_표시는_자금계획에서_제외():
    """비고에 '에이팜'이 적힌 지출계획은 집계에서 빠지고 별도관리된다."""
    rows = [
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 30),
         "팀명": "경영지원팀", "거래처": "서원회계법인", "지출내용": "기장료",
         "예상금액": 330_000.0, "지급방법": "계좌송금", "비고": "에이팜"},
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 21),
         "팀명": "건강사업팀", "거래처": "네이버SA&GFA", "지출내용": "광고비",
         "예상금액": 3_498_000.0, "지급방법": "계좌송금",
         "비고": "화/수 2일치 금액"},
    ]
    plan = {"countable": list(rows), "integrated": rows}
    marked = fe.split_apalm_marked(plan)
    assert [r["거래처"] for r in marked] == ["서원회계법인"]
    assert marked[0]["반영상태"] == fe.APALM_EXCLUDED_STATUS
    assert [r["거래처"] for r in plan["countable"]] == ["네이버SA&GFA"]
    # 취합(integrated)에는 별도관리 상태로 남는다
    assert rows[0]["반영상태"] == fe.APALM_EXCLUDED_STATUS

    # 별도관리 건은 원본 상세 그대로 '미반영'으로 수집된다
    out = fe.collect_apalm_expenses(plan["countable"], [], marked)
    assert len(out) == 1
    assert out[0]["반영"] == "미반영(별도 관리)"
    assert out[0]["거래처"] == "서원회계법인"
    assert out[0]["비고"] == "에이팜"

    # 경영지원팀(대외비) 행도 상세를 싣되, 급여·세금보험류 분류만 가린다
    conf = [{"반영상태": fe.APALM_EXCLUDED_STATUS, "confidential": True,
             "자금계획 반영일": date(2026, 9, 30), "팀명": "경영지원팀",
             "거래처": "가가사무기", "지출내용": "복합기 임대",
             "예상금액": 280_000.0, "대외비구분": "", "비고": "에이팜"},
            {"반영상태": fe.APALM_EXCLUDED_STATUS, "confidential": True,
             "자금계획 반영일": date(2026, 9, 25), "팀명": "경영지원팀",
             "거래처": "메트라이프", "지출내용": "정기보험",
             "예상금액": 2_497_000.0, "대외비구분": "세금·보험(대외비)",
             "비고": "에이팜"}]
    out = fe.collect_apalm_expenses([], [], conf)
    by_amt = {r["예상금액"]: r for r in out}
    assert by_amt[280_000.0]["거래처"] == "가가사무기"      # 일반 내용은 노출
    assert by_amt[2_497_000.0]["거래처"] == "(대외비)"      # 민감 분류는 가림
    assert by_amt[2_497_000.0]["지출내용"] == "세금·보험(대외비)"


def test_비고에서_에이팜_제외():
    """4주일별계획 비고에는 에이팜 상세를 넣지 않는다."""
    import app as app_module

    daily = [{"일자": date(2026, 9, 23), "실적": False,
              "비고": "정기지출 추정(자동 초안): ㈜에이팜 신뢰도 상; "
                    "정기지출 추정(자동 초안): SKB 신뢰도 상"}]
    masked = [
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 23),
         "팀명": "경영지원팀", "거래처": "㈜에이팜", "지출내용": "외상대 지급",
         "예상금액": 5_000_000.0},
        {"반영상태": "정상반영", "자금계획 반영일": date(2026, 9, 23),
         "팀명": "디자인팀", "거래처": "OO인쇄", "지출내용": "리플렛",
         "예상금액": 25_000.0},
    ]
    app_module._annotate_daily_notes(daily, masked)
    note = daily[0]["비고"]
    assert "에이팜" not in note
    assert "OO인쇄" in note and "SKB" in note


def test_요일평균은_최근주에_가중치():
    """새로 올린 주의 실적이 예상 입금액에 더 크게 반영된다."""
    base = date(2026, 9, 21)  # 월요일
    history = [
        # 1주 전 월요일: 2백만 / 4주 전 월요일: 1백만
        _tx(date(2026, 9, 14), in_amt=2_000_000, cls="온라인매출입금"),
        _tx(date(2026, 8, 24), in_amt=1_000_000, cls="온라인매출입금"),
    ]
    plain = fe.weekday_online_averages(history, base, 12, recency_halflife=0)
    weighted = fe.weekday_online_averages(history, base, 12)
    # 단순 평균: 3백만 / 월요일 4회 = 75만
    assert round(plain[0]) == 750_000
    # 가중 평균은 최근 주(2백만) 쪽으로 끌려 올라간다
    assert weighted[0] > plain[0]
    # 다른 요일은 실적이 없으므로 0
    assert weighted[1] == 0.0


def test_성격_변동이면_자동초안_추정_제외():
    """외상매입금처럼 금액이 변하는 항목은 자동 초안 추정을 쓰지 않는다."""
    adjustments = [
        {"일자": date(2026, 9, 28), "조정입금": 0.0, "조정지출": 1_369_025.0,
         "내용": "정기지출 추정(자동 초안): 국민주식회사 에이팜 신뢰도 하"},
        {"일자": date(2026, 9, 30), "조정입금": 0.0, "조정지출": 100_000.0,
         "내용": "정기지출 추정(자동 초안): SKB 신뢰도 상"},
        # 입금 추정과 수동 조정은 건드리지 않는다
        {"일자": date(2026, 9, 30), "조정입금": 10_021_867.0, "조정지출": 0.0,
         "내용": "관계사 외상대 입금 추정(주식회사에이팜, 말일)"},
    ]
    overrides = {"국민주식회사 에이팜": {"분류": "외상매입금", "성격": "변동"},
                 "SKB": {"분류": "통신비", "성격": "정기"}}
    kept, dropped = fe.filter_adjustments_by_overrides(adjustments, overrides)
    assert len(dropped) == 1 and "에이팜" in dropped[0]["내용"]
    assert {a["내용"][:2] for a in kept} == {"정기", "관계"}

    # 성격을 '정기'로 되돌리면 다시 반영된다
    overrides["국민주식회사 에이팜"]["성격"] = "정기"
    kept2, dropped2 = fe.filter_adjustments_by_overrides(
        adjustments, overrides)
    assert not dropped2 and len(kept2) == 3


def test_금주일별_시나리오_생성():
    base = date(2026, 9, 21)  # 월요일
    fc = fe.build_forecast([], base, 1_000_000, [], [], [], [0.8, 0.9], 0.8)
    days = fc["rate_scenarios"][0.9]["금주일별"]
    assert len(days) == 5
    assert days[0][0] == base and days[-1][0] == date(2026, 9, 25)
