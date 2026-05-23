import numpy as np
import pandas as pd
from src.data_fetcher import _get


def calculate_snapshot(data: dict) -> dict:
    info = data["info"]
    qi = data["quarterly_income"]
    qb = data["quarterly_balance"]
    qc = data["quarterly_cashflow"]
    ai = data["annual_income"]
    ab = data["annual_balance"]
    ac = data["annual_cashflow"]

    price = info.get("currentPrice") or info.get("regularMarketPrice", np.nan)
    market_cap = info.get("marketCap", np.nan)
    shares = info.get("sharesOutstanding", np.nan)

    # ── P/B ──────────────────────────────────────────────────────────────────
    book_value = _get(ab, "Stockholders Equity", "Total Stockholders Equity",
                      "Common Stock Equity")
    bvps = (book_value / shares) if (shares and not np.isnan(book_value)) else np.nan
    pb = (price / bvps) if (price and bvps and bvps > 0) else info.get("priceToBook", np.nan)

    # ── ROE ──────────────────────────────────────────────────────────────────
    net_income_ttm = _ttm(ai, "Net Income")
    equity = book_value
    roe = (net_income_ttm / equity * 100) if (equity and not np.isnan(net_income_ttm) and equity > 0) else np.nan

    # ── EBITDA margin ────────────────────────────────────────────────────────
    ebitda_ttm = _ttm(ai, "EBITDA", "Normalized EBITDA")
    revenue_ttm = _ttm(ai, "Total Revenue")
    ebitda_margin = (ebitda_ttm / revenue_ttm * 100) if (revenue_ttm and not np.isnan(ebitda_ttm) and revenue_ttm > 0) else np.nan

    # ── Net Debt / EBITDA ────────────────────────────────────────────────────
    total_debt = _get(ab, "Total Debt", "Long Term Debt And Capital Lease Obligation")
    cash = _get(ab, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    net_debt = (total_debt - cash) if (not np.isnan(total_debt) and not np.isnan(cash)) else np.nan
    nd_ebitda = (net_debt / ebitda_ttm) if (not np.isnan(net_debt) and not np.isnan(ebitda_ttm) and ebitda_ttm > 0) else np.nan

    # ── Free Cash Flow ───────────────────────────────────────────────────────
    cfo_ttm = _ttm(ac, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    capex_ttm = _ttm(ac, "Capital Expenditure")
    if np.isnan(capex_ttm):
        capex_ttm = 0.0
    # capex in financial statements is typically negative
    fcf = cfo_ttm + capex_ttm if not np.isnan(cfo_ttm) else np.nan

    return {
        "price": price,
        "market_cap": market_cap,
        "pb": pb,
        "roe": roe,
        "ebitda_margin": ebitda_margin,
        "nd_ebitda": nd_ebitda,
        "fcf": fcf,
        "net_debt": net_debt,
        "ebitda_ttm": ebitda_ttm,
        "revenue_ttm": revenue_ttm,
        "net_income_ttm": net_income_ttm,
    }


def calculate_quarterly_trends(data: dict) -> pd.DataFrame:
    qi = data["quarterly_income"]
    qb = data["quarterly_balance"]
    qc = data["quarterly_cashflow"]
    info = data["info"]
    shares = info.get("sharesOutstanding", np.nan)

    if qi.empty:
        return pd.DataFrame()

    cols = qi.columns[:8]  # last 8 quarters (newest first)
    records = []

    for col in cols:
        quarter_label = col.strftime("%Y-Q%q") if hasattr(col, "strftime") else str(col)
        # Use pandas Period for Q label
        try:
            period = pd.Period(col, freq="Q")
            quarter_label = str(period)
        except Exception:
            quarter_label = str(col)[:10]

        revenue = _col(qi, col, "Total Revenue")
        ebitda = _col(qi, col, "EBITDA", "Normalized EBITDA")
        net_income = _col(qi, col, "Net Income")

        equity = _col(qb, col, "Stockholders Equity", "Total Stockholders Equity",
                      "Common Stock Equity") if not qb.empty else np.nan

        cfo = _col(qc, col, "Operating Cash Flow",
                   "Cash Flow From Continuing Operating Activities") if not qc.empty else np.nan
        capex = _col(qc, col, "Capital Expenditure") if not qc.empty else 0.0
        if np.isnan(capex):
            capex = 0.0
        fcf = cfo + capex if not np.isnan(cfo) else np.nan

        ebitda_margin = (ebitda / revenue * 100) if (revenue and not np.isnan(ebitda) and revenue > 0) else np.nan
        roe = (net_income / equity * 4 * 100) if (equity and not np.isnan(net_income) and equity > 0) else np.nan  # annualised

        records.append({
            "quarter": quarter_label,
            "revenue": revenue,
            "ebitda": ebitda,
            "net_income": net_income,
            "ebitda_margin": ebitda_margin,
            "roe_annualized": roe,
            "fcf": fcf,
        })

    df = pd.DataFrame(records)
    df = df.iloc[::-1].reset_index(drop=True)  # oldest → newest
    return df


def calculate_price_bvps(data: dict) -> pd.DataFrame:
    qb = data["quarterly_balance"]
    hist = data["history"]
    shares = data["info"].get("sharesOutstanding", np.nan)

    if qb.empty or hist is None or hist.empty or not shares or np.isnan(shares):
        return pd.DataFrame()

    records = []
    for col in qb.columns[:8]:
        equity = _col(qb, col, "Stockholders Equity", "Total Stockholders Equity",
                      "Common Stock Equity")
        bvps = equity / shares if (not np.isnan(equity) and shares > 0) else np.nan

        try:
            target = pd.Timestamp(col).tz_localize(None)
            hist_tz = hist.copy()
            hist_tz.index = hist_tz.index.tz_localize(None) if hist_tz.index.tz else hist_tz.index
            window = hist_tz.loc[target - pd.Timedelta(days=10): target + pd.Timedelta(days=1)]
            price = float(window["Close"].iloc[-1]) if not window.empty else np.nan
        except Exception:
            price = np.nan

        try:
            quarter_label = str(pd.Period(col, freq="Q"))
        except Exception:
            quarter_label = str(col)[:10]

        records.append({"quarter": quarter_label, "price": price, "bvps": bvps})

    df = pd.DataFrame(records)
    df = df.iloc[::-1].reset_index(drop=True)
    return df


_DCF_SCENARIOS = {
    "bull": {"label": "Bull", "g": 0.15, "r": 0.10},
    "base": {"label": "Base", "g": 0.08, "r": 0.12},
    "bear": {"label": "Bear", "g": 0.02, "r": 0.15},
}
_TERMINAL_G = 0.03
_PROJECTION_YEARS = 5
_SENSITIVITY_RATES = [0.10, 0.12, 0.15]
_SENSITIVITY_GROWTHS = [0.02, 0.08, 0.15]


def calculate_dcf(data: dict, snapshot: dict) -> dict:
    """Three-scenario DCF using TTM FCF.

    Returns a dict with keys:
      scenarios  – {bear/base/bull: {intrinsic_value, upside_pct, …}}
      sensitivity – {r: {g: intrinsic_value}}
      base_fcf, shares, net_debt, current_price
    On failure returns {"error": "<reason>"}.
    """
    fcf = snapshot.get("fcf")
    price = snapshot.get("price")
    shares = data["info"].get("sharesOutstanding")
    net_debt = snapshot.get("net_debt", 0) or 0
    qc = data.get("quarterly_cashflow", pd.DataFrame())

    if not shares or np.isnan(float(shares)):
        return {"error": "Shares outstanding data unavailable.", "fcf_unreliable": True}

    # Check TTM FCF
    if fcf is None or np.isnan(float(fcf)) or fcf <= 0:
        return {
            "error": (
                "DCF valuation skipped: Free Cash Flow is negative or insufficient for reliable "
                "discounted cash flow analysis. Valuation is based on P/B, EV/EBITDA, and "
                "relative multiples instead."
            ),
            "fcf_unreliable": True,
        }

    # Check quarterly FCF history: reject if 2+ of the last 4 quarters are negative
    quarterly_fcf_vals = []
    if not qc.empty:
        for key in ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"):
            if key in qc.index:
                cfo_row = qc.loc[key].dropna()
                break
        else:
            cfo_row = pd.Series(dtype=float)
        capex_row = pd.Series(dtype=float)
        for key in ("Capital Expenditure",):
            if key in qc.index:
                capex_row = qc.loc[key].dropna()
                break
        shared_cols = cfo_row.index.intersection(capex_row.index)[:4]
        for col in shared_cols:
            q_fcf = float(cfo_row[col]) + float(capex_row.get(col, 0))
            quarterly_fcf_vals.append(q_fcf)

    negative_quarters = sum(1 for v in quarterly_fcf_vals if v < 0)
    if negative_quarters >= 2:
        return {
            "error": (
                "DCF valuation skipped: Free Cash Flow is negative or insufficient for reliable "
                "discounted cash flow analysis. Valuation is based on P/B, EV/EBITDA, and "
                "relative multiples instead."
            ),
            "fcf_unreliable": True,
            "negative_quarters": negative_quarters,
            "quarterly_fcf": quarterly_fcf_vals,
        }
    if np.isnan(float(net_debt)):
        net_debt = 0.0

    fcf = float(fcf)
    shares = float(shares)
    net_debt = float(net_debt)
    price = float(price) if price else np.nan

    def _dcf_one(g: float, r: float) -> dict:
        if r <= _TERMINAL_G:
            return {}
        # 5-year FCF projection
        projected = [fcf * (1 + g) ** t for t in range(1, _PROJECTION_YEARS + 1)]
        # Terminal value (Gordon Growth)
        tv = projected[-1] * (1 + _TERMINAL_G) / (r - _TERMINAL_G)
        # Discount
        pv_fcf = sum(cf / (1 + r) ** t for t, cf in enumerate(projected, 1))
        pv_tv = tv / (1 + r) ** _PROJECTION_YEARS
        ev = pv_fcf + pv_tv
        eq_val = ev - net_debt
        iv = eq_val / shares
        upside = (iv / price - 1) * 100 if (price and not np.isnan(price) and price > 0) else np.nan
        return {
            "g": g, "r": r,
            "projected_fcf": projected,
            "pv_fcf": pv_fcf,
            "pv_tv": pv_tv,
            "terminal_value": tv,
            "enterprise_value": ev,
            "equity_value": eq_val,
            "intrinsic_value": iv,
            "upside_pct": upside,
        }

    scenarios = {k: {**v, **_dcf_one(v["g"], v["r"])}
                 for k, v in _DCF_SCENARIOS.items()}

    # Sensitivity: rows = discount rates, cols = FCF growth rates
    sensitivity: dict = {}
    for r in _SENSITIVITY_RATES:
        sensitivity[r] = {}
        for g in _SENSITIVITY_GROWTHS:
            res = _dcf_one(g, r)
            sensitivity[r][g] = res.get("intrinsic_value", np.nan)

    return {
        "scenarios": scenarios,
        "sensitivity": sensitivity,
        "base_fcf": fcf,
        "shares": shares,
        "net_debt": net_debt,
        "current_price": price,
        "terminal_growth": _TERMINAL_G,
    }


def calculate_pb_trend(data: dict) -> pd.DataFrame:
    """Build a P/B ratio time series by merging annual + quarterly balance sheets.

    Annual data covers 4-5 fiscal years; quarterly fills in recent periods and
    overrides annual values where dates overlap.  This gives the widest possible
    history (typically 3-5 years) matched to actual closing prices.
    """
    qb = data["quarterly_balance"]
    ab = data["annual_balance"]
    hist = data["history"]
    shares = data["info"].get("sharesOutstanding", np.nan)

    if not shares or np.isnan(float(shares)):
        return pd.DataFrame()
    if hist is None or hist.empty:
        return pd.DataFrame()

    hist_tz = hist.copy()
    if hist_tz.index.tz:
        hist_tz.index = hist_tz.index.tz_localize(None)

    # Build equity map {normalized_date: equity}.
    # Annual goes in first; quarterly overwrites on overlap (more granular).
    equity_map: dict = {}
    for df_bs in (ab, qb):
        if df_bs.empty:
            continue
        for col in df_bs.columns:
            eq = _equity_at(df_bs, col)
            if not np.isnan(eq):
                equity_map[pd.Timestamp(col).normalize()] = eq

    rows = []
    for ts, equity in sorted(equity_map.items()):
        price = _price_at(hist_tz, ts)
        if np.isnan(price):
            continue
        bvps = equity / float(shares)
        if bvps <= 0:
            continue
        pb = price / bvps
        rows.append({
            "date": ts,
            "label": ts.strftime("%b '%y"),
            "price": price,
            "bvps": bvps,
            "pb": pb,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def _ttm(df: pd.DataFrame, *keys) -> float:
    """Sum the 4 most recent quarters for TTM, fall back to annual col 0."""
    if df.empty:
        return np.nan
    for key in keys:
        if key in df.index:
            vals = df.loc[key].dropna()
            if len(vals) >= 4:
                return float(vals.iloc[:4].sum())
            elif len(vals) > 0:
                return float(vals.iloc[0])
    return np.nan


def _col(df: pd.DataFrame, col, *keys) -> float:
    if df.empty or col not in df.columns:
        return np.nan
    for key in keys:
        if key in df.index:
            val = df.loc[key, col]
            if pd.notna(val):
                return float(val)
    return np.nan


_EQUITY_KEYS = (
    "Stockholders Equity",
    "Total Stockholders Equity",
    "Common Stock Equity",
)


def _equity_at(df: pd.DataFrame, col) -> float:
    """Return equity for a balance-sheet column, trying all known row labels."""
    if df.empty or col not in df.columns:
        return np.nan
    for key in _EQUITY_KEYS:
        if key in df.index:
            val = df.loc[key, col]
            if pd.notna(val):
                return float(val)
    return np.nan


def _price_at(hist_tz_naive: pd.DataFrame, ts: pd.Timestamp,
               lookback: int = 15) -> float:
    """Closing price on or just before a balance-sheet date (up to lookback days)."""
    try:
        lo = ts - pd.Timedelta(days=lookback)
        hi = ts + pd.Timedelta(days=1)
        window = hist_tz_naive.loc[lo:hi]
        return float(window["Close"].iloc[-1]) if not window.empty else np.nan
    except Exception:
        return np.nan
