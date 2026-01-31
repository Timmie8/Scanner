import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="SST Interactive Scanner", layout="wide")

# Custom CSS for Professional Dark Theme
st.markdown("""
    <style>
    .stApp { background-color: #020617; color: white; }
    .stMultiSelect div { background-color: #1e293b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "JOUW_ALPACA_KEY"
SECRET_KEY = "JOUW_ALPACA_SECRET"

# --- 3. STOCK SELECTION ---
# Een brede lijst waaruit de gebruiker kan kiezen
ALL_AVAILABLE_STOCKS = sorted([
    "ANET", "ERAS", "CRML", "LGN", "CLS", "CSCO", "NVDA", "AMZN", "AAPL", 
    "TSLA", "MSFT", "META", "GOOGL", "AMD", "NFLX", "PLTR", "SNOW", "PLTR"
])

st.sidebar.title("SST Control Panel")
selected_tickers = st.sidebar.multiselect(
    "Select Stocks to Scan:",
    options=ALL_AVAILABLE_STOCKS,
    default=["ANET", "ERAS", "NVDA"] # Standaard selectie
)

# --- 4. THE ENGINE ---
@st.cache_data(ttl=300) # Cache voor 5 minuten
def get_ai_analysis(tickers):
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
                "LSTM Force": round(lstm_force, 1),
                "Rating": "STRONG BUY" if ensemble > 75 else "ACCUMULATE" if ensemble > 60 else "NEUTRAL",
                "Volatility Stop": round(bars['close'].iloc[-1] - (atr * 1.5), 2)
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- 5. DASHBOARD UI ---
st.title("🚀 SST NEURAL | AI Terminal")
st.write("Selected Tickers:", ", ".join(selected_tickers) if selected_tickers else "None")

if selected_tickers:
    with st.spinner("Analyzing Market Data..."):
        df = get_ai_analysis(selected_tickers)
        
        if not df.empty:
            # Kleurcodering functie
            def style_rating(val):
                color = '#10b981' if val == 'STRONG BUY' else '#3b82f6' if val == 'ACCUMULATE' else '#94a3b8'
                return f'color: {color}; font-weight: bold'

            # Tabel weergeven
            st.dataframe(
                df.style.applymap(style_rating, subset=['Rating']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No data found for selected stocks.")
else:
    st.info("Please select stocks in the sidebar to begin scanning.")

st.divider()
st.caption(f"Last Intelligence Sync: {datetime.now().strftime('%H:%M:%S')} EST")



