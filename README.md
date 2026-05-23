# Equity Research Tool

A Streamlit-based equity research application that fetches live financial data from Yahoo Finance, computes key valuation metrics, runs a three-scenario DCF model, and exports a formatted Word report — all from a single stock ticker input.

Built as part of an MSc Finance programme.

---

## Features

- **Automatic market detection** — detects Turkey (`.IS` suffix → TRY) and US markets (no suffix → USD) from the ticker
- **Key financial metrics** — P/B ratio, ROE, EBITDA margin, Net Debt/EBITDA, Free Cash Flow, Revenue, Net Income (TTM)
- **8-quarter trend charts** — Revenue & EBITDA, EBITDA Margin, Return on Equity, Free Cash Flow
- **Price vs Book Value chart** — smart single/dual axis depending on scale ratio
- **P/B ratio trend** — combines annual and quarterly balance sheet data for maximum history (3–5 years)
- **DCF valuation model** — three scenarios (Bull/Base/Bear) with 5-year FCF projection, Gordon Growth terminal value, sensitivity table, and FCF reliability guard
- **Recent news** — Google News RSS (Turkish/English based on market) + Yahoo Finance news
- **Word report export** — colour-coded tables, charts, scenario analysis, and DCF section embedded in a `.docx` file

---

## Screenshots

| Metrics & Charts | DCF Valuation |
|---|---|
| Key metrics snapshot, 8-quarter trends, P/B trend | Three-scenario intrinsic value, sensitivity table |

---

## Tech Stack

| Library | Purpose |
|---|---|
| `streamlit` | Web UI |
| `yfinance` | Yahoo Finance data |
| `pandas` | Data manipulation |
| `numpy` | Numerical calculations |
| `matplotlib` | Chart rendering (server-side PNG) |
| `python-docx` | Word report generation |
| `Pillow` | Image handling |
| `requests` | Google News RSS fetch |

---

## Installation

**Requirements:** Python 3.10+ and `pip` (Anaconda recommended).

```bash
git clone https://github.com/kaanzabtiye-cmd/equity-research-tool.git
cd equity-research-tool
pip install -r requirements.txt
```

---

## Usage

```bash
streamlit run app.py --server.headless true
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

1. Enter a stock ticker (e.g. `AAPL`, `SISE.IS`, `MSFT`)
2. Click **Analyse**
3. Browse metrics, charts, DCF valuation, and recent news
4. Download the Word report with the **Download Report** button

---

## Project Structure

```
equity-research-tool/
├── app.py                  # Streamlit UI
├── requirements.txt
└── src/
    ├── data_fetcher.py     # yfinance data fetch
    ├── market_detector.py  # Ticker → market/currency detection
    ├── metrics.py          # Metric calculations & DCF model
    ├── charts.py           # matplotlib chart rendering
    ├── news_fetcher.py     # Google News RSS + Yahoo Finance news
    └── report_generator.py # python-docx Word report
```

---

## DCF Model

The DCF valuation uses TTM Free Cash Flow as the base and projects three scenarios:

| Scenario | FCF Growth | Discount Rate |
|---|---|---|
| Bull | 15% | 10% |
| Base | 8% | 12% |
| Bear | 2% | 15% |

Terminal value is calculated using the Gordon Growth Model with a 3% perpetuity growth rate. Intrinsic value = (PV of FCFs + PV of terminal value − Net Debt) / Shares outstanding.

**Reliability guard:** DCF is skipped and a warning is shown if TTM FCF is negative, or if FCF was negative in 2 or more of the last 4 quarters.

---

## Supported Markets

| Market | Suffix | Currency |
|---|---|---|
| United States | *(none)* | USD |
| Turkey (Borsa Istanbul) | `.IS` | TRY |

Additional markets can be added in `src/market_detector.py`.

---

## Disclaimer

This tool is for academic and educational purposes only. It does not constitute investment advice or a solicitation to buy or sell any security. All data is sourced from Yahoo Finance via the `yfinance` library and may not be accurate or complete. Past performance is not indicative of future results.
