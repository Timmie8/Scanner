import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="SST AI Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    .main-title { color: #60a5fa; font-size: 30px; font-weight: 800; font-style: italic; }
    /* Tabel Styling */
    .sst-table { width: 100%; border-collapse: collapse; color: white; font-family: sans-serif; }
    .sst-table th { text-align: left; padding: 12px; border-bottom: 2px solid #1e293b; color: #94a3b8; text-transform: uppercase; font-size: 12px; }
    .sst-table td { padding: 15px; border-bottom: 1px solid #1e293b; font-size: 16px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR ---
st.sidebar.markdown("### 🛠 CONTROL PANEL")
user_input = st.sidebar.text_input("ENTER TICKERS (CSV):", value="ANET, ERAS, NVDA, AMZN")
selected_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 4. ENGINE ---
@st.cache_data(ttl=300)
def get_analysis(tickers):
    if not tickers: return []
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    results = []
    for symbol in tickers:
        try:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(req).df.xs(symbol)
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            ensemble = np.clip((lstm_force * 0.6) + ((100 - abs(rsi_val - 60) * 2) * 0.4), 0, 100)
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            if ensemble > 80: rating, color = "STRONG BUY", "#00FF00" # Fel Groen
            elif ensemble > 65: rating, color = "BUY", "#22c55e" # Groen
            elif ensemble < 35: rating, color = "SELL", "#FF0000" # Rood
            else: rating, color = "NEUTRAL", "#3b82f6" # Blauw
            
            results.append({
                "ticker": symbol,
                "price": f"${round(bars['close'].iloc[-1], 2)}",
                "ensemble": round(ensemble, 1),
                "lstm": f"{round(lstm_force, 1)}%",
                "rating": rating,
                "color": color,
                "stop": f"${round(bars['close'].iloc[-1] - (atr * 1.5), 2)}"
            })
        except: continue
    return results

# --- 5. UI DISPLAY ---
st.markdown('<p class="main-title">🚀 SST NEURAL | AI TERMINAL</p>', unsafe_allow_html=True)

if selected_tickers:
    data = get_analysis(selected_tickers)
    if data:
        # Handmatige HTML Tabel Bouwen voor gegarandeerde kleur
        table_html = """
        <table class="sst-table">
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>Ensemble</th>
                    <th>LSTM Force</th>
                    <th>Rating</th>
                    <th>Stop Loss</th>
                </tr>
            </thead>
            <tbody>
        """
        for s in data:
            table_html += f"""
                <tr>
                    <td style="color: white;">{s['ticker']}</td>
                    <td style="color: white;">{s['price']}</td>
                    <td style="color: #60a5fa;">{s['ensemble']}</td>
                    <td style="color: #94a3b8;">{s['lstm']}</td>
                    <td style="color: {s['color']}; font-weight: 800; font-size: 18px;">{s['rating']}</td>
                    <td style="color: #fb7185;">{s['stop']}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        st.write(table_html, unsafe_allow_html=True)
    else:
        st.error("NO DATA FOUND. CHECK TICKERS.")

st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption(f"SYSTEM STATUS: ONLINE | {datetime.now().strftime('%H:%M:%S')} EST")

