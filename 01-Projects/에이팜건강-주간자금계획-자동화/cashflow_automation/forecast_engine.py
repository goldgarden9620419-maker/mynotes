# -*- coding: utf-8 -*-
"""입금 예측과 4주 일별 / 13주 주별 자금계획, 정기지출 분석 (21~24번).

- 온라인 입금: 최근 12주 요일별 평균 × 반영률(기본 80%)
- 4주 일별: 팀 확정 지출 + 주간조정
- 13주 주별: 1~4주는 일별 합산, 5~13주는 요일평균·팀계획·정기지출·카드
- 정기지출: 최근 6개월 중 4개월 이상 반복된 출금
"""
from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Optional

from common import (
    BANK_REFLECT_OK, PAY_METHOD_AUTO, PAY_METHOD_CARD, PAY_METHOD_TRANSFER,
    normalize_text, parse_amount, parse_date, weekday_ko, week_monday,
)
from bank_classifier import CLASS_ONLINE_SALES

STATE_OK = "정상"
STATE_WARN = "주의"
STATE_SHORTAGE = "자금부족"

ADJUST_SHEET_NAME = "주간조정"


# ---------------------------------------------------------------------------
# 주간조정 시트 (기준파일, 선택사항)
# ---------------------------------------------------------------------------

def load_adjustments(base_workbook: Path) -> list[dict]:
    """기준파일의 '주간조정' 시트: 일자·조정입금·조정지출·내용."""
    base_workbook = Path(base_workbook)
    if not base_workbook.exists():
        return []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook, data_only=True, read_only=True)
    except Exception:
        return []
    try:
        sheet = None
        for name in wb.sheetnames:
            if normalize_text(name) == ADJUST_SHEET_NAME:
                sheet = wb[name]
                break
        if sheet is None:
            return []
        rows = list(sheet.iter_rows(values_only=True))
        header_idx = None
        header: list[str] = []
        for i, row in enumerate(rows[:10]):
            values = [normalize_text(v) for v in row]
            if "일자" in values:
                header_idx, header = i, values
                break
        if header_idx is None:
            return []
        result = []
        for row in rows[header_idx + 1:]:
            raw = {header[i]: row[i] for i in range(min(len(header), len(row)))
                   if header[i]}
            d = parse_date(raw.get("일자"))
            if d is None:
                continue
            result.append({
                "일자": d,
                "조정입금": parse_amount(raw.get("조정입금")) or 0.0,
                "조정지출": parse_amount(raw.get("조정지출")) or 0.0,
                "내용": normalize_text(raw.get("내용")),
            })
        return result
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# 온라인 입금 요일 평균 (21번 항목)
# ---------------------------------------------------------------------------

def weekday_online_averages(history_rows: list[dict], base_date: date,
                            weeks: int = 12) -> dict[int, float]:
    """최근 N주의 요일별 온라인 매출 입금 평균."""
    start = base_date - timedelta(days=weeks * 7)
    daily: dict[date, float] = defaultdict(float)
    for row in history_rows:
        if row.get("자동분류") != CLASS_ONLINE_SALES or row.get("내부이체"):
            continue
        d = row.get("거래일")
        if d is None or not (start <= d < base_date):
            continue
        daily[d] += row.get("입금액") or 0.0

    if not daily:
        return {i: 0.0 for i in range(7)}

    data_start = max(start, min(daily))
    sums = defaultdict(float)
    counts = defaultdict(int)
    d = data_start
    while d < base_date:
        sums[d.weekday()] += daily.get(d, 0.0)
        counts[d.weekday()] += 1
        d += timedelta(days=1)
    return {i: (sums[i] / counts[i] if counts[i] else 0.0) for i in range(7)}


# ---------------------------------------------------------------------------
# 정기지출 분석 (24번 항목)
# ---------------------------------------------------------------------------

OVERRIDE_SHEET_NAME = "정기지출분류"
_NATURE_VALUES = ("정기", "변동", "제외")


