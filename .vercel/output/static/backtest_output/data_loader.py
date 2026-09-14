"""
ES Futures Data Loader
=====================
Supports multiple data formats for backtesting.
Target: ES (E-mini S&P 500) 5-minute intraday data, Jan 1 - Aug 31, 2026.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
from typing import Optional, Tuple


class ESDataLoader:
    """Load and prepare ES futures 5-min data for backtesting."""
    
    POINT_VALUE = 50.0  # ES = $50/point
    TICK_SIZE = 0.25
    TICK_VALUE = 12.50
    
    def __init__(self, data_path: str = None):
        self.data_path = Path(data_path) if data_path else None
        self.raw_data = None
        self.processed_data = None
    
    def load_from_csv(self, filepath: str, 
                      date_col: str = 'date',
                      time_col: str = 'time',
                      open_col: str = 'open',
                      high_col: str = 'high',
                      low_col: str = 'low',
                      close_col: str = 'close',
                      volume_col: str = 'volume',
                      datetime_format: str = None) -> pd.DataFrame:
        """
        Load from CSV. Expects columns: datetime/open/high/low/close/volume.
        Common formats from NinjaTrader, Tradovate, Sierra Chart.
        """
        df = pd.read_csv(filepath)
        
        # Handle different datetime formats
        if datetime_format:
            df['datetime'] = pd.to_datetime(df[date_col] + ' ' + df[time_col], 
                                            format=datetime_format)
        else:
            df['datetime'] = pd.to_datetime(df[date_col] + ' ' + df[time_col])
        
        df = df.rename(columns={
            open_col: 'open',
            high_col: 'high', 
            low_col: 'low',
            close_col: 'close',
            volume_col: 'volume'
        })
        
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Filter to NY session hours (9:30 AM - 4:00 PM ET)
        df['time'] = df['datetime'].dt.time
        df['date'] = df['datetime'].dt.date
        df = df[df['time'].between(time(9, 30), time(16, 0))]
        
        self.raw_data = df
        self.processed_data = self._add_indicators(df)
        return self.processed_data
    
    def load_from_ninjaTrader(self, filepath: str) -> pd.DataFrame:
        """Load NinjaTrader export (tab-separated)."""
        df = pd.read_csv(filepath, sep='\t')
        df.columns = [c.strip().lower() for c in df.columns]
        
        # NinjaTrader typically has 'Date' and 'Time' columns
        date_col = [c for c in df.columns if 'date' in c][0]
        time_col = [c for c in df.columns if 'time' in c][0]
        
        return self.load_from_csv(filepath, date_col, time_col)
    
    def load_from_databento(self, filepath: str) -> pd.DataFrame:
        """Load Databento format (tsv with nanosecond timestamps)."""
        df = pd.read_csv(filepath, sep='\t')
        
        # Databento uses 'ts_event' in nanoseconds
        if 'ts_event' in df.columns:
            df['datetime'] = pd.to_datetime(df['ts_event'], unit='ns')
        elif 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ns')
        
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 
            'low': 'low', 'close': 'close',
            'volume': 'volume'
        })
        
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('datetime').reset_index(drop=True)
        
        df['time'] = df['datetime'].dt.time
        df['date'] = df['datetime'].dt.date
        
        self.raw_data = df
        self.processed_data = self._add_indicators(df)
        return self.processed_data
    
    def load_from_interactive_brokers(self, filepath: str) -> pd.DataFrame:
        """Load Interactive Brokers CSV export."""
        df = pd.read_csv(filepath)
        df.columns = [c.strip() for c in df.columns]
        
        # IB format: Date,Time,Open,High,Low,Close,Volume,BarCount,WAP
        df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df = df.rename(columns={
            'Open': 'open', 'High': 'high',
            'Low': 'low', 'Close': 'close', 
            'Volume': 'volume'
        })
        
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('datetime').reset_index(drop=True)
        
        df['time'] = df['datetime'].dt.time
        df['date'] = df['datetime'].dt.date
        
        self.raw_data = df
        self.processed_data = self._add_indicators(df)
        return self.processed_data
    
    def generate_synthetic_data(self, start_date: str = '2026-01-01',
                                 end_date: str = '2026-08-31',
                                 start_price: float = 4800.0,
                                 volatility: float = 0.015) -> pd.DataFrame:
        """
        Generate realistic synthetic ES data for testing framework.
        Uses geometric Brownian motion with mean-reversion.
        NOT for actual trading decisions.
        """
        np.random.seed(42)
        
        dates = pd.bdate_range(start=start_date, end=end_date)
        
        all_bars = []
        price = start_price
        
        for date in dates:
            # Skip weekends/holidays
            if date.weekday() >= 5:
                continue
            
            # Daily parameters
            daily_vol = volatility * np.sqrt(252)
            drift = 0.0002  # Slight upward drift
            
            # Generate 5-min bars for NY session (9:30 - 16:00 = 78 bars)
            n_bars = 78
            bar_returns = np.random.normal(drift/n_bars, daily_vol/np.sqrt(n_bars*252), n_bars)
            
            # Add mean-reversion
            mean_price = start_price + (date - pd.Timestamp(start_date)).days * 0.5
            
            for i in range(n_bars):
                bar_time = pd.Timestamp(date.date()) + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=5*i)
                
                ret = bar_returns[i] + 0.0001 * (mean_price - price) / price
                
                open_price = price
                close_price = open_price * (1 + ret)
                
                # High/low with intra-bar range
                intra_range = abs(ret) + np.random.exponential(0.002)
                high_price = max(open_price, close_price) * (1 + np.random.exponential(intra_range/3))
                low_price = min(open_price, close_price) * (1 - np.random.exponential(intra_range/3))
                
                # Volume (higher at open/close)
                if i < 6:  # First 30 min
                    vol = np.random.lognormal(8, 0.5)
                elif i > 72:  # Last 30 min  
                    vol = np.random.lognormal(7.5, 0.5)
                else:
                    vol = np.random.lognormal(6, 0.5)
                
                all_bars.append({
                    'datetime': bar_time,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': int(vol)
                })
                
                price = close_price
        
        df = pd.DataFrame(all_bars)
        df['time'] = df['datetime'].dt.time
        df['date'] = df['datetime'].dt.date
        
        self.raw_data = df
        self.processed_data = self._add_indicators(df)
        return self.processed_data
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators needed for strategies."""
        df = df.copy()
        
        # ATR (14-period)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr_14'] = df['tr'].rolling(14).mean()
        
        # VWAP (intraday, resets daily)
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_vol'] = df['typical_price'] * df['volume']
        
        df['cumulative_tp_vol'] = df.groupby('date')['tp_vol'].cumsum()
        df['cumulative_volume'] = df.groupby('date')['volume'].cumsum()
        df['vwap'] = df['cumulative_tp_vol'] / df['cumulative_volume']
        
        # RSI (14-period)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Previous Day High/Low
        daily = df.groupby('date').agg({'high': 'max', 'low': 'min'}).reset_index()
        daily.columns = ['date', 'pdh', 'pdl']
        df = df.merge(daily, on='date', how='left')
        
        # Shift PDH/PDL to use previous day's values
        df['pdh'] = df.groupby('date')['pdh'].shift(1)
        df['pdl'] = df.groupby('date')['pdl'].shift(1)
        
        # ORB levels (calculated per strategy, but base columns here)
        df['orb_high'] = np.nan
        df['orb_low'] = np.nan
        df['orb_range'] = np.nan
        
        return df
    
    def get_session_data(self, df: pd.DataFrame, 
                         session: str = 'full') -> pd.DataFrame:
        """Filter data by session."""
        if session == 'full':
            return df  # Already filtered to 9:30-16:00
        elif session == 'morning':
            return df[df['time'] <= time(12, 0)]
        elif session == 'afternoon':
            return df[df['time'] >= time(12, 0)]
        elif session == 'first_90':
            return df[df['time'] <= time(11, 0)]
        return df
    
    def get_day_filter(self, df: pd.DataFrame, 
                       day_filter: str = 'all') -> pd.DataFrame:
        """Filter by day of week."""
        dow = df['datetime'].dt.dayofweek
        
        if day_filter == 'all':
            return df
        elif day_filter == 'monday':
            return df[dow == 0]
        elif day_filter == 'tue_fri':
            return df[dow >= 1]
        elif day_filter == 'wed_fri':
            return df[dow >= 2]
        elif day_filter == 'thu_fri':
            return df[dow >= 3]
        return df


def load_es_data(data_path: str = None, 
                 use_synthetic: bool = False) -> pd.DataFrame:
    """
    Main entry point for loading ES data.
    
    Args:
        data_path: Path to CSV file with ES 5-min data
        use_synthetic: If True, generate synthetic data for framework testing
    
    Returns:
        DataFrame with OHLCV + indicators
    """
    loader = ESDataLoader(data_path)
    
    if use_synthetic or data_path is None:
        print("!  Using SYNTHETIC data for framework testing only.")
        print("   For real backtests, supply actual ES historical data.")
        return loader.generate_synthetic_data()
    
    # Auto-detect format
    ext = Path(data_path).suffix.lower()
    if ext == '.csv':
        return loader.load_from_csv(data_path)
    elif ext == '.tsv':
        return loader.load_from_databento(data_path)
    else:
        return loader.load_from_csv(data_path)


if __name__ == "__main__":
    # Quick test
    df = load_es_data(use_synthetic=True)
    print(f"\nLoaded {len(df)} bars")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Price range: {df['low'].min():.2f} to {df['high'].max():.2f}")
    print(f"\nIndicators available: {[c for c in df.columns if c not in ['datetime','open','high','low','close','volume','time','date']]}")

