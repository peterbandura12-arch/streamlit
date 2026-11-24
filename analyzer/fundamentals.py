from __future__ import annotations

import yfinance as yf

FIELDS = [
    ("shortName", "Spoločnosť", None),
    ("sector", "Sektor", None),
    ("industry", "Industria", None),
    ("marketCap", "Market cap", "cap"),
    ("trailingPE", "P/E (trailing)", "num"),
    ("forwardPE", "P/E (forward)", "num"),
    ("priceToBook", "P/B", "num"),
    ("dividendYield", "Dividendový výnos", "pct_raw"),
    ("profitMargins", "Zisková marža", "pct"),
    ("operatingMargins", "Operačná marža", "pct"),
    ("revenueGrowth", "Rast tržieb (YoY)", "pct"),
    ("earningsGrowth", "Rast zisku (YoY)", "pct"),
    ("debtToEquity", "Dlhopis/Equity", "num_raw"),
    ("beta", "Beta", "num"),
    ("targetMeanPrice", "Cieľová cena (priemer)", "num"),
    ("recommendationMean", "Konsenzus analytikov", "rec"),
    ("numberOfAnalystOpinions", "Počet analytikov", "num"),
    ("totalCash", "Hotovosť", "cap"),
    ("totalDebt", "Dlh", "cap"),
]


def _fmt(value, kind):
    if value is None:
        return "—"
    try:
        if kind == "cap":
            v = float(value)
            for unit, div in (("B", 1e9), ("M", 1e6)):
                if abs(v) >= div:
                    return f"{v / div:,.1f} {unit}".replace(",", " ")
            return f"{v:,.0f}"
        if kind == "num":
            return f"{float(value):,.2f}"
        if kind == "num_raw":
            return f"{float(value):,.1f}"
        if kind == "pct":
            return f"{float(value) * 100:+.1f} %"
        if kind == "pct_raw":
            v = float(value)
            if abs(v) < 1:
                return f"{v * 100:.2f} %"
            return f"{v:.2f} %"
        if kind == "rec":
            v = float(value)
            label = {1.0: "Strong Buy", 2.0: "Buy", 3.0: "Hold", 4.0: "Sell", 5.0: "Strong Sell"}
            nearest = min(label, key=lambda k: abs(k - v))
            return f"{v:.2f} ({label[nearest]})"
        return str(value)
    except (TypeError, ValueError):
        return str(value)


def fundamentals_analysis(ticker: str, current_price: float | None = None) -> dict:
    info = yf.Ticker(ticker).get_info() or {}

    table = []
    for key, label, kind in FIELDS:
        if key not in info or info[key] is None:
            continue
        table.append({"Meta": label, "Hodnota": _fmt(info[key], kind)})

    signals = []

    pe = info.get("trailingPE")
    if isinstance(pe, (int, float)) and pe > 0:
        if pe < 15:
            signals.append((0.6, f"Nízke P/E {pe:.1f} – relatívne lacné ocenenie."))
        elif pe > 50:
            signals.append((-0.4, f"Vysoké P/E {pe:.1f} – drahé ocenenie, veľké očakávania."))
        else:
            signals.append((0.0, f"P/E {pe:.1f} – stredný rozsah."))

    growth = info.get("revenueGrowth")
    if isinstance(growth, (int, float)):
        if growth > 0.1:
            signals.append((0.6, f"Silný rast tržieb {growth * 100:+.1f} % YoY."))
        elif growth < -0.05:
            signals.append((-0.6, f"Klesajúce tržby {growth * 100:+.1f} % YoY."))
        else:
            signals.append((0.1, f"Tržby približne stagnujú ({growth * 100:+.1f} % YoY)."))

    margins = info.get("profitMargins")
    if isinstance(margins, (int, float)):
        if margins > 0.15:
            signals.append((0.5, f"Zisková marža {margins * 100:.1f} % – vysoká rentabilita."))
        elif margins < 0:
            signals.append((-0.6, f"Negatívna marža {margins * 100:.1f} % – spoločnosť stráca."))
        else:
            signals.append((0.0, f"Marža {margins * 100:.1f} %."))

    de = info.get("debtToEquity")
    if isinstance(de, (int, float)) and de > 0:
        if de > 200:
            signals.append((-0.4, f"Vysoké zadlženie D/E {de:.0f} %."))
        elif de < 80:
            signals.append((0.3, f"Zdravé zadlženie D/E {de:.0f} %."))

    target = info.get("targetMeanPrice")
    if isinstance(target, (int, float)) and isinstance(current_price, (int, float)) and current_price > 0:
        upside = (target / current_price - 1) * 100
        if upside > 15:
            signals.append((0.6, f"Analytici vidia potenciál {upside:+.1f} % (cieľ {target:.2f})."))
        elif upside < -15:
            signals.append((-0.6, f"Analytici vidia pokles {upside:+.1f} % (cieľ {target:.2f})."))
        else:
            signals.append((0.0, f"Cieľ analytikov {target:.2f} ({upside:+.1f} %)."))

    rec = info.get("recommendationMean")
    if isinstance(rec, (int, float)) and rec > 0:
        if rec <= 2.0:
            signals.append((0.5, f"Konsenzus analytikov {rec:.2f} – Buy."))
        elif rec >= 4.0:
            signals.append((-0.5, f"Konsenzus analytikov {rec:.2f} – Sell."))
        else:
            signals.append((0.0, f"Konsenzus analytikov {rec:.2f} – Hold."))

    if not signals:
        signals.append((0.0, "Chýbajú fundamentálne dáta pre tento ticker."))

    total_w = len(signals)
    raw = sum(s for s, _ in signals)
    score_100 = round(50 + raw / total_w * 50)

    return {
        "score": score_100,
        "signals": [{"reason": r, "score": s} for s, r in signals],
        "table": table,
    }
