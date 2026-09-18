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

    story.append(Paragraph("주별 잔액 전망 (13주)", section))
    weekly_rows = [["주차", "기간", "예상입금", "지출합계", "기말잔액", "상태"]]
    for w in forecast.get("weekly", []):
        out_total = (w["송금예정"] + w["카드결제"] + w["자동이체"] + w["기타지출"])
        weekly_rows.append([
            w["주차"], w["기간"], _fmt_money(w["예상입금"]),
            _fmt_money(out_total), _fmt_money(w["기말잔액"]), w["상태"]])
    wt = Table(weekly_rows, colWidths=[16 * mm, 28 * mm, 32 * mm, 32 * mm,
                                       34 * mm, 18 * mm])
    wt.setStyle(table_style)
    for i, w in enumerate(forecast.get("weekly", []), start=1):
        if w["상태"] == "자금부족":
            wt.setStyle(TableStyle([("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFC7CE"))]))
        elif w["상태"] == "주의":
            wt.setStyle(TableStyle([("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFEB9C"))]))
    story.append(wt)

    story.append(Paragraph("입금 반영률 시나리오", section))
    sc_rows = [["반영률", "4주 기말잔액", "4주 최저잔액", "13주 기말잔액"]]
    for rate, sc in sorted(forecast.get("rate_scenarios", {}).items()):
        sc_rows.append([f"{int(round(rate * 100))}%",
                        _fmt_money(sc.get("4주 기말잔액")),
                        _fmt_money(sc.get("4주 최저잔액")),
                        _fmt_money(sc.get("13주 기말잔액"))])
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