def load_recurring_overrides(base_workbook: Path) -> dict[str, dict]:
    """기준파일 '정기지출분류' 시트: 정기지출명 → {분류, 성격}.

    성격은 정기(기본)/변동/제외. 변동·제외는 13주 자동 추정에서 뺀다
    (예: 외상대 지급처럼 매월 나가지만 금액이 구매량에 따라 변하는 지출).
    사용자가 이 시트를 수정하면 다음 실행부터 반영된다.
    """
    overrides: dict[str, dict] = {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook, data_only=True, read_only=True)
    except Exception:
        return overrides
    try:
        if OVERRIDE_SHEET_NAME not in wb.sheetnames:
            return overrides
        ws = wb[OVERRIDE_SHEET_NAME]
        for row in ws.iter_rows(min_row=2, max_col=3, values_only=True):
            name = normalize_text(row[0] if len(row) > 0 else None)
            if not name:
                continue
            cls = normalize_text(row[1] if len(row) > 1 else None)
            nature = normalize_text(row[2] if len(row) > 2 else None)
            if nature and nature not in _NATURE_VALUES:
                nature = ""
            overrides[name] = {"분류": cls, "성격": nature or "정기"}
        return overrides
    finally:
        wb.close()


def apply_recurring_overrides(recurring_items: list[dict],
                              overrides: dict[str, dict]) -> None:
    """정기지출 목록에 사용자 분류·성격을 적용한다 (제자리 수정)."""
    for item in recurring_items:
        ov = overrides.get(item.get("정기지출명", ""))
        if ov:
            if ov.get("분류"):
                item["분류"] = ov["분류"]
            item["성격"] = ov.get("성격") or "정기"
        elif "외상" in (item.get("분류") or ""):
            item["성격"] = "변동"  # 외상대 지급은 기본적으로 변동 취급
        else:
            item.setdefault("성격", "정기")


def ensure_recurring_override_sheet(base_workbook: Path,
                                    recurring_items: list[dict]) -> int:
    """기준파일에 '정기지출분류' 시트를 만들고 새 항목을 추가한다.

    기존 행(사용자 수정 포함)은 건드리지 않는다. 추가된 행 수를 돌려준다.
    """
    try:
        from openpyxl import load_workbook
        wb = load_workbook(base_workbook)
    except Exception:
        return 0
    try:
        if OVERRIDE_SHEET_NAME in wb.sheetnames:
            ws = wb[OVERRIDE_SHEET_NAME]
        else:
            ws = wb.create_sheet(OVERRIDE_SHEET_NAME)
            ws.append(["정기지출명", "분류", "성격"])
            ws.append(["(안내) 성격: 정기=매월 자동 추정 반영 / "
                       "변동=외상대 등 금액 변동(추정 제외) / 제외",
                       "", ""])
        existing = {normalize_text(row[0])
                    for row in ws.iter_rows(min_row=2, max_col=1,
                                            values_only=True)
                    if row and row[0]}
        added = 0
        for item in recurring_items:
            name = item.get("정기지출명", "")
            if not name or name in existing:
                continue
            ws.append([name, item.get("분류") or "",
                       item.get("성격") or "정기"])
            existing.add(name)
            added += 1
        if added:
            wb.save(base_workbook)
        return added
    finally:
        wb.close()


def _recurring_name_key(row: dict) -> str:
    text = normalize_text(row.get("기재내용·상대방")) \
        or normalize_text(row.get("적요"))
    text = re.sub(r"[\d\-/.,()*:]+", "", text)
    return text.strip()[:20]


