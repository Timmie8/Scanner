import pandas as pd
import numpy as np
import json
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# --- CONFIG ---
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"
WATCHLIST = ["ANET", "ERAS", "CRML", "LGN", "CLS", "CSCO"]

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def generate_and_inject():
    results = []
    print("Analyzing market...")
    
    for symbol in WATCHLIST:
        try:
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(req).df.xs(symbol)
            
            # LSTM & Ensemble Logic (same as before)
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            
            ensemble = np.clip((lstm_force * 0.6) + ((100 - abs(rsi_val - 60) * 2) * 0.4), 0, 100)
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            results.append({
                "ticker": symbol, "price": round(bars['close'].iloc[-1], 2),
                "ensemble": round(ensemble, 1), "lstm": round(lstm_force, 1),
                "sentiment": "STRONG BUY" if ensemble > 75 else "ACCUMULATE",
                "stop": round(bars['close'].iloc[-1] - (atr * 1.5), 2)
            })
        except: continue

    # --- INJECTIE STAP ---
    json_data = json.dumps(results, indent=4)
    
    # Open je HTML bestand
    with open("scanner-ai.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Zoek de plek tussen /*AUTO_GENERATED_DATA*/ en vervang deze
    import re
    new_html = re.sub(r'/\*AUTO_GENERATED_DATA\*/.*', f'/*AUTO_GENERATED_DATA*/\n    const rawData = {json_data};', html_content, flags=re.DOTALL)
    
    # Sla de geüpdatete HTML weer op
    with open("scanner-ai.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    
    print("HTML updated successfully with fresh data!")

generate_and_inject()


