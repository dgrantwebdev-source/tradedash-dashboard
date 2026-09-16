#!/usr/bin/env python3
"""
Fetch futures data from Yahoo Finance and save as JSON for the dashboard.
Runs via GitHub Action every hour during market hours.
"""
import json
import os
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance -q")
    import yfinance as yf

SYMBOLS = ['ES=F', 'NQ=F', 'CL=F', 'GC=F', 'M2K=F', 'ZN=F']
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

def fetch_candles(symbol, interval='15m', range_='5d'):
    """Fetch OHLCV candles from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=range_, interval=interval)
        if df.empty:
            print(f"  No data for {symbol} {interval} {range_}")
            return []
        candles = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp())
            candles.append({
                'time': ts,
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']) if row['Volume'] > 0 else 0
            })
        print(f"  {symbol} {interval} {range_}: {len(candles)} candles")
        return candles
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return []

def fetch_prices():
    """Fetch current prices for all symbols."""
    prices = {}
    for sym in SYMBOLS:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.fast_info
            price = round(float(info.last_price), 2) if hasattr(info, 'last_price') else None
            prev = round(float(info.previous_close), 2) if hasattr(info, 'previous_close') else None
            high = round(float(info.day_high), 2) if hasattr(info, 'day_high') else price
            low = round(float(info.day_low), 2) if hasattr(info, 'day_low') else price
            if price and prev:
                change = round((price - prev) / prev * 100, 2)
            else:
                change = 0
            prices[sym] = {
                'price': price,
                'change': change,
                'high': high,
                'low': low
            }
            print(f"  {sym}: ${price} ({change:+.2f}%)")
        except Exception as e:
            print(f"  Error fetching price for {sym}: {e}")
    return prices

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Fetching prices...")
    prices = fetch_prices()
    
    # Save prices
    with open(os.path.join(OUTPUT_DIR, 'prices.json'), 'w') as f:
        json.dump(prices, f)
    
    # Fetch candles for each symbol
    for sym in SYMBOLS:
        print(f"\nFetching {sym}...")
        
        # 15m data (5 days)
        candles_15m = fetch_candles(sym, '15m', '5d')
        with open(os.path.join(OUTPUT_DIR, f'{sym.replace("=", "_")}_15m_5d.json'), 'w') as f:
            json.dump(candles_15m, f)
        
        # 5m data (1 day)
        candles_5m = fetch_candles(sym, '5m', '1d')
        with open(os.path.join(OUTPUT_DIR, f'{sym.replace("=", "_")}_5m_1d.json'), 'w') as f:
            json.dump(candles_5m, f)
        
        # 1h data (1 month) - for backtesting
        candles_1h = fetch_candles(sym, '1h', '1mo')
        with open(os.path.join(OUTPUT_DIR, f'{sym.replace("=", "_")}_1h_1mo.json'), 'w') as f:
            json.dump(candles_1h, f)
    
    # Save metadata
    meta = {
        'updated': datetime.utcnow().isoformat() + 'Z',
        'symbols': SYMBOLS,
        'status': 'live'
    }
    with open(os.path.join(OUTPUT_DIR, 'meta.json'), 'w') as f:
        json.dump(meta, f)
    
    print(f"\nData saved to {OUTPUT_DIR}")
    print(f"Updated: {meta['updated']}")

if __name__ == '__main__':
    main()
