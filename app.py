import pandas as pd
import numpy as np
import json
import warnings
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# 1. SETUP
API_KEY = "PK5GBMQVMM4XSH2Y4OMA7X3NYZ"
SECRET_KEY = "DfkqRpMWaBVsJQydvhpBXA5bRAvG3tG9yPn1eMoEpEWt"
WATCHLIST = ["ANET", "ERAS", "CRML", "LGN", "CLS", "CSCO", "AMZN", "NVDA", "STEP"]

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def run_sst_engine():
    results = []
    print(f"Deep Learning Scan initiated for swingstocktraders.com...")
    
    for symbol in WATCHLIST:
        try:
            request_params = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=datetime.now() - timedelta(days=45))
            bars = client.get_stock_bars(request_params).df.xs(symbol)
            
            # LSTM & Ensemble Logic
            bars['log_ret'] = np.log(bars['close'] / bars['close'].shift(1))
            lstm_force = np.clip((bars['log_ret'].iloc[-5:].sum() * 100 + 2) * 20, 0, 100)
            
            # RSI
            delta = bars['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = 100 - (100 / (1 + gain.iloc[-1]/loss.iloc[-1]))
            
            # Ensemble calculation (Momentum + RSI Health)
            rsi_health = 100 - abs(rsi_val - 60) * 2
            ensemble = np.clip((lstm_force * 0.6) + (rsi_health * 0.4), 0, 100)
            
            # Volatility-based Stop Loss
            atr = (bars['high'] - bars['low']).rolling(14).mean().iloc[-1]
            
            results.append({
                "ticker": symbol,
                "price": round(bars['close'].iloc[-1], 2),
                "ensemble": round(ensemble, 1),
                "lstm": round(lstm_force, 1),
                "sentiment": "STRONG BUY" if ensemble > 75 else "ACCUMULATE" if ensemble > 60 else "NEUTRAL",
                "stop": round(bars['close'].iloc[-1] - (atr * 1.5), 2),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            continue
    
    # Save the file. Upload THIS file to your server's root directory.
    with open('data.json', 'w') as f:
        json.dump(results, f)
    print("Scan complete. 'data.json' is ready for upload.")

run_sst_engine()

