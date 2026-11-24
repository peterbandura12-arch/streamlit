from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyzer import llm as llm_mod
from analyzer import technical as tech
from analyzer.fundamentals import fundamentals_analysis
from analyzer.news import fetch_news, news_score, rule_sentiment
from analyzer.verdict import verdict

st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    .big-verdict {font-size: 3rem; font-weight: 800; text-align: center; padding: .3em;}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ Nastavenia")
    ticker = st.text_input("Ticker (Yahoo Finance)", value="AAPL").strip().upper()
    period = st.select_slider("Obdobie grafu", options=list(tech.PERIODS), value="1y")

    st.divider()
    st.subheader("🤖 Voliteľné LLM rozšírenie")
    st.caption("Ak vyplníš API kľúč, správy vyhodnotí jazykový model namiesto pravidiel.")
    provider = st.selectbox("Poskytovateľ", list(llm_mod.PRESET.keys()))
    default_url, default_model = llm_mod.PRESET[provider]
    llm_url = st.text_input("Base URL", value=default_url or "https://api.mistral.ai/v1").strip()
    llm_model = st.text_input("Model", value=default_model or "mistral-small-latest").strip()
    llm_key = st.text_input("API kľúč", type="password")

st.title("📈 Analyzer BUY / HOLD / SELL")
st.caption("Technická + fundamentálna + news analýza. Nie je to investičná rada.")

if not ticker:
    st.info("Zadaj ticker v bočnom paneli.")
    st.stop()

@st.cache_data(ttl=600, show_spinner="Načítavam dáta…")
def run_technical(t: str, p: str):
    df = tech.fetch_history(t, p)
    return df, tech.technical_analysis(df)

@st.cache_data(ttl=600, show_spinner="Načítavam fundamenty…")
def run_fundamentals(t: str, price: float):
    return fundamentals_analysis(t, price)

@st.cache_data(ttl=600, show_spinner="Načítavam správy…")
def run_news(t: str, count: int):
    return fetch_news(t, count)

@st.cache_data(ttl=600, show_spinner="LLM analyzuje správy…")
def run_llm(news, key: str, url: str, model: str):
    return llm_mod.llm_sentiment(news, key, url, model)

try:
    df, tech_res = run_technical(ticker, period)
except Exception as e:
    st.error(f"Nepodarilo sa načítať dáta pre '{ticker}': {e}")
    st.stop()

fund_res = run_fundamentals(ticker, tech_res["stats"]["price"])

news_raw = run_news(ticker, 20)
news_results = rule_sentiment(news_raw)
llm_used = False
if llm_key and news_results:
    try:
        news_results = run_llm(news_results, llm_key, llm_url, llm_model)
        news_results = llm_mod.apply_llm_overrides(news_results)
        llm_used = True
    except Exception as e:
        st.warning(f"LLM analýza zlyhala ({e}) – používa sa pravidlový sentiment.")
news_res, news_weight_total = news_score(news_results)

ver = verdict(tech_res["score"], fund_res["score"], news_res)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cena", f"{tech_res['stats']['price']:,.2f}")
c2.metric("RSI (14)", f"{tech_res['stats']['rsi']:.1f}")
c3.metric("SMA200", f"{tech_res['stats']['sma200']:,.2f}")
c4.metric("Konsenzus analytikov", next(
    (row["Hodnota"] for row in fund_res["table"] if row["Meta"] == "Konsenzus analytikov"),
    "—",
))

