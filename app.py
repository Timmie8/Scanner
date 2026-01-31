import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. CONFIG ---
st.set_page_config(page_title="SST AI Terminal", layout="wide")

# CSS injecteren voor de algemene look van de pagina
st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1e293b; }
    h1 { color: #60a5fa !important; font-family: sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR ---
st.sidebar.markdown("<h2 style='color: white;'>🛠 CONTROL</h2>", unsafe_allow_html=True)
user_input = st.sidebar.text_input("TICKERS (CSV):", value="ANET, ERAS, NVDA, AMZN")
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
            
            if ensemble > 80: rating, color = "STRONG BUY", "#00FF00" 
            elif ensemble > 65: rating, color = "BUY", "#2ecc71"         
            elif ensemble < 35: rating, color = "SELL", "#FF0000"        
            else: rating, color = "NEUTRAL", "#3498db"      
            
            results.append({
                "ticker": symbol,
                "price": f"${bars['close'].iloc[-1]:.2f}",
                "ensemble": f"{ensemble:.1f}",
                "lstm": f"{lstm_force:.1f}%",
                "rating": rating,
                "color": color,
                "stop": f"${(bars['close'].iloc[-1] - (atr * 1.5)):.2f}"
            })
        except: continue
    return results

# --- 5. UI DISPLAY (DIT IS DE FIX) ---
st.markdown("<h1 style='font-style: italic;'>🚀 SST NEURAL | AI TERMINAL</h1>", unsafe_allow_html=True)

if selected_tickers:
    data = get_analysis(selected_tickers)
    if data:
        # We bouwen de HTML string
        table_html = """
        <table style="width: 100%; border-collapse: collapse; background-color: black; color: white; font-family: sans-serif;">
            <thead>
                <tr style="border-bottom: 2px solid #334155; color: #94a3b8; text-transform: uppercase; font-size: 13px;">
                    <th style="padding: 15px; text-align: left;">Symbol</th>
                    <th style="padding: 15px; text-align: left;">Price</th>
                    <th style="padding: 15px; text-align: left;">Ensemble</th>
                    <th style="padding: 15px; text-align: left;">LSTM Force</th>
                    <th style="padding: 15px; text-align: left;">Rating</th>
                    <th style="padding: 15px; text-align: left;">Risk Stop</th>
                </tr>
            </thead>
            <tbody>
        """
        for s in data:
            table_html += f"""
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 15px; font-weight: 800; color: #FFFFFF;">{s['ticker']}</td>
                    <td style="padding: 15px; color: #FFFFFF;">{s['price']}</td>
                    <td style="padding: 15px; color: #60a5fa; font-family: monospace;">{s['ensemble']}</td>
                    <td style="padding: 15px; color: #94a3b8;">{s['lstm']}</td>
                    <td style="padding: 15px; color: {s['color']}; font-weight: 900; text-transform: uppercase;">{s['rating']}</td>
                    <td style="padding: 15px; color: #fb7185; font-style: italic;">{s['stop']}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        
        # CRUCIALE STAP: Gebruik markdown met unsafe_allow_html=True om de tabel te renderen
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.error("NO DATA FOUND.")

st.markdown("<br><hr style='border: 1px solid #1e293b;'>", unsafe_allow_html=True)
st.caption(f"SYNC: {datetime.now().strftime('%H:%M:%S')} EST")

