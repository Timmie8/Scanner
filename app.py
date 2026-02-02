import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="SST AI Bulk Scanner", layout="wide")

# Ledenlijst (Blijft hetzelfde)
USERS = {
    "admin@swingstocktraders.com": "SST2024!",
    "winstmaken@gmx.com": "winstmaken8"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.markdown("<h2 style='text-align: center;'>🔐 SST Leden Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        email = st.text_input("E-mailadres")
        password = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen", use_container_width=True):
            if email in USERS and USERS[email] == password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Onjuist e-mailadres of wachtwoord.")

if not st.session_state.logged_in:
    login_screen()
else:
    # --- CSS VOOR BREEDTE EN CONTRAST ---
    st.markdown("""
        <style>
        .stApp { background-color: #000000; }
        
        /* Tabel breeder maken (+150px effect) */
        .stTable {
            width: 100% !important;
            max-width: 1400px !important; /* Verbreed de container */
            margin: auto;
        }
        
        .stTable td { font-size: 14px !important; color: white !important; padding: 12px !important; }
        .stTable th { background-color: #1e1e1e !important; color: #60a5fa !important; text-transform: uppercase; }
        [data-testid="stSidebar"] { background-color: #020617 !important; }
        </style>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.write(f"Account: **{st.session_state.user_email}**")
        if st.button("Uitloggen"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("---")
        
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META", "AMZN"]
        
        st.subheader("Manage Watchlist")
        new_ticker = st.text_input("Voeg Ticker toe:").upper().strip()
        if st.button("➕ Voeg toe") and new_ticker:
            if new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.rerun()
        
        if st.button("🗑 Reset Lijst"):
            st.session_state.watchlist = ["AAPL", "NVDA", "TSLA"]
            st.rerun()

    # --- SCANNER ENGINE ---
    st.title("🚀 SST NEURAL | Bulk Momentum Scanner")

    if st.button("🚀 START FULL MARKET SCAN", type="primary", use_container_width=True):
        scan_results = []
        progress_bar = st.progress(0)
        
        for index, ticker in enumerate(st.session_state.watchlist):
            try:
                progress_bar.progress((index + 1) / len(st.session_state.watchlist))
                t_obj = yf.Ticker(ticker)
                data = t_obj.history(period="250d")
                
                if data.empty or len(data) < 50: continue
                
                current_price = float(data['Close'].iloc[-1])
                
                # AI Trend (Linear Regression)
                y_reg = data['Close'].values.reshape(-1, 1)
                X_reg = np.array(range(len(y_reg))).reshape(-1, 1)
                reg_model = LinearRegression().fit(X_reg, y_reg)
                pred_price = float(reg_model.predict(np.array([[len(y_reg)]]))[0][0])
                
                # Momentum AI Score
                last_5_days = data['Close'].iloc[-5:].pct_change().sum()
                momentum_score = int(68 + (last_5_days * 160))
                momentum_score = max(5, min(98, momentum_score))
                
                # RSI Berekening
                delta = data['Close'].diff()
                up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rsi = float(100 - (100 / (1 + (ema_up.iloc[-1] / (ema_down.iloc[-1] + 1e-9)))))
                
                # AI Ensemble Score
                ensemble_score = int(70 + (10 if pred_price > current_price else -10) + (12 if rsi < 45 else 0))
                ensemble_score = max(5, min(98, ensemble_score))

                # Signaal Logica
                if momentum_score >= 70:
                    status = "🚀 MOMENTUM BUY"
                elif ensemble_score >= 70:
                    status = "✅ ENSEMBLE BUY"
                elif rsi > 70:
                    status = "⚠️ OVERBOUGHT"
                else:
                    status = "🔵 NEUTRAL"

                atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]

                scan_results.append({
                    "Ticker": ticker,
                    "Prijs": f"${current_price:.2f}",
                    "Momentum_Score": momentum_score, # Numeriek voor styling
                    "Ensemble": f"{ensemble_score}%",
                    "RSI": round(rsi, 1),
                    "Status": status,
                    "Target": f"${pred_price:.2f}",
                    "Stop Loss": f"${(current_price - (1.5 * atr)):.2f}"
                })
            except Exception:
                continue

        # --- WEERGAVE RESULTATEN ---
        if scan_results:
            df_results = pd.DataFrame(scan_results)
            
            # De gevraagde highlight logica: Alleen oplichten als Momentum_Score > 70
            def style_momentum(row):
                # We checken de numerieke waarde die we in de dict hebben opgeslagen
                if row.Momentum_Score >= 70:
                    return ['background-color: #06402B; color: #00FF00; font-weight: bold'] * len(row)
                return [''] * len(row)

            # We hernoemen de kolom voor de display naar een mooiere naam
            df_display = df_results.rename(columns={"Momentum_Score": "Momentum AI %"})

            st.subheader(f"Markt Scan Resultaten ({datetime.now().strftime('%H:%M:%S')})")
            st.table(df_display.style.apply(style_momentum, axis=1))
            
            st.download_button(
                label="📥 Exporteer naar CSV",
                data=df_results.to_csv(index=False),
                file_name=f"SST_Scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.error("Geen data gevonden.")

st.markdown("---")
st.caption("SST Neural Engine v2.2 | Momentum Focus Mode")



