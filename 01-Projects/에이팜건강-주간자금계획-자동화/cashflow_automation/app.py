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
from datetime import date, datetime, timedelta
from pathlib import Path

from common import (
    APP_VERSION, BANK_REFLECT_OK, REFLECT_OK, REFLECT_PAID, STATUS_FAILED,
    STATUS_PARTIAL, STATUS_SUCCESS, STATUS_WAITING_FILES, iso_week_key,
    now_local, unique_path, week_monday,
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
        bank_classifier.classify_rows(
            [r for r in merged_history if not r.get("자동분류")], rules)
        recurring = forecast_engine.analyze_recurring(
            merged_history, base_date,
            cfg.get("recurring", "lookback_months", default=6),
            cfg.get("recurring", "min_months", default=4))
        # 직전 라이브 결과물에서 사용자의 분류·성격 수정을 수확해 저장한다
        prev_lives = sorted(
            cfg.folder("output").glob("주간자금계획_라이브_*.xlsx"))
        if prev_lives:
            harvested = forecast_engine.harvest_recurring_edits(prev_lives[-1])
            applied = forecast_engine.update_override_sheet(
                cfg.base_workbook_path(), harvested)
            if applied:
                log.info("정기지출분석 사용자 수정 %d건을 정기지출분류에 반영",
                         applied)
        # 기준파일 '정기지출분류' 시트의 사용자 분류·성격을 반영한다
        # (성격 변동·제외는 13주 자동 추정에서 뺀다; 예: 외상대 지급)
        overrides = forecast_engine.load_recurring_overrides(
            cfg.base_workbook_path())
        forecast_engine.apply_recurring_overrides(recurring, overrides)
        added = forecast_engine.ensure_recurring_override_sheet(
            cfg.base_workbook_path(), recurring)
        if added:
            log.info("정기지출분류 시트에 새 항목 %d개 추가 (기준파일)", added)
        recurring_projectable = [i for i in recurring
                                 if i.get("성격", "정기") == "정기"]

        # 7) 잔액과 예정·실제 대조 (20번 항목)
        balances, total_balance = bank_loader.summarize_balances(kept)
        match_targets = plan["countable"] + [
            r for r in plan["integrated"] if r.get("반영상태") == REFLECT_PAID]
        matched = payment_matcher.match_payments(
            match_targets, kept, now.date(),
            cfg.get("matching", "date_window_days", default=3),
            cfg.get("matching", "name_similarity_threshold", default=70),
            cfg.get("bank", "recent_days", default=14))
        for row in matched["results"]:
            if row["대조결과"] in ("수동확인필요",):
                issues.append({"구분": "수동 대조 필요",
                               "팀명": row.get("팀명"),
                               "요청ID": row.get("요청ID"),
                               "내용": row.get("비고") or "대조결과 수동확인필요",
                               "원본파일": ""})
        for row in matched["unplanned"]:
            issues.append({"구분": "계획 없는 실제출금",
                           "은행": row.get("은행"),
                           "내용": f"{row.get('실제출금일')} "
                                  f"{row.get('실제금액', 0):,.0f}원 "
                                  f"{row.get('거래처', '')}",
                           "원본파일": row.get("비고", "")})

        # 8) 4주·13주 자금계획 (21~23번 항목)
        # 팀 지출계획과 겹치는 '자동 초안' 추정은 이중 반영 방지를 위해 제외
        adjustments, dup_adjust = forecast_engine.filter_duplicate_adjustments(
            adjustments, plan["countable"])
        for adj in dup_adjust:
            issues.append({
                "구분": "추정 중복 제외",
                "내용": f"{adj['일자']} {adj.get('내용', '')} "
                       f"{(adj.get('조정지출') or 0):,.0f}원 — "
                       "팀 지출계획에 같은 건이 있어 자동 추정에서 제외",
                "원본파일": "기준파일 주간조정"})
        rates = cfg.get("forecast", "receipt_rates",
                        default=[0.6, 0.7, 0.8, 0.9, 1.0])
        forecast = forecast_engine.build_forecast(
            plan["countable"], base_date, total_balance, merged_history,
            adjustments, recurring_projectable, rates,
            cfg.get("forecast", "default_receipt_rate", default=0.8),
            cfg.get("forecast", "minimum_cash_balance", default=0),
            cfg.get("forecast", "online_history_weeks", default=12))
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
            plan["integrated"])
        _annotate_daily_notes(forecast["daily"], integrated_masked)
        report = {
            "meta": {
                "company": cfg.get("company_name", default="(주)에이팜건강"),
                "base_date": base_date,
                "run_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "week_key": week_key,
                "status": "정상 실행",
            },
            "balances": balances,
            "total_balance": total_balance,
            "integrated_masked": integrated_masked,
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

        workspace = backup_manager.TempWorkspace(cfg)
        outputs = []
        if cfg.get("options", "create_excel", default=True):
            excel_report.create_report_workbook(
                report, workspace.path(excel_name))
            if not excel_report.verify_workbook(workspace.path(excel_name)):
                raise RuntimeError("결과 Excel 재열기 검증 실패")
            outputs.append(excel_name)
        excel_report.create_issue_workbook(issues, workspace.path(issue_name))
        if not excel_report.verify_workbook(workspace.path(issue_name),
                                            ["확인필요"]):
            raise RuntimeError("확인필요 파일 재열기 검증 실패")
        outputs.append(issue_name)
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
        review_copy = None
        if issues:
            # 확인필요 파일은 06_확인필요 폴더에도 복사본을 둔다
            review_dir = cfg.folder("review")
            review_dir.mkdir(parents=True, exist_ok=True)
            src = next((p for p in moved if p.name.startswith("확인필요")), None)
            if src is not None:
                import shutil
                review_copy = unique_path(review_dir / src.name)
                shutil.copy2(src, review_copy)

        # 10) 이력 저장·지난자료 정리·상태 기록
        bank_loader.save_history(history_path, merged_history)
        backup_manager.archive_old_outputs(cfg)
        # 결과 폴더에는 이번 실행분만 남긴다 (이전 버전은 99_지난자료/지난결과)
        if cfg.get("options", "keep_only_latest_outputs", default=True):
            swept = backup_manager.archive_superseded_outputs(
                cfg, {p.name for p in moved},
                {review_copy.name} if review_copy is not None else ())
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


def _annotate_daily_notes(daily_rows: list[dict], masked_rows: list[dict],
                          max_items: int = 3) -> None:
    """4주일별계획 비고란용: 그날 반영된 지출 내역 요약을 daily 행에 넣는다.

    대외비 행은 분류·금액만 표시한다(집계행이라 거래처가 이미 가려짐).
    """
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
        if r.get("confidential"):
            label = f"{r.get('지출내용') or '대외비'} {amount:,.0f}"
        else:
            subject = (r.get("거래처") or r.get("지출내용")
                       or r.get("팀명") or "")
            label = f"{subject} {amount:,.0f}"
        by_date.setdefault(d, []).append(label)
    for row in daily_rows:
        if row.get("실적"):
            continue  # 지난 날짜는 실제 입출금 실적 표시를 유지한다
        labels = by_date.get(row.get("일자")) or []
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

    if args.run_now:
        result = run_weekly_job(cfg, state, log, mode="manual",
                                allow_partial=args.allow_partial,
                                force=args.force)
        print(f"[{result.status}] {result.message}")
        return 0 if result.status in (STATUS_SUCCESS, STATUS_PARTIAL,
                                      "SKIPPED") else 1

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
