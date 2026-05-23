import io
import math
import numpy as np
from datetime import date
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── colour palette ────────────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x1F, 0x4E, 0x79)
LIGHT_BLUE = RGBColor(0x2E, 0x75, 0xB6)
ACCENT = RGBColor(0xED, 0x7D, 0x31)
GREEN = RGBColor(0x70, 0xAD, 0x47)
RED = RGBColor(0xFF, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)


def _set_cell_bg(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _para_fmt(para, size=11, bold=False, color: RGBColor = None,
              align=WD_ALIGN_PARAGRAPH.LEFT):
    para.alignment = align
    for run in para.runs:
        run.font.size = Pt(size)
        run.font.bold = bold
        if color:
            run.font.color.rgb = color


def _heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.font.size = Pt(16 if level == 1 else 13)
    run.font.bold = True
    run.font.color.rgb = DARK_BLUE
    return p


def _fmt_num(val, unit="", decimals=2, pct=False):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if pct:
        return f"{val:.{decimals}f}%"
    if unit == "$B":
        return f"${val/1e9:.{decimals}f}B"
    if unit == "$M":
        return f"${val/1e6:.{decimals}f}M"
    if unit == "B":
        return f"{val/1e9:.{decimals}f}B"
    if unit == "x":
        return f"{val:.{decimals}f}x"
    return f"{val:.{decimals}f}"


def _fmt_large(val, currency="USD"):
    sym = "$" if currency == "USD" else ""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if abs(val) >= 1e12:
        return f"{sym}{val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"{sym}{val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"{sym}{val/1e6:.2f}M"
    return f"{sym}{val:,.0f}"


def generate_report(
    ticker: str,
    market_info: dict,
    info: dict,
    snapshot: dict,
    quarterly_df,
    charts: dict,
    dcf_result: dict = None,
) -> bytes:
    doc = Document()

    # ── page margins ──────────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    currency = market_info.get("currency", "USD")
    exchange = market_info.get("exchange", "")
    company = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    doc.add_paragraph()
    doc.add_paragraph()

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_p.add_run("EQUITY RESEARCH REPORT")
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = DARK_BLUE

    doc.add_paragraph()

    comp_p = doc.add_paragraph()
    comp_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = comp_p.add_run(company)
    run2.font.size = Pt(22)
    run2.font.bold = True
    run2.font.color.rgb = LIGHT_BLUE

    tick_p = doc.add_paragraph()
    tick_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = tick_p.add_run(f"{ticker}  |  {exchange}")
    run3.font.size = Pt(13)
    run3.font.color.rgb = ACCENT

    doc.add_paragraph()

    # Info grid table (cover)
    tbl = doc.add_table(rows=2, cols=4)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = ["Sector", "Industry", "Market", "Currency"]
    values = [sector, industry, market_info.get("market", ""), currency]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        h_cell = tbl.rows[0].cells[i]
        v_cell = tbl.rows[1].cells[i]
        _set_cell_bg(h_cell, "1F4E79")
        _set_cell_bg(v_cell, "F2F2F2")
        hp = h_cell.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hr = hp.add_run(lbl)
        hr.font.bold = True
        hr.font.color.rgb = WHITE
        hr.font.size = Pt(10)
        vp = v_cell.paragraphs[0]
        vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        vr = vp.add_run(val)
        vr.font.size = Pt(10)

    doc.add_paragraph()

    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = date_p.add_run(f"Report Date: {date.today().strftime('%d %B %Y')}")
    dr.font.size = Pt(11)
    dr.font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    disc_p = doc.add_paragraph()
    disc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    discr = disc_p.add_run(
        "This report is for academic/research purposes only and does not constitute investment advice."
    )
    discr.font.size = Pt(9)
    discr.font.color.rgb = RGBColor(0x90, 0x90, 0x90)
    discr.font.italic = True

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # COMPANY OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    _heading(doc, "1. Company Overview")

    # Business description
    desc = info.get("longBusinessSummary", "")
    if desc:
        p = doc.add_paragraph(desc[:800] + ("..." if len(desc) > 800 else ""))
        p.runs[0].font.size = Pt(10)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # KEY METRICS CARDS
    # ══════════════════════════════════════════════════════════════════════════
    _heading(doc, "2. Key Financial Metrics")

    snap = snapshot
    metrics = [
        ("Current Price", f"{currency} {_fmt_large(snap.get('price'), currency='')}"),
        ("Market Cap", _fmt_large(snap.get("market_cap"), currency=currency)),
        ("P/B Ratio", _fmt_num(snap.get("pb"), "x")),
        ("ROE", _fmt_num(snap.get("roe"), pct=True)),
        ("EBITDA Margin", _fmt_num(snap.get("ebitda_margin"), pct=True)),
        ("Net Debt/EBITDA", _fmt_num(snap.get("nd_ebitda"), "x")),
        ("Free Cash Flow", _fmt_large(snap.get("fcf"), currency=currency)),
        ("EBITDA (TTM)", _fmt_large(snap.get("ebitda_ttm"), currency=currency)),
        ("Revenue (TTM)", _fmt_large(snap.get("revenue_ttm"), currency=currency)),
        ("Net Income (TTM)", _fmt_large(snap.get("net_income_ttm"), currency=currency)),
    ]

    # 2-column metric cards
    rows = math.ceil(len(metrics) / 2)
    mt = doc.add_table(rows=rows, cols=4)
    mt.alignment = WD_TABLE_ALIGNMENT.CENTER

    for idx, (label, value) in enumerate(metrics):
        row = idx // 2
        col_offset = (idx % 2) * 2
        lbl_cell = mt.rows[row].cells[col_offset]
        val_cell = mt.rows[row].cells[col_offset + 1]
        _set_cell_bg(lbl_cell, "2E75B6")
        _set_cell_bg(val_cell, "F2F2F2")

        lp = lbl_cell.paragraphs[0]
        lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lr = lp.add_run(label)
        lr.font.bold = True
        lr.font.color.rgb = WHITE
        lr.font.size = Pt(9)

        vp = val_cell.paragraphs[0]
        vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        vr = vp.add_run(value)
        vr.font.bold = True
        vr.font.size = Pt(10)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # CHARTS
    # ══════════════════════════════════════════════════════════════════════════
    _heading(doc, "3. Financial Trend Charts")

    chart_spec = [
        ("price", "3.1 Price History (2Y)"),
        ("revenue_ebitda", "3.2 Revenue & EBITDA"),
        ("ebitda_margin", "3.3 EBITDA Margin"),
        ("roe", "3.4 Return on Equity"),
        ("fcf", "3.5 Free Cash Flow"),
    ]

    for key, title in chart_spec:
        if key in charts and charts[key]:
            p = doc.add_paragraph()
            run = p.add_run(title)
            run.font.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = DARK_BLUE

            img_stream = io.BytesIO(charts[key])
            doc.add_picture(img_stream, width=Inches(6.0))
            last_para = doc.paragraphs[-1]
            last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # BULL / BEAR SCENARIO ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    doc.add_page_break()
    _heading(doc, "4. Scenario Analysis")

    price = snap.get("price") or 0
    pb = snap.get("pb")
    roe = snap.get("roe")
    nd_ebitda = snap.get("nd_ebitda")

    bull_args, bear_args = _build_scenarios(price, pb, roe, nd_ebitda, currency)

    scenario_tbl = doc.add_table(rows=1, cols=2)
    scenario_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    bull_cell = scenario_tbl.rows[0].cells[0]
    bear_cell = scenario_tbl.rows[0].cells[1]
    _set_cell_bg(bull_cell, "E2EFDA")  # light green
    _set_cell_bg(bear_cell, "FCE4D6")  # light red

    # Bull
    bp = bull_cell.paragraphs[0]
    br = bp.add_run("BULL CASE")
    br.font.bold = True
    br.font.size = Pt(13)
    br.font.color.rgb = GREEN
    for arg in bull_args:
        pp = bull_cell.add_paragraph(f"• {arg}")
        pp.runs[0].font.size = Pt(9)

    # Bear
    bep = bear_cell.paragraphs[0]
    ber = bep.add_run("BEAR CASE")
    ber.font.bold = True
    ber.font.size = Pt(13)
    ber.font.color.rgb = RED
    for arg in bear_args:
        pp = bear_cell.add_paragraph(f"• {arg}")
        pp.runs[0].font.size = Pt(9)

    doc.add_paragraph()

    # Price target range
    _heading(doc, "4.1 Indicative Price Target Range", level=2)
    if price > 0:
        bull_tp = price * 1.25
        base_tp = price * 1.10
        bear_tp = price * 0.80
        pt_tbl = doc.add_table(rows=2, cols=3)
        pt_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        scenarios = [("Bear Target", bear_tp, "FF0000"),
                     ("Base Target", base_tp, "ED7D31"),
                     ("Bull Target", bull_tp, "70AD47")]
        for i, (lbl, tp, hex_c) in enumerate(scenarios):
            h = pt_tbl.rows[0].cells[i]
            v = pt_tbl.rows[1].cells[i]
            _set_cell_bg(h, hex_c)
            _set_cell_bg(v, "F2F2F2")
            hp = h.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hr = hp.add_run(lbl)
            hr.font.bold = True
            hr.font.color.rgb = WHITE
            hr.font.size = Pt(10)
            vp = v.paragraphs[0]
            vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            vr = vp.add_run(f"{currency} {tp:.2f}")
            vr.font.bold = True
            vr.font.size = Pt(11)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # DCF VALUATION
    # ══════════════════════════════════════════════════════════════════════════
    doc.add_page_break()
    _heading(doc, "5. DCF Valuation")

    if dcf_result and "error" not in dcf_result and not dcf_result.get("fcf_unreliable"):
        scen = dcf_result["scenarios"]
        price_now = dcf_result.get("current_price", math.nan)

        # Methodology summary
        meth_p = doc.add_paragraph(
            f"Base FCF (TTM): {_fmt_large(dcf_result['base_fcf'], currency=currency)}  |  "
            f"Projection: {5} years  |  "
            f"Terminal growth: {dcf_result['terminal_growth']*100:.0f}%  |  "
            f"Net Debt: {_fmt_large(dcf_result['net_debt'], currency=currency)}"
        )
        meth_p.runs[0].font.size = Pt(9)
        meth_p.runs[0].font.italic = True
        doc.add_paragraph()

        # Scenario cards (3-column table)
        sc_tbl = doc.add_table(rows=2, cols=3)
        sc_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        sc_configs = [
            ("bear", "Bear Case\ng=2%  r=15%", "FF0000"),
            ("base", "Base Case\ng=8%  r=12%", "808080"),
            ("bull", "Bull Case\ng=15%  r=10%", "70AD47"),
        ]
        for col_i, (key, lbl, hex_c) in enumerate(sc_configs):
            h_cell = sc_tbl.rows[0].cells[col_i]
            v_cell = sc_tbl.rows[1].cells[col_i]
            _set_cell_bg(h_cell, hex_c)
            _set_cell_bg(v_cell, "F2F2F2")

            hp = h_cell.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hr = hp.add_run(lbl)
            hr.font.bold = True
            hr.font.color.rgb = WHITE
            hr.font.size = Pt(9)

            iv = scen[key].get("intrinsic_value", math.nan)
            up = scen[key].get("upside_pct", math.nan)
            iv_str = _fmt_large(iv, currency=currency) if not math.isnan(iv) else "N/A"
            up_str = (f"  ({up:+.1f}%)" if not math.isnan(up) else "")
            vp = v_cell.paragraphs[0]
            vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            vr = vp.add_run(f"{iv_str}{up_str}")
            vr.font.bold = True
            vr.font.size = Pt(10)

        doc.add_paragraph()

        # DCF chart
        if "dcf" in charts and charts["dcf"]:
            img_stream = io.BytesIO(charts["dcf"])
            doc.add_picture(img_stream, width=Inches(5.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()

        # Sensitivity table
        _heading(doc, "5.1 Sensitivity Table — Intrinsic Value per Share", level=2)

        sens = dcf_result["sensitivity"]
        rate_keys   = [0.10, 0.12, 0.15]
        growth_keys = [0.02, 0.08, 0.15]
        rate_lbls   = ["r = 10%", "r = 12%", "r = 15%"]
        growth_lbls = ["g = 2%", "g = 8%", "g = 15%"]

        n_rows = len(rate_keys) + 1  # header row
        n_cols = len(growth_keys) + 1  # label column
        sens_tbl = doc.add_table(rows=n_rows, cols=n_cols)
        sens_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header row
        _set_cell_bg(sens_tbl.rows[0].cells[0], "1F4E79")
        hp = sens_tbl.rows[0].cells[0].paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hp.add_run("Discount Rate \\ FCF Growth").font.color.rgb = WHITE

        for j, gl in enumerate(growth_lbls):
            cell = sens_tbl.rows[0].cells[j + 1]
            _set_cell_bg(cell, "2E75B6")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_run = p.add_run(gl)
            r_run.font.bold = True
            r_run.font.color.rgb = WHITE
            r_run.font.size = Pt(9)

        # Data rows
        for i, (rk, rl) in enumerate(zip(rate_keys, rate_lbls)):
            row = sens_tbl.rows[i + 1]
            _set_cell_bg(row.cells[0], "2E75B6")
            lp = row.cells[0].paragraphs[0]
            lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lr = lp.add_run(rl)
            lr.font.bold = True
            lr.font.color.rgb = WHITE
            lr.font.size = Pt(9)

            for j, gk in enumerate(growth_keys):
                iv = sens.get(rk, {}).get(gk, math.nan)
                iv_str = _fmt_large(iv, currency=currency) if not math.isnan(iv) else "N/A"

                # Colour cell green/red based on upside vs current price
                if not math.isnan(iv) and not math.isnan(price_now) and price_now > 0:
                    ratio = iv / price_now
                    hex_bg = "C8F7C5" if ratio > 1.10 else "FCD5D5" if ratio < 0.90 else "FFF3CD"
                else:
                    hex_bg = "F2F2F2"

                cell = row.cells[j + 1]
                _set_cell_bg(cell, hex_bg)
                vp = cell.paragraphs[0]
                vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                vr = vp.add_run(iv_str)
                vr.font.size = Pt(9)

        doc.add_paragraph()

        # Disclaimer note below sensitivity table
        disc_p = doc.add_paragraph(
            "⚠ DCF assumes FCF growth continues at projected rates. "
            "Verify against most recent quarterly filings."
        )
        disc_p.runs[0].font.size = Pt(9)
        disc_p.runs[0].font.italic = True
        disc_p.runs[0].font.color.rgb = RGBColor(0x7F, 0x6B, 0x00)
        doc.add_paragraph()

    elif dcf_result and "error" in dcf_result:
        warn_p = doc.add_paragraph(f"⚠ {dcf_result['error']}")
        warn_p.runs[0].font.size = Pt(10)
        warn_p.runs[0].font.italic = True
        warn_p.runs[0].font.color.rgb = ACCENT
        doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # DISCLAIMER
    # ══════════════════════════════════════════════════════════════════════════
    doc.add_page_break()
    _heading(doc, "Disclaimer")
    disc_text = (
        "This report has been prepared for academic and educational purposes as part of an MSc Finance programme. "
        "It does not constitute investment advice, a solicitation, or an offer to buy or sell any securities. "
        "All data is sourced from Yahoo Finance via the yfinance library and may not be accurate or complete. "
        "The author assumes no liability for decisions made based on this report. "
        "Past performance is not indicative of future results. "
        "All price targets and scenario analyses are purely illustrative."
    )
    p = doc.add_paragraph(disc_text)
    p.runs[0].font.size = Pt(9)
    p.runs[0].font.italic = True
    p.runs[0].font.color.rgb = RGBColor(0x70, 0x70, 0x70)

    # ── serialise ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def _build_scenarios(price, pb, roe, nd_ebitda, currency):
    bull = []
    bear = []

    if price:
        bull.append(f"Current price {currency} {price:.2f} offers upside to intrinsic value estimate.")
        bear.append(f"Current price {currency} {price:.2f} may already reflect optimistic expectations.")

    if pb is not None and not math.isnan(pb):
        if pb < 2:
            bull.append(f"P/B of {pb:.2f}x is below sector average — potential re-rating opportunity.")
        elif pb > 4:
            bear.append(f"P/B of {pb:.2f}x signals stretched valuation relative to book value.")
        else:
            bull.append(f"P/B of {pb:.2f}x reflects reasonable valuation.")

    if roe is not None and not math.isnan(roe):
        if roe > 15:
            bull.append(f"Strong ROE of {roe:.1f}% demonstrates efficient capital utilisation.")
        elif roe < 5:
            bear.append(f"Weak ROE of {roe:.1f}% raises concerns about capital efficiency.")
        else:
            bear.append(f"Moderate ROE of {roe:.1f}% leaves room for improvement.")

    if nd_ebitda is not None and not math.isnan(nd_ebitda):
        if nd_ebitda < 1.5:
            bull.append(f"Net Debt/EBITDA of {nd_ebitda:.2f}x indicates a conservative balance sheet.")
        elif nd_ebitda > 3.5:
            bear.append(f"High leverage (Net Debt/EBITDA {nd_ebitda:.2f}x) limits financial flexibility.")
        else:
            bull.append(f"Manageable leverage at {nd_ebitda:.2f}x Net Debt/EBITDA.")

    bull += [
        "Continued margin expansion through operational efficiency gains.",
        "Potential for increased dividend payouts or share buybacks if FCF improves.",
        "Sector tailwinds could accelerate revenue growth.",
    ]
    bear += [
        "Macro headwinds (inflation, rate hikes) could compress margins.",
        "Currency risk and geopolitical uncertainty may weigh on earnings.",
        "Competitive pressure could erode market share.",
    ]

    return bull[:5], bear[:5]
