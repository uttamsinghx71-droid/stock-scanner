import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import yfinance as yf
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_complete_8_layer_scanner():
    try:
        supabase.table("signals").delete().neq("id", 0).execute()
    except Exception as e:
        print("Note on clearing old signals:", e)

    response = supabase.table("watchlist_100").select("symbol").execute()
    stocks = [row['symbol'] for row in response.data]
    print(f"Scanning {len(stocks)} stocks with Clean 8-Layer Strategy...\n")
    
    matches_found = 0
    for symbol in stocks:
        ticker_symbol = f"{symbol}.NS"
        data = yf.download(ticker_symbol, period="60d", interval="1d", progress=False)
        
        if len(data) < 50:
            continue
            
        close_prices = data['Close']
        volumes = data['Volume']
        
        current_close = float(close_prices.iloc[-1].item())
        high_20d = float(close_prices.iloc[-20:-1].max().item())
        avg_volume_20d = float(volumes.iloc[-20:-1].mean().item())
        current_volume = float(volumes.iloc[-1].item())
        
        sma_20 = float(close_prices.rolling(window=20).mean().iloc[-1].item())
        sma_50 = float(close_prices.rolling(window=50).mean().iloc[-1].item())
        
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1].item())
        
        l1_volume_acc = current_volume > (avg_volume_20d * 1.3)
        l2_breakout = current_close >= high_20d
        l4_momentum = (current_close > sma_20) and (sma_20 > sma_50) and (rsi > 50)
        
        if l1_volume_acc and l2_breakout and l4_momentum:
            matches_found += 1
            print(f"---> Clean Match: {symbol} | Price: {round(current_close, 2)} | RSI: {round(rsi, 2)}")
            
            supabase.table("signals").insert({
                "stock_symbol": symbol,
                "signal_type": "BUY",
                "matched_layers": "L1(Vol), L2(Breakout), L4(SMA/RSI)",
                "price": current_close,
                "volume_spike": "Yes"
            }).execute()
            
    print(f"\nScanning Completed! Total matches found: {matches_found}")

if __name__ == "__main__":
    run_complete_8_layer_scanner()
