import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

PALETTE = {
    "blue": "#1F4E79",
    "light_blue": "#2E75B6",
    "accent": "#ED7D31",
    "green": "#70AD47",
    "red": "#FF0000",
    "bg": "#F2F2F2",
    "white": "#FFFFFF",
}


def _fig(w=8, h=4):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(PALETTE["white"])
    ax.set_facecolor(PALETTE["bg"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CCCCCC")
    ax.tick_params(colors="#444444")
    ax.yaxis.label.set_color("#444444")
    return fig, ax


def _to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _billions(val):
    if abs(val) >= 1e9:
        return val / 1e9, "B"
    elif abs(val) >= 1e6:
        return val / 1e6, "M"
    return val, ""


def revenue_ebitda_chart(df: pd.DataFrame, currency: str = "USD") -> bytes:
    df = df.dropna(subset=["revenue"])
    if df.empty:
        return _placeholder("No revenue data")

    fig, ax = _fig(9, 4.5)
    x = np.arange(len(df))
    width = 0.35

    rev_scaled, unit = _billions(df["revenue"].abs().max())
    scale = 1e9 if unit == "B" else 1e6 if unit == "M" else 1

    bars1 = ax.bar(x - width / 2, df["revenue"] / scale, width,
                   color=PALETTE["light_blue"], label="Revenue", zorder=3)
    bars2 = ax.bar(x + width / 2, df["ebitda"] / scale, width,
                   color=PALETTE["accent"], label="EBITDA", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(list(df["quarter"]), rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(f"{currency} {unit}")
    ax.set_title("Revenue & EBITDA (Quarterly)", fontweight="bold", color=PALETTE["blue"])
    ax.legend(framealpha=0.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    fig.tight_layout()
    return _to_bytes(fig)


def ebitda_margin_chart(df: pd.DataFrame) -> bytes:
    df = df.dropna(subset=["ebitda_margin"])
    if df.empty:
        return _placeholder("No EBITDA margin data")

    fig, ax = _fig()
    ax.plot(df["quarter"], df["ebitda_margin"], marker="o",
            color=PALETTE["blue"], linewidth=2.5, markersize=6)
    ax.fill_between(range(len(df)), df["ebitda_margin"],
                    alpha=0.15, color=PALETTE["blue"])
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(list(df["quarter"]), rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("EBITDA Margin (%)")
    ax.set_title("EBITDA Margin Trend", fontweight="bold", color=PALETTE["blue"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _to_bytes(fig)


def roe_chart(df: pd.DataFrame) -> bytes:
    df = df.dropna(subset=["roe_annualized"])
    if df.empty:
        return _placeholder("No ROE data")

    fig, ax = _fig()
    colors = [PALETTE["green"] if v >= 0 else PALETTE["red"] for v in df["roe_annualized"]]
    ax.bar(range(len(df)), df["roe_annualized"], color=colors, zorder=3)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(list(df["quarter"]), rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("ROE (%, annualised)")
    ax.set_title("Return on Equity (Annualised)", fontweight="bold", color=PALETTE["blue"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    fig.tight_layout()
    return _to_bytes(fig)


def fcf_chart(df: pd.DataFrame, currency: str = "USD") -> bytes:
    df = df.dropna(subset=["fcf"])
    if df.empty:
        return _placeholder("No FCF data")

    fig, ax = _fig()
    _, unit = _billions(df["fcf"].abs().max())
    scale = 1e9 if unit == "B" else 1e6 if unit == "M" else 1

    colors = [PALETTE["green"] if v >= 0 else PALETTE["red"] for v in df["fcf"]]
    ax.bar(range(len(df)), df["fcf"] / scale, color=colors, zorder=3)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(list(df["quarter"]), rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(f"FCF ({currency} {unit})")
    ax.set_title("Free Cash Flow (Quarterly)", fontweight="bold", color=PALETTE["blue"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    fig.tight_layout()
    return _to_bytes(fig)


def price_vs_bvps_chart(df: pd.DataFrame, currency: str = "USD") -> bytes:
    df = df.dropna(subset=["price", "bvps"])
    if df.empty:
        return _placeholder("No Price vs Book Value data")

    x = list(range(len(df)))
    prices = df["price"].values
    bvps = df["bvps"].values
    labels = list(df["quarter"])

    # Latest P/B for annotation
    pb_latest = prices[-1] / bvps[-1] if bvps[-1] > 0 else float("nan")

    # Decide: single axis when scales are within 10x of each other
    ratio = max(bvps) / max(prices) if max(prices) > 0 else 1
    single_axis = 0.15 < ratio < 8.0

    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor(PALETTE["white"])
    ax1.set_facecolor(PALETTE["bg"])
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.spines[["left", "bottom"]].set_color("#CCCCCC")
    ax1.tick_params(colors="#444444")

    line1, = ax1.plot(x, prices, marker="o", color=PALETTE["blue"],
                      linewidth=2.5, markersize=6, label="Stock Price")
    line2_obj = None

    if single_axis:
        # Both series on the same axis — directly comparable
        line2, = ax1.plot(x, bvps, marker="s", color=PALETTE["accent"],
                          linewidth=2.5, markersize=6, linestyle="--",
                          label="Book Value/Share")
        # Shade the gap between price and bvps to highlight discount/premium
        ax1.fill_between(x, prices, bvps,
                         where=(bvps > prices),
                         alpha=0.12, color=PALETTE["accent"],
                         label="_nolegend_")
        ax1.fill_between(x, prices, bvps,
                         where=(prices >= bvps),
                         alpha=0.12, color=PALETTE["blue"],
                         label="_nolegend_")

        all_vals = np.concatenate([prices, bvps])
        pad = (all_vals.max() - all_vals.min()) * 0.15 or all_vals.max() * 0.1
        ax1.set_ylim(max(0, all_vals.min() - pad), all_vals.max() + pad)
        ax1.set_ylabel(f"Value ({currency})", color=PALETTE["blue"])
        ax1.tick_params(axis="y", labelcolor="#444444")
        lines_list = [line1, line2]
        ax1.legend(lines_list, [l.get_label() for l in lines_list],
                   loc="upper left", framealpha=0.5, fontsize=8)
    else:
        # Scales differ too much — use dual axis, both anchored at 0
        ax1.set_ylabel(f"Stock Price ({currency})", color=PALETTE["blue"])
        ax1.tick_params(axis="y", labelcolor=PALETTE["blue"])
        ax1.set_ylim(0, max(prices) * 1.25)

        ax2 = ax1.twinx()
        ax2.spines[["top", "left"]].set_visible(False)
        ax2.spines[["right", "bottom"]].set_color("#CCCCCC")
        line2, = ax2.plot(x, bvps, marker="s", color=PALETTE["accent"],
                          linewidth=2.5, markersize=6, linestyle="--",
                          label="Book Value/Share")
        ax2.set_ylabel(f"Book Value/Share ({currency})", color=PALETTE["accent"])
        ax2.tick_params(axis="y", labelcolor=PALETTE["accent"])
        ax2.set_ylim(0, max(bvps) * 1.25)
        lines_list = [line1, line2]
        ax1.legend(lines_list, [l.get_label() for l in lines_list],
                   loc="upper left", framealpha=0.5, fontsize=8)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    pb_str = f"Current P/B: {pb_latest:.2f}x" if not np.isnan(pb_latest) else ""
    title = f"Stock Price vs Book Value per Share   {pb_str}"
    ax1.set_title(title, fontweight="bold", color=PALETTE["blue"], fontsize=11)
    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    return _to_bytes(fig)


def dcf_chart(dcf_result: dict, currency: str = "USD") -> bytes:
    """Bar chart: Bear / Base / Bull intrinsic values vs current price."""
    scenarios = dcf_result.get("scenarios", {})
    current_price = dcf_result.get("current_price", np.nan)

    labels, values = [], []
    for key in ("bear", "base", "bull"):
        s = scenarios.get(key, {})
        iv = s.get("intrinsic_value", np.nan)
        labels.append(
            f"{s.get('label', key.title())}\n"
            f"g={s['g']*100:.0f}%  r={s['r']*100:.0f}%"
        )
        values.append(iv)

    if all(np.isnan(v) for v in values):
        return _placeholder("DCF data unavailable")

    fig, ax = _fig(8, 5)

    bar_colors = []
    for v in values:
        if np.isnan(v) or np.isnan(current_price):
            bar_colors.append("#AAAAAA")
        elif v >= current_price * 1.05:
            bar_colors.append(PALETTE["green"])
        elif v <= current_price * 0.95:
            bar_colors.append(PALETTE["red"])
        else:
            bar_colors.append("#AAAAAA")

    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=bar_colors, width=0.5,
                  edgecolor="white", linewidth=0.8, zorder=3)

    # Current price reference line
    if not np.isnan(current_price):
        ax.axhline(current_price, color=PALETTE["blue"],
                   linewidth=2.0, linestyle="--", zorder=4,
                   label=f"Current Price  {current_price:,.2f} {currency}")

    # Value labels on bars
    y_max = max((v for v in values if not np.isnan(v)), default=1)
    for bar, val in zip(bars, values):
        if np.isnan(val):
            continue
        label_y = bar.get_height() + y_max * 0.02
        ax.text(bar.get_x() + bar.get_width() / 2, label_y,
                f"{val:,.1f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#333333")

    # Upside/downside % annotation inside each bar
    for bar, val in zip(bars, values):
        if np.isnan(val) or np.isnan(current_price) or current_price == 0:
            continue
        upside = (val / current_price - 1) * 100
        sign = "+" if upside >= 0 else ""
        bar_mid = bar.get_height() / 2
        ax.text(bar.get_x() + bar.get_width() / 2, bar_mid,
                f"{sign}{upside:.1f}%",
                ha="center", va="center",
                fontsize=8.5, color="white", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel(f"Intrinsic Value per Share ({currency})")
    ax.set_title("DCF Valuation — Intrinsic Value vs Current Price",
                 fontweight="bold", color=PALETTE["blue"])
    if not np.isnan(current_price):
        ax.legend(framealpha=0.5, fontsize=9)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.set_ylim(0, y_max * 1.25)
    fig.tight_layout()
    return _to_bytes(fig)


def pb_trend_chart(df: pd.DataFrame) -> bytes:
    """P/B ratio over time with a 1.0× book-value reference line."""
    if df.empty or "pb" not in df.columns:
        return _placeholder("No P/B data available")
    df = df.dropna(subset=["pb"])
    if len(df) < 2:
        return _placeholder("Not enough data points for P/B trend")

    pb = df["pb"].values
    labels = list(df["label"])
    x = np.arange(len(pb))

    fig, ax = _fig(10, 4.5)

    # ── 1.0× reference ───────────────────────────────────────────────────────
    ax.axhline(1.0, color=PALETTE["accent"], linewidth=1.6,
               linestyle="--", zorder=3, alpha=0.85)
    ax.text(x[-1] + 0.35, 1.0, "1.0×", fontsize=9,
            color=PALETTE["accent"], va="center", fontweight="bold")

    # ── shaded premium / discount bands ──────────────────────────────────────
    ax.fill_between(x, pb, 1.0,
                    where=(pb >= 1.0), interpolate=True,
                    alpha=0.18, color=PALETTE["blue"],   label="Trading at Premium")
    ax.fill_between(x, pb, 1.0,
                    where=(pb < 1.0),  interpolate=True,
                    alpha=0.22, color=PALETTE["accent"], label="Trading at Discount")

    # ── main line ─────────────────────────────────────────────────────────────
    ax.plot(x, pb, color=PALETTE["blue"], linewidth=2.5, zorder=5)

    # ── colour-coded dots ─────────────────────────────────────────────────────
    for xi, yi in zip(x, pb):
        dot = PALETTE["blue"] if yi >= 1.0 else PALETTE["accent"]
        ax.plot(xi, yi, "o", color=dot, markersize=6, zorder=6,
                markeredgecolor="white", markeredgewidth=0.8)

    # ── latest value label ────────────────────────────────────────────────────
    ax.annotate(f"  {pb[-1]:.2f}×",
                xy=(x[-1], pb[-1]),
                fontsize=9, color=PALETTE["blue"], fontweight="bold",
                va="center")

    # ── min / max callouts (only when range is meaningful) ────────────────────
    pb_range = pb.max() - pb.min()
    if pb_range > 0.1 and len(pb) > 3:
        lo_i, hi_i = int(np.argmin(pb)), int(np.argmax(pb))
        # avoid crowding the latest-value label
        if lo_i != len(pb) - 1:
            ax.annotate(f"{pb[lo_i]:.2f}×",
                        xy=(x[lo_i], pb[lo_i]),
                        xytext=(0, -14), textcoords="offset points",
                        fontsize=7.5, color=PALETTE["accent"],
                        ha="center", alpha=0.85)
        if hi_i != len(pb) - 1:
            ax.annotate(f"{pb[hi_i]:.2f}×",
                        xy=(x[hi_i], pb[hi_i]),
                        xytext=(0, 7), textcoords="offset points",
                        fontsize=7.5, color=PALETTE["blue"],
                        ha="center", alpha=0.85)

    # ── axes ──────────────────────────────────────────────────────────────────
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("P/B Ratio (×)")
    ax.set_title("Price-to-Book (P/B) Ratio — Historical Trend",
                 fontweight="bold", color=PALETTE["blue"])
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.1f}×"))
    ax.legend(framealpha=0.5, fontsize=8, loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # y-limits: always include 0 so the 1.0× line is in context
    y_top = max(pb.max() * 1.18, 1.35)
    ax.set_ylim(0, y_top)

    fig.tight_layout()
    return _to_bytes(fig)


def price_chart(history: "pd.DataFrame", ticker: str, currency: str = "USD") -> bytes:
    if history is None or history.empty:
        return _placeholder("No price data")

    fig, ax = _fig(10, 4)
    ax.plot(history.index, history["Close"], color=PALETTE["blue"],
            linewidth=1.5, label="Close")

    # 50-day & 200-day MA
    if len(history) >= 50:
        ax.plot(history.index, history["Close"].rolling(50).mean(),
                color=PALETTE["accent"], linewidth=1, linestyle="--", label="50d MA")
    if len(history) >= 200:
        ax.plot(history.index, history["Close"].rolling(200).mean(),
                color=PALETTE["green"], linewidth=1, linestyle="--", label="200d MA")

    ax.set_ylabel(f"Price ({currency})")
    ax.set_title(f"{ticker} — Price History (2Y)", fontweight="bold", color=PALETTE["blue"])
    ax.legend(framealpha=0.5, fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.autofmt_xdate()
    fig.tight_layout()
    return _to_bytes(fig)


def _placeholder(msg: str) -> bytes:
    fig, ax = _fig(6, 3)
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, color="#888888", fontsize=12)
    ax.set_axis_off()
    return _to_bytes(fig)
