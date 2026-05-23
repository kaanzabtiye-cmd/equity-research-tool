import streamlit as st
import math
import numpy as np
import pandas as pd

from src.market_detector import detect_market
from src.data_fetcher import fetch_all
from src.metrics import (
    calculate_snapshot,
    calculate_quarterly_trends,
    calculate_price_bvps,
    calculate_pb_trend,
    calculate_dcf,
)
from src.charts import (
    revenue_ebitda_chart,
    ebitda_margin_chart,
    roe_chart,
    fcf_chart,
    price_chart,
    price_vs_bvps_chart,
    pb_trend_chart,
    dcf_chart,
)
from src.news_fetcher import fetch_news
from src.report_generator import generate_report

st.set_page_config(
    page_title="Equity Research Tool",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #f0f4f8;
        border-left: 4px solid #1F4E79;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .metric-label { font-size: 12px; color: #666; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 22px; font-weight: 700; color: #1F4E79; }
    .news-card {
        background: #f8f9fa;
        border-left: 4px solid #2E75B6;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 10px;
    }
    .news-source { font-size: 11px; color: #888; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Equity Research Tool")
st.caption("Powered by Yahoo Finance · MSc Finance Project")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    ticker_input = st.text_input(
        "Stock Ticker",
        value="AAPL",
        placeholder="e.g. AAPL, SISE.IS",
        help="Yahoo Finance ticker. Add .IS for Borsa Istanbul, .L for London, etc.",
    ).strip().upper()

    st.markdown("**Examples**")
    example_cols = st.columns(2)
    example_tickers = ["AAPL", "SISE.IS", "MSFT", "THYAO.IS", "GOOGL", "ASELS.IS"]
    for i, ex in enumerate(example_tickers):
        if example_cols[i % 2].button(ex, key=f"ex_{ex}"):
            ticker_input = ex

    run_btn = st.button("Generate Report", type="primary", use_container_width=True)
    st.divider()
    st.markdown(
        "1. Enter a ticker symbol\n"
        "2. Click **Generate Report**\n"
        "3. Browse metrics, charts & news\n"
        "4. Download the Word report"
    )

# ── Guard ─────────────────────────────────────────────────────────────────────
if not run_btn:
    st.info("Enter a ticker on the left and click **Generate Report** to begin.")
    st.stop()

ticker = ticker_input
market_info = detect_market(ticker)
market = market_info["market"]
currency = market_info["currency"]

st.markdown(f"### {ticker} · {market} · {market_info['exchange']}")

# ── Data fetch ────────────────────────────────────────────────────────────────
with st.spinner(f"Fetching data for **{ticker}** from Yahoo Finance…"):
    try:
        data = fetch_all(ticker)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        st.stop()

info = data["info"]
company = info.get("longName") or info.get("shortName") or ticker

if not info:
    st.error("No data returned. Check the ticker symbol.")
    st.stop()

st.subheader(company)
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
col_m2.markdown(f"**Industry:** {info.get('industry', 'N/A')}")
col_m3.markdown(f"**Currency:** {currency}")

# ── Metrics ───────────────────────────────────────────────────────────────────
with st.spinner("Calculating metrics…"):
    snapshot = calculate_snapshot(data)
    quarterly_df = calculate_quarterly_trends(data)
    price_bvps_df = calculate_price_bvps(data)
    pb_trend_df = calculate_pb_trend(data)
    dcf_result = calculate_dcf(data, snapshot)


def _fmt(val, unit="", pct=False, decimals=2):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if pct:
        return f"{val:.{decimals}f}%"
    if unit == "x":
        return f"{val:.{decimals}f}x"
    return f"{val:.{decimals}f}"


def _fmt_large(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if abs(val) >= 1e12:
        return f"{currency} {val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"{currency} {val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"{currency} {val/1e6:.2f}M"
    return f"{currency} {val:,.0f}"


st.divider()
st.subheader("Key Metrics")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Price", _fmt_large(snapshot.get("price")))
c2.metric("Market Cap", _fmt_large(snapshot.get("market_cap")))
c3.metric("P/B Ratio", _fmt(snapshot.get("pb"), "x"))
c4.metric("ROE", _fmt(snapshot.get("roe"), pct=True))
c5.metric("EBITDA Margin", _fmt(snapshot.get("ebitda_margin"), pct=True))

c6, c7, c8, c9, c10 = st.columns(5)
c6.metric("Net Debt/EBITDA", _fmt(snapshot.get("nd_ebitda"), "x"))
c7.metric("Free Cash Flow", _fmt_large(snapshot.get("fcf")))
c8.metric("EBITDA (TTM)", _fmt_large(snapshot.get("ebitda_ttm")))
c9.metric("Revenue (TTM)", _fmt_large(snapshot.get("revenue_ttm")))
c10.metric("Net Income (TTM)", _fmt_large(snapshot.get("net_income_ttm")))

# ── Charts ────────────────────────────────────────────────────────────────────
with st.spinner("Generating charts…"):
    charts = {}
    charts["price"] = price_chart(data["history"], ticker, currency)
    if not quarterly_df.empty:
        charts["revenue_ebitda"] = revenue_ebitda_chart(quarterly_df, currency)
        charts["ebitda_margin"] = ebitda_margin_chart(quarterly_df)
        charts["roe"] = roe_chart(quarterly_df)
        charts["fcf"] = fcf_chart(quarterly_df, currency)
    if not price_bvps_df.empty:
        charts["price_bvps"] = price_vs_bvps_chart(price_bvps_df, currency)
    if not pb_trend_df.empty:
        charts["pb_trend"] = pb_trend_chart(pb_trend_df)
    if "error" not in dcf_result:
        charts["dcf"] = dcf_chart(dcf_result, currency)

st.divider()
st.subheader("Financial Trends")

if charts.get("price"):
    st.image(charts["price"], use_column_width=True)

tab_labels = ["Revenue & EBITDA", "EBITDA Margin", "ROE", "Free Cash Flow",
              "Price vs Book Value", "P/B Ratio Trend"]
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_labels)

with tab1:
    if charts.get("revenue_ebitda"):
        st.image(charts["revenue_ebitda"], use_column_width=True)
    else:
        st.info("Quarterly income data not available.")

with tab2:
    if charts.get("ebitda_margin"):
        st.image(charts["ebitda_margin"], use_column_width=True)
    else:
        st.info("EBITDA margin data not available.")

with tab3:
    if charts.get("roe"):
        st.image(charts["roe"], use_column_width=True)
    else:
        st.info("ROE data not available.")

with tab4:
    if charts.get("fcf"):
        st.image(charts["fcf"], use_column_width=True)
    else:
        st.info("FCF data not available.")

with tab5:
    if charts.get("price_bvps"):
        st.image(charts["price_bvps"], use_column_width=True)
        if not price_bvps_df.empty:
            st.dataframe(
                price_bvps_df.rename(columns={
                    "quarter": "Quarter",
                    "price": f"Price ({currency})",
                    "bvps": f"Book Value/Share ({currency})",
                }),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Price vs Book Value data not available.")

with tab6:
    if charts.get("pb_trend"):
        st.image(charts["pb_trend"], use_column_width=True)
        if not pb_trend_df.empty:
            disp = pb_trend_df[["label", "price", "bvps", "pb"]].copy()
            disp["price"] = disp["price"].map(lambda v: f"{v:.2f}")
            disp["bvps"]  = disp["bvps"].map(lambda v: f"{v:.2f}")
            disp["pb"]    = disp["pb"].map(lambda v: f"{v:.2f}×")
            disp.columns  = ["Period", f"Price ({currency})",
                              f"BVPS ({currency})", "P/B Ratio"]
            st.dataframe(disp, use_container_width=True, hide_index=True)
    else:
        st.info("P/B trend data not available.")

# ── Quarterly table ───────────────────────────────────────────────────────────
if not quarterly_df.empty:
    st.divider()
    st.subheader("Quarterly Data Table")
    display_df = quarterly_df.copy()
    for col in ["revenue", "ebitda", "net_income", "fcf"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda v: f"{v/1e6:.1f}M"
                if (v is not None and not (isinstance(v, float) and math.isnan(v)))
                else "N/A"
            )
    for col in ["ebitda_margin", "roe_annualized"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda v: f"{v:.1f}%"
                if (v is not None and not (isinstance(v, float) and math.isnan(v)))
                else "N/A"
            )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Scenario Analysis ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Scenario Analysis")

price_val = snapshot.get("price") or 0
bull_col, bear_col = st.columns(2)

with bull_col:
    st.markdown("#### 🟢 Bull Case")
    bull_pts = [
        f"P/B of {_fmt(snapshot.get('pb'), 'x')} suggests re-rating potential if ROE expands."
        if snapshot.get("pb") and snapshot["pb"] < 3
        else "Valuation re-rating on margin expansion.",
        f"Strong ROE of {_fmt(snapshot.get('roe'), pct=True)} demonstrates efficient capital allocation."
        if snapshot.get("roe") and snapshot["roe"] > 12
        else "Potential ROE improvement through operational leverage.",
        "Balance sheet strength supports dividends or buybacks."
        if (snapshot.get("nd_ebitda") or 99) < 2
        else "Deleveraging could unlock shareholder returns.",
        "Sector tailwinds and market share gains drive revenue growth.",
        "FCF inflection supports multiple expansion and equity value creation.",
    ]
    for pt in bull_pts:
        st.markdown(f"• {pt}")

with bear_col:
    st.markdown("#### 🔴 Bear Case")
    bear_pts = [
        f"High P/B of {_fmt(snapshot.get('pb'), 'x')} leaves little margin of safety."
        if snapshot.get("pb") and snapshot["pb"] > 3
        else "Macro slowdown could compress valuation multiples.",
        f"Leverage of {_fmt(snapshot.get('nd_ebitda'), 'x')} Net Debt/EBITDA constrains financial flexibility."
        if snapshot.get("nd_ebitda") and snapshot["nd_ebitda"] > 2
        else "Rising rates increase cost of debt refinancing.",
        "Margin compression from input cost inflation or pricing pressure.",
        "Currency depreciation risk in emerging market operations.",
        "Regulatory headwinds or ESG concerns could limit institutional demand.",
    ]
    for pt in bear_pts:
        st.markdown(f"• {pt}")

if price_val > 0:
    st.markdown("#### Indicative Price Targets")
    pt1, pt2, pt3 = st.columns(3)
    pt1.metric("Bear Target (-20%)", f"{currency} {price_val * 0.80:.2f}")
    pt2.metric("Base Target (+10%)", f"{currency} {price_val * 1.10:.2f}")
    pt3.metric("Bull Target (+25%)", f"{currency} {price_val * 1.25:.2f}")

# ── DCF Valuation ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("📐 DCF Valuation")

_DCF_WARNING = (
    "DCF valuation skipped: Free Cash Flow is negative or insufficient for reliable "
    "discounted cash flow analysis. Valuation is based on P/B, EV/EBITDA, and "
    "relative multiples instead."
)
_DCF_DISCLAIMER = (
    "⚠️ DCF assumes FCF growth continues at projected rates. "
    "Verify against most recent quarterly filings."
)

if dcf_result.get("fcf_unreliable") or "error" in dcf_result:
    st.warning(_DCF_WARNING)
else:
    scen = dcf_result["scenarios"]
    price_now = dcf_result["current_price"]

    # Metric cards
    dc1, dc2, dc3 = st.columns(3)
    for col, key, label in [
        (dc1, "bear", "Bear Case"),
        (dc2, "base", "Base Case"),
        (dc3, "bull", "Bull Case"),
    ]:
        iv = scen[key].get("intrinsic_value", float("nan"))
        up = scen[key].get("upside_pct", float("nan"))
        g  = scen[key]["g"] * 100
        r  = scen[key]["r"] * 100
        iv_str = _fmt_large(iv) if not math.isnan(iv) else "N/A"
        up_str = f"{up:+.1f}%" if not math.isnan(up) else "N/A"
        col.metric(
            label=f"{label}  (g={g:.0f}%, r={r:.0f}%)",
            value=iv_str,
            delta=up_str,
        )

    # DCF chart
    if charts.get("dcf"):
        st.image(charts["dcf"], use_column_width=True)

    # Methodology note
    with st.expander("DCF Methodology"):
        st.markdown(
            f"- **Base FCF (TTM):** {_fmt_large(dcf_result['base_fcf'])}\n"
            f"- **Projection:** 5-year FCF growth, then terminal value\n"
            f"- **Terminal growth rate:** {dcf_result['terminal_growth']*100:.0f}% (Gordon Growth Model)\n"
            f"- **Equity value** = Enterprise Value − Net Debt "
            f"({_fmt_large(dcf_result['net_debt'])})\n"
            f"- **Intrinsic value per share** = Equity Value ÷ "
            f"{dcf_result['shares']/1e6:.0f}M shares\n\n"
            "_Assumptions are fixed for illustrative purposes. "
            "Adjust discount rates and growth rates for your own view._"
        )

    # Sensitivity table
    st.markdown("#### Sensitivity Table — Intrinsic Value per Share")
    st.caption(
        "Rows = Discount Rate (WACC), Columns = FCF Growth Rate. "
        "Green = >10% upside vs current price. Red = >10% downside."
    )
    sens = dcf_result["sensitivity"]
    rate_labels   = ["r = 10%", "r = 12%", "r = 15%"]
    growth_labels = ["g = 2%",  "g = 8%",  "g = 15%"]
    rate_keys     = [0.10, 0.12, 0.15]
    growth_keys   = [0.02, 0.08, 0.15]

    table_data = {
        gl: [sens[r][g] for r in rate_keys]
        for gl, g in zip(growth_labels, growth_keys)
    }
    sens_df = pd.DataFrame(table_data, index=rate_labels)

    def _color_cell(val):
        try:
            v = float(str(val).replace(",", "").split()[0])
        except Exception:
            return ""
        if math.isnan(v) or math.isnan(price_now) or price_now == 0:
            return ""
        ratio = v / price_now
        if ratio > 1.10:
            return "background-color: #c8f7c5; color: #1a6b18"
        if ratio < 0.90:
            return "background-color: #fcd5d5; color: #7b1818"
        return "background-color: #fff3cd; color: #7d5a00"

    fmt_val = lambda v: _fmt_large(v) if not math.isnan(v) else "N/A"
    display_sens = sens_df.map(fmt_val)
    styled = display_sens.style.map(_color_cell)
    st.dataframe(styled, use_container_width=True)

    # Disclaimer note below sensitivity table
    st.caption(_DCF_DISCLAIMER)

# ── News ──────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📰 Recent News")

with st.spinner("Fetching latest news…"):
    news_items = fetch_news(ticker=ticker, company=company, market=market, max_items=7)

if not news_items:
    st.info("No recent news found.")
else:
    for item in news_items:
        title = item.get("title", "")
        source = item.get("source", "")
        date_str = item.get("date", "")
        url = item.get("url", "#")

        # Strip Google News redirect wrapper titles that appear as "Title - Source"
        display_title = title.split(" - ")[0] if " - " in title else title

        st.markdown(
            f"""<div class="news-card">
            <a href="{url}" target="_blank" style="text-decoration:none;color:#1F4E79;font-weight:600;">
                {display_title}
            </a><br>
            <span class="news-source">📌 {source} &nbsp;|&nbsp; 🗓 {date_str}</span>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Report download ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Download Report")

with st.spinner("Building Word report…"):
    report_bytes = generate_report(
        ticker=ticker,
        market_info=market_info,
        info=info,
        snapshot=snapshot,
        quarterly_df=quarterly_df,
        charts=charts,
        dcf_result=dcf_result,
    )

st.download_button(
    label="📥 Download Word Report (.docx)",
    data=report_bytes,
    file_name=f"equity_research_{ticker}_{market}.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    type="primary",
    use_container_width=True,
)

st.caption("Data sourced from Yahoo Finance. For academic use only. Not investment advice.")
