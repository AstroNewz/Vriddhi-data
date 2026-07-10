"""VRIDDHI वृद्धि — the rule-based scoring engine.

Every rule here is transparent and produces a plain-English sentence. This is
deliberately NOT a price predictor — it is a screener. The output "score" out
of 10 is just the sum of points from four honest checks:

    Value        (up to 3)  P/E below the sector median → cheaper than peers
    Debt         (up to 3)  low debt-to-equity → resilient balance sheet
    Profit       (up to 2)  net profit rising over the available years
    Technical    (up to 2)  price above its long-term (200-day) average

Each satisfied rule appends a reason; near-misses append a caution. The app
renders these verbatim as the "why to buy" / "what to watch" card.
"""

from __future__ import annotations


def _profit_rising(trend: list[float]) -> bool:
    if len(trend) < 2:
        return False
    return all(trend[i] > trend[i - 1] for i in range(1, len(trend)))


def score_stock(stock: dict, sector_median_pe: float, tech: dict | None) -> dict:
    reasons: list[str] = []
    cautions: list[str] = []
    score = 0.0

    pe = stock.get("pe", 0.0)
    dte = stock.get("debtToEquity", 0.0)
    trend = stock.get("profitTrend", [])
    sector = stock.get("sector", "")

    # ── Value (max 3) ──────────────────────────────────────────────────────
    if pe > 0 and sector_median_pe > 0:
        if pe < sector_median_pe * 0.8:
            score += 3
            reasons.append(
                f"Very cheap: P/E {pe:.1f} vs {sector} median {sector_median_pe:.1f}")
        elif pe < sector_median_pe:
            score += 2
            reasons.append(
                f"Cheaper than peers: P/E {pe:.1f} vs median {sector_median_pe:.1f}")
        elif pe > sector_median_pe * 1.3:
            cautions.append(
                f"Expensive: P/E {pe:.1f} vs {sector} median {sector_median_pe:.1f}")

    # ── Debt (max 3) ───────────────────────────────────────────────────────
    if dte <= 0.0:
        score += 3
        reasons.append("Effectively debt-free — strong balance sheet")
    elif dte < 0.5:
        score += 2
        reasons.append(f"Low debt (D/E {dte:.2f})")
    elif dte > 1.0:
        cautions.append(f"High debt (D/E {dte:.2f}) — watch borrowings")

    # ── Profitability (max 2) ──────────────────────────────────────────────
    if _profit_rising(trend):
        score += 2
        reasons.append(f"Net profit rose every year for {len(trend)} years")
    elif trend and trend[-1] < trend[0]:
        cautions.append("Profit lower than a few years ago")

    # ── Technical (max 2) ──────────────────────────────────────────────────
    if tech:
        sma200 = tech.get("sma200", 0.0)
        rsi = tech.get("rsi", 50.0)
        if sma200 > 0 and stock.get("price", 0) > sma200:
            score += 2
            reasons.append("Trading above its 200-day average (uptrend)")
        elif sma200 > 0:
            cautions.append("Below its 200-day average (downtrend)")
        if rsi >= 70:
            cautions.append(f"Overbought (RSI {rsi:.0f}) — may be due a pullback")

    verdict = "Strong" if score >= 7 else "Watch" if score >= 4 else "Weak"

    return {
        "symbol": stock["symbol"],
        "name": stock["name"],
        "score": round(score, 1),
        "verdict": verdict,
        "reasons": reasons,
        "cautions": cautions,
    }
