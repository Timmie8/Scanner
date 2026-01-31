import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. PAGINA INSTELLINGEN ---
st.set_page_config(page_title="SST Custom Scanner", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #020617; color: white; }
    .stTextInput input { background-color: #1e293b !important; color: white !important; border: 1px solid #3b82f6 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR: HANDMATIGE INVOER ---
st.sidebar.title("SST Neural Control")
st.sidebar.write("Voer de tickers in gescheiden door een komma:")

# Het invoervak
user_input = st.sidebar.text_input("Aandelen Tickers:", value="ANET, ERAS, NVDA, AMZN")

# Verwerk de invoer naar een lijst
selected_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 4. DE ENGINE ---
@st.cache_data(ttl=300)
def get_analysis(tickers):
    if not tickers:
        return pd.DataFrame()
        
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    results = []
    
    for symbol in tickers:
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbol, 
                timeframe=TimeFrame.Day, 
                start=datetime.now() - timedelta(days=45)
            )
            bars = client.get_stock_bars(req).df.xs(symbol)
            
            # LSTM Versnelling (Momentum)
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            # RSI & Ensemble Score
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            
            # Ensemble (Momentum + RSI Health)
            rsi_health = 100 - abs(rsi_val - 60) * 2
            ensemble = np.clip((lstm_force * 0.6) + (rsi_health * 0.4), 0, 100)
            
            # ATR Stop Loss
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            results.append({
                "Ticker": symbol,
                "Price": round(bars['close'].iloc[-1], 2),
                "Ensemble Score": round(ensemble, 1),
                "LSTM Force": f"{round(lstm_force, 1)}%",
                "Rating": "STRONG BUY" if ensemble > 75 else "ACCUMULATE" if ensemble > 60 else "NEUTRAL",
                "Stop Loss": f"${round(bars['close'].iloc[-1] - (atr * 1.5), 2)}"
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- 5. DASHBOARD DISPLAY ---
st.title("🚀 SST NEURAL | Custom AI Scanner")

if selected_tickers:
    with st.spinner(f"Bezig met analyseren van {len(selected_tickers)} aandelen..."):
        df = get_analysis(selected_tickers)
        
        if not df.empty:
            # Kleur styling voor de tabel
            def color_rating(val):
                color = '#10b981' if val == 'STRONG BUY' else '#3b82f6' if val == 'ACCUMULATE' else '#94a3b8'
                return f'color: {color}; font-weight: bold'

            st.table(df.style.applymap(color_rating, subset=['Rating']))
        else:
            st.error("Geen data gevonden. Controleer of de tickers correct zijn (bijv: AAPL, NVDA).")
else:
    st.info("Voer tickers in de sidebar in om de scan te starten.")

st.divider()
st.caption(f"SST Engine Sync: {datetime.now().strftime('%H:%M:%S')} EST")