def analyze_recurring(history_rows: list[dict], base_date: date,
                      lookback_months: int = 6,
                      min_months: int = 4) -> list[dict]:
    """최근 6개월 중 4개월 이상 반복된 출금을 찾는다."""
    start = base_date - timedelta(days=lookback_months * 31)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in history_rows:
        if row.get("내부이체") or (row.get("출금액") or 0) <= 0:
            continue
        d = row.get("거래일")
        if d is None or not (start <= d < base_date):
            continue
        key_name = _recurring_name_key(row)
        if not key_name:
            continue
        groups[(row.get("은행", ""), key_name)].append(row)

    items = []
    for (bank, name), rows in groups.items():
        months: dict[tuple, float] = defaultdict(float)
        days = []
        for row in rows:
            d = row["거래일"]
            months[(d.year, d.month)] += row["출금액"]
            days.append(d.day)
        if len(months) < min_months:
            continue
        monthly = list(months.values())
        rep_day = int(median(days))
        day_spread = max(days) - min(days)
        if len(months) >= lookback_months and day_spread <= 5:
            confidence = "상"
        elif day_spread <= 10:
            confidence = "중"
        else:
            confidence = "하"
        cls = next((r.get("자동분류") for r in rows if r.get("자동분류")), "")
        items.append({
            "은행": bank,
            "정기지출명": name,
            "분류": cls,
            "발생개월수": len(months),
            "거래건수": len(rows),
            "평균 월지출": sum(monthly) / len(monthly),
            "최소 월지출": min(monthly),
            "최대 월지출": max(monthly),
            "대표 지급일": rep_day,
            "신뢰도": confidence,
        })
        for row in rows:
            row["정기지출후보"] = True
    items.sort(key=lambda x: -x["평균 월지출"])
    return items


# ---------------------------------------------------------------------------
# 4주 일별 / 13주 주별 계획 (22~23번 항목)
# ---------------------------------------------------------------------------

def _plan_amounts_by_date(plans: list[dict]) -> dict[date, dict[str, float]]:
    """반영일별 (송금, 카드, 자동이체) 합계."""
    result: dict[date, dict[str, float]] = defaultdict(
        lambda: {"송금": 0.0, "카드": 0.0, "자동이체": 0.0})
    for plan in plans:
        d = plan.get("자금계획 반영일")
        amount = plan.get("예상금액") or 0.0
        if d is None or amount == 0:
            continue
        method = plan.get("지급방법")
        if method == PAY_METHOD_TRANSFER:
            result[d]["송금"] += amount
        elif method == PAY_METHOD_CARD:
            result[d]["카드"] += amount
        elif method == PAY_METHOD_AUTO:
            result[d]["자동이체"] += amount
        else:
            result[d]["송금"] += amount
    return result


def actual_daily_flows(history_rows: list[dict],
                       base_date: date) -> tuple[dict, Optional[date]]:
    """기준일 이후 실제 외부 입출금을 일자별로 집계한다.

    반환: ({일자: {"온라인입금","기타입금","출금"}}, 마지막 실적일)
    내부이체는 총잔액에 영향이 없으므로 제외한다.
    """
    flows: dict[date, dict[str, float]] = {}
    last: Optional[date] = None
    for r in history_rows:
        d = r.get("거래일")
        if d is None or d < base_date or r.get("내부이체"):
            continue
        f = flows.setdefault(d, {"온라인입금": 0.0, "기타입금": 0.0,
                                 "출금": 0.0})
        amount_in = r.get("입금액") or 0.0
        amount_out = r.get("출금액") or 0.0
        if amount_in:
            key = ("온라인입금" if r.get("자동분류") == CLASS_ONLINE_SALES
                   else "기타입금")
            f[key] += amount_in
        if amount_out:
            f["출금"] += amount_out
        if last is None or d > last:
            last = d
    return flows, last


