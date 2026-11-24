from __future__ import annotations

import re
from datetime import datetime, timezone

import yfinance as yf

POSITIVE = {
    "beat": 2, "beats": 2, "surge": 2, "surges": 2, "soar": 2, "soars": 2, "record": 2,
    "upgrade": 2, "upgraded": 2, "upgrades": 2, "outperform": 2, "bullish": 2, "rally": 2,
    "growth": 1, "gain": 1, "gains": 1, "profit": 1, "strong": 1, "wins": 2, "win": 1,
    "expansion": 1, "expand": 1, "partner": 1, "partnership": 1, "contract": 1, "dividend": 1,
    "raise": 1, "raised": 1, "rising": 1, "jumps": 2, "jump": 1, "climbs": 1, "tops": 1,
    "optimism": 1, "optimistic": 1, "innovatio": 1, "breakthrough": 2, "buy": 1, "boost": 1,
    "boosts": 1, "recovery": 1, "robust": 1, "exceeds": 1, "milestone": 1, "approval": 2,
    "approved": 2, "acquisition": 1, "ai leader": 2,
}

NEGATIVE = {
    "miss": -2, "misses": -2, "missed": -2, "plunge": -2, "plunges": -2, "crash": -2,
    "downgrade": -2, "downgraded": -2, "underperform": -2, "bearish": -2, "slump": -2,
    "slumps": -2, "loss": -2, "losses": -2, "lawsuit": -2, "probe": -2, "investigation": -2,
    "fraud": -3, "recall": -2, "layoff": -2, "layoffs": -2, "cuts": -1, "cut": -1,
    "weak": -1, "decline": -1, "declines": -1, "falls": -1, "fall": -1, "drop": -1,
    "drops": -1, "warning": -2, "warns": -2, "risk": -1, "fine": -1, "fined": -2,
    "shortage": -2, "deficit": -2, "halt": -2, "halted": -2, "debts": -1, "bankruptcy": -3,
    "sell": -1, "sell-off": -2, "selloff": -2, "sink": -2, "sinks": -2, "slip": -1,
    "slips": -1, "delay": -1, "delays": -1, "scandal": -3, "crisis": -2, "turmoil": -2,
}

WORD_RE = re.compile(r"[a-zA-Z]+")


def fetch_news(ticker: str, count: int = 20) -> list[dict]:
    raw = yf.Ticker(ticker).get_news(count=count) or []
    news = []
    for item in raw:
        content = item.get("content", item) if isinstance(item, dict) else {}
        title = content.get("title") or item.get("title")
        if not title:
            continue
        pub = content.get("pubDate") or item.get("providerPublishTime")
        published = None
        if isinstance(pub, str):
            try:
                published = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                published = None
        elif isinstance(pub, (int, float)):
            published = datetime.fromtimestamp(pub, tz=timezone.utc)
        summary = content.get("summary") or item.get("summary") or ""
        url = None
        canonical = content.get("canonicalUrl")
        if isinstance(canonical, dict):
            url = canonical.get("url")
        elif isinstance(canonical, str):
            url = canonical
        link = url or content.get("clickThroughUrl") or item.get("link")
        news.append({"title": title, "summary": summary, "published": published, "url": link})
    return news


def _match(text: str, lexicon: dict) -> tuple[list[str], float]:
    words = set(w.lower() for w in WORD_RE.findall(text))
    hits = []
    total = 0.0
    lowered = text.lower()
    for phrase, weight in lexicon.items():
        if " " in phrase:
            if phrase in lowered:
                hits.append((phrase, weight))
                total += weight
        elif phrase in words:
            hits.append((phrase, weight))
            total += weight
    return hits, total


def rule_sentiment(news: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    results = []
    for item in news:
        text = f"{item['title']} {item['summary']}"
        pos_hits, pos_score = _match(text, POSITIVE)
        neg_hits, neg_score = _match(text, NEGATIVE)
        raw = pos_score + neg_score
        raw = max(-4.0, min(4.0, raw))
        published = item.get("published")
        if published is not None and published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_days = ((now - published).days if published else 14)
        age_days = max(0, age_days)
        recency = max(0.4, 1.0 - age_days / 21)
        results.append({
            **item,
            "sentiment": round(raw * 25, 1),
            "raw": raw,
            "positive": [h for h, _ in pos_hits],
            "negative": [h for h, _ in neg_hits],
            "recency": recency,
        })
    return results


def news_score(results: list[dict]) -> tuple[float, float]:
    if not results:
        return 50.0, 0.0
    weighted = 0.0
    weights = 0.0
    for r in results:
        w = r.get("recency", 1.0)
        weighted += r["raw"] / 4 * 50 * w
        weights += w
    if weights == 0:
        return 50.0, 0.0
    score = round(50 + weighted / weights, 1)
    score = max(0.0, min(100.0, score))
    return score, weights
