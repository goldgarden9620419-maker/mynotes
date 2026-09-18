# -*- coding: utf-8 -*-
"""지급예정(팀 계획)과 실제 출금(은행) 대조 (20번 항목).

대조 기준: ① 금액 ② 거래처·적요 유사도 ③ 지급예정일 전후 기간
④ 지급방법·출금계좌. 불확실한 건은 지급완료로 확정하지 않고
'수동확인필요'로 표시한다.
"""
from __future__ import annotations

from datetime import date
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


def _tx_text(tx: dict) -> str:
    return " ".join([normalize_text(tx.get("기재내용·상대방")),
                     normalize_text(tx.get("적요"))])


def _name_similarity(plan: dict, tx: dict) -> float:
    vendor = normalize_text(plan.get("거래처"))
    if not vendor:
        return 0.0
    return float(fuzz.partial_ratio(vendor, _tx_text(tx)))


def _method_matches(plan: dict, tx: dict) -> bool:
    method = plan.get("지급방법")
    cls = tx.get("자동분류") or ""
    if method == PAY_METHOD_CARD:
        return "카드" in cls
    if method in (PAY_METHOD_TRANSFER, PAY_METHOD_AUTO):
        return "카드" not in cls
    return False


def _score(plan: dict, tx: dict, name_threshold: float,
           window_days: int) -> float:
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
    sim = _name_similarity(plan, tx)
    if sim >= name_threshold:
        score += 30 * (sim / 100.0)
    score += max(0.0, 15 - 5 * day_gap)
    if _method_matches(plan, tx):
        score += 10
    return score


def match_payments(plans: list[dict], bank_rows: list[dict],
                   base_date: date, window_days: int = 3,
                   name_threshold: float = 70) -> dict:
    """대조 수행.

    plans: 반영상태가 정상반영/지급완료인 행(대외비 포함, 내부용).
    bank_rows: 중복 제거·분류 완료된 표준 은행 행.
    반환: {"results": [...], "unplanned": [...]}
    """
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
            s = _score(plan, tx, name_threshold, window_days)
            if s > 0:
                scored.append((s, idx))
        scored.sort(reverse=True)
        result = _decide(plan, scored, withdrawals, name_threshold)
        if result["_tx_index"] is not None:
            used_tx.add(result["_tx_index"])
        results.append(result)

    unplanned = []
    for idx, tx in enumerate(withdrawals):
        if idx in used_tx:
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
            withdrawals: list[dict], name_threshold: float) -> dict:
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
    })

    name_ok = _name_similarity(plan, tx) >= name_threshold
    amount_exact = abs(actual - planned) < 1

    if ambiguous:
        base["대조결과"] = MATCH_MANUAL
        base["비고"] = "후보 거래가 여러 건이라 수동확인 필요"
        return base
    if not name_ok and not _method_matches(plan, tx):
        base["대조결과"] = MATCH_MANUAL
        base["비고"] = "거래처·지급방법 근거가 약해 수동확인 필요"
        return base

    if amount_exact:
        if plan_date is not None and tx.get("거래일") == plan_date:
            base["대조결과"] = MATCH_PAID
        else:
            base["대조결과"] = MATCH_DATE_DIFF
    elif actual < planned:
        base["대조결과"] = MATCH_PARTIAL
    else:
        base["대조결과"] = MATCH_AMOUNT_DIFF
    return base