def filter_duplicate_adjustments(adjustments: list[dict],
                                 countable_plans: list[dict],
                                 window_days: int = 5,
                                 tolerance: float = 0.25,
                                 name_threshold: int = 60
                                 ) -> tuple[list[dict], list[dict]]:
    """팀 지출계획과 겹치는 '자동 초안' 추정 조정을 제외한다.

    같은 지출이 정기지출 추정(주간조정)과 팀 제출 계획 양쪽에서
    이중 반영되는 것을 막는다. 금액만 비슷한 우연 일치를 배제하기 위해
    이름 유사도(거래처·지출내용)가 임계값 이상일 때만 중복으로 본다.
    사용자가 직접 넣은 조정(내용에 '자동 초안'이 없는 행)은 건드리지 않는다.
    반환: (남긴 조정, 제외한 조정)
    """
    from rapidfuzz import fuzz

    kept, skipped = [], []
    plans = []
    for p in countable_plans:
        d = p.get("자금계획 반영일")
        amt = p.get("예상금액") or 0.0
        if d is None or amt <= 0:
            continue
        name = " ".join(str(p.get(k) or "") for k in ("거래처", "지출내용"))
        plans.append((d, amt, name.lower()))
    for adj in adjustments:
        amount = adj.get("조정지출") or 0.0
        content = adj.get("내용") or ""
        dup = False
        if "자동 초안" in content and amount > 0:
            m = re.search(r":\s*(.+?)\s*신뢰도", content)
            adj_name = (m.group(1) if m else content).lower()
            for d, plan_amt, plan_name in plans:
                if abs((d - adj["일자"]).days) > window_days:
                    continue
                if abs(plan_amt - amount) > max(plan_amt, amount) * tolerance:
                    continue
                if fuzz.partial_ratio(adj_name, plan_name) >= name_threshold:
                    dup = True
                    break
        (skipped if dup else kept).append(adj)
    return kept, skipped


def build_daily_plan(countable_plans: list[dict], base_date: date,
                     opening_balance: float, weekday_avg: dict[int, float],
                     rate: float, adjustments: list[dict],
                     minimum_balance: float = 0,
                     days: int = 28,
                     actual_flows: Optional[dict] = None,
                     actual_until: Optional[date] = None) -> list[dict]:
    """4주(28일) 일별 자금계획.

    actual_until까지의 날짜는 예측 대신 실제 입출금(실적)으로 채운다.
    opening_balance는 base_date 시작 시점 잔액이어야 한다.
    """
    by_date = _plan_amounts_by_date(countable_plans)
    adj_by_date: dict[date, dict] = defaultdict(
        lambda: {"입금": 0.0, "지출": 0.0, "내용": []})
    for adj in adjustments:
        a = adj_by_date[adj["일자"]]
        a["입금"] += adj["조정입금"]
        a["지출"] += adj["조정지출"]
        if adj["내용"]:
            a["내용"].append(adj["내용"])

    rows = []
    balance = opening_balance
    for i in range(days):
        d = base_date + timedelta(days=i)
        is_actual = (actual_until is not None and d <= actual_until)
        if is_actual:
            f = (actual_flows or {}).get(
                d, {"온라인입금": 0.0, "기타입금": 0.0, "출금": 0.0})
            online = f["온라인입금"]
            adj_in = f["기타입금"]
            planned = {"송금": 0.0, "카드": 0.0, "자동이체": 0.0}
            etc_out = f["출금"]
            note = "실적(실제 입출금 반영)"
        else:
            online = weekday_avg.get(d.weekday(), 0.0) * rate
            adj = adj_by_date.get(d, {"입금": 0.0, "지출": 0.0, "내용": []})
            adj_in = adj["입금"]
            planned = by_date.get(d, {"송금": 0.0, "카드": 0.0,
                                      "자동이체": 0.0})
            etc_out = adj["지출"]
            note = "; ".join(adj["내용"])
        inflow = online + adj_in
        outflow = planned["송금"] + planned["카드"] + planned["자동이체"] + etc_out
        net = inflow - outflow
        opening = balance
        balance = opening + net
        if balance < 0:
            state = STATE_SHORTAGE
        elif balance < minimum_balance:
            state = STATE_WARN
        else:
            state = STATE_OK
        rows.append({
            "일자": d, "요일": weekday_ko(d),
            "온라인 예상입금": online,
            "확정·기타입금": adj_in,
            "팀별 송금예정": planned["송금"],
            "카드결제": planned["카드"],
            "자동이체": planned["자동이체"],
            "기타지출": etc_out,
            "순현금흐름": net,
            "기초잔액": opening,
            "기말잔액": balance,
            "상태": state,
            "비고": note,
            "실적": is_actual,
        })
    return rows


