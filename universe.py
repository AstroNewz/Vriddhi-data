"""VRIDDHI वृद्धि — the stock universe.

Primary source: the official **Nifty 500** constituents CSV from NSE — ~500
companies covering 95%+ of India's market cap (every investable name). This is
fetched fresh each run so the list stays current as the index is rebalanced.

If NSE is unreachable in a given CI run, we fall back to a small hardcoded set
of large-caps so the build never fails outright.

Each entry is (symbol, display name, sector). Symbols are the NSE ticker
WITHOUT the ".NS" suffix (the builder appends it for Yahoo Finance).
"""

from __future__ import annotations

import csv
import io
import urllib.request

NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"

# Minimal fallback if NSE is unreachable.
_FALLBACK: list[tuple[str, str, str]] = [
    ("RELIANCE", "Reliance Industries", "Energy"),
    ("TCS", "Tata Consultancy Services", "IT"),
    ("HDFCBANK", "HDFC Bank", "Banking"),
    ("INFY", "Infosys", "IT"),
    ("ICICIBANK", "ICICI Bank", "Banking"),
    ("SBIN", "State Bank of India", "Banking"),
    ("BHARTIARTL", "Bharti Airtel", "Telecom"),
    ("ITC", "ITC Ltd", "FMCG"),
    ("LT", "Larsen & Toubro", "Infrastructure"),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG"),
    ("TATAMOTORS", "Tata Motors", "Auto"),
    ("MARUTI", "Maruti Suzuki", "Auto"),
    ("SUNPHARMA", "Sun Pharmaceutical", "Pharma"),
    ("TATASTEEL", "Tata Steel", "Metals"),
    ("AXISBANK", "Axis Bank", "Banking"),
]


def _clean_name(name: str) -> str:
    """Trim the common corporate suffixes so display names stay tidy."""
    n = name.strip()
    for suffix in (" Ltd.", " Ltd", " Limited", "."):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def load_universe() -> list[tuple[str, str, str]]:
    """Fetch the live Nifty 500 list; fall back to the hardcoded set on error."""
    try:
        req = urllib.request.Request(
            NIFTY500_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        rows = list(csv.DictReader(io.StringIO(raw)))
        out: list[tuple[str, str, str]] = []
        for r in rows:
            symbol = (r.get("Symbol") or "").strip()
            name = _clean_name(r.get("Company Name") or symbol)
            sector = (r.get("Industry") or "Other").strip() or "Other"
            if symbol:
                out.append((symbol, name, sector))
        if len(out) >= 100:  # sanity check the fetch actually worked
            print(f"Universe: loaded {len(out)} Nifty 500 constituents from NSE")
            return out
        print("Universe: NSE list looked too short, using fallback")
    except Exception as e:  # noqa: BLE001 — never let this break the build
        print(f"Universe: NSE fetch failed ({e}), using fallback")
    return _FALLBACK


# Loaded once at import so build_data.py can iterate it directly.
UNIVERSE: list[tuple[str, str, str]] = load_universe()
