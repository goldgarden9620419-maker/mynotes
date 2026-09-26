# -*- coding: utf-8 -*-
"""지급 대조 매칭 개선(별칭·허용오차·합산) 테스트 — v12."""
from datetime import date

import payment_matcher as pm
from common import (BANK_REFLECT_OK, MATCH_AMOUNT_DIFF, MATCH_NOT_FOUND,
                    MATCH_PAID, MATCH_PARTIAL, REFLECT_OK)

RUN = date(2026, 9, 25)          # 금요일


def _plan(day, amount, vendor, method="자동이체", req="경영-20260918-001"):
    return {"요청ID": req, "팀명": "경영지원팀", "거래처": vendor,
            "지출내용": f"{vendor} 결제", "예상금액": amount,
            "자금계획 반영일": day, "지급예정일": day,
            "지급방법": method, "반영상태": REFLECT_OK}


def _tx(day, out, name, bank="우리은행", memo="인터넷"):
    return {"거래일": day, "거래일시": None, "은행": bank, "계좌": "220351",
            "출금액": out, "입금액": 0.0, "거래후잔액": 0.0,
            "적요": memo, "기재내용·상대방": name, "취급점": "",
            "자동분류": "", "내부이체": False, "정기지출후보": False,
            "반영상태": BANK_REFLECT_OK, "원본파일": "은행.xlsx"}


def test_별칭_한영표기_메트라이프_매칭():
    """'메트라이프' 계획이 영문 'METLIFE' CMS 출금과 매칭돼야 한다."""
    plans = [_plan(date(2026, 9, 21), 4_900_000, "메트라이프")]
    txs = [_tx(date(2026, 9, 21), 4_795_900, "METLIFE09002 CMS 공동",
               bank="국민은행", memo="CMS공동")]
    got = pm.match_payments(plans, txs, RUN)["results"][0]
    assert got["대조결과"] == MATCH_PARTIAL       # 2.1% 차이 — 일부지급 표시
    assert got["실제금액"] == 4_795_900
    assert got["차이금액"] == 4_795_900 - 4_900_000


def test_별칭_농협카드_NH카드대금_매칭():
    plans = [_plan(date(2026, 9, 23), 2_266_495, "농협카드")]
    txs = [_tx(date(2026, 9, 23), 2_311_495, "NH기업카드 NH카드대금",
               bank="농협", memo="NH카드")]
    got = pm.match_payments(plans, txs, RUN)["results"][0]
    assert got["대조결과"] == MATCH_AMOUNT_DIFF   # 2.0% 초과 지급
    assert got["실제금액"] == 2_311_495


def test_합산매칭_SKB_회선별_두건():
    """SK브로드밴드 계획 1건 = SKB 회선별 출금 2건의 합."""
    plans = [_plan(date(2026, 9, 21), 220_000, "SK브로드밴드")]
    txs = [_tx(date(2026, 9, 21), 134_622, "SKB6452342048"),
           _tx(date(2026, 9, 21), 85_621, "SKB6486358411")]
    matched = pm.match_payments(plans, txs, RUN)
    got = matched["results"][0]
    assert got["대조결과"] == MATCH_PAID
    assert got["실제금액"] == 220_243
    assert "합산" in got["비고"]
    assert sorted(got["_tx_indices"]) == [0, 1]
    # 합산에 쓰인 출금은 '계획없는출금'으로 남지 않는다
    assert matched["unplanned"] == []


def test_허용오차_이내는_지급완료():
    plans = [_plan(date(2026, 9, 22), 1_000_000, "테스트상사",
                   method="계좌송금")]
    txs = [_tx(date(2026, 9, 22), 999_500, "테스트상사")]
    got = pm.match_payments(plans, txs, RUN)["results"][0]
    assert got["대조결과"] == MATCH_PAID
    assert "허용 오차" in got["비고"]


def test_무관한_거래는_여전히_미매칭():
    """이름 유사도가 낮으면 별칭·합산이 없는 한 매칭하지 않는다."""
    plans = [_plan(date(2026, 9, 23), 3_498_000, "네이버SA&GFA",
                   method="계좌송금")]
    txs = [_tx(date(2026, 9, 23), 4_675_000, "농협하나로마트 결제",
               bank="국민은행")]
    got = pm.match_payments(plans, txs, RUN)["results"][0]
    assert got["대조결과"] == MATCH_NOT_FOUND


def test_사용자_별칭_추가():
    """classify_rules.json '매칭별칭'으로 새 묶음을 더할 수 있다."""
    plans = [_plan(date(2026, 9, 22), 500_000, "구글광고",
                   method="계좌송금")]
    txs = [_tx(date(2026, 9, 22), 497_000, "GOOGLE ADS KR")]
    base = pm.match_payments(plans, txs, RUN)["results"][0]
    assert base["대조결과"] == MATCH_NOT_FOUND
    got = pm.match_payments(plans, txs, RUN,
                            aliases=[["구글광고", "google ads"]])
    # 별칭으로 거래처가 확인되고 0.6% 차이는 허용 오차 내 → 지급완료
    assert got["results"][0]["대조결과"] == MATCH_PAID
    assert "허용 오차" in got["results"][0]["비고"]
