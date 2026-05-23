SUFFIX_MAP = {
    ".IS": {"market": "Turkey", "currency": "TRY", "exchange": "Borsa Istanbul"},
    ".L":  {"market": "UK",     "currency": "GBP", "exchange": "London Stock Exchange"},
    ".DE": {"market": "Germany","currency": "EUR", "exchange": "Frankfurt"},
    ".PA": {"market": "France", "currency": "EUR", "exchange": "Euronext Paris"},
    ".HK": {"market": "HongKong","currency":"HKD", "exchange": "HKEX"},
    ".T":  {"market": "Japan",  "currency": "JPY", "exchange": "Tokyo Stock Exchange"},
    ".AX": {"market": "Australia","currency":"AUD","exchange": "ASX"},
    ".TO": {"market": "Canada", "currency": "CAD", "exchange": "TSX"},
    ".SW": {"market": "Switzerland","currency":"CHF","exchange":"SIX"},
    ".AS": {"market": "Netherlands","currency":"EUR","exchange":"Euronext Amsterdam"},
}

US_DEFAULT = {"market": "US", "currency": "USD", "exchange": "NYSE/NASDAQ"}


def detect_market(ticker: str) -> dict:
    ticker = ticker.strip().upper()
    for suffix, info in SUFFIX_MAP.items():
        if ticker.endswith(suffix):
            return {"ticker": ticker, **info}
    return {"ticker": ticker, **US_DEFAULT}
