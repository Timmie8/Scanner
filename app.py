import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="SST AI Pro Scanner", layout="wide")

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
    # --- 2. CSS ---
    st.markdown("""
        <style>
        .stApp { background-color: #000000; }
        .block-container { max-width: 1450px !important; padding: 2rem 3rem; }
        [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1e293b; }
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

    # --- 3. SCANNER ENGINE ---
    st.title("🚀 SST NEURAL | AI Momentum & Earnings Scanner")

    if st.button("🚀 START FULL MARKET SCAN", type="primary", use_container_width=True):
        scan_results = []
        progress_bar = st.progress(0)
        today = datetime.now()

        for index, ticker in enumerate(st.session_state.watchlist):
            try:
                progress_bar.progress((index + 1) / len(st.session_state.watchlist))
                t_obj = yf.Ticker(ticker)
                data = t_obj.history(period="250d")
                
                if data.empty: continue
                
                # --- EARNINGS CHECK ---
                earnings_alert = "Nee"
                try:
                    # Haal de volgende earnings datum op
                    calendar = t_obj.calendar
                    if calendar is not None and not calendar.empty:
                        # yfinance geeft vaak een DataFrame terug met datums
                        next_earnings = calendar.iloc[0, 0]
                        # Zet om naar datetime voor vergelijking
                        if isinstance(next_earnings, datetime):
                            days_to_earnings = (next_earnings - today).days
                            if 0 <= days_to_earnings <= 7:
                                earnings_alert = f"⚠️ JA ({next_earnings.strftime('%d-%m')})"
                except:
                    earnings_alert = "Check"

                # --- AI BEREKENINGEN ---
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

                # Status
                if momentum_score >= 70: status = "🚀 MOMENTUM"
                elif rsi > 70: status = "⚠️ OVERBOUGHT"
                else: status = "🔵 NEUTRAL"

                atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]

                scan_results.append({
                    "Ticker": ticker,
                    "Prijs": f"${current_price:.2f}",
                    "Momentum AI %": momentum_score,
                    "RSI": round(rsi, 1),
                    "Earnings <7d": earnings_alert,
                    "Status": status,
                    "Target": f"${pred_price:.2f}",
                    "🛡️ Stop": f"${(current_price - (1.5 * atr)):.2f}"
                })
            except: continue

        # --- 4. WEERGAVE ---
        if scan_results:
            df_display = pd.DataFrame(scan_results)
            
            def style_rows(row):
                # Highlight groen bij hoog momentum
                if row["Momentum AI %"] >= 70:
                    return ['background-color: #06402B; color: #00FF00; font-weight: bold'] * len(row)
                # Subtiel oranje/rood bij earnings waarschuwing
                if "⚠️" in str(row["Earnings <7d"]):
                    return ['color: #fbbf24; font-style: italic'] * len(row)
                return [''] * len(row)

            styled_df = df_display.style.apply(style_rows, axis=1).format({"Momentum AI %": "{}%"})
            
            st.subheader(f"Markt Scan ({datetime.now().strftime('%H:%M:%S')})")
            st.dataframe(styled_df, use_container_width=True, height=500)
            
            st.info("💡 Tip: Als 'Earnings <7d' op JA staat, wees dan extra voorzichtig. De volatiliteit is dan extreem hoog.")
        else:
            st.error("Geen data gevonden.")

st.markdown("---")
st.caption("SST Neural Engine v2.5 | Risk Management Enabled")