st.markdown(
    f"""
    <div class="big-verdict" style="color:{ver['color']};">
        {ver['action']} &nbsp;•&nbsp; {ver['score']}/100
    </div>
    <div style="text-align:center; margin-top:-8px; margin-bottom:16px;">
        Technická {tech_res['score']}/100 (50 %) • Fundamenty {fund_res['score']}/100 (20 %) •
        News {news_res:.0f}/100 (30 %{' – LLM' if llm_used else ''})
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Technická", "🏛️ Fundamenty", "📰 Správy", "⚖️ Zhrnutie"])

with tab1:
    st.subheader(f"{ticker} – cena a indikátory")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Cena", line=dict(color="#1f77b4", width=2)))
    for col, color, dash in (("SMA20", "#ff7f0e", "solid"), ("SMA50", "#2ca02c", "solid"), ("SMA200", "#d62728", "dash")):
        if df[col].notna().any():
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(color=color, dash=dash, width=1.2)))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_UP"], name="BB horné", line=dict(width=0.8, color="gray"),
        showlegend=True))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_LOW"], name="BB dolné", fill="tonexty",
        fillcolor="rgba(128,128,128,0.08)", line=dict(width=0.8, color="gray"), showlegend=True))
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI", line=dict(color="#9467bd")))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(height=260, title="RSI (14)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_rsi, use_container_width=True)
    with col2:
        fig_macd = go.Figure()
        fig_macd.add_bar(x=df.index, y=df["MACD_HIST"], marker_color="rgba(100,100,100,0.4)", name="Hist")
        fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#1f77b4")))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD_SIGNAL"], name="Signal", line=dict(color="#ff7f0e")))
        fig_macd.update_layout(height=260, title="MACD (12, 26, 9)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_macd, use_container_width=True)

    st.markdown("#### Signály")
    for s in tech_res["signals"]:
        emoji = "🟢" if s["score"] > 0.1 else ("🔴" if s["score"] < -0.1 else "🟡")
        st.markdown(f"{emoji} **{s['name']}** – {s['reason']}")

with tab2:
    st.subheader("Fundamentálne dáta")
    st.dataframe(
        fund_res["table"],
        hide_index=True,
        use_container_width=True,
        column_config={"Meta": st.column_config.TextColumn("Ukazovateľ", width="medium")},
    )
    st.markdown("#### Fundamentálne signály")
    for s in fund_res["signals"]:
        emoji = "🟢" if s["score"] > 0.1 else ("🔴" if s["score"] < -0.1 else "🟡")
        st.markdown(f"{emoji} {s['reason']}")

with tab3:
    st.subheader("Správy (news)")
    st.caption(
        "Sentiment počítaný "
        + ("LLM modelom 🤖." if llm_used else "pravidlami (kľúčové slová). Zadaj API kľúč v sidebare pre LLM analýzu.")
    )
    if not news_results:
        st.info("Pre tento ticker sa nenašli žiadne správy.")
    else:
        for r in news_results:
            if llm_used and r.get("llm_reason"):
                detail = r["llm_reason"]
            elif r["positive"] or r["negative"]:
                parts = []
                if r["positive"]:
                    parts.append("pozitívne: " + ", ".join(r["positive"][:5]))
                if r["negative"]:
                    parts.append("negatívne: " + ", ".join(r["negative"][:5]))
                detail = " | ".join(parts)
            else:
                detail = "bez jasného sentimentu"
            emoji = "🟢" if r["sentiment"] > 5 else ("🔴" if r["sentiment"] < -5 else "🟡")
            title_html = r["title"]
            if r.get("url"):
                st.markdown(f"{emoji} **[{title_html}]({r['url']})** — sentiment {r['sentiment']:+.0f}  \n{detail}")
            else:
                st.markdown(f"{emoji} **{title_html}** — sentiment {r['sentiment']:+.0f}  \n{detail}")

with tab4:
    st.subheader("Zhrnutie odporúčania")
    z1, z2, z3 = st.columns(3)
    z1.metric("Technická analýza", f"{tech_res['score']}/100", "50 % váhy")
    z2.metric("Fundamenty", f"{fund_res['score']}/100", "20 % váhy")
    z3.metric("Správy", f"{news_res:.0f}/100", "30 % váhy")

    total = ver["score"]
    st.progress(int(total), text=f"Celkové skóre {total}/100 → {ver['action']}")

    st.markdown("""
    Ako čítať výsledok:

    - **BUY** (skóre ≥ 62): technické signály aj fundamenty/správy podporujú rast.
    - **HOLD** (38–62): zmiešané signály – počkaj na jasnejší obraz.
    - **SELL** (skóre ≤ 38): prevažujú negatívne signály naprieč oblasťami.
    """)

    st.error(
        "⚠️ Tento nástroj je informatívny a nie je investičným poradenstvom. "
        "Nie je to investičná rada."
    )

st.caption(f"Aktuálizované: {df.index[-1].date()} • Ticker: {ticker} • Obdobie: {period}")
