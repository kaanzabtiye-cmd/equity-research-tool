import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
_TIMEOUT = 8


def fetch_news(ticker: str, company: str, market: str, max_items: int = 7) -> list:
    """Return list of {title, source, date, url} dicts, newest first."""
    items = []

    if market == "Turkey":
        # Primary: Turkish Google News using company name and ticker root
        ticker_root = ticker.split(".")[0]
        items += _google_rss(company, lang="tr", country="TR", ceid="TR:tr")
        if len(items) < max_items:
            items += _google_rss(ticker_root, lang="tr", country="TR", ceid="TR:tr")
    else:
        # Primary: Yahoo Finance news (most relevant for US)
        items += _yahoo_news(ticker)
        # Supplement with Google News
        if len(items) < max_items:
            items += _google_rss(company, lang="en", country="US", ceid="US:en")

    return _dedup(items)[:max_items]


# ── Google News RSS ───────────────────────────────────────────────────────────

def _google_rss(query: str, lang: str, country: str, ceid: str) -> list:
    q = urllib.parse.quote_plus(query)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={q}&hl={lang}&gl={country}&ceid={ceid}"
    )
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        items = []
        for item in root.iter("item"):
            title = _text(item, "title") or ""
            link = _text(item, "link") or ""
            pub = _text(item, "pubDate") or ""
            source_el = item.find("source")
            source = source_el.text if source_el is not None else _domain(link)
            date_str = _parse_date(pub)
            if title and link:
                items.append({
                    "title": title,
                    "source": source,
                    "date": date_str,
                    "url": link,
                })
        return items
    except Exception:
        return []


# ── Yahoo Finance news ────────────────────────────────────────────────────────

def _yahoo_news(ticker: str) -> list:
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
        items = []
        for n in raw:
            # yfinance news dict keys vary by version
            title = n.get("title") or n.get("headline", "")
            url = n.get("link") or n.get("url", "")
            ts = n.get("providerPublishTime") or n.get("publishedAt")
            source = n.get("publisher") or n.get("source", "Yahoo Finance")
            if ts:
                try:
                    date_str = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%d %b %Y")
                except Exception:
                    date_str = str(ts)
            else:
                date_str = ""
            if title and url:
                items.append({"title": title, "source": source, "date": date_str, "url": url})
        return items
    except Exception:
        return []


# ── helpers ───────────────────────────────────────────────────────────────────

def _text(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_date(rfc2822: str) -> str:
    try:
        dt = parsedate_to_datetime(rfc2822)
        return dt.strftime("%d %b %Y")
    except Exception:
        return rfc2822[:16] if rfc2822 else ""


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _dedup(items: list) -> list:
    seen, out = set(), []
    for it in items:
        key = it["url"]
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out
