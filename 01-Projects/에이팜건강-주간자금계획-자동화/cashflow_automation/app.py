# -*- coding: utf-8 -*-
"""(주)에이팜건강 주간 자금계획 자동화 — 메인 실행부.

사용법:
  python app.py             # 트레이 + 스케줄러 상주 실행 (기본)
  python app.py --run-now   # 지금 1회 실행 후 종료
  python app.py --once      # 미실행 보완 검사 1회 후 종료
  python app.py --status    # 이번 주 실행상태 출력
  python app.py --headless  # 트레이 없이 상주 실행
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

from common import (
    APP_VERSION, BANK_REFLECT_OK, MATCH_NOT_FOUND, REFLECT_OK, REFLECT_PAID,
    STATUS_FAILED, STATUS_PARTIAL, STATUS_REVIEW_WAIT, STATUS_SUCCESS,
    STATUS_WAITING_FILES, iso_week_key, now_local, unique_path, week_monday,
)
from config import Config
from state_manager import LockError, RunLock, StateManager
from logger import get_logger
import backup_manager
import bank_classifier
import bank_loader
import duplicate_checker
import excel_report
import file_validator
import forecast_engine
import live_report
import management_report
import payment_matcher
import pdf_report
import team_loader
from card_payment import CardPaymentCalculator


class RunResult:
    def __init__(self, status: str, message: str = "",
                 output_files: list[Path] | None = None,
                 issue_count: int = 0):
        self.status = status
        self.message = message
        self.output_files = output_files or []
        self.issue_count = issue_count

    def __repr__(self):
        return f"RunResult({self.status}, {self.message})"


def run_weekly_job(cfg: Config, state: StateManager, log,
                   mode: str = "auto", now=None,
                   allow_partial: bool = False,
                   force: bool = False) -> RunResult:
    """주간 자금계획 파이프라인 전체 실행 (2번 항목 흐름)."""
    now = now or now_local(cfg.timezone_name)
    week_key = iso_week_key(now.date())
    base_date = week_monday(now.date())

    # 지난 주 미완료 기록 정리 (18번 항목)
    last_week = state.state.get("last_run_week")
    if last_week and last_week != week_key \
            and state.state.get("last_run_status") not in (STATUS_SUCCESS, ""):
        state.record_pending_week(last_week, state.state["last_run_status"])

    signature = file_validator.current_input_signature(cfg)
    if not force and state.is_week_completed(now) \
            and state.state.get("input_signature") == signature:
        return RunResult("SKIPPED",
                         f"{week_key} 작업이 이미 완료되었고 입력자료 변경이 없습니다.")

    try:
        lock = RunLock(cfg.state_dir, week_key, mode).acquire()
    except LockError as exc:
        log.warning("중복 실행 방지: %s", exc)
        return RunResult("LOCKED", str(exc))

    # '확인 완료'는 검토 대기 중(REVIEW_WAIT)에만 유효하다 — 결과가 이미
    # 만들어진 뒤의 새 실행은 항상 새 확인 단계부터 시작한다
    # (2026-09-20 사용자 요청: 실행할 때마다 확인 받고 결과 생성)
    prior_status = state.state.get("last_run_status", "")

    workspace = None
    try:
        state.mark_running(now)
        log.info("주간 자금계획 실행 시작 (주차 %s, 방식 %s, v%s)",
                 week_key, mode, APP_VERSION)

        # 1) 입력파일 검사 (18번 항목)
        validation = file_validator.validate_inputs(cfg)
        log.info("입력파일 %d개 확인: %s",
                 len(validation.input_files), validation.summary())
        if validation.missing_required and not allow_partial:
            state.mark_result(now, STATUS_WAITING_FILES,
                              error=validation.summary())
            log.warning("필수자료 대기: %s", validation.summary())
            return RunResult(STATUS_WAITING_FILES, validation.summary())

        # 2) 입력자료 백업 (31번 항목)
        if cfg.get("options", "backup_input_files", default=True):
            backup = backup_manager.backup_inputs(cfg, week_key,
                                                  validation.input_files)
            if backup:
                log.info("입력자료 백업: %s", backup.name)

        issues: list[dict] = list(validation.corrupted)

        # 3) 기준파일: 카드결제기준·주간조정
        card_calc = CardPaymentCalculator.from_workbook(
            cfg.base_workbook_path())
        adjustments = forecast_engine.load_adjustments(
            cfg.base_workbook_path())

        # 4) 팀 지출계획 취합·통합 (9~13, 19번 항목)
        team_data = team_loader.load_all_teams(cfg)
        if team_data.get("consolidated_file"):
            log.info("팀 지출계획: 통일 취합 파일 사용 (%s)",
                     team_data["consolidated_file"])
        issues.extend(team_data["issues"])
        plan = team_loader.build_integrated_plan(
            team_data["rows"], card_calc.settlement_date,
            include_unconfirmed=cfg.get("forecast", "include_unconfirmed",
                                        default=True))
        issues.extend(plan["issues"])
        # 비고에 '에이팜'이 적힌 행은 자금계획 집계·대조에서 뺀다
        # (라이브 파일 '에이팜 지출계획' 시트에서 별도 확인)
        apalm_marked = forecast_engine.split_apalm_marked(plan)
        if apalm_marked:
            log.info("에이팜 별도관리 %d건 %s원 — 자금계획 미반영",
                     len(apalm_marked),
                     f"{sum(r.get('예상금액') or 0 for r in apalm_marked):,.0f}")
        log.info("팀 지출계획 %d건 (반영 %d건, 확인필요 %d건, 미제출 팀 %d)",
                 len(team_data["rows"]), len(plan["countable"]),
                 len(plan["issues"]), len(team_data["missing_teams"]))

        # 5) 은행 거래 표준화·중복 제거·자동분류 (16~17번 항목)
        bank_data = bank_loader.load_all_banks(cfg)
        issues.extend(bank_data["issues"])
        kept, dup_rows = duplicate_checker.remove_duplicates(bank_data["rows"])
        if dup_rows:
            # 파일 기간이 겹치면 중복은 설계상 정상이므로 은행별 요약 1줄만 남긴다
            from collections import Counter
            dup_by_bank = Counter(d.get("은행", "") for d in dup_rows)
            summary = ", ".join(f"{b} {n}건" for b, n in dup_by_bank.items())
            issues.append({"구분": "중복 은행거래(자동 제외)",
                           "내용": f"파일 기간 겹침으로 {len(dup_rows)}건 자동"
                                  f" 제외 ({summary}) — 조치 불필요",
                           "원본파일": ""})
        rules = bank_classifier.load_rules(
            cfg.state_dir / cfg.get("bank", "classify_rules_file",
                                    default="classify_rules.json"))
        issues.extend(bank_classifier.classify_rows(kept, rules))
        log.info("은행 거래 %d건 (중복 제외 %d건)", len(kept), len(dup_rows))

        # 6) 거래 이력 누적 → 정기지출·입금 예측 (21, 24번 항목)
        history_path = cfg.state_dir / "bank_history.csv"
        history = bank_loader.load_history(history_path)
        merged_history = duplicate_checker.merge_with_history(kept, history)
        # 파일명 뒷자리 계좌(더존 등)를 이력의 전체 계좌번호와 통일한다
        # — 잔액 이중 합산·내부이체 오판 방지 (kept와 같은 행 객체라 함께 반영)
        bank_loader.unify_account_labels(merged_history)
        # 내부이체는 이력 전체를 놓고 짝(같은 날·같은 금액·다른 계좌)으로
        # 다시 판정한다 — 과거에 키워드만으로 잘못 표시된 행도 되돌아오고,
        # 상대 계좌 파일이 늦게 온 이체도 짝이 생기면 표시된다
        bank_classifier.mark_internal_transfers(merged_history, rules)
        bank_classifier.classify_rows(
            [r for r in merged_history if not r.get("자동분류")], rules)
        recurring = forecast_engine.analyze_recurring(
            merged_history, base_date,
            cfg.get("recurring", "lookback_months", default=6),
            cfg.get("recurring", "min_months", default=4))
        # 지난 정기지출분석 검토 파일(06_확인필요)과 예전 버전 라이브의
        # 사용자 분류·성격 수정을 수확해 저장한다. 단, 기준파일이 그 파일보다
        # 최신이면(프로그램 업데이트 pull 직후 등) 낡은 값으로 기준파일을
        # 되돌리지 않도록 수확을 생략한다
        base_wb_path = cfg.base_workbook_path()
        harvest_sources = []
        prev_lives = sorted(
            cfg.folder("output").glob("주간자금계획_라이브_*.xlsx"))
        if prev_lives:
            harvest_sources.append(prev_lives[-1])
        prev_recurs = sorted(
            cfg.folder("review").glob("정기지출분석_*.xlsx"),
            key=lambda p: p.stat().st_mtime)
        if prev_recurs:
            harvest_sources.append(prev_recurs[-1])
        prev_reviews = sorted(
            cfg.folder("review").glob("확인필요_*.xlsx"),
            key=lambda p: p.stat().st_mtime)
        if prev_reviews:
            harvest_sources.append(prev_reviews[-1])
        for src in harvest_sources:
            if base_wb_path.exists() \
                    and src.stat().st_mtime < base_wb_path.stat().st_mtime:
                log.info("기준파일이 %s 보다 최신이라 정기지출분석 수확 생략",
                         src.name)
                continue
            applied = forecast_engine.update_override_sheet(
                base_wb_path, forecast_engine.harvest_recurring_edits(src))
            if applied:
                log.info("정기지출분석 사용자 수정 %d건을 정기지출분류에 "
                         "반영 (%s)", applied, src.name)
        # 확인필요 2단계: 확인 완료된 파일을 먼저 찾는다 — 그 안의
        # 정기지출분석 수정(분류·성격, K4 일괄 변경)은 이번 결과 생성에
        # 바로 반영한다 (라이브 수확보다 나중이라 확인 파일이 우선한다)
        review_dir = cfg.folder("review")
        review_dir.mkdir(parents=True, exist_ok=True)
        input_sig = file_validator.current_input_signature(cfg)
        confirm_mode = cfg.get("options", "confirm_before_results",
                               default=False)
        confirmed_review = None
        review_directives = []
        intraday_holds: set = set()
        if confirm_mode and prior_status == STATUS_REVIEW_WAIT:
            confirmed_review = excel_report.find_confirmed_review(
                review_dir, week_key, input_sig)
        if confirmed_review is not None:
            review_directives = excel_report.load_review_directives(
                confirmed_review)
            # 당일 지출·실제 차이 항목 중 '보류(제외)' 선택 — 오늘 계획에서 뺀다
            intraday_holds = excel_report.load_intraday_holds(
                confirmed_review)
            if intraday_holds:
                log.info("당일 지출 보류(제외) %d건 반영: %s",
                         len(intraday_holds),
                         ", ".join(sorted(intraday_holds)[:5]))
            # 확인 파일의 정기지출분석 시트 수정(분류·성격)을 반영한다.
            # 예전 형식(별도 정기지출분석 파일)도 계속 읽는다.
            rev_edits = forecast_engine.harvest_recurring_edits(
                confirmed_review)
            legacy = confirmed_review.with_name(
                excel_report.recurring_review_name(confirmed_review.name))
            if not rev_edits and legacy.exists():
                rev_edits = forecast_engine.harvest_recurring_edits(legacy)
            rev_applied = forecast_engine.update_override_sheet(
                base_wb_path, rev_edits)
            if rev_applied:
                log.info("확인 파일의 정기지출분석 수정 %d건을 "
                         "정기지출분류에 반영", rev_applied)
        # 기준파일 '정기지출분류' 시트의 사용자 분류·성격을 반영한다
        # (성격 변동·제외는 13주 자동 추정에서 뺀다; 예: 외상대 지급)
        overrides = forecast_engine.load_recurring_overrides(
            cfg.base_workbook_path())
        forecast_engine.apply_recurring_overrides(recurring, overrides)
        added = forecast_engine.ensure_recurring_override_sheet(
            cfg.base_workbook_path(), recurring)
        if added:
            log.info("정기지출분류 시트에 새 항목 %d개 추가 (기준파일)", added)
        # 공휴일 시트: 주말·공휴일을 결과물에서 붉은 글자로 표시하기 위함
        if forecast_engine.ensure_holiday_sheet(cfg.base_workbook_path()):
            log.info("기준파일에 '공휴일' 시트 생성 (기본 공휴일 채움 — "
                     "해마다 추가하세요)")
        holidays = forecast_engine.load_holidays(cfg.base_workbook_path())
        recurring_projectable = [i for i in recurring
                                 if i.get("성격", "정기") == "정기"]
        # 자동추정은 별도 목록 파일(04_기준파일/자동추정_지출목록.xlsx)로
        # 관리한다: 첫 실행 때 주간조정의 자동 초안을 이관하고, 매 실행
        # 정기지출 분석으로 새 항목을 추가한 뒤(사용자 수정 보존),
        # '반영' 행만 자금계획에 넣는다
        draft_path = (cfg.folder("base_workbook")
                      / forecast_engine.AUTO_DRAFT_FILE)
        draft_mode_default = cfg.get("forecast", "auto_draft_default",
                                     default="개별 관리")
        # 확인 파일의 '자동추정_지출목록' 시트 수정을 원본 목록에 반영한다
        if confirmed_review is not None:
            try:
                draft_changed = forecast_engine.apply_review_draft_edits(
                    confirmed_review, draft_path)
                if draft_changed:
                    log.info("확인 파일의 자동추정 목록 수정 %d건을 "
                             "원본 목록에 반영", draft_changed)
            except OSError:
                log.warning("자동추정_지출목록이 사용 중이라 확인 파일의 "
                            "목록 수정을 반영하지 못했습니다")
        # 확인 단계에서 목록 파일을 자동으로 열어 주므로, Excel이 잡고
        # 있어 저장이 막혀도 실행은 계속한다 (저장된 내용 그대로 사용)
        try:
            migrated = forecast_engine.migrate_auto_drafts(
                cfg.base_workbook_path(), draft_path, overrides,
                draft_mode_default)
            if migrated:
                log.info("자동추정 %d건을 %s(으)로 이관", migrated,
                         forecast_engine.AUTO_DRAFT_FILE)
            draft_added, draft_pruned = \
                forecast_engine.refresh_auto_draft_file(
                    draft_path, recurring_projectable, base_date,
                    default_mode=draft_mode_default, holidays=holidays)
            if draft_added or draft_pruned:
                log.info("자동추정 목록 갱신: 신규 %d건, 지난 항목 정리 %d건",
                         draft_added, draft_pruned)
        except OSError:
            log.warning("자동추정_지출목록이 사용 중(Excel에 열림)이라 "
                        "목록 갱신을 건너뜁니다 — 저장된 내용으로 계속 진행")
        auto_drafts, draft_excluded = forecast_engine.load_auto_drafts(
            draft_path, base_date)
        adjustments = [a for a in adjustments
                       if "자동 초안" not in (a.get("내용") or "")]
        adjustments += auto_drafts
        log.info("자동추정 목록 %d건 반영 (제외 %d건)",
                 len(auto_drafts), draft_excluded)
        # 성격 변동·제외 항목의 '자동 초안' 지출 추정은 쓰지 않는다
        # (예: 외상매입금 — 팀 지출예정 파일 금액으로만 반영)
        adjustments, var_dropped = \
            forecast_engine.filter_adjustments_by_overrides(
                adjustments, overrides)
        if var_dropped:
            log.info("성격 변동·제외 정기지출의 자동 초안 %d건 제외 (%s)",
                     len(var_dropped),
                     ", ".join((a.get("내용") or "")[:30]
                               for a in var_dropped[:3]))

        # 확인 완료된 확인필요 파일의 '처리' 지시
        # (정기지출 누락 → 계획에 반영/반영 안 함)를 반영한다
        if review_directives:
            adjustments += [
                {"일자": d["일자"], "조정입금": 0.0, "조정지출": d["금액"],
                 "내용": f"확인필요 지시 반영: {d['항목']} (정기지출 누락 보완)"}
                for d in review_directives]
            log.info("확인필요 지시 '계획에 반영' %d건 적용 (%s)",
                     len(review_directives),
                     ", ".join(d["항목"] for d in review_directives[:5]))

        # 7) 잔액과 예정·실제 대조 (20번 항목)
        balances, total_balance = bank_loader.summarize_balances(kept)
        match_targets = plan["countable"] + [
            r for r in plan["integrated"] if r.get("반영상태") == REFLECT_PAID]
        matched = payment_matcher.match_payments(
            match_targets, kept, now.date(),
            cfg.get("matching", "date_window_days", default=3),
            cfg.get("matching", "name_similarity_threshold", default=70),
            cfg.get("bank", "recent_days", default=14))
        mask_conf = cfg.get("options", "mask_confidential", default=True)
        today = now.date()
        for row in matched["results"]:
            if row["대조결과"] in ("수동확인필요",):
                issues.append({"구분": "수동 대조 필요",
                               "팀명": row.get("팀명"),
                               "요청ID": row.get("요청ID"),
                               "내용": row.get("비고") or "대조결과 수동확인필요",
                               "원본파일": ""})
                continue
            # 지급예정일이 지났는데 실제 출금을 찾지 못한 예정 지출
            # → 안 나간 건이므로 확인필요에 표시 (미래 예정 건은 정상)
            if row.get("대조결과") == MATCH_NOT_FOUND:
                d = row.get("지급예정일")
                if d is None or d >= today:
                    continue
                subject = row.get("거래처") or ""
                if mask_conf and row.get("confidential"):
                    subject = row.get("_conf_category") or "대외비"
                issues.append({
                    "구분": "예정지출 미출금",
                    "팀명": row.get("팀명"),
                    "요청ID": row.get("요청ID"),
                    "일자": d,
                    "내용": f"{subject} — 지급예정일이 지났는데 실제 출금을 "
                           "찾지 못함. 지연 지급이면 새 취합 파일에 새 "
                           "지급일로 다시 올리세요",
                    "금액": row.get("예정금액"),
                    "원본파일": ""})
        for row in matched["unplanned"]:
            issues.append({"구분": "계획 없는 실제출금",
                           "은행": row.get("은행"),
                           "일자": row.get("실제출금일"),
                           "내용": row.get("거래처", ""),
                           "금액": row.get("실제금액", 0),
                           "원본파일": row.get("비고", "")})

        # 8) 4주·13주 자금계획 (21~23번 항목)
        # 팀 지출계획과 겹치는 '자동 초안' 추정은 이중 반영 방지를 위해 제외
        draft_aliases = forecast_engine.load_draft_aliases(draft_path)
        adjustments, dup_adjust = forecast_engine.filter_duplicate_adjustments(
            adjustments, plan["countable"], aliases=draft_aliases)
        for adj in dup_adjust:
            issues.append({
                "구분": "추정 중복 제외",
                "내용": f"{adj['일자']} {adj.get('내용', '')} "
                       f"{(adj.get('조정지출') or 0):,.0f}원 — "
                       "팀 지출계획에 같은 건이 있어 자동 추정에서 제외",
                "원본파일": "기준파일 주간조정"})
        # 당일 지출계획 vs 실제 출금 대조. 대조 자체는 항상 계산해
        # 경영보고 '실지출' 표시에 쓰고, 실적 마감·이월과 확인필요의
        # 유지/보류 선택 행은 마감 시각(기본 17:00) 이후 실행에만 적용한다
        # (2026-09-22 사용자 확정 — 아침 실행은 오늘 예정을 계획 그대로)
        close_after = str(cfg.get("intraday", "close_after",
                                  default="17:00"))
        try:
            _h, _m = close_after.split(":")
            close_time = dtime(int(_h), int(_m))
        except (ValueError, AttributeError):
            close_time = dtime(17, 0)
        intraday_on = now.time() >= close_time
        intraday_check = forecast_engine.intraday_actuals(
            plan["countable"], merged_history, adjustments, now.date(),
            holds=intraday_holds, holidays=holidays)
        intraday_preview = intraday_check if intraday_on else None
        for det in (intraday_preview or {}).get("대조내역", []):
            if det["상태"] == "집행 확인":
                continue
            subject = det.get("거래처") or det.get("요청ID") or ""
            if mask_conf and any(
                    p.get("confidential") for p in plan["countable"]
                    if p.get("요청ID") == det.get("요청ID")):
                subject = "대외비"
            issues.append({
                "구분": excel_report.ISSUE_INTRADAY,
                "팀명": det.get("팀명"),
                "요청ID": det.get("요청ID"),
                "일자": now.date(),
                "내용": f"{subject} — {det['상태']}: {det['사유']}. "
                       "오늘 나갈 예정이면 '지출 예정(유지)', 안 나갈 "
                       "것이면 '보류(제외)'를 처리 열에서 고르세요",
                "금액": det.get("잔여") or det.get("예상금액"),
                "원본파일": "",
                "당일지시": det.get("잔여", 0) > 0})
        rates = cfg.get("forecast", "receipt_rates",
                        default=[0.6, 0.7, 0.8, 0.9, 1.0])
        # 대표보고 '일별 잔액 전망(월~금)': 주말 실행이면 차주를 보여준다
        display_monday = week_monday(now.date())
        if now.date().weekday() >= 5:       # 토·일
            display_monday += timedelta(days=7)
        forecast = forecast_engine.build_forecast(
            plan["countable"], base_date, total_balance, merged_history,
            adjustments, recurring_projectable, rates,
            cfg.get("forecast", "default_receipt_rate", default=0.8),
            cfg.get("forecast", "minimum_cash_balance", default=0),
            cfg.get("forecast", "online_history_weeks", default=12),
            cfg.get("forecast", "online_recency_halflife", default=4),
            display_week_start=display_monday, holidays=holidays,
            run_date=now.date(), intraday_holds=intraday_holds,
            intraday_enabled=intraday_on)
        # 계좌별 일별 잔액 시나리오 (우리→농협→국민 인출 우선순위).
        # 실행일 당일 거래는 실적으로 확정하지 않으므로 시작 잔액도
        # 전일 마감으로 되돌린다 (backout_from)
        account_scenario = forecast_engine.build_account_scenario(
            forecast["daily"], balances, merged_history,
            forecast.get("actual_until"), backout_from=now.date())
        for row in forecast["daily"]:
            if row["상태"] == forecast_engine.STATE_SHORTAGE:
                issues.append({"구분": "음수 예상잔액",
                               "내용": f"{row['일자']} 예상 기말잔액 "
                                      f"{row['기말잔액']:,.0f}원",
                               "원본파일": ""})
        # 9) 결과물 생성 — 임시폴더에 만들고 검증 후 이동
        # 요약 시트용 통계 (기존 자금계획 양식 항목)
        last_dates: dict[tuple, object] = {}
        for row in kept:
            if row.get("반영상태") != BANK_REFLECT_OK:
                continue
            key = (row["은행"], row.get("계좌") or "")
            d = row.get("거래일")
            if d and (key not in last_dates or d > last_dates[key]):
                last_dates[key] = d
        history_stats = {
            "외부입금": sum(r.get("입금액") or 0 for r in merged_history
                        if not r.get("내부이체")),
            "외부출금": sum(r.get("출금액") or 0 for r in merged_history
                        if not r.get("내부이체")),
            "온라인입금": sum(r.get("입금액") or 0 for r in merged_history
                         if r.get("자동분류") == "온라인매출입금"),
            "주평균온라인": sum(forecast.get("weekday_avg", {}).values()),
        }
        account_labels = {key: excel_report.account_label(*key)
                          for key in balances}

        horizon_end = base_date + timedelta(days=27)
        next4w = [p for p in plan["countable"]
                  if p.get("자금계획 반영일")
                  and base_date <= p["자금계획 반영일"] <= horizon_end]
        integrated_masked = team_loader.mask_confidential_rows(
            plan["integrated"], enabled=mask_conf)
        # 에이팜 관련 지출은 4주일별계획 비고 대신 전용 시트로 분리
        apalm_expenses = forecast_engine.collect_apalm_expenses(
            integrated_masked, adjustments, apalm_marked)
        _annotate_daily_notes(forecast["daily"], integrated_masked)
        # 경영보고용: 자금계획에 반영된 향후 4주 지출예정 목록
        # (대외비는 분류·총액). 실적으로 확정된 지난 날짜는 제외한다
        week_end = base_date + timedelta(days=27)
        week_start = base_date
        actual_until = forecast.get("actual_until")
        if actual_until is not None and actual_until >= week_start:
            week_start = actual_until + timedelta(days=1)
        week_expenses = []
        for r0 in integrated_masked:
            if r0.get("반영상태") != REFLECT_OK:
                continue
            d = r0.get("자금계획 반영일")
            if isinstance(d, datetime):
                d = d.date()
            if d is None or not (week_start <= d <= week_end):
                continue
            subject = " ".join(x for x in (r0.get("거래처"),
                                           r0.get("지출내용")) if x)
            week_expenses.append({"일자": d, "구분": r0.get("팀명") or "",
                                  "내용": subject,
                                  "금액": r0.get("예상금액") or 0,
                                  "지급방법": r0.get("지급방법") or "",
                                  "요청ID": r0.get("요청ID") or ""})
        for adj in adjustments:
            amt = adj.get("조정지출") or 0
            d = adj.get("일자")
            if amt <= 0 or d is None or not (week_start <= d <= week_end):
                continue
            gubun = ("확인반영" if "확인필요 지시" in (adj.get("내용") or "")
                     else "자동추정")
            week_expenses.append({"일자": d, "구분": gubun,
                                  "내용": adj.get("내용") or "",
                                  "금액": amt, "지급방법": ""})
        week_expenses.sort(key=lambda x: (x["일자"], -x["금액"]))
        # 금주(실행일~차주 금요일) 도래 정기지출 — 팀 지출예정 제출 대조
        chk_start, chk_end = live_report.exec_window(now.date())
        recurring_check = forecast_engine.weekly_recurring_check(
            forecast_engine.load_auto_draft_rows(draft_path,
                                                 chk_start, chk_end),
            plan["countable"], draft_aliases, chk_start, chk_end,
            variable_items=[i for i in recurring
                            if i.get("성격") == "변동"],
            holidays=holidays)
        # 확인필요 지시로 이미 계획에 넣은 항목은 누락이 아니다
        directive_keys = {(d["항목"], d["일자"]) for d in review_directives}
        for c in recurring_check:
            if c["누락"] and (c["항목"], c["예정일"]) in directive_keys:
                c["누락"] = False
                c["판정"] = "확인필요 지시로 반영"
        missing_chk = [c for c in recurring_check if c["누락"]]
        log.info("금주 정기지출 체크(%s~%s): %d건 중 누락 의심 %d건",
                 chk_start, chk_end, len(recurring_check), len(missing_chk))
        for c in missing_chk:
            issues.append({
                "구분": "정기지출 누락 의심",
                "일자": c["예정일"],
                "내용": f"{c['항목']} — 팀 지출예정 파일에서 찾지 못함. "
                       "'처리' 열에서 계획에 반영/반영 안 함 선택 "
                       "(일자·금액을 고치면 고친 값으로 반영)",
                "금액": c["예상금액"],
                "원본파일": forecast_engine.AUTO_DRAFT_FILE,
                "지시항목": c["항목"]})
        report = {
            "meta": {
                "company": cfg.get("company_name", default="(주)에이팜건강"),
                "base_date": base_date,
                "run_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "run_date": now.date(),
                "week_key": week_key,
                "status": "정상 실행",
            },
            "balances": balances,
            "total_balance": total_balance,
            "integrated_masked": integrated_masked,
            "account_scenario": account_scenario,
            "apalm_expenses": apalm_expenses,
            "week_expenses": week_expenses,
            "adjustments": adjustments,
            "intraday_check": intraday_check,
            "recurring_check": recurring_check,
            "receipt_rates": rates,
            "holidays": holidays,
            "stability_target": cfg.get("forecast", "minimum_cash_balance",
                                        default=0),
            "match_results": matched["results"],
            "unplanned": matched["unplanned"],
            "recurring": recurring,
            "bank_rows": bank_data["rows"],
            "issues": issues,
            "forecast": forecast,
            "card_rules": _card_rules_display(card_calc),
            "classify_rules": rules,
            "history_stats": history_stats,
            "account_last_dates": last_dates,
            "account_labels": account_labels,
            "missing_teams": team_data["missing_teams"],
            "next4w_confirmed_out": sum(p.get("예상금액") or 0
                                        for p in next4w),
            "card_due_4w": sum(p.get("예상금액") or 0 for p in next4w
                               if p.get("지급방법") == "법인카드"),
        }

        stamp = now.strftime("%Y%m%d_%H%M")
        excel_name = f"주간자금계획_{stamp}.xlsx"
        pdf_name = f"주간자금계획_대표보고_{stamp}.pdf"
        issue_name = f"확인필요_{stamp}.xlsx"

        # 확인 파일은 06_확인필요 폴더에만 둔다 (05_결과는 결과물만).
        # confirm_before_results가 켜져 있으면 2단계로 실행한다:
        # ① 확인 파일 하나(안내·자동추정_지출목록·확인필요·정기지출분석
        # 시트)를 만들어 열어 보여주고 대기 → 사용자가 검토 후 '안내'
        # 시트의 '확인 완료'='예'를 저장 → ② 다음 실행(10분 주기 자동
        # 감지 포함)이 수정 내용을 반영해 결과 생성
        review_path = confirmed_review
        if confirm_mode:
            if review_path is None:
                review_path = unique_path(review_dir / issue_name)
                draft_table = forecast_engine.read_draft_table(draft_path)
                # 지난 확인 파일과 비교해 새로 생긴 항목을 강조 표시한다
                prev_files = sorted(review_dir.glob("확인필요_*.xlsx"),
                                    key=lambda p: p.stat().st_mtime)
                snapshot = (excel_report.review_snapshot(prev_files[-1])
                            if prev_files else None)
                new_marks = excel_report.diff_new_items(
                    issues, recurring, draft_table, snapshot)
                excel_report.create_issue_workbook(
                    issues, review_path, week_key=week_key,
                    signature=input_sig, recurring=recurring,
                    draft_table=draft_table, holidays=holidays,
                    new_marks=new_marks)
                expected = (["안내", "자동추정_지출목록", "확인필요"]
                            + (["정기지출분석"] if recurring else []))
                if not excel_report.verify_workbook(review_path, expected):
                    raise RuntimeError("확인 파일 재열기 검증 실패")
                backup_manager.archive_superseded_reviews(
                    cfg, {review_path.name})
                bank_loader.save_history(history_path, merged_history)
                _open_file(review_path)
                state.mark_result(now, STATUS_REVIEW_WAIT,
                                  input_signature=input_sig)
                new_note = (f" ⚠ 지난 확인 이후 새 항목 "
                            f"{new_marks['count']}건이 주황색으로 표시되어 "
                            "있습니다 — 꼭 확인해 주세요."
                            if new_marks.get("count") else "")
                log.info("확인필요 %d건 검토 대기 — %s 의 시트들(안내·"
                         "자동추정_지출목록·확인필요·정기지출분석)을 검토한 "
                         "뒤 '안내' 시트의 '확인 완료'(B2)를 '예'로 바꾸고 "
                         "저장하면 결과 파일이 만들어집니다 (켜져 있으면 "
                         "10분 안에 자동)%s",
                         len(issues), review_path.name, new_note)
                return RunResult(
                    STATUS_REVIEW_WAIT,
                    f"확인필요 {len(issues)}건 검토 대기 — "
                    f"{review_path.name}의 시트들을 확인한 뒤 '안내' 시트 "
                    "'확인 완료'를 '예'로 바꾸면 결과 3개가 만들어집니다"
                    + new_note,
                    [review_path], len(issues))
            log.info("확인 완료 확인됨(%s) — 결과 파일을 만듭니다",
                     review_path.name)

        workspace = backup_manager.TempWorkspace(cfg)
        outputs = []
        if cfg.get("options", "create_excel", default=False):
            excel_report.create_report_workbook(
                report, workspace.path(excel_name))
            if not excel_report.verify_workbook(workspace.path(excel_name)):
                raise RuntimeError("결과 Excel 재열기 검증 실패")
            outputs.append(excel_name)
        # 대화형 경영보고 (고정서식 주간자금계획 파일을 대신함)
        if cfg.get("options", "create_management_report", default=True):
            mgmt_name = f"주간자금계획_경영보고_{stamp}.xlsx"
            management_report.create_management_workbook(
                report, workspace.path(mgmt_name))
            if not management_report.verify_management_workbook(
                    workspace.path(mgmt_name)):
                raise RuntimeError("경영보고 파일 재열기 검증 실패")
            outputs.append(mgmt_name)
        if review_path is None:
            # 확인 생략 모드: 결과와 함께 확인필요를 06_확인필요에 기록
            review_path = unique_path(review_dir / issue_name)
            excel_report.create_issue_workbook(issues, review_path,
                                               week_key=week_key,
                                               signature=input_sig,
                                               holidays=holidays)
            expected = ["안내", "확인필요"]
            if not excel_report.verify_workbook(review_path, expected):
                raise RuntimeError("확인필요 파일 재열기 검증 실패")
        if cfg.get("options", "create_pdf_summary", default=True):
            pdf_report.create_pdf_summary(report, workspace.path(pdf_name))
            outputs.append(pdf_name)

        # 라이브 양식(수식 유지, 반영률 즉시 재계산) — 템플릿이 있을 때만
        template_name = cfg.get("options", "live_template_name",
                                default=live_report.LIVE_TEMPLATE_NAME)
        live_template = cfg.folder("base_workbook") / template_name
        if not live_template.exists():
            # 확장자 숨김 상태에서 이름을 바꿔 '….xlsx.xlsx'가 된 경우 등
            # 이름이 같은 접두어로 시작하는 xlsx를 관대하게 찾는다
            stem = template_name.rsplit(".xlsx", 1)[0]
            candidates = sorted(
                cfg.folder("base_workbook").glob(f"{stem}*.xlsx"),
                key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                live_template = candidates[0]
                log.info("라이브 템플릿을 유사한 이름으로 찾음: %s",
                         live_template.name)
        if cfg.get("options", "create_live_workbook", default=True):
            if live_template.exists():
                live_name = f"주간자금계획_라이브_{stamp}.xlsx"
                live_report.fill_live_workbook(live_template, report,
                                               workspace.path(live_name))
                if not live_report.verify_live_workbook(
                        workspace.path(live_name), base_date):
                    raise RuntimeError("라이브 자금계획 수식·날짜 검증 실패")
                outputs.append(live_name)
            else:
                log.warning("라이브 템플릿이 없어 라이브 파일을 건너뜁니다. "
                            "여기에 넣어주세요: %s", live_template)

        moved = workspace.commit(outputs, unique_path)

        # 10) 이력 저장·지난자료 정리·상태 기록
        bank_loader.save_history(history_path, merged_history)
        backup_manager.archive_old_outputs(cfg)
        # 지난자료는 임시 보관소 — 보관 기간이 지나면 자동으로 비운다
        retention = int(cfg.get("options", "archive_retention_days",
                                default=14))
        purged = backup_manager.purge_old_archive(cfg, retention)
        if purged:
            log.info("지난자료 정리: 보관 %d일 지난 파일 %d개 삭제",
                     retention, purged)
        # 결과 폴더에는 이번 실행분만 남긴다 (이전 버전은 99_지난자료/지난결과)
        if cfg.get("options", "keep_only_latest_outputs", default=True):
            swept = backup_manager.archive_superseded_outputs(
                cfg, {p.name for p in moved},
                {review_path.name,
                 excel_report.recurring_review_name(review_path.name)})
            if swept:
                log.info("이전 결과 %d개를 99_지난자료/지난결과로 이동", swept)
        # 은행 폴더에도 계좌별 최신 파일만 남긴다 (이력은 CSV로 보존)
        if cfg.get("options", "keep_only_latest_bank_files", default=True):
            swept_banks = backup_manager.archive_superseded_bank_files(
                cfg, bank_data["rows"])
            if swept_banks:
                log.info("이전 은행 파일 %d개를 99_지난자료/지난입력파일로 이동",
                         swept_banks)

        status = STATUS_PARTIAL if validation.missing_required else STATUS_SUCCESS
        excel_out = next((p.name for p in moved
                          if p.name.startswith("주간자금계획_")
                          and p.suffix == ".xlsx"), "")
        state.mark_result(now, status, output_file=excel_out,
                          input_signature=file_validator.
                          current_input_signature(cfg))
        log.info("실행 완료: 상태 %s, 결과 %s, 확인필요 %d건",
                 status, ", ".join(p.name for p in moved), len(issues))
        return RunResult(status,
                         f"결과 {len(moved)}개 파일 생성, 확인필요 {len(issues)}건",
                         moved, len(issues))

    except Exception as exc:
        if workspace is not None:
            workspace.cleanup()
        state.mark_result(now, STATUS_FAILED, error=str(exc))
        log.error("실행 실패: %s", exc)
        log.error("%s", traceback.format_exc())
        return RunResult(STATUS_FAILED, str(exc))
    finally:
        lock.release()


def _wait_for_confirmation(cfg, state, log, allow_partial: bool = False,
                           poll_seconds: float = 5.0,
                           now=None) -> RunResult:
    """'지금 실행' 창에서 확인 완료 저장을 기다렸다가 곧바로 결과를 만든다.

    확인필요 파일에서 '확인 완료'(B2)를 '예'로 바꾸고 저장하는 순간
    감지해 결과 3종을 생성한다. 제한 시간이 지나면 그대로 종료해도
    상주 프로그램의 감시(30초 간격)와 10분 주기 검사가 이어받는다.
    """
    import time
    wait_minutes = float(cfg.get("options", "confirm_wait_minutes",
                                 default=30))
    if wait_minutes <= 0:
        return RunResult(STATUS_REVIEW_WAIT, "확인 대기 생략")
    review_dir = cfg.folder("review")
    deadline = time.monotonic() + wait_minutes * 60
    log.info("확인 완료 저장을 기다립니다 (최대 %d분) — 확인필요 파일을 "
             "검토한 뒤 '확인 완료'(B2)를 '예'로 바꾸고 저장하면 곧바로 "
             "결과 3개를 만듭니다.", int(wait_minutes))
    while True:
        current = now or now_local(cfg.timezone_name)
        week = iso_week_key(current.date())
        sig = file_validator.current_input_signature(cfg)
        if excel_report.find_confirmed_review(review_dir, week,
                                              sig) is not None:
            log.info("확인 완료 감지 — 결과 생성을 시작합니다.")
            return run_weekly_job(cfg, state, log, mode="retry",
                                  allow_partial=allow_partial, now=now)
        if time.monotonic() >= deadline:
            log.info("확인 대기 시간이 지나 창을 닫습니다. '확인 완료'만 "
                     "저장해 두면 프로그램이 자동으로 이어서 결과를 만들고, "
                     "'자금계획 지금 실행'을 다시 눌러도 됩니다.")
            return RunResult(STATUS_REVIEW_WAIT,
                             "확인 대기 시간 초과 — 저장 후 자동 처리 예정")
        time.sleep(poll_seconds)


def _open_file(path) -> None:
    """확인필요 파일을 사용자에게 바로 보여준다 (Windows 전용, 실패 무시)."""
    import os
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def _annotate_daily_notes(daily_rows: list[dict], masked_rows: list[dict],
                          max_items: int = 6) -> None:
    """4주일별계획 비고란용: 그날 반영된 지출 내역 요약을 daily 행에 넣는다.

    금액 큰 순으로 나열해 큰 지출이 '외 N건'에 묻히지 않게 한다.
    대외비 가림이 켜져 있으면 집계행이라 분류·금액만 보이고, 꺼져
    있으면(대표·관리자 전용 운영) 거래처가 그대로 보인다.
    """
    from common import CONFIDENTIAL_MASK
    by_date: dict = {}
    for r in masked_rows:
        if r.get("반영상태") != REFLECT_OK:
            continue
        d = r.get("자금계획 반영일")
        if isinstance(d, datetime):
            d = d.date()
        if d is None:
            continue
        amount = r.get("예상금액") or 0
        vendor = r.get("거래처") or ""
        if r.get("confidential") and vendor in ("", CONFIDENTIAL_MASK):
            # 가림이 켜진 집계행: 분류·금액만
            label = f"{r.get('지출내용') or '대외비'} {amount:,.0f}"
        else:
            # 에이팜 관련은 '에이팜 지출예정' 시트에서만 상세를 보여준다
            if forecast_engine.mentions_apalm(r.get("거래처"),
                                              r.get("지출내용")):
                continue
            subject = (vendor or r.get("지출내용") or r.get("팀명") or "")
            label = f"{subject} {amount:,.0f}"
        by_date.setdefault(d, []).append((amount, label))
    for row in daily_rows:
        if row.get("실적"):
            continue  # 지난 날짜는 실제 입출금 실적 표시를 유지한다
        pairs = sorted(by_date.get(row.get("일자")) or [],
                       key=lambda p: -p[0])
        labels = [p[1] for p in pairs]
        text = ", ".join(labels[:max_items])
        if len(labels) > max_items:
            text += f" 외 {len(labels) - max_items}건"
        existing = _compact_recurring_note(row.get("비고") or "")
        row["비고"] = "; ".join(p for p in (text, existing) if p)


def _compact_recurring_note(note: str) -> str:
    """'정기지출 추정(자동 초안): X 신뢰도 상' 나열을 짧게 줄인다."""
    parts = [p.strip() for p in note.split(";") if p.strip()]
    names, other = [], []
    for p in parts:
        if p.startswith("정기지출 추정"):
            name = p.split(":", 1)[1].strip() if ":" in p else p
            for grade in (" 신뢰도 상", " 신뢰도 중", " 신뢰도 하"):
                name = name.replace(grade, "")
            if forecast_engine.mentions_apalm(name):
                continue  # 에이팜 관련은 '에이팜 지출예정' 시트로 분리
            names.append(name)
        else:
            other.append(p)
    out = []
    if names:
        head = ", ".join(names[:4])
        if len(names) > 4:
            head += f" 외 {len(names) - 4}건"
        out.append(f"자동추정: {head}")
    out.extend(other)
    return "; ".join(out)


def _card_rules_display(card_calc: CardPaymentCalculator) -> list[dict]:
    rows = []
    for rule in card_calc.rules:
        rows.append({
            "카드구분": rule.card_type, "카드사": rule.issuer,
            "결제일": rule.settle_day,
            "이용기간 시작일": _spec_text(rule.start_spec),
            "이용기간 종료일": _spec_text(rule.end_spec),
            "출금계좌": rule.account,
            "사용여부": "사용" if rule.active else "미사용",
        })
    return rows


def _spec_text(spec) -> str:
    if spec is None:
        return "(해석불가)"
    names = {0: "당월", -1: "전월", -2: "전전월"}
    offset, day = spec
    return f"{names.get(offset, offset)} {'말일' if day is None else str(day) + '일'}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_runtime(config_path=None, base_dir=None):
    cfg = Config.load(config_path, base_dir)
    cfg.ensure_folders()
    state = StateManager(cfg.state_dir)
    log = get_logger(cfg.folder("log"))
    return cfg, state, log


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="주간 자금계획 자동화")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--base-dir", type=Path, default=None)
    parser.add_argument("--run-now", action="store_true",
                        help="즉시 1회 실행 후 종료")
    parser.add_argument("--force", action="store_true",
                        help="이번 주 완료 여부와 무관하게 실행(--run-now와 함께)")
    parser.add_argument("--allow-partial", action="store_true",
                        help="필수파일이 없어도 부분 실행")
    parser.add_argument("--once", action="store_true",
                        help="미실행 보완 검사만 1회 수행 후 종료")
    parser.add_argument("--weekly-reconcile", action="store_true",
                        help="이번 주 계획 vs 실제 입출금 대조 파일 생성 후 종료")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--headless", action="store_true",
                        help="트레이 아이콘 없이 상주 실행")
    args = parser.parse_args(argv)

    cfg, state, log = build_runtime(args.config, args.base_dir)

    if args.status:
        s = state.state
        print(f"이번 주({iso_week_key(now_local().date())}) 상태:")
        for key in ("last_run_status", "last_run_week", "last_run_at",
                    "last_successful_week", "last_output_file", "last_error"):
            print(f"  {key}: {s.get(key, '')}")
        return 0

    if args.weekly_reconcile:
        import weekly_reconcile
        out = weekly_reconcile.run_weekly_reconcile(cfg, log)
        print(f"[OK] 주간 대조 파일: {out}")
        return 0

    if args.run_now:
        result = run_weekly_job(cfg, state, log, mode="manual",
                                allow_partial=args.allow_partial,
                                force=args.force)
        if result.status == STATUS_REVIEW_WAIT:
            # 확인필요 검토 대기: 저장하는 즉시 이어서 결과 생성
            result = _wait_for_confirmation(
                cfg, state, log, allow_partial=args.allow_partial)
        print(f"[{result.status}] {result.message}")
        return 0 if result.status in (STATUS_SUCCESS, STATUS_PARTIAL,
                                      STATUS_REVIEW_WAIT, "SKIPPED") else 1

    from scheduler import AutomationService
    service = AutomationService(cfg, state, log)

    if args.once:
        ran = service.check_missed_run(wait=False)
        print("미실행 보완:", "실행함" if ran else "실행할 작업 없음")
        return 0

    service.start()
    if args.headless:
        log.info("헤드리스 모드로 상주 실행합니다. Ctrl+C로 종료.")
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        finally:
            service.stop()
        return 0

    try:
        from tray_app import run_tray
    except Exception as exc:  # pystray 미설치·GUI 불가 환경
        log.warning("트레이를 시작할 수 없어 헤드리스로 전환합니다: %s", exc)
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        finally:
            service.stop()
        return 0
    run_tray(service)
    return 0


if __name__ == "__main__":
    sys.exit(main())
