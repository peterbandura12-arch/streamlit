# 📈 Stock Analyzer – BUY / HOLD / SELL

Streamlit appka, ktorá podrobne analyzuje akcie a odporučí, či je vhodnejší nákup, držanie alebo predaj.

## Funkcie

- **Technická analýza** – SMA 20/50/200, EMA 20, RSI (14), MACD (12, 26, 9), Bollingerove pásma, objemový trend, 52-týždňový rozsah. Každý signál má vlastné vysvetlenie a váhu.
- **Fundamentálna analýza** – P/E, P/B, market cap, marže, rast tržieb a zisku, zadlženie, cieľová cena a konsenzus analytikov.
- **Správy (news)** – automaticky stiahne aktuálne články viazané na ticker a vyhodnotí sentiment:
  - **default** – pravidlový sentiment (kľúčové slová, vážené podľa veku správy),
  - **voliteľne LLM** – zadaj vlastný API kľúč (Mistral alebo akýkoľvek OpenAI-compatible endpoint) a správy prehodnotí jazykový model vrátane krátkeho vysvetlenia v slovenčine.
- **Finálne odporúčanie** – kombinácia váh: 50 % technika + 20 % fundamenty + 30 % správy → skóre 0–100 → **BUY / HOLD / SELL**.
- **Grafy** – vývoj ceny s kĺzavými priemermi a Bollingerovými pásmi, RSI, MACD.

## Spustenie

```bash
pip install -r requirements.txt
streamlit run app.py
```

Appka sa otvorí na `http://localhost:8501`.

## Použitie

1. V bočnom paneli zadaj ticker (napr. `AAPL`, `MSFT`, `TSLA`, `SIE.DE`).
2. Vyber obdobie grafu (6 mesiacov – 5 rokov).
3. (Voliteľné) V sekcii 🤖 zadaj API kľúč pre LLM analýzu správ – napr. pre Mistral alebo OpenAI.
4. V appke sa zobrazí finálne odporúčanie: **BUY / HOLD / SELL** + skóre a taby s detailmi.

## Ako sa počítá skóre

| Oblasť     | Váha | Podklad                                        |
|------------|------|------------------------------------------------|
| Technika   | 50 % | Kĺzavé priemery, RSI, MACD, Bollinger, objem  |
| Fundamenty | 20 % | Oceńovanie, rast, marže, zadlženie, konsenzus analytikov |
| Správy     | 30 % | Sentiment článkov (pravidlá alebo LLM), recency váhový faktor |

Skóre ≥ 62 → **BUY**, skóre ≤ 38 → **SELL**, medzi tým → **HOLD**.

## ⚠️ Dôležité upozornenie

Tento nástroj je **informatívny a nie je investičným poradenstvom**. Negarantuje presnosť dát ani výsledok – investovanie nesie riziko. Dáta sú stiahnuté z Yahoo Finance cez knižnicu `yfinance`.
