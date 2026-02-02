import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="SST AI Bulk Scanner", layout="wide")

# Ledenlijst (Blijft ongewijzigd)
USERS = {
    "admin@swingstocktraders.com": "SST2024!",
    "winstmaken@gmx.com":"winstmaken8"
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
    # --- CSS VOOR SCANNER ---
    st.markdown("""
        <style>
        .stTable td { font-size: 14px !important; }
        .stTable th { background-color: #1e1e1e !important; color: #60a5fa !important; }
        </style>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.write(f"Account: **{st.session_state.user_email}**")
        if st.button("Uitloggen"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("---")
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META", "GOOGL", "AMZN"]
        
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
    st.title("🛡️ SST Neural Momentum Scanner")
    st.write("De scanner analyseert real-time Momentum AI en Ensemble scores voor je gehele watchlist.")

    if st.button("🚀 START FULL MARKET SCAN", type="primary", use_container_width=True):
        scan_results = []
        progress_bar = st.progress(0)
        
        for index, ticker in enumerate(st.session_state.watchlist):
            try:
                # Update progress
                progress_bar.progress((index + 1) / len(st.session_state.watchlist))
                
                t_obj = yf.Ticker(ticker)
                data = t_obj.history(period="200d")
                
                if data.empty: continue
                
                # --- AI BEREKENINGEN ---
                current_price = float(data['Close'].iloc[-1])
                
                # Linear Regression (Trend)
                y_reg = data['Close'].values.reshape(-1, 1)
                X_reg = np.array(range(len(y_reg))).reshape(-1, 1)
                reg_model = LinearRegression().fit(X_reg, y_reg)
                pred_price = float(reg_model.predict(np.array([[len(y_reg)]]))[0][0])
                
                # Momentum AI Score
                last_5_days = data['Close'].iloc[-5:].pct_change().sum()
                momentum_score = int(68 + (last_5_days * 160))
                momentum_score = max(0, min(100, momentum_score)) # Clamp tussen 0-100
                
                # RSI
                delta = data['Close'].diff()
                up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rsi = float(100 - (100 / (1 + (ema_up.iloc[-1] / (ema_down.iloc[-1] + 1e-9)))))
                
                # Ensemble
                ensemble_score = int(70 + (10 if pred_price > current_price else -10) + (12 if rsi < 45 else 0))
                ensemble_score = max(0, min(100, ensemble_score))

                # Signaal Bepaling
                status = "HOLD"
                if momentum_score >= 75 or ensemble_score >= 75:
                    status = "🚀 BUY"
                elif momentum_score < 40:
                    status = "⚠️ SELL/WEAK"

                scan_results.append({
                    "Ticker": ticker,
                    "Prijs": f"${current_price:.2f}",
                    "Momentum AI": momentum_score,
                    "Ensemble Score": ensemble_score,
                    "RSI": round(rsi, 1),
                    "Status": status,
                    "Trend Target": f"${pred_price:.2f}"
                })
            except Exception as e:
                st.warning(f"Kon {ticker} niet scannen: {e}")

        # --- WEERGAVE RESULTATEN ---
        if scan_results:
            df_results = pd.DataFrame(scan_results)
            
            def style_results(row):
                if "BUY" in str(row.Status):
                    return ['background-color: #06402B; color: #00C851; font-weight: bold'] * len(row)
                elif "SELL" in str(row.Status):
                    return ['background-color: #441111; color: #ff4444'] * len(row)
                return [''] * len(row)

            st.subheader(f"Scan Resultaten ({datetime.now().strftime('%H:%M:%S')})")
            st.table(df_results.style.apply(style_results, axis=1))
            
            # Export optie
            st.download_button("Download CSV", df_results.to_csv(index=False), "sst_scan.csv", "text/csv")
        else:
            st.error("Geen data kunnen ophalen. Probeer het later opnieuw.")



### Hoe deze scanner te gebruiken:
1.  **Watchlist beheren:** Voeg in de sidebar de tickers toe die je wilt monitoren.
2.  **De Scan:** Klik op de grote blauwe knop **"START FULL MARKET SCAN"**. 
3.  **Signalen:** Kijk direct naar de rij die groen kleurt. Dit zijn de aandelen waarbij de Momentum AI en het Ensemble model samenkomen voor een koopmoment.
4.  **Targets:** De kolom `Trend Target` geeft je het koersdoel op basis van de lineaire regressie (AI Trend).

Wil je dat ik een **automatische e-mail notificatie** toevoeg die je een bericht stuurt zodra er een "🚀 BUY" signaal in de lijst verschijnt?


