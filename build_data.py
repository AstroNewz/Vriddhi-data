"""VRIDDHI वृद्धि — data builder.

Runs for free on GitHub Actions. Fetches Indian large-cap data from Yahoo
Finance (yfinance) and emits four JSON files consumed by the Flutter app:

    stocks.json      fundamentals per company
    sectors.json     sector rollups + median P/E
    signals.json     rule-based scored picks with plain-English reasons
    technicals.json  SMA50 / SMA200 / RSI / recent prices

Design notes
------------
* The phone never scrapes; all computation happens here, for free, in CI.
* Every scoring rule is transparent (see scoring.py) — VRIDDHI does NOT
  predict prices. It screens on value, debt, profitability and trend.
* Fetching is best-effort and per-stock guarded: one bad symbol never breaks
  the whole run. Missing fields fall back to 0 / [] so the app stays robust.

Run locally:  python build_data.py
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone, timedelta

import yfinance as yf

from universe import UNIVERSE
from scoring import score_stock

# India Standard Time for the lastUpdated stamp.
IST = timezone(timedelta(hours=5, minutes=30))

# Yahoo market cap / financials for .NS are in absolute rupees; ÷1e7 → ₹ crore.
CRORE = 1e7


def _safe(fn, default=None):
    """Call fn(), swallowing any exception and returning default on failure."""
    try:
        v = fn()
        return v if v is not None else default
    except Exception:
        return default


def _profit_trend(tkr) -> list[float]:
    """Net income oldest→newest in ₹ crore from the annual income statement."""
    def build():
        fin = tkr.financials  # columns are periods, newest first
        if fin is None or fin.empty:
            return []
        for key in ("Net Income", "NetIncome", "Net Income Common Stockholders"):
            if key in fin.index:
                vals = [float(x) / CRORE for x in fin.loc[key].tolist()
                        if x == x]  # drop NaN
                return list(reversed(vals))[-4:]
        return []
    return _safe(build, []) or []


def _balance_sheet(tkr) -> dict[str, float]:
    """A few headline balance-sheet lines in ₹ crore."""
    def build():
        bs = tkr.balance_sheet
        if bs is None or bs.empty:
            return {}
        latest = bs.columns[0]
        wanted = {
            "Total Assets": "Total Assets",
            "Total Debt": "Total Debt",
            "Equity": "Stockholders Equity",
            "Cash": "Cash And Cash Equivalents",
        }
        out = {}
        for label, key in wanted.items():
            if key in bs.index:
                v = bs.loc[key, latest]
                if v == v:  # not NaN
                    out[label] = round(float(v) / CRORE)
        return out
    return _safe(build, {}) or {}


def _technicals(tkr) -> dict:
    """SMA50, SMA200, RSI(14) and the last 30 closes from 1y of history."""
    def build():
        hist = tkr.history(period="1y", interval="1d")
        if hist is None or hist.empty:
            return {}
        close = hist["Close"].dropna()
        if len(close) < 30:
            return {}
        sma50 = float(close.tail(50).mean())
        sma200 = float(close.tail(200).mean()) if len(close) >= 200 else 0.0
        # RSI(14)
        delta = close.diff()
        gain = delta.clip(lower=0).tail(14).mean()
        loss = -delta.clip(upper=0).tail(14).mean()
        rsi = 100.0 if loss == 0 else 100 - (100 / (1 + gain / loss))
        prices = [round(float(x), 2) for x in close.tail(30).tolist()]
        return {
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "rsi": round(float(rsi), 1),
            "priceHistory": prices,
        }
    return _safe(build, {}) or {}


def _calendar_from_info(symbol: str, name: str, info: dict) -> dict | None:
    """Extract upcoming dividend / earnings dates from the already-fetched info
    dict (no extra API calls). Returns None if nothing useful is present."""
    def to_date(epoch):
        try:
            if not epoch:
                return None
            return datetime.fromtimestamp(float(epoch), IST).date().isoformat()
        except Exception:
            return None

    ex_div = to_date(info.get("exDividendDate"))
    earnings = to_date(info.get("earningsTimestamp")
                       or info.get("earningsTimestampStart"))
    if not ex_div and not earnings:
        return None
    entry = {"symbol": symbol, "name": name}
    if ex_div:
        entry["exDividend"] = ex_div
    if earnings:
        entry["earnings"] = earnings
    div_rate = _safe(lambda: float(info.get("dividendRate")), 0.0) or 0.0
    if div_rate:
        entry["dividendRate"] = round(div_rate, 2)
    return entry


def fetch_stock(symbol: str, name: str, sector: str) -> dict | None:
    """Fetch one company; returns a stock dict merged with its technicals."""
    ticker = f"{symbol}.NS"
    tkr = yf.Ticker(ticker)
    info = _safe(lambda: tkr.info, {}) or {}

    price = _safe(lambda: float(info.get("currentPrice")
                                or info.get("regularMarketPrice")), 0.0) or 0.0
    if price == 0.0:
        print(f"  ! {symbol}: no price, skipping")
        return None

    prev = _safe(lambda: float(info.get("previousClose")), price) or price
    change_pct = ((price - prev) / prev * 100) if prev else 0.0

    stock = {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "price": round(price, 2),
        "changePct": round(change_pct, 2),
        "marketCap": round((_safe(lambda: float(info.get("marketCap")), 0.0) or 0.0) / CRORE),
        "pe": round(_safe(lambda: float(info.get("trailingPE")), 0.0) or 0.0, 1),
        "debtToEquity": round((_safe(lambda: float(info.get("debtToEquity")), 0.0) or 0.0) / 100, 2),
        "roe": round((_safe(lambda: float(info.get("returnOnEquity")), 0.0) or 0.0) * 100, 1),
        "eps": round(_safe(lambda: float(info.get("trailingEps")), 0.0) or 0.0, 1),
        "bookValue": round(_safe(lambda: float(info.get("bookValue")), 0.0) or 0.0, 1),
        "dividendYield": round((_safe(lambda: float(info.get("dividendYield")), 0.0) or 0.0), 2),
        "profitTrend": [round(x) for x in _profit_trend(tkr)],
        "balanceSheet": _balance_sheet(tkr),
        "marketSharePct": 0.0,  # filled in after all fetched (sector-relative)
    }
    tech = _technicals(tkr)
    calendar = _calendar_from_info(symbol, name, info)
    return {"stock": stock, "tech": tech, "calendar": calendar}


def compute_market_share(stocks: list[dict]) -> None:
    """Approx market share = a stock's cap ÷ its sector's total cap (percent)."""
    totals: dict[str, float] = {}
    for s in stocks:
        totals[s["sector"]] = totals.get(s["sector"], 0.0) + s["marketCap"]
    for s in stocks:
        total = totals.get(s["sector"], 0.0)
        s["marketSharePct"] = round((s["marketCap"] / total * 100) if total else 0.0, 1)


def build_sectors(stocks: list[dict]) -> list[dict]:
    """Sector rollups with median P/E (ignoring zero/negative P/E)."""
    by_sector: dict[str, list[dict]] = {}
    for s in stocks:
        by_sector.setdefault(s["sector"], []).append(s)
    out = []
    for name, members in by_sector.items():
        pes = [m["pe"] for m in members if m["pe"] > 0]
        median_pe = round(statistics.median(pes), 1) if pes else 0.0
        ordered = sorted(members, key=lambda m: m["marketCap"], reverse=True)
        out.append({
            "name": name,
            "medianPe": median_pe,
            "members": [m["symbol"] for m in ordered],
        })
    return sorted(out, key=lambda x: x["name"])


def fetch_indices() -> list[dict]:
    """Fetch the headline indices (Sensex, Nifty 50) with day change."""
    wanted = [
        ("^BSESN", "SENSEX", "BSE Sensex"),
        ("^NSEI", "NIFTY", "Nifty 50"),
    ]
    out = []
    for yahoo, code, name in wanted:
        def build():
            tkr = yf.Ticker(yahoo)
            info = _safe(lambda: tkr.info, {}) or {}
            price = _safe(lambda: float(info.get("regularMarketPrice")
                                        or info.get("previousClose")), 0.0) or 0.0
            prev = _safe(lambda: float(info.get("previousClose")), price) or price
            if price == 0.0:
                # Fall back to the last two closes from history.
                hist = tkr.history(period="5d", interval="1d")
                if hist is None or hist.empty:
                    return None
                closes = hist["Close"].dropna().tolist()
                price = float(closes[-1])
                prev = float(closes[-2]) if len(closes) >= 2 else price
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0.0
            return {
                "code": code,
                "name": name,
                "value": round(price, 2),
                "change": round(change, 2),
                "changePct": round(change_pct, 2),
            }
        idx = _safe(build, None)
        if idx:
            out.append(idx)
        else:
            print(f"  ! index {code}: unavailable")
    return out


def fetch_news() -> list[dict]:
    """Fetch market headlines from free RSS feeds. Headlines + links only — no
    scraping of article bodies, no editorialising. Best-effort."""
    import urllib.request
    import xml.etree.ElementTree as ET

    feeds = [
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/business.xml",
    ]
    items: list[dict] = []
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=20).read()
            root = ET.fromstring(raw)
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                if title and link:
                    items.append({"title": title, "link": link, "date": pub})
                if len(items) >= 40:
                    break
        except Exception as e:  # noqa: BLE001
            print(f"  ! news feed failed ({url}): {e}")
    # De-dupe by title, keep order.
    seen = set()
    unique = []
    for it in items:
        if it["title"] in seen:
            continue
        seen.add(it["title"])
        unique.append(it)
    return unique[:30]


def fetch_ipos() -> list[dict]:
    """Best-effort upcoming/current IPO list. Free reliable sources for Indian
    IPOs are scarce, so this may return an empty list; the app shows a friendly
    'no data' state in that case rather than fabricating entries."""
    # Placeholder: returns empty. A future revision can wire a specific free
    # source here. We deliberately do NOT invent IPO data.
    return []


def main() -> None:
    now = datetime.now(IST).isoformat(timespec="seconds")
    is_monthly = datetime.now(IST).day <= 7  # first run of the month = full report

    stocks: list[dict] = []
    technicals: list[dict] = []
    calendar: list[dict] = []

    print(f"Fetching {len(UNIVERSE)} stocks…")
    for symbol, name, sector in UNIVERSE:
        print(f"- {symbol}")
        res = fetch_stock(symbol, name, sector)
        if res is None:
            continue
        stocks.append(res["stock"])
        if res["tech"]:
            technicals.append({"symbol": symbol, **res["tech"]})
        if res.get("calendar"):
            calendar.append(res["calendar"])

    compute_market_share(stocks)
    sectors = build_sectors(stocks)
    sector_median = {s["name"]: s["medianPe"] for s in sectors}
    tech_by_symbol = {t["symbol"]: t for t in technicals}

    # Score every stock, then keep the strongest as "signals" (the Home feed).
    # With a 500-name universe we cap the feed to the top picks so the app stays
    # snappy; the full list still lives in stocks.json for search/screener.
    all_signals = []
    for s in stocks:
        sig = score_stock(s, sector_median.get(s["sector"], 0.0),
                          tech_by_symbol.get(s["symbol"]))
        all_signals.append(sig)
    all_signals.sort(key=lambda x: x["score"], reverse=True)
    signals = all_signals[:40]

    _write("stocks.json", {"lastUpdated": now, "stocks": stocks})
    _write("sectors.json", {"lastUpdated": now, "sectors": sectors})
    _write("signals.json", {
        "lastUpdated": now,
        "reportType": "monthly" if is_monthly else "daily",
        "signals": signals,
    })
    _write("technicals.json", {"lastUpdated": now, "technicals": technicals})
    _write("indices.json", {"lastUpdated": now, "indices": fetch_indices()})
    # Corporate calendar — sort by nearest upcoming date.
    calendar.sort(key=lambda c: c.get("earnings") or c.get("exDividend") or "z")
    _write("calendar.json", {"lastUpdated": now, "events": calendar})
    _write("news.json", {"lastUpdated": now, "news": fetch_news()})
    _write("ipo.json", {"lastUpdated": now, "ipos": fetch_ipos()})
    print(f"Done. {len(stocks)} stocks, {len(signals)} signals, "
          f"{len(calendar)} calendar entries.")


def _write(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
