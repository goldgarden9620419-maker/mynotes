# -*- coding: utf-8 -*-
"""대표 보고용 PDF 요약 생성 (28번 항목).

한글 글꼴: Windows 맑은고딕 → 나눔고딕 → reportlab 내장 한글 CID 글꼴
순서로 사용한다.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

_FONT_CANDIDATES = [
    ("MalgunGothic", r"C:\Windows\Fonts\malgun.ttf"),
    ("MalgunGothic", r"C:\Windows\Fonts\malgunsl.ttf"),
    ("NanumGothic", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    ("NanumGothic", "/usr/share/fonts/nanum/NanumGothic.ttf"),
]


def _register_korean_font() -> str:
    for name, path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    for cid in ("HYGothic-Medium", "HYSMyeongJo-Medium"):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(cid))
            return cid
        except Exception:
            continue
    return "Helvetica"  # 한글 미지원 환경 최후 수단


def _fmt_money(value) -> str:
    if value is None:
        return "-"
    return f"{value:,.0f}원"


def _fmt_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value) if value else "-"


def create_pdf_summary(report: dict, out_path: Path) -> Path:
    font = _register_korean_font()
    meta = report["meta"]
    forecast = report["forecast"]
    scenario = forecast.get("scenario", {})

    title_style = ParagraphStyle("title", fontName=font, fontSize=16,
                                 leading=22, spaceAfter=4)
    small = ParagraphStyle("small", fontName=font, fontSize=9, leading=13,
                           textColor=colors.HexColor("#555555"))
    body = ParagraphStyle("body", fontName=font, fontSize=10, leading=15)
    warn_style = ParagraphStyle("warn", fontName=font, fontSize=10,
                                leading=15, textColor=colors.HexColor("#B00000"))
    section = ParagraphStyle("section", fontName=font, fontSize=12,
                             leading=16, spaceBefore=10, spaceAfter=4,
                             textColor=colors.HexColor("#1F4E79"))

    table_style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F4F7FB")]),
    ])

    story = []
    story.append(Paragraph(
        f"{meta.get('company', '')} 주간 자금계획 보고", title_style))
    story.append(Paragraph(
        f"기준일 {_fmt_date(meta.get('base_date'))} · "
        f"작성 {meta.get('run_at', '')} · "
        f"입금 반영률 {int(round(forecast.get('rate', 0) * 100))}%", small))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("핵심 요약", section))
    key_rows = [
        ["항목", "금액·내용"],
        ["현재 전체 계좌잔액", _fmt_money(report.get("total_balance"))],
        ["4주 예상 기말잔액", _fmt_money(scenario.get("4주 기말잔액"))],
        ["4주 최저 예상잔액",
         f"{_fmt_money(scenario.get('4주 최저잔액'))}"
         f" ({_fmt_date(scenario.get('4주 최저잔액일'))})"],
        ["13주 예상 기말잔액", _fmt_money(scenario.get("13주 기말잔액"))],
        ["향후 4주 확정지출", _fmt_money(report.get("next4w_confirmed_out"))],
        ["카드 결제 예정액(4주)", _fmt_money(report.get("card_due_4w"))],
        ["확인필요 건수", f"{len(report.get('issues', []))}건"],
        ["자료 미제출 팀",
         ", ".join(report.get("missing_teams", [])) or "없음"],
        ["자금부족 예상일", _fmt_date(scenario.get("자금부족 예상일")) or "없음"],
    ]
    t = Table(key_rows, colWidths=[55 * mm, 105 * mm])
    t.setStyle(table_style)
    story.append(t)

    note = scenario.get("안내", "")
    if note:
        style = warn_style if ("부족" in note or "아래" in note) else body
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(note, style))

    # 보고 기준 반영률: 80% / 90% / 100%
    report_rates = [r for r in (0.8, 0.9, 1.0)
                    if r in forecast.get("rate_scenarios", {})]
    scenarios = forecast.get("rate_scenarios", {})

    base_days = (scenarios.get(report_rates[0], {}).get("금주일별", [])
                 if report_rates else [])
    # 조회 시점보다 뒤의 주면 '차주'로 표기 (주말 실행 시 다가오는 주)
    from common import week_monday
    title_label = "금주 일별 잔액 전망 (월~금)"
    if base_days:
        first_d, last_d = base_days[0][0], base_days[-1][0]
        run_d = meta.get("run_date")
        word = ("차주" if run_d is not None
                and week_monday(first_d) > week_monday(run_d) else "금주")
        title_label = (f"{word} 일별 잔액 전망 "
                       f"({first_d.month}/{first_d.day} ~ "
                       f"{last_d.month}/{last_d.day})")
    story.append(Paragraph(title_label, section))
    day_rows = [["일자"] + [f"반영률 {int(r * 100)}% 기말잔액"
                          for r in report_rates]]
    shortage_cells = []
    holidays = report.get("holidays") or {}
    offday_rows = []
    for i, (d, _bal, _state) in enumerate(base_days, start=1):
        name = holidays.get(d, "")
        day_label = f"{_fmt_date(d)} ({'월화수목금토일'[d.weekday()]})"
        if name:
            day_label += f" {name}"
        if d.weekday() >= 5 or d in holidays:
            offday_rows.append(i)
        row = [day_label]
        for j, rate in enumerate(report_rates, start=1):
            days = scenarios[rate].get("금주일별", [])
            bal = days[i - 1][1] if len(days) >= i else None
            row.append(_fmt_money(bal))
            if bal is not None and bal < 0:
                shortage_cells.append((j, i))
        day_rows.append(row)
    dt_widths = [46 * mm] + [38 * mm] * max(len(report_rates), 1)
    dt = Table(day_rows, colWidths=dt_widths)
    dt.setStyle(table_style)
    for col, row in shortage_cells:
        dt.setStyle(TableStyle([("BACKGROUND", (col, row), (col, row),
                                 colors.HexColor("#FFC7CE"))]))
    for r in offday_rows:      # 주말·공휴일 일자는 붉은 글자
        dt.setStyle(TableStyle([("TEXTCOLOR", (0, r), (0, r),
                                 colors.HexColor("#C00000"))]))
    story.append(dt)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "· 실적이 반영된 날짜는 세 반영률의 잔액이 동일합니다 "
        "(실제 입출금 확정치).", small))

    story.append(Paragraph("입금 반영률 시나리오 (80·90·100%)", section))
    sc_rows = [["반영률", "4주 기말잔액", "4주 최저잔액", "자금부족 예상일"]]
    for rate in report_rates:
        sc = scenarios.get(rate, {})
        sc_rows.append([f"{int(round(rate * 100))}%",
                        _fmt_money(sc.get("4주 기말잔액")),
                        _fmt_money(sc.get("4주 최저잔액")),
                        _fmt_date(sc.get("자금부족 예상일")) or "없음"])
    st = Table(sc_rows, colWidths=[25 * mm, 45 * mm, 45 * mm, 45 * mm])
    st.setStyle(table_style)
    story.append(st)

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "· 대외비 항목(급여·인건비, 퇴직금·퇴직연금, 세금·보험 등)은 "
        "분류별 총액으로만 반영되어 있습니다.", small))
    story.append(Paragraph(
        "· 상세 내역은 같은 시각에 생성된 주간자금계획 Excel 파일을 "
        "확인하십시오.", small))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title="주간 자금계획 보고")
    doc.build(story)
    return out_path
