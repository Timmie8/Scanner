import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. STYLING VOOR CONTRAST & LEESBAARHEID ---
st.set_page_config(page_title="SST AI Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    
    /* Felwitte algemene tekst */
    p, span, label, .stMarkdown {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Titels */
    h1, h2 { color: #60a5fa !important; text-transform: uppercase; }

    /* Input veld contrast */
    .stTextInput input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 2px solid #3b82f6 !important;
    }

    /* Tabel layout */
    .stTable { background-color: #000000; }
    .stTable td { 
        color: #ffffff !important; 
        font-size: 16px !important;
        border-bottom: 1px solid #1e293b !important;
    }
    .stTable th { color: #94a3b8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR: INPUT ---
st.sidebar.markdown("### 🛠 CONTROL PANEL")
user_input = st.sidebar.text_input("ENTER TICKERS (CSV):", value="ANET, ERAS, NVDA, AMZN")
selected_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 4. ENGINE ---
@st.cache_data(ttl=300)
def get_analysis(tickers):
    if not tickers: return pd.DataFrame()
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    results = []
    
    for symbol in tickers:
        try:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(req).df.xs(symbol)
            
            # LSTM & Momentum logic
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            # RSI logic
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            
            ensemble = np.clip((lstm_force * 0.6) + ((100 - abs(rsi_val - 60) * 2) * 0.4), 0, 100)
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            # Rating bepaling op basis van ensemble score
            if ensemble > 80: rating = "STRONG BUY"
            elif ensemble > 65: rating = "BUY"
            elif ensemble < 35: rating = "SELL"
            else: rating = "NEUTRAL"
            
            results.append({
                "TICKER": symbol,
                "PRICE": f"${round(bars['close'].iloc[-1], 2)}",
                "ENSEMBLE": round(ensemble, 1),
                "LSTM FORCE": f"{round(lstm_force, 1)}%",
                "RATING": rating,
                "STOP LOSS": f"${round(bars['close'].iloc[-1] - (atr * 1.5), 2)}"
            })
        except: continue
    return pd.DataFrame(results)

# --- 5. UI DISPLAY & COLOR LOGIC ---
st.title("🚀 SST NEURAL | AI TERMINAL")

if selected_tickers:
    df = get_analysis(selected_tickers)
    if not df.empty:
        # Kleurfunctie voor de RATING kolom
        def style_df(val):
            if val == 'STRONG BUY': return 'color: #00ff00; font-weight: bold; font-size: 18px;' # Fel groen
            if val == 'BUY': return 'color: #22c55e; font-weight: bold;' # Normaal groen
            if val == 'NEUTRAL': return 'color: #3b82f6; font-weight: bold;' # Blauw
            if val == 'SELL': return 'color: #ef4444; font-weight: bold;' # Rood
            return 'color: #ffffff;'

        # Tabel tonen met styling
        st.table(df.style.applymap(style_df, subset=['RATING']))
    else:
        st.error("NO DATA FOUND. CHECK TICKERS.")
else:
    st.info("AWAITING INPUT...")

st.markdown("---")
st.caption(f"SYSTEM STATUS: ONLINE | {datetime.now().strftime('%H:%M:%S')} EST")


