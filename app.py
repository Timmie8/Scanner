import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- 1. STYLING VOOR MAXIMAAL CONTRAST ---
st.set_page_config(page_title="SST Custom Scanner", layout="wide")

st.markdown("""
    <style>
    /* Achtergrond en algemene tekst */
    .stApp { 
        background-color: #000000; 
    }
    
    /* Alle standaard tekst naar fel wit */
    p, span, label, .stMarkdown {
        color: #ffffff !important;
        font-weight: 500;
    }

    /* Titels extra laten opvallen */
    h1, h2, h3 {
        color: #60a5fa !important;
        font-weight: 800 !important;
        text-transform: uppercase;
    }

    /* Input vak aanpassen voor leesbaarheid */
    .stTextInput input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 2px solid #3b82f6 !important;
        font-size: 18px !important;
    }

    /* Tabel styling: Fel witte tekst op donkere rijen */
    .stTable td {
        color: #ffffff !important;
        font-size: 16px !important;
        border-bottom: 1px solid #334155 !important;
    }
    
    .stTable th {
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Sidebar contrast */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"

# --- 3. SIDEBAR: INPUT ---
st.sidebar.markdown("### 🛠 CONTROL PANEL")
user_input = st.sidebar.text_input("ENTER TICKERS (CSV):", value="ANET, ERAS, NVDA, AMZN")

# Verwerk de invoer
selected_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 4. ENGINE ---
@st.cache_data(ttl=300)
def get_analysis(tickers):
    if not tickers:
        return pd.DataFrame()
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
            
            results.append({
                "TICKER": symbol,
                "PRICE": f"${round(bars['close'].iloc[-1], 2)}",
                "ENSEMBLE": f"{round(ensemble, 1)}/100",
                "LSTM FORCE": f"{round(lstm_force, 1)}%",
                "RATING": "STRONG BUY" if ensemble > 75 else "ACCUMULATE" if ensemble > 60 else "NEUTRAL",
                "STOP LOSS": f"${round(bars['close'].iloc[-1] - (atr * 1.5), 2)}"
            })
        except: continue
    return pd.DataFrame(results)

# --- 5. UI ---
st.title("🚀 SST NEURAL | AI TERMINAL")

if selected_tickers:
    with st.spinner("QUANT ANALYSIS IN PROGRESS..."):
        df = get_analysis(selected_tickers)
        if not df.empty:
            # Kleurcodes voor ratings (Neon groen/blauw voor leesbaarheid)
            def color_rating(val):
                if val == 'STRONG BUY': return 'color: #00ff99; font-weight: bold; font-size: 18px;'
                if val == 'ACCUMULATE': return 'color: #00d4ff; font-weight: bold;'
                return 'color: #ffffff;'

            st.table(df.style.applymap(color_rating, subset=['RATING']))
        else:
            st.error("NO DATA FOUND. CHECK TICKER SYMBOLS.")
else:
    st.info("AWAITING INPUT: ENTER TICKERS IN THE SIDEBAR.")

st.markdown("---")
st.caption(f"SYSTEM STATUS: ACTIVE | SYNC TIME: {datetime.now().strftime('%H:%M:%S')} EST")



