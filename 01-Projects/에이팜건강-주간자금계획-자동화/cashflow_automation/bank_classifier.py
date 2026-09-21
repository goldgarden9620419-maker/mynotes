# -*- coding: utf-8 -*-
"""은행 거래 자동분류 (17번 항목).

키워드 규칙은 00_프로그램/classify_rules.json에서 수정할 수 있고,
파일이 없으면 기본 규칙으로 생성한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from common import BANK_REFLECT_OK, CONF_CAT_PAYROLL, normalize_text

CLASS_INTERNAL = "내부이체"
CLASS_ONLINE_SALES = "온라인매출입금"
CLASS_REVIEW = "확인필요"

DEFAULT_RULES = {
    "rules": [
        {"분류": "4대보험", "은행": "우리은행",
         "키워드": ["사회보험", "건강보험", "국민연금", "고용보험", "산재보험"],
         "방향": "출금"},
        {"분류": "원천세·국세", "은행": "우리은행",
         "키워드": ["국고", "원천세", "국세"], "방향": "출금"},
        {"분류": "국민카드 결제", "키워드": ["KB카드출금", "KB카드"],
         "방향": "출금"},
        {"분류": "우리카드 결제", "키워드": ["우리카드결제대금", "우리카드"],
         "방향": "출금"},
        {"분류": "보험료",
         "키워드": ["한화생명", "메트라이프", "ABL생명", "미래에셋"],
         "방향": "출금"},
        {"분류": CLASS_ONLINE_SALES,
         "키워드": ["스마트스토어", "KG이니시스", "이니시스", "Npay",
                  "네이버페이", "NHN페이", "NHN KCP", "SSG상품대", "SSG"],
         "방향": "입금"},
    ],
    "top_withdrawal": {
        "은행": "국민은행",
        "키워드": ["TOP출금"],
        "month_end_day": 25,
        "월말분류": CONF_CAT_PAYROLL,
        "그외분류": CLASS_REVIEW,
    },
    # 내부이체 '후보' 키워드 — 키워드만으로 확정하지 않는다.
    # 네이버 광고비 충전 가상계좌처럼 계좌명에 광고주(회사)명이 붙는
    # 외부 지급('국민네이버 에이팜건', '국민네이버 apha')도 걸리므로,
    # 같은 날·같은 금액의 반대편 거래가 다른 우리 계좌에 있을 때만
    # 내부이체로 표시한다 (mark_internal_transfers).
    "internal_keywords": ["에이팜건강", "(주)에이팜건강", "에이팜건", "apha"],
}


def load_rules(rules_path: Path | None) -> dict:
    """분류 규칙을 읽는다. 없으면 기본 규칙 파일을 만들어 준다."""
    if rules_path is None:
        return DEFAULT_RULES
    rules_path = Path(rules_path)
    if not rules_path.exists():
        try:
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            with open(rules_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_RULES, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        return DEFAULT_RULES
    try:
        with open(rules_path, encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_RULES)
        merged.update({k: v for k, v in data.items() if v})
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_RULES


def _row_text(row: dict) -> str:
    return " ".join([
        normalize_text(row.get("적요")),
        normalize_text(row.get("기재내용·상대방")),
    ])


def _direction_ok(row: dict, direction: str) -> bool:
    if direction == "출금":
        return (row.get("출금액") or 0) > 0
    if direction == "입금":
        return (row.get("입금액") or 0) > 0
    return True


def mark_internal_transfers(rows: list[dict], rules: dict) -> None:
    """회사 계좌 간 이체를 표시한다 (전체 목록 기준으로 다시 판정).

    키워드(회사명)만으로 확정하면 네이버 광고비 충전 가상계좌처럼
    계좌명에 회사명이 붙는 외부 지급까지 내부이체가 되므로,
    같은 거래일·같은 금액의 반대편 거래가 '다른' 우리 계좌에 실제로
    있을 때만 짝으로 묶어 표시한다. 이전 실행이 남긴 표시는 지우고
    다시 판정하므로, 상대 계좌 파일이 늦게 들어와 한 다리만 보이던
    이체도 다음 실행에서 짝을 찾으면 자동으로 표시된다.
    """
    internal_keywords = [normalize_text(k)
                         for k in rules.get("internal_keywords", [])]

    def _candidate(row: dict) -> bool:
        text = _row_text(row)
        return any(k and k in text for k in internal_keywords)

    # 이전 표시를 지우고(현금유출입 복원) 아래에서 짝으로 다시 판정한다
    eligible: list[dict] = []
    for row in rows:
        if row.get("반영상태") != BANK_REFLECT_OK:
            continue
        if row.get("내부이체") or row.get("자동분류") == CLASS_INTERNAL:
            row["자동분류"] = ""
            row["내부이체"] = False
            row["현금유출입"] = ((row.get("입금액") or 0.0)
                                - (row.get("출금액") or 0.0))
        # 다른 규칙으로 이미 분류된 행(온라인매출 등)은 짝 후보에서 제외
        if not row.get("자동분류"):
            eligible.append(row)

    buckets: dict[tuple, dict[str, list[dict]]] = {}
    for row in eligible:
        out_amt = row.get("출금액") or 0.0
        in_amt = row.get("입금액") or 0.0
        if row.get("거래일") is None:
            continue
        if out_amt > 0:
            key, side = (row["거래일"], round(out_amt)), "출금"
        elif in_amt > 0:
            key, side = (row["거래일"], round(in_amt)), "입금"
        else:
            continue
        buckets.setdefault(key, {"입금": [], "출금": []})[side].append(row)

    def _acct(row: dict) -> tuple:
        return (row.get("은행"), row.get("계좌"))

    def _mark(row: dict) -> None:
        row["자동분류"] = CLASS_INTERNAL
        row["내부이체"] = True
        row["현금유출입"] = 0.0

    for pair in buckets.values():
        used: set[int] = set()
        for w in pair["출금"]:
            for d in pair["입금"]:
                if id(d) in used or _acct(d) == _acct(w):
                    continue
                if not (_candidate(w) or _candidate(d)):
                    continue
                used.add(id(d))
                _mark(w)
                _mark(d)
                break


def classify_rows(rows: list[dict], rules: dict) -> list[dict]:
    """자동분류·내부이체를 표시한다. 확인필요 목록을 돌려준다.

    내부이체는 현금유출입 0으로 만들어 실제 입금·지출 합계에서 제외한다.
    """
    issues: list[dict] = []
    top_cfg = rules.get("top_withdrawal", {}) or {}
    rule_list = rules.get("rules", [])

    # 1) 회사 계좌 간 이체 (짝이 확인된 거래만)
    mark_internal_transfers(rows, rules)

    for row in rows:
        if row.get("반영상태") != BANK_REFLECT_OK:
            continue
        if row.get("내부이체"):
            continue
        text = _row_text(row)

        # 2) 국민은행 TOP출금 (월말=급여, 그외=확인필요)
        if row.get("은행") == top_cfg.get("은행", "국민은행") and any(
                k in text for k in top_cfg.get("키워드", ["TOP출금"])):
            tx_date = row.get("거래일")
            month_end_day = int(top_cfg.get("month_end_day", 25))
            if tx_date is not None and tx_date.day >= month_end_day:
                row["자동분류"] = top_cfg.get("월말분류", CONF_CAT_PAYROLL)
            else:
                row["자동분류"] = top_cfg.get("그외분류", CLASS_REVIEW)
                issues.append({
                    "구분": "수동 대조 필요", "은행": row.get("은행"),
                    "내용": f"월말이 아닌 TOP출금 {int(row.get('출금액') or 0):,}원"
                           f" ({tx_date})",
                    "원본파일": row.get("원본파일", "")})
            continue

        # 3) 일반 키워드 규칙
        for rule in rule_list:
            bank = rule.get("은행")
            if bank and row.get("은행") != bank:
                continue
            if not _direction_ok(row, rule.get("방향", "")):
                continue
            if any(normalize_text(k) in text
                   for k in rule.get("키워드", []) if normalize_text(k)):
                row["자동분류"] = rule.get("분류", "")
                break
    return issues
