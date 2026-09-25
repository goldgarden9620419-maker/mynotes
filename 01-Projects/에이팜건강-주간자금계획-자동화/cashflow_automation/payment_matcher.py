# -*- coding: utf-8 -*-
"""지급예정(팀 계획)과 실제 출금(은행) 대조 (20번 항목).

대조 기준: ① 금액 ② 거래처·적요 유사도 ③ 지급예정일 전후 기간
④ 지급방법·출금계좌. 불확실한 건은 지급완료로 확정하지 않고
'수동확인필요'로 표시한다.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from rapidfuzz import fuzz

from common import (
    BANK_REFLECT_OK, MATCH_AMOUNT_DIFF, MATCH_DATE_DIFF, MATCH_MANUAL,
    MATCH_NOT_FOUND, MATCH_PAID, MATCH_PARTIAL, MATCH_UNPLANNED,
    PAY_METHOD_AUTO, PAY_METHOD_CARD, PAY_METHOD_TRANSFER,
    REFLECT_OK, REFLECT_PAID, classify_confidential, normalize_text,
)

_MIN_SCORE = 60          # 이 점수 미만이면 매칭 없음으로 본다
_AMBIGUITY_GAP = 5       # 1·2위 점수 차가 이내면 수동확인필요
_SUM_MATCH_MAX_TX = 8    # 합산 매칭에서 검토할 후보 출금 수 상한

# 계획서의 거래처명과 은행 적요가 서로 다른 표기(한/영, 약칭)를 쓰는
# 거래처 묶음. 같은 묶음의 표기는 동일 거래처로 보고 유사도를 계산한다.
# 사용자는 00_프로그램/classify_rules.json 에 "매칭별칭" 목록(같은 형식의
# 이중 리스트)을 추가해 묶음을 늘릴 수 있다.
_DEFAULT_ALIASES = [
    ["메트라이프", "metlife"],
    ["sk브로드밴드", "skb", "브로드밴드"],
    ["농협카드", "nh기업카드", "nh카드대금", "nh카드"],
    ["트라이앵글하모니", "트라이앵글"],
]


def _tx_text(tx: dict) -> str:
    return " ".join([normalize_text(tx.get("기재내용·상대방")),
                     normalize_text(tx.get("적요"))])


def _vendor_terms(vendor: str,
                  aliases: Optional[list[list[str]]]) -> list[str]:
    """거래처명 + 별칭 묶음에서 얻은 비교 표기 목록 (casefold 상태)."""
    v = vendor.casefold()
    terms = {v}
    for group in list(_DEFAULT_ALIASES) + list(aliases or []):
        folded = [normalize_text(t).casefold() for t in group
                  if normalize_text(t)]
        if any(t and (t in v or v in t) for t in folded):
            terms.update(t for t in folded if len(t) >= 2)
    return sorted(terms)


def _name_similarity(plan: dict, tx: dict,
                     aliases: Optional[list[list[str]]] = None) -> float:
    vendor = normalize_text(plan.get("거래처"))
    if not vendor:
        return 0.0
    text = _tx_text(tx).casefold()
    return max(float(fuzz.partial_ratio(term, text))
               for term in _vendor_terms(vendor, aliases))


def _method_matches(plan: dict, tx: dict) -> bool:
    method = plan.get("지급방법")
    cls = tx.get("자동분류") or ""
    if method == PAY_METHOD_CARD:
        return "카드" in cls
    if method in (PAY_METHOD_TRANSFER, PAY_METHOD_AUTO):
        return "카드" not in cls
    return False


def _score(plan: dict, tx: dict, name_threshold: float,
           window_days: int,
           aliases: Optional[list[list[str]]] = None) -> float:
    planned = plan.get("예상금액") or 0
    actual = tx.get("출금액") or 0
    plan_date = plan.get("자금계획 반영일") or plan.get("지급예정일")
    if plan_date is None or tx.get("거래일") is None or actual <= 0:
        return 0.0
    day_gap = abs((tx["거래일"] - plan_date).days)
    if day_gap > window_days:
        return 0.0

    score = 0.0
    if planned > 0:
        if abs(actual - planned) < 1:
            score += 50
        else:
            ratio = actual / planned
            if 0.5 <= ratio <= 1.5:
                score += 25
    sim = _name_similarity(plan, tx, aliases)
    if sim >= name_threshold:
        score += 30 * (sim / 100.0)
    score += max(0.0, 15 - 5 * day_gap)
    if _method_matches(plan, tx):
        score += 10
    return score


def match_payments(plans: list[dict], bank_rows: list[dict],
                   base_date: date, window_days: int = 3,
                   name_threshold: float = 70,
                   unplanned_days: int = 14,
                   aliases: Optional[list[list[str]]] = None,
                   amount_tolerance: float = 0.01) -> dict:
    """대조 수행.

    plans: 반영상태가 정상반영/지급완료인 행(대외비 포함, 내부용).
    bank_rows: 중복 제거·분류 완료된 표준 은행 행.
    unplanned_days: '계획없는출금'으로 표시할 최근 기간(과거 이력이
    길게 들어와도 지난 거래를 전부 확인필요로 만들지 않는다).
    aliases: classify_rules.json "매칭별칭"에서 온 거래처 별칭 묶음
    (기본 묶음 _DEFAULT_ALIASES에 더해진다).
    amount_tolerance: 이 비율 이내 금액 차이는 지급완료로 본다
    (CMS 수수료·소액 단수 차이 흡수).
    반환: {"results": [...], "unplanned": [...]}
    """
    unplanned_since = base_date - timedelta(days=unplanned_days)
    withdrawals = [tx for tx in bank_rows
                   if tx.get("반영상태") == BANK_REFLECT_OK
                   and not tx.get("내부이체")
                   and (tx.get("출금액") or 0) > 0]

    targets = []
    for plan in plans:
        status = plan.get("반영상태")
        if status not in (REFLECT_OK, REFLECT_PAID):
            continue
        plan_date = plan.get("자금계획 반영일") or plan.get("지급예정일")
        # 아직 도래하지 않은 예정 건은 대조 대상이 아니다
        if status == REFLECT_OK and (plan_date is None
                                     or plan_date > base_date):
            continue
        targets.append(plan)
    targets.sort(key=lambda p: (p.get("자금계획 반영일")
                                or p.get("지급예정일") or date.max))

    used_tx: set[int] = set()
    results: list[dict] = []
    for plan in targets:
        scored = []
        for idx, tx in enumerate(withdrawals):
            if idx in used_tx:
                continue
            s = _score(plan, tx, name_threshold, window_days, aliases)
            if s > 0:
                scored.append((s, idx))
        scored.sort(reverse=True)
        result = _decide(plan, scored, withdrawals, name_threshold,
                         aliases, amount_tolerance)
        if (result["대조결과"] in (MATCH_NOT_FOUND, MATCH_PARTIAL)
                or (result["대조결과"] == MATCH_MANUAL
                    and "후보 거래" in result["비고"])):
            # 단건으로 못 찾았거나, 일부지급으로 보이거나, 같은 거래처
            # 후보가 여러 건이라 모호한 경우: 그 출금들의 합이 계획
            # 금액과 (허용 오차 내로) 일치하면 합산 매칭이 더 정확한
            # 해석이다. 예: SKB 회선별 2건 = 계획 1건.
            combo = _sum_match(plan, withdrawals, used_tx, window_days,
                               name_threshold, aliases, amount_tolerance,
                               result)
            if combo is not None:
                result = combo
        used_tx.update(result.get("_tx_indices") or [])
        results.append(result)

    unplanned = []
    for idx, tx in enumerate(withdrawals):
        if idx in used_tx:
            continue
        if tx.get("거래일") is None or tx["거래일"] < unplanned_since:
            continue
        cls = tx.get("자동분류") or ""
        # 자동분류로 성격이 확인된 정기 성격의 출금은 계획없는출금에서 제외
        if cls and cls != "확인필요":
            continue
        unplanned.append({
            "요청ID": "", "팀명": "",
            "예정금액": None, "실제금액": tx.get("출금액"),
            "차이금액": None,
            "지급예정일": None, "실제출금일": tx.get("거래일"),
            "대조결과": MATCH_UNPLANNED,
            "거래처": _tx_text(tx)[:40], "은행": tx.get("은행"),
            "confidential": False,
            "비고": f"{tx.get('원본파일', '')}",
            "_tx_index": idx,
        })
    return {"results": results, "unplanned": unplanned}


def _decide(plan: dict, scored: list[tuple[float, int]],
            withdrawals: list[dict], name_threshold: float,
            aliases: Optional[list[list[str]]] = None,
            amount_tolerance: float = 0.01) -> dict:
    planned = plan.get("예상금액") or 0
    plan_date = plan.get("자금계획 반영일") or plan.get("지급예정일")
    base = {
        "요청ID": plan.get("요청ID", ""),
        "팀명": plan.get("팀명", ""),
        "예정금액": planned,
        "실제금액": None,
        "차이금액": None,
        "지급예정일": plan_date,
        "실제출금일": None,
        "대조결과": MATCH_NOT_FOUND,
        "거래처": plan.get("거래처", ""),
        "은행": "",
        "confidential": bool(plan.get("confidential")),
        "_conf_category": classify_confidential(
            plan.get("지출내용", ""), plan.get("대외비구분", ""))
        if plan.get("confidential") else "",
        "비고": "",
        "_tx_index": None,
        "_tx_indices": [],
    }
    if not scored or scored[0][0] < _MIN_SCORE:
        return base

    best_score, best_idx = scored[0]
    ambiguous = len(scored) > 1 and (best_score - scored[1][0]) < _AMBIGUITY_GAP
    tx = withdrawals[best_idx]
    actual = tx.get("출금액") or 0
    base.update({
        "실제금액": actual,
        "차이금액": actual - planned,
        "실제출금일": tx.get("거래일"),
        "은행": tx.get("은행", ""),
        "_tx_index": best_idx,
        "_tx_indices": [best_idx],
    })

    name_ok = _name_similarity(plan, tx, aliases) >= name_threshold
    amount_exact = abs(actual - planned) < 1
    within_tol = (planned > 0 and
                  abs(actual - planned) <= max(1.0,
                                               planned * amount_tolerance))

    if ambiguous:
        base["대조결과"] = MATCH_MANUAL
        base["비고"] = "후보 거래가 여러 건이라 수동확인 필요"
        return base
    if not name_ok and not _method_matches(plan, tx):
        base["대조결과"] = MATCH_MANUAL
        base["비고"] = "거래처·지급방법 근거가 약해 수동확인 필요"
        return base

    if amount_exact or (within_tol and name_ok):
        if plan_date is not None and tx.get("거래일") == plan_date:
            base["대조결과"] = MATCH_PAID
        else:
            base["대조결과"] = MATCH_DATE_DIFF
        if not amount_exact:
            base["비고"] = (f"금액 차이 {actual - planned:+,.0f}원 "
                          f"(허용 오차 내 — 지급완료 처리)")
    elif actual < planned:
        base["대조결과"] = MATCH_PARTIAL
    else:
        base["대조결과"] = MATCH_AMOUNT_DIFF
    return base


def _sum_match(plan: dict, withdrawals: list[dict], used_tx: set[int],
               window_days: int, name_threshold: float,
               aliases: Optional[list[list[str]]],
               amount_tolerance: float, base: dict) -> Optional[dict]:
    """같은 거래처 출금 여러 건의 합으로 계획 1건을 맞춘다.

    예: SK브로드밴드 220,000원 계획 ↔ SKB 회선별 2건(134,622+85,621).
    거래처 유사도가 기준 이상인 미사용 출금만 후보로 하고, 합이 계획
    금액과 허용 오차 이내로 일치할 때만 매칭한다 (큰 묶음 우선).
    """
    from itertools import combinations

    planned = plan.get("예상금액") or 0
    plan_date = plan.get("자금계획 반영일") or plan.get("지급예정일")
    if planned <= 0 or plan_date is None:
        return None
    candidates = []
    for idx, tx in enumerate(withdrawals):
        if idx in used_tx or tx.get("거래일") is None:
            continue
        if abs((tx["거래일"] - plan_date).days) > window_days:
            continue
        if (tx.get("출금액") or 0) <= 0:
            continue
        if _name_similarity(plan, tx, aliases) >= name_threshold:
            candidates.append(idx)
    if len(candidates) < 2:
        return None
    candidates = candidates[:_SUM_MATCH_MAX_TX]
    tol = max(1.0, planned * amount_tolerance)
    for size in range(len(candidates), 1, -1):
        for combo in combinations(candidates, size):
            total = sum(withdrawals[i].get("출금액") or 0 for i in combo)
            if abs(total - planned) > tol:
                continue
            txs = [withdrawals[i] for i in combo]
            result = dict(base)
            result.update({
                "실제금액": total,
                "차이금액": total - planned,
                "실제출금일": max(t["거래일"] for t in txs),
                "은행": txs[0].get("은행", ""),
                "대조결과": MATCH_PAID,
                "비고": f"같은 거래처 출금 {len(txs)}건 합산 매칭"
                       + (f" (금액 차이 {total - planned:+,.0f}원)"
                          if abs(total - planned) >= 1 else ""),
                "_tx_index": combo[0],
                "_tx_indices": list(combo),
            })
            return result
    return None
