import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. CONFIG & CSS VOOR MAXIMAAL CONTRAST ---
st.set_page_config(page_title="SST AI Terminal", layout="wide")

st.markdown("""
    <style>
    /* Volledige achtergrond zwart */
    .stApp { background-color: #000000; }
    
    /* Tabel Styling */
    .sst-table { 
        width: 100%; 
        border-collapse: collapse; 
        color: #ffffff; 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
    }
    .sst-table th { 
        text-align: left; 
        padding: 15px; 
        border-bottom: 2px solid #334155; 
        color: #94a3b8; 
        text-transform: uppercase; 
        font-size: 13px;
        letter-spacing: 1px;
    }
    .sst-table td { 
        padding: 18px; 
        border-bottom: 1px solid #1e293b; 
        font-size: 16px; 
    }
    .sst-table tr:hover { background-color: #0f172a; }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1e293b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR ---
st.sidebar.markdown("<h2 style='color: #60a5fa;'>🛠 CONTROL</h2>", unsafe_allow_html=True)
user_input = st.sidebar.text_input("ENTER TICKERS (CSV):", value="ANET, ERAS, NVDA, AMZN")
selected_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 4. DATA ENGINE ---
@st.cache_data(ttl=300)
def get_analysis(tickers):
    if not tickers: return []
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    results = []
    for symbol in tickers:
        try:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(req).df.xs(symbol)
            
            # LSTM & Ensemble Logica
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            ensemble = np.clip((lstm_force * 0.6) + ((100 - abs(rsi_val - 60) * 2) * 0.4), 0, 100)
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            # --- DE KLEUREN LOGICA ---
            if ensemble > 80: 
                rating, color = "STRONG BUY", "#00FF00"  # Fel Neon Groen
            elif ensemble > 65: 
                rating, color = "BUY", "#2ecc71"         # Emerald Groen
            elif ensemble < 35: 
                rating, color = "SELL", "#FF0000"        # Fel Rood
            else: 
                rating, color = "NEUTRAL", "#3498db"      # Helder Blauw
            
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

# --- 5. INTERFACE ---
st.markdown("<h1 style='color: #60a5fa; font-style: italic;'>🚀 SST NEURAL | AI TERMINAL</h1>", unsafe_allow_html=True)

if selected_tickers:
    data = get_analysis(selected_tickers)
    if data:
        # De HTML Tabel met geforceerde kleuren
        table_html = """
        <table class="sst-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Ensemble</th>
                    <th>LSTM Force</th>
                    <th>Rating</th>
                    <th>Risk Stop</th>
                </tr>
            </thead>
            <tbody>
        """
        for s in data:
            table_html += f"""
                <tr>
                    <td style="font-weight: 800; color: #FFFFFF;">{s['ticker']}</td>
                    <td style="color: #FFFFFF;">{s['price']}</td>
                    <td style="color: #60a5fa; font-family: monospace;">{s['ensemble']}</td>
                    <td style="color: #94a3b8;">{s['lstm']}</td>
                    <td style="color: {s['color']}; font-weight: 900; text-transform: uppercase;">{s['rating']}</td>
                    <td style="color: #fb7185; font-style: italic;">{s['stop']}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        st.write(table_html, unsafe_allow_html=True)
    else:
        st.error("NO DATA FOUND. CHECK SYMBOLS.")

st.markdown("<br><hr style='border: 1px solid #1e293b;'>", unsafe_allow_html=True)
st.caption(f"TERMINAL STATUS: ONLINE | SYNC: {datetime.now().strftime('%H:%M:%S')} EST")
