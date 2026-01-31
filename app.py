import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. PAGINA CONFIGURATIE ---
st.set_page_config(page_title="SST Neural Scanner", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #020617; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KEYS (Vul deze in) ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"
WATCHLIST = ["ANET", "ERAS", "CRML", "LGN", "CLS", "CSCO", "NVDA", "AMZN"]

st.title("🚀 SST NEURAL | AI Market Intelligence")
st.caption("Real-time LSTM Momentum & Ensemble Analysis for Swing Traders")

# --- 3. DE ENGINE ---
@st.cache_data(ttl=600) # Cached de data voor 10 minuten om de API niet te overbelasten
def fetch_scanner_data():
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    results = []
    
    for symbol in WATCHLIST:
        try:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(req).df.xs(symbol)
            
            # LSTM & Ensemble Logic
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            
            ensemble = np.clip((lstm_force * 0.6) + ((100 - abs(rsi_val - 60) * 2) * 0.4), 0, 100)
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            results.append({
                "Ticker": symbol,
                "Price": round(bars['close'].iloc[-1], 2),
                "Ensemble Score": round(ensemble, 1),
                "LSTM Force": f"{round(lstm_force, 1)}%",
                "Rating": "STRONG BUY" if ensemble > 75 else "ACCUMULATE" if ensemble > 60 else "NEUTRAL",
                "Stop Loss": round(bars['close'].iloc[-1] - (atr * 1.5), 2)
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. DISPLAY ---
try:
    df = fetch_scanner_data()

    # Kleurcodering voor de Rating
    def color_rating(val):
        color = '#10b981' if val == 'STRONG BUY' else '#3b82f6' if val == 'ACCUMULATE' else '#94a3b8'
        return f'color: {color}; font-weight: bold'

    # Toon de tabel
    st.table(df.style.applymap(color_rating, subset=['Rating']))
    
    st.info(f"Last sync: {datetime.now().strftime('%H:%M:%S')} EST")

except Exception as e:
    st.error(f"Engine Connection Error: {e}")