def build_weekly_plan(countable_plans: list[dict], base_date: date,
                      daily_rows: list[dict], weekday_avg: dict[int, float],
                      rate: float, recurring_items: list[dict],
                      adjustments: list[dict],
                      minimum_balance: float = 0,
                      weeks: int = 13) -> list[dict]:
    """13주 주별 자금계획. base_date는 월요일이어야 한다."""
    base_monday = week_monday(base_date)
    by_date = _plan_amounts_by_date(countable_plans)

    # 정기지출을 대표 지급일 기준으로 미래 날짜에 배분 (5주차 이후용)
    recurring_by_date: dict[date, dict[str, float]] = defaultdict(
        lambda: {"카드": 0.0, "기타": 0.0})
    horizon_end = base_monday + timedelta(weeks=weeks)
    for item in recurring_items:
        day = int(item.get("대표 지급일") or 0)
        if not 1 <= day <= 31:
            continue
        amount = item.get("평균 월지출") or 0.0
        y, m = base_monday.year, base_monday.month
        for _ in range(weeks // 4 + 2):
            settle = date(y, m, min(day, calendar.monthrange(y, m)[1]))
            if base_monday <= settle < horizon_end:
                bucket = "카드" if "카드" in (item.get("분류") or "") else "기타"
                recurring_by_date[settle][bucket] += amount
            m += 1
            if m > 12:
                y, m = y + 1, 1

    adj_by_date: dict[date, dict] = defaultdict(lambda: {"입금": 0.0, "지출": 0.0})
    for adj in adjustments:
        adj_by_date[adj["일자"]]["입금"] += adj["조정입금"]
        adj_by_date[adj["일자"]]["지출"] += adj["조정지출"]

    weekly_online_full = sum(weekday_avg.values()) * rate

    rows = []
    balance = None
    for w in range(weeks):
        w_start = base_monday + timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        label = f"{w + 1}주차"
        period = f"{w_start.strftime('%m/%d')}~{w_end.strftime('%m/%d')}"
        if w < 4 and daily_rows:
            in_week = [r for r in daily_rows if w_start <= r["일자"] <= w_end]
            online = sum(r["온라인 예상입금"] for r in in_week)
            adj_in = sum(r["확정·기타입금"] for r in in_week)
            transfer = sum(r["팀별 송금예정"] for r in in_week)
            card = sum(r["카드결제"] for r in in_week)
            auto = sum(r["자동이체"] for r in in_week)
            etc = sum(r["기타지출"] for r in in_week)
            if balance is None and in_week:
                balance = in_week[0]["기초잔액"]
        else:
            online = weekly_online_full
            adj_in = 0.0
            transfer = card = auto = etc = 0.0
            d = w_start
            while d <= w_end:
                planned = by_date.get(d)
                if planned:
                    transfer += planned["송금"]
                    card += planned["카드"]
                    auto += planned["자동이체"]
                rec = recurring_by_date.get(d)
                if rec:
                    card += rec["카드"]
                    etc += rec["기타"]
                adj = adj_by_date.get(d)
                if adj:
                    adj_in += adj["입금"]
                    etc += adj["지출"]
                d += timedelta(days=1)
        income = online + adj_in
        net = income - (transfer + card + auto + etc)
        opening = balance if balance is not None else 0.0
        closing = opening + net
        balance = closing
        if closing < 0:
            state = STATE_SHORTAGE
        elif closing < minimum_balance:
            state = STATE_WARN
        else:
            state = STATE_OK
        rows.append({
            "주차": label, "기간": period,
            "예상입금": income, "온라인입금": online, "확정기타입금": adj_in,
            "송금예정": transfer, "카드결제": card,
            "자동이체": auto, "기타지출": etc, "순현금흐름": net,
            "기말잔액": closing, "상태": state,
        })
    return rows


# ---------------------------------------------------------------------------
# 반영률 시나리오 (21번 항목)
# ---------------------------------------------------------------------------

def build_forecast(countable_plans: list[dict], base_date: date,
                   opening_balance: float, history_rows: list[dict],
                   adjustments: list[dict], recurring_items: list[dict],
                   rates: list[float], default_rate: float,
                   minimum_balance: float = 0,
                   history_weeks: int = 12) -> dict:
    """전체 예측 결과와 반영률별 시나리오를 만든다.

    opening_balance는 '현재(최신 거래내역 기준) 총잔액'이다.
    기준일~마지막 실적일 구간은 실제 입출금으로 채우므로,
    일별 계획의 시작잔액은 실적 순증감을 되돌린 기준일 시작잔액을 쓴다.
    """
    weekday_avg = weekday_online_averages(history_rows, base_date,
                                          history_weeks)
    actual_flows, actual_until = actual_daily_flows(history_rows, base_date)
    net_actual = sum(f["온라인입금"] + f["기타입금"] - f["출금"]
                     for f in actual_flows.values())
    start_balance = opening_balance - net_actual
    scenarios = {}
    main = None
    for rate in sorted(set(list(rates) + [default_rate])):
        daily = build_daily_plan(countable_plans, base_date, start_balance,
                                 weekday_avg, rate, adjustments,
                                 minimum_balance,
                                 actual_flows=actual_flows,
                                 actual_until=actual_until)
        weekly = build_weekly_plan(countable_plans, base_date, daily,
                                   weekday_avg, rate, recurring_items,
                                   adjustments, minimum_balance)
        min_row = min(daily, key=lambda r: r["기말잔액"]) if daily else None
        shortage = next((r["일자"] for r in daily
                         if r["상태"] == STATE_SHORTAGE), None)
        scenario = {
            "rate": rate,
            "4주 온라인입금": sum(r["온라인 예상입금"] for r in daily),
            "4주 기말잔액": daily[-1]["기말잔액"] if daily else 0.0,
            "4주 최저잔액": min_row["기말잔액"] if min_row else 0.0,
            "4주 최저잔액일": min_row["일자"] if min_row else None,
            "13주 온라인입금": sum(r["예상입금"] for r in weekly),
            "13주 기말잔액": weekly[-1]["기말잔액"] if weekly else 0.0,
            "자금부족 예상일": shortage,
            "안내": _scenario_note(rate, daily, minimum_balance),
        }
        scenarios[rate] = scenario
        if abs(rate - default_rate) < 1e-9:
            main = {"daily": daily, "weekly": weekly, "scenario": scenario}

    return {
        "base_date": base_date,
        "rate": default_rate,
        "weekday_avg": weekday_avg,
        "daily": main["daily"] if main else [],
        "weekly": main["weekly"] if main else [],
        "scenario": main["scenario"] if main else {},
        "rate_scenarios": scenarios,
        "opening_balance": opening_balance,
        "start_balance": start_balance,
        "actual_until": actual_until,
        "minimum_balance": minimum_balance,
    }


def _scenario_note(rate: float, daily: list[dict],
                   minimum_balance: float) -> str:
    if not daily:
        return "계산할 일별 자료가 없습니다."
    shortage = [r for r in daily if r["상태"] == STATE_SHORTAGE]
    warn = [r for r in daily if r["상태"] == STATE_WARN]
    pct = int(round(rate * 100))
    if shortage:
        first = shortage[0]["일자"]
        return (f"반영률 {pct}% 기준 {first.strftime('%m월 %d일')}에 "
                f"잔액이 0원 미만으로 예상됩니다. 자금 조치가 필요합니다.")
    if warn:
        first = warn[0]["일자"]
        return (f"반영률 {pct}% 기준 {first.strftime('%m월 %d일')}에 "
                f"최소 필요잔액({minimum_balance:,.0f}원) 아래로 내려갑니다.")
    return f"반영률 {pct}% 기준 4주간 자금부족 없이 운영 가능합니다."
