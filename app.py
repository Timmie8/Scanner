import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="SST AI Bulk Scanner", layout="wide")

# Ledenlijst
USERS = {
    "admin@swingstocktraders.com": "SST2024!",
    "winstmaken@gmx.com": "winstmaken8",
    "member@test.nl": "Welkom01"
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
    # --- 2. CSS VOOR BREEDTE EN CONTRAST ---
    st.markdown("""
        <style>
        .stApp { background-color: #000000; }
        
        /* Forceer de container breedte (+150px extra ruimte) */
        .block-container {
            max-width: 1450px !important;
            padding-top: 2rem !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] { 
            background-color: #020617 !important; 
            border-right: 1px solid #1e293b;
        }

        /* Tabel tekst kleur forceren */
        .stDataFrame div[data-testid="stTable"] td {
            color: white !important;
        }
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

    # --- 3. SCANNER ENGINE ---
    st.title("🚀 SST NEURAL | Bulk Momentum Scanner")
    st.markdown("---")

    if st.button("🚀 START FULL MARKET SCAN", type="primary", use_container_width=True):
        scan_results = []
        progress_bar = st.progress(0)
        
        # We gebruiken een placeholder om de lijst tijdens het scannen alvast te tonen (optioneel)
        for index, ticker in enumerate(st.session_state.watchlist):
            try:
                progress_bar.progress((index + 1) / len(st.session_state.watchlist))
                t_obj = yf.Ticker(ticker)
                data = t_obj.history(period="250d")
                
                if data.empty or len(data) < 50: continue
                
                current_price = float(data['Close'].iloc[-1])
                
                # Linear Regression
                y_reg = data['Close'].values.reshape(-1, 1)
                X_reg = np.array(range(len(y_reg))).reshape(-1, 1)
                reg_model = LinearRegression().fit(X_reg, y_reg)
                pred_price = float(reg_model.predict(np.array([[len(y_reg)]]))[0][0])
                
                # Momentum AI
                last_5_days = data['Close'].iloc[-5:].pct_change().sum()
                momentum_score = int(68 + (last_5_days * 160))
                momentum_score = max(5, min(98, momentum_score))
                
                # RSI
                delta = data['Close'].diff()
                up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rsi = float(100 - (100 / (1 + (ema_up.iloc[-1] / (ema_down.iloc[-1] + 1e-9)))))
                
                # Ensemble
                ensemble_score = int(70 + (10 if pred_price > current_price else -10) + (12 if rsi < 45 else 0))
                ensemble_score = max(5, min(98, ensemble_score))

                # Status bepaling
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
                    "Momentum AI %": momentum_score,
                    "AI Ensemble": f"{ensemble_score}%",
                    "RSI": round(rsi, 1),
                    "Status": status,
                    "Target": f"${pred_price:.2f}",
                    "🛡️ Stop Loss": f"${(current_price - (1.5 * atr)):.2f}"
                })
            except Exception:
                continue

        # --- 4. WEERGAVE RESULTATEN ---
        if scan_results:
            df_display = pd.DataFrame(scan_results)
            
            # Styling functie: we kijken naar de kolom "Momentum AI %"
            def style_rows(row):
                if row["Momentum AI %"] >= 70:
                    # Donkergroene achtergrond met felgroene tekst
                    return ['background-color: #06402B; color: #00FF00; font-weight: bold'] * len(row)
                return [''] * len(row)

            # Styling toepassen
            styled_df = df_display.style.apply(style_rows, axis=1).format({
                "Momentum AI %": "{}%"
            })

            st.subheader(f"Markt Scan Resultaten ({datetime.now().strftime('%H:%M:%S')})")
            
            # Weergave via st.dataframe voor beste compatibiliteit en breedte
            st.dataframe(styled_df, use_container_width=True, height=len(df_display) * 40 + 40)
            
            st.download_button(
                label="📥 Exporteer naar CSV",
                data=df_display.to_csv(index=False),
                file_name=f"SST_Scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.error("Geen data gevonden. Controleer je watchlist.")

st.markdown("---")
st.caption("SST Neural Engine v2.4 | High-Contrast Momentum Scanner")







