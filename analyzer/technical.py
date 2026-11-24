from __future__ import annotations

import pandas as pd
import yfinance as yf

PERIODS = ("6mo", "1y", "2y", "5y")


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def _bollinger(close: pd.Series, length: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(length).mean()
    std = close.rolling(length).std()
    return mid, mid + 2 * std, mid - 2 * std


def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df.empty:
        raise ValueError(f"Nenašli sa dáta pre ticker '{ticker}'.")
    close = df["Close"]
    df["SMA20"] = close.rolling(20).mean()
    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["RSI14"] = _rsi(close)
    macd, signal, hist = _macd(close)
    df["MACD"] = macd
    df["MACD_SIGNAL"] = signal
    df["MACD_HIST"] = hist
    mid, upper, lower = _bollinger(close)
    df["BB_MID"] = mid
    df["BB_UP"] = upper
    df["BB_LOW"] = lower
    df["VOL_AVG20"] = df["Volume"].rolling(20).mean()
    return df.dropna(subset=["Close"])


def _signal(name: str, score: float, reason: str) -> dict:
    return {"name": name, "score": score, "reason": reason}


def technical_analysis(df: pd.DataFrame) -> dict:
    if df.empty:
        raise ValueError("Prázdna história cien.")
    close = df["Close"]
    last = float(close.iloc[-1])

    sma20 = df["SMA20"].iloc[-1] if pd.notna(df["SMA20"].iloc[-1]) else last
    sma50 = df["SMA50"].iloc[-1] if pd.notna(df["SMA50"].iloc[-1]) else last
    sma200 = df["SMA200"].iloc[-1] if pd.notna(df["SMA200"].iloc[-1]) else sma50
    rsi = float(df["RSI14"].iloc[-1])
    macd = float(df["MACD"].iloc[-1])
    macd_sig = float(df["MACD_SIGNAL"].iloc[-1])
    bb_mid = float(df["BB_MID"].iloc[-1])
    bb_up = float(df["BB_UP"].iloc[-1])
    bb_low = float(df["BB_LOW"].iloc[-1])
    vol_avg = df["VOL_AVG20"].iloc[-1]
    vol_last = float(df["Volume"].iloc[-1])

    signals: list[dict] = []

    if last > sma200:
        signals.append(_signal("Trend (SMA200)", 1.0, f"Cena je nad SMA200 ({sma200:.2f}) – dlhodobý rastový trend."))
    else:
        signals.append(_signal("Trend (SMA200)", -1.0, f"Cena je pod SMA200 ({sma200:.2f}) – dlhodobý poklesový trend."))

    if sma50 > sma200:
        signals.append(_signal("Kríženie SMA50/SMA200", 1.0, "SMA50 nad SMA200 (golden cross) – býčí signál."))
    else:
        signals.append(_signal("Kríženie SMA50/SMA200", -1.0, "SMA50 pod SMA200 (death cross) – medvedí signál."))

    if last > sma20:
        signals.append(_signal("Krátkodobý trend (SMA20)", 0.5, f"Cena nad SMA20 ({sma20:.2f})."))
    else:
        signals.append(_signal("Krátkodobý trend (SMA20)", -0.5, f"Cena pod SMA20 ({sma20:.2f})."))

    if rsi >= 70:
        signals.append(_signal("RSI (14)", -0.8, f"RSI {rsi:.1f} – prekúpená zóna, riziko korekcie."))
    elif rsi <= 30:
        signals.append(_signal("RSI (14)", 0.8, f"RSI {rsi:.1f} – prepredaná zóna, potenciálny odraz."))
    elif rsi > 55:
        signals.append(_signal("RSI (14)", 0.4, f"RSI {rsi:.1f} – mierna dominantná kupujúcich strana."))
    elif rsi < 45:
        signals.append(_signal("RSI (14)", -0.4, f"RSI {rsi:.1f} – mierna dominanta predávajúcich."))
    else:
        signals.append(_signal("RSI (14)", 0.0, f"RSI {rsi:.1f} – neutrálna zóna."))

    if macd > macd_sig:
        signals.append(_signal("MACD", 0.7, "MACD nad signálnou linkou – pozitívna hybnosť."))
    else:
        signals.append(_signal("MACD", -0.7, "MACD pod signálnou linkou – negatívna hybnosť."))

    if last >= bb_up:
        signals.append(_signal("Bollinger pásmo", -0.5, f"Cena nad horným pásmom ({bb_up:.2f}) – prehriatie."))
    elif last <= bb_low:
        signals.append(_signal("Bollinger pásmo", 0.5, f"Cena pod dolným pásmom ({bb_low:.2f}) – vypredané, možný odraz."))
    else:
        pos = (last - bb_low) / max(bb_up - bb_low, 1e-9)
        score = (pos - 0.5) * 0.6
        signals.append(_signal("Bollinger pásmo", score, f"Cena na {pos:.0%} rozsahu pásmi ({bb_low:.2f} – {bb_up:.2f})."))

    if pd.notna(vol_avg) and vol_avg > 0:
        vol_ratio = vol_last / float(vol_avg)
        pct20 = (last / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else 0.0
        if vol_ratio > 1.5:
            trend_score = 0.5 if pct20 > 0 else -0.5
            signals.append(_signal("Objem", trend_score, f"Objem {vol_ratio:.1f}× nadpriemer, {pct20:+.1f}% za 20 dní – silný presun."))
        else:
            signals.append(_signal("Objem", 0.0, f"Objem {vol_ratio:.1f}× priemer – bez extrémov, {pct20:+.1f}% za 20 dní."))

    high52 = float(close.tail(252).max()) if len(close) > 0 else last
    low52 = float(close.tail(252).min())
    off_high = (last / high52 - 1) * 100
    off_low = (last / low52 - 1) * 100
    signals.append(_signal("52-týždňový rozsah", 0.0, f"{off_high:+.1f}% od maxima ({high52:.2f}), {off_low:+.1f}% od minima ({low52:.2f})."))

    weights = {
        "Trend (SMA200)": 1.5,
        "Kríženie SMA50/SMA200": 1.2,
        "Krátkodobý trend (SMA20)": 0.8,
        "RSI (14)": 1.0,
        "MACD": 1.2,
        "Bollinger pásmo": 0.8,
        "Objem": 0.6,
        "52-týždňový rozsah": 0.0,
    }
    total_w = sum(w for s in signals if (w := weights.get(s["name"], 1.0)) and s["name"] != "52-týždňový rozsah")
    raw = sum(s["score"] * weights.get(s["name"], 1.0) for s in signals if s["name"] != "52-týždňový rozsah")
    score_100 = round(50 + raw / total_w * 50)

    return {
        "score": score_100,
        "signals": signals,
        "stats": {
            "price": last,
            "rsi": rsi,
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "high52": high52,
            "low52": low52,
        },
    }
