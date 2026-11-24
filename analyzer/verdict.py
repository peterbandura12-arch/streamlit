from __future__ import annotations

WEIGHTS = {"technical": 0.5, "fundamentals": 0.2, "news": 0.3}


def verdict(technical: float, fundamentals: float, news: float) -> dict:
    total = (
        technical * WEIGHTS["technical"]
        + fundamentals * WEIGHTS["fundamentals"]
        + news * WEIGHTS["news"]
    )
    total = round(max(0.0, min(100.0, total)), 1)

    if total >= 62:
        action, color = "BUY", "green"
    elif total <= 38:
        action, color = "SELL", "red"
    else:
        action, color = "HOLD", "orange"

    return {"score": total, "action": action, "color": color}
