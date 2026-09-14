#!/usr/bin/env python3
"""
Comprehensive Backtest: August 2026 Trading Strategies on ES=F
==============================================================
Strategies: Gap Fill, ORB, IB Breakout, Mean Reversion, Event-Driven
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
SYMBOL = "ES=F"
START_DATE = "2026-08-01"
END_DATE = "2026-08-31"
INITIAL_CAPITAL = 100000
CONTRACT_MULTIPLIER = 50  # ES futures
TICK_SIZE = 0.25
TICK_VALUE = 12.50
RISK_PER_TRADE = 0.01  # 1% of capital per trade

OUTPUT_DIR = r"C:\Users\dgran\AppData\Local\Temp\opencode"

# ============================================================
# DATA ACQUISITION
# ============================================================
print("=" * 70)
print("DOWNLOADING DATA FOR", SYMBOL, ":", START_DATE, "to", END_DATE)
print("=" * 70)

# Download 1-minute data for August 2026
data = yf.download(SYMBOL, start=START_DATE, end=END_DATE, interval="1m", progress=False)

if data.empty:
    print("WARNING: No 1-minute data available. Falling back to 15-minute data.")
    data = yf.download(SYMBOL, start=START_DATE, end=END_DATE, interval="15m", progress=False)

if data.empty:
    print("WARNING: No intraday data available. Using daily data with synthetic intraday.")
    data = yf.download(SYMBOL, start=START_DATE, end=END_DATE, interval="1d", progress=False)
    USE_DAILY = True
else:
    USE_DAILY = False

print(f"Data shape: {data.shape}")
print(f"Date range: {data.index.min()} to {data.index.max()}")

# Flatten MultiIndex columns if present
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()
print(f"After cleaning: {data.shape} bars\n")

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def calculate_rsi(series, period=14):
    """Calculate RSI indicator."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_correlation(series1, series2, window=20):
    """Calculate rolling correlation."""
    return series1.rolling(window=window).corr(series2)

def get_trading_days(data):
    """Extract unique trading days."""
    if USE_DAILY:
        return data.index.normalize().unique()
    return data.index.normalize().unique()

def get_market_hours(data):
    """Filter data to regular trading hours (9:30 AM - 4:00 PM ET)."""
    if USE_DAILY:
        return data
    mask = (data.index.hour >= 9) & (data.index.hour < 16)
    return data[mask]

def resample_ohlcv(data, interval):
    """Resample OHLCV data to specified interval."""
    return data.resample(interval).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

# ============================================================
# STRATEGY 1: GAP FILL STRATEGY
# ============================================================
print("=" * 70)
print("STRATEGY 1: GAP FILL")
print("=" * 70)

def backtest_gap_fill(data):
    """Backtest gap fill strategy."""
    trades = []
    daily_data = data.copy()

    if USE_DAILY:
        # For daily data, calculate gaps between consecutive days
        daily_data['Prev_Close'] = daily_data['Close'].shift(1)
        daily_data['Gap_Size'] = abs(daily_data['Open'] - daily_data['Prev_Close'])
        daily_data['Gap_Direction'] = np.where(
            daily_data['Open'] > daily_data['Prev_Close'], 'up', 'down'
        )

        for i in range(1, len(daily_data)):
            row = daily_data.iloc[i]
            prev_close = daily_data.iloc[i-1]['Close']
            gap_size = abs(row['Open'] - prev_close)

            if gap_size < 2:  # Minimum gap threshold (2 points)
                continue

            # Check if gap was filled during the day
            if row['Gap_Direction'] == 'up':
                # Gap up: price needs to come down to prev_close
                if row['Low'] <= prev_close:
                    entry_price = prev_close
                    target = entry_price - 1.5 * gap_size
                    stop = entry_price + 2.0 * gap_size

                    if row['Close'] <= target:
                        pnl = 1.5 * gap_size
                    elif row['Close'] >= stop:
                        pnl = -2.0 * gap_size
                    else:
                        pnl = (entry_price - row['Close'])

                    trades.append({
                        'date': daily_data.index[i],
                        'direction': 'short',
                        'entry': entry_price,
                        'pnl_points': pnl,
                        'gap_size': gap_size
                    })
            else:
                # Gap down: price needs to come up to prev_close
                if row['High'] >= prev_close:
                    entry_price = prev_close
                    target = entry_price + 1.5 * gap_size
                    stop = entry_price - 2.0 * gap_size

                    if row['Close'] >= target:
                        pnl = 1.5 * gap_size
                    elif row['Close'] <= stop:
                        pnl = -2.0 * gap_size
                    else:
                        pnl = (row['Close'] - entry_price)

                    trades.append({
                        'date': daily_data.index[i],
                        'direction': 'long',
                        'entry': entry_price,
                        'pnl_points': pnl,
                        'gap_size': gap_size
                    })
    else:
        # For intraday data, detect gaps between sessions
        dates = data.index.normalize().unique()
        for i in range(1, len(dates)):
            day_data = data[data.index.normalize() == dates[i]]
            prev_day_data = data[data.index.normalize() == dates[i-1]]

            if day_data.empty or prev_day_data.empty:
                continue

            prev_close = prev_day_data['Close'].iloc[-1]
            current_open = day_data['Open'].iloc[0]
            gap_size = abs(current_open - prev_close)

            if gap_size < 2:
                continue

            if current_open > prev_close:
                # Gap up
                filled = day_data[day_data['Low'] <= prev_close]
                if not filled.empty:
                    entry_price = prev_close
                    target = entry_price - 1.5 * gap_size
                    stop = entry_price + 2.0 * gap_size

                    day_low = day_data['Low'].min()
                    if day_low <= target:
                        pnl = 1.5 * gap_size
                    elif day_data['High'].max() >= stop:
                        pnl = -2.0 * gap_size
                    else:
                        pnl = (entry_price - day_data['Close'].iloc[-1])

                    trades.append({
                        'date': dates[i],
                        'direction': 'short',
                        'entry': entry_price,
                        'pnl_points': pnl,
                        'gap_size': gap_size
                    })
            else:
                # Gap down
                filled = day_data[day_data['High'] >= prev_close]
                if not filled.empty:
                    entry_price = prev_close
                    target = entry_price + 1.5 * gap_size
                    stop = entry_price - 2.0 * gap_size

                    day_high = day_data['High'].max()
                    if day_high >= target:
                        pnl = 1.5 * gap_size
                    elif day_data['Low'].min() <= stop:
                        pnl = -2.0 * gap_size
                    else:
                        pnl = (day_data['Close'].iloc[-1] - entry_price)

                    trades.append({
                        'date': dates[i],
                        'direction': 'long',
                        'entry': entry_price,
                        'pnl_points': pnl,
                        'gap_size': gap_size
                    })

    return pd.DataFrame(trades) if trades else pd.DataFrame()

gap_trades = backtest_gap_fill(data)
print(f"Gap Fill Trades: {len(gap_trades)}")

# ============================================================
# STRATEGY 2: OPENING RANGE BREAKOUT (ORB)
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 2: OPENING RANGE BREAKOUT (ORB)")
print("=" * 70)

def backtest_orb(data):
    """Backtest Opening Range Breakout strategy (15-min opening range)."""
    trades = []
    if USE_DAILY:
        # For daily data, simulate ORB using open as the range
        for i in range(len(data)):
            row = data.iloc[i]
            or_high = row['High']
            or_low = row['Low']
            or_range = or_high - or_low

            if or_range < 3:
                continue

            # Simulate breakout: use open price as reference
            entry_long = row['Open'] + or_range * 0.1
            entry_short = row['Open'] - or_range * 0.1

            # Check direction based on close
            if row['Close'] > entry_long:
                # Long breakout
                target = entry_long + 1.5 * or_range
                stop = entry_long - or_range

                if row['High'] >= target:
                    pnl = 1.5 * or_range
                elif row['Low'] <= stop:
                    pnl = -or_range
                else:
                    pnl = (row['Close'] - entry_long)

                trades.append({
                    'date': data.index[i],
                    'direction': 'long',
                    'entry': entry_long,
                    'pnl_points': pnl,
                    'orb_range': or_range
                })
            elif row['Close'] < entry_short:
                # Short breakout
                target = entry_short - 1.5 * or_range
                stop = entry_short + or_range

                if row['Low'] <= target:
                    pnl = 1.5 * or_range
                elif row['High'] >= stop:
                    pnl = -or_range
                else:
                    pnl = (entry_short - row['Close'])

                trades.append({
                    'date': data.index[i],
                    'direction': 'short',
                    'entry': entry_short,
                    'pnl_points': pnl,
                    'orb_range': or_range
                })
    else:
        dates = data.index.normalize().unique()
        for date in dates:
            day_data = data[data.index.normalize() == date]

            # Filter to 9:30-9:45 AM ET for opening range
            or_data = day_data[
                (day_data.index.hour == 9) & (day_data.index.minute >= 30) |
                (day_data.index.hour == 9) & (day_data.index.minute < 45) |
                (day_data.index.hour == 9) & (day_data.index.minute == 45)
            ]

            if len(or_data) < 5:
                continue

            or_high = or_data['High'].max()
            or_low = or_data['Low'].min()
            or_range = or_high - or_low

            if or_range < 3:
                continue

            # Trading after 9:45
            trade_data = day_data[day_data.index.hour > 9] if not day_data[day_data.index.hour > 9].empty else day_data.iloc[-10:]

            for i in range(len(trade_data)):
                bar = trade_data.iloc[i]

                # Long breakout
                if bar['High'] > or_high and not any(t.get('date') == date and t['direction'] == 'long' for t in trades):
                    entry = or_high
                    target = entry + 1.5 * or_range
                    stop = entry - or_range

                    if bar['High'] >= target:
                        pnl = 1.5 * or_range
                    elif bar['Low'] <= stop:
                        pnl = -or_range
                    else:
                        pnl = (bar['Close'] - entry)

                    trades.append({
                        'date': date,
                        'direction': 'long',
                        'entry': entry,
                        'pnl_points': pnl,
                        'orb_range': or_range
                    })
                    break

                # Short breakout
                if bar['Low'] < or_low and not any(t.get('date') == date and t['direction'] == 'short' for t in trades):
                    entry = or_low
                    target = entry - 1.5 * or_range
                    stop = entry + or_range

                    if bar['Low'] <= target:
                        pnl = 1.5 * or_range
                    elif bar['High'] >= stop:
                        pnl = -or_range
                    else:
                        pnl = (entry - bar['Close'])

                    trades.append({
                        'date': date,
                        'direction': 'short',
                        'entry': entry,
                        'pnl_points': pnl,
                        'orb_range': or_range
                    })
                    break

    return pd.DataFrame(trades) if trades else pd.DataFrame()

orb_trades = backtest_orb(data)
print(f"ORB Trades: {len(orb_trades)}")

# ============================================================
# STRATEGY 3: INITIAL BALANCE (IB) BREAKOUT
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 3: INITIAL BALANCE (IB) BREAKOUT")
print("=" * 70)

def backtest_ib(data):
    """Backtest Initial Balance Breakout strategy (30-min opening range)."""
    trades = []
    direction_stats = {'long': {'wins': 0, 'losses': 0}, 'short': {'wins': 0, 'losses': 0}}

    if USE_DAILY:
        for i in range(len(data)):
            row = data.iloc[i]
            ib_high = row['High']
            ib_low = row['Low']
            ib_range = ib_high - ib_low

            if ib_range < 4:
                continue

            entry_long = ib_high + 1
            entry_short = ib_low - 1

            if row['Close'] > entry_long:
                target = entry_long + 1.5 * ib_range
                stop = entry_long - 0.5 * ib_range

                if row['High'] >= target:
                    pnl = 1.5 * ib_range
                    direction_stats['long']['wins'] += 1
                elif row['Low'] <= stop:
                    pnl = -0.5 * ib_range
                    direction_stats['long']['losses'] += 1
                else:
                    pnl = (row['Close'] - entry_long)
                    if pnl > 0:
                        direction_stats['long']['wins'] += 1
                    else:
                        direction_stats['long']['losses'] += 1

                trades.append({
                    'date': data.index[i],
                    'direction': 'long',
                    'entry': entry_long,
                    'pnl_points': pnl,
                    'ib_range': ib_range
                })
            elif row['Close'] < entry_short:
                target = entry_short - 1.5 * ib_range
                stop = entry_short + 0.5 * ib_range

                if row['Low'] <= target:
                    pnl = 1.5 * ib_range
                    direction_stats['short']['wins'] += 1
                elif row['High'] >= stop:
                    pnl = -0.5 * ib_range
                    direction_stats['short']['losses'] += 1
                else:
                    pnl = (entry_short - row['Close'])
                    if pnl > 0:
                        direction_stats['short']['wins'] += 1
                    else:
                        direction_stats['short']['losses'] += 1

                trades.append({
                    'date': data.index[i],
                    'direction': 'short',
                    'entry': entry_short,
                    'pnl_points': pnl,
                    'ib_range': ib_range
                })
    else:
        dates = data.index.normalize().unique()
        for date in dates:
            day_data = data[data.index.normalize() == date]

            # IB: 9:30-10:00 AM
            ib_data = day_data[
                (day_data.index.hour == 9) & (day_data.index.minute >= 30) |
                (day_data.index.hour == 10) & (day_data.index.minute == 0)
            ]

            if len(ib_data) < 10:
                continue

            ib_high = ib_data['High'].max()
            ib_low = ib_data['Low'].min()
            ib_range = ib_high - ib_low

            if ib_range < 4:
                continue

            # After 10:00 AM
            trade_data = day_data[day_data.index.hour >= 10]

            for i in range(len(trade_data)):
                bar = trade_data.iloc[i]

                if bar['High'] > ib_high + 1 and not any(t.get('date') == date for t in trades):
                    entry = ib_high + 1
                    target = entry + 1.5 * ib_range
                    stop = entry - 0.5 * ib_range

                    if bar['High'] >= target:
                        pnl = 1.5 * ib_range
                        direction_stats['long']['wins'] += 1
                    elif bar['Low'] <= stop:
                        pnl = -0.5 * ib_range
                        direction_stats['long']['losses'] += 1
                    else:
                        pnl = (bar['Close'] - entry)
                        if pnl > 0:
                            direction_stats['long']['wins'] += 1
                        else:
                            direction_stats['long']['losses'] += 1

                    trades.append({
                        'date': date,
                        'direction': 'long',
                        'entry': entry,
                        'pnl_points': pnl,
                        'ib_range': ib_range
                    })
                    break

                if bar['Low'] < ib_low - 1 and not any(t.get('date') == date for t in trades):
                    entry = ib_low - 1
                    target = entry - 1.5 * ib_range
                    stop = entry + 0.5 * ib_range

                    if bar['Low'] <= target:
                        pnl = 1.5 * ib_range
                        direction_stats['short']['wins'] += 1
                    elif bar['High'] >= stop:
                        pnl = -0.5 * ib_range
                        direction_stats['short']['losses'] += 1
                    else:
                        pnl = (entry - bar['Close'])
                        if pnl > 0:
                            direction_stats['short']['wins'] += 1
                        else:
                            direction_stats['short']['losses'] += 1

                    trades.append({
                        'date': date,
                        'direction': 'short',
                        'entry': entry,
                        'pnl_points': pnl,
                        'ib_range': ib_range
                    })
                    break

    return pd.DataFrame(trades) if trades else pd.DataFrame(), direction_stats

ib_trades, ib_direction_stats = backtest_ib(data)
print(f"IB Breakout Trades: {len(ib_trades)}")
print(f"Direction Stats: {ib_direction_stats}")

# ============================================================
# STRATEGY 4: MEAN REVERSION (RSI-BASED)
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 4: MEAN REVERSION (RSI-BASED)")
print("=" * 70)

def backtest_mean_reversion(data):
    """Backtest RSI-based mean reversion strategy."""
    trades = []

    # Calculate RSI
    data_with_rsi = data.copy()
    data_with_rsi['RSI'] = calculate_rsi(data_with_rsi['Close'], period=14)

    # Determine market regime (trending vs ranging)
    data_with_rsi['SMA_50'] = data_with_rsi['Close'].rolling(50).mean()
    data_with_rsi['Trend_Strength'] = abs(data_with_rsi['Close'] - data_with_rsi['SMA_50']) / data_with_rsi['SMA_50']

    in_trade = False
    trade_direction = None
    entry_price = 0

    for i in range(50, len(data_with_rsi)):
        row = data_with_rsi.iloc[i]
        prev_row = data_with_rsi.iloc[i-1]

        if pd.isna(row['RSI']):
            continue

        # Entry conditions
        if not in_trade:
            if row['RSI'] < 30:
                # Long entry (oversold)
                in_trade = True
                trade_direction = 'long'
                entry_price = row['Close']
            elif row['RSI'] > 70:
                # Short entry (overbought)
                in_trade = True
                trade_direction = 'short'
                entry_price = row['Close']
        else:
            # Exit condition: RSI returns to 50
            if trade_direction == 'long' and row['RSI'] >= 50:
                pnl = row['Close'] - entry_price
                trades.append({
                    'date': data_with_rsi.index[i],
                    'direction': 'long',
                    'entry': entry_price,
                    'exit': row['Close'],
                    'pnl_points': pnl,
                    'rsi_entry': prev_row['RSI'],
                    'rsi_exit': row['RSI'],
                    'trend_strength': row['Trend_Strength']
                })
                in_trade = False
            elif trade_direction == 'short' and row['RSI'] <= 50:
                pnl = entry_price - row['Close']
                trades.append({
                    'date': data_with_rsi.index[i],
                    'direction': 'short',
                    'entry': entry_price,
                    'exit': row['Close'],
                    'pnl_points': pnl,
                    'rsi_entry': prev_row['RSI'],
                    'rsi_exit': row['RSI'],
                    'trend_strength': row['Trend_Strength']
                })
                in_trade = False

    # Classify performance by market regime
    if trades:
        df = pd.DataFrame(trades)
        avg_trend = df['trend_strength'].median()
        df['regime'] = np.where(df['trend_strength'] > avg_trend, 'trending', 'ranging')
        regime_perf = df.groupby('regime')['pnl_points'].agg(['mean', 'count', 'sum'])
        print(f"Performance by regime:\n{regime_perf}")

    return pd.DataFrame(trades) if trades else pd.DataFrame()

mv_trades = backtest_mean_reversion(data)
print(f"Mean Reversion Trades: {len(mv_trades)}")

# ============================================================
# STRATEGY 5: EVENT-DRIVEN (FOMC/JACKSON HOLE SIMULATION)
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 5: EVENT-DRIVEN (NEWS SIMULATION)")
print("=" * 70)

def backtest_event_driven(data):
    """
    Simulate event-driven trading around major news events.
    Since we can't get real event times, we simulate based on high-volatility periods.
    """
    trades = []

    # Calculate volatility to identify "event" periods
    data_with_vol = data.copy()
    data_with_vol['Returns'] = data_with_vol['Close'].pct_change()
    data_with_vol['Volatility'] = data_with_vol['Returns'].rolling(20).std()
    data_with_vol['Vol_Spike'] = data_with_vol['Volatility'] > data_with_vol['Volatility'].quantile(0.9)

    # Identify potential event days (high volatility)
    if USE_DAILY:
        event_days = data_with_vol[data_with_vol['Vol_Spike']].index
    else:
        event_days = data_with_vol[data_with_vol['Vol_Spike']].index.normalize().unique()

    for event_date in event_days[:5]:  # Simulate up to 5 events
        day_data = data[data.index.normalize() == event_date] if not USE_DAILY else data[data.index == event_date]

        if day_data.empty or len(day_data) < 5:
            continue

        # Simulate event at 2:00 PM (common FOMC time)
        if USE_DAILY:
            event_price = day_data['Open'].iloc[0]
            entry_price = event_price  # Enter at "event"
            # Hold for "2 hours" (use close as proxy)
            exit_price = day_data['Close'].iloc[0]

            # Determine direction based on price action
            if exit_price > event_price:
                direction = 'long'
                pnl = exit_price - event_price
            else:
                direction = 'short'
                pnl = event_price - exit_price

            trades.append({
                'date': event_date,
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'pnl_points': pnl,
                'event_type': 'simulated'
            })
        else:
            # Find 2 PM bar
            event_bar = day_data[(day_data.index.hour == 14) & (day_data.index.minute == 0)]
            if event_bar.empty:
                continue

            entry_price = event_bar['Close'].iloc[0]

            # Exit 2 hours later (4 PM)
            exit_bar = day_data[(day_data.index.hour == 16) & (day_data.index.minute == 0)]
            if exit_bar.empty:
                exit_bar = day_data.iloc[-1:]

            exit_price = exit_bar['Close'].iloc[0]

            if exit_price > entry_price:
                direction = 'long'
                pnl = exit_price - entry_price
            else:
                direction = 'short'
                pnl = entry_price - exit_price

            trades.append({
                'date': event_date,
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'pnl_points': pnl,
                'event_type': 'simulated'
            })

    return pd.DataFrame(trades) if trades else pd.DataFrame()

ed_trades = backtest_event_driven(data)
print(f"Event-Driven Trades: {len(ed_trades)}")

# ============================================================
# PERFORMANCE ANALYSIS
# ============================================================
print("\n" + "=" * 70)
print("COMPREHENSIVE PERFORMANCE ANALYSIS")
print("=" * 70)

def calculate_metrics(trades_df, strategy_name):
    """Calculate comprehensive performance metrics."""
    if trades_df.empty:
        return {
            'strategy': strategy_name,
            'total_trades': 0,
            'total_return_points': 0,
            'total_return_dollars': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown_points': 0,
            'max_drawdown_dollars': 0,
            'max_drawdown_pct': 0,
            'sharpe_ratio': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_trade': 0
        }

    pnl = trades_df['pnl_points']
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]

    # Calculate equity curve
    equity = INITIAL_CAPITAL + pnl.cumsum() * CONTRACT_MULTIPLIER
    equity = np.insert(equity, 0, INITIAL_CAPITAL)

    # Drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity)
    max_dd_pct = (drawdown / peak).max() * 100

    # Sharpe ratio (annualized, assuming 252 trading days)
    daily_returns = pnl * CONTRACT_MULTIPLIER / INITIAL_CAPITAL
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0

    # Profit factor
    gross_profit = wins.sum() * CONTRACT_MULTIPLIER if len(wins) > 0 else 0
    gross_loss = abs(losses.sum() * CONTRACT_MULTIPLIER) if len(losses) > 0 else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'strategy': strategy_name,
        'total_trades': len(trades_df),
        'total_return_points': pnl.sum(),
        'total_return_dollars': pnl.sum() * CONTRACT_MULTIPLIER,
        'win_rate': (len(wins) / len(pnl) * 100) if len(pnl) > 0 else 0,
        'avg_win': wins.mean() if len(wins) > 0 else 0,
        'avg_loss': losses.mean() if len(losses) > 0 else 0,
        'profit_factor': profit_factor,
        'max_drawdown_points': drawdown.max() / CONTRACT_MULTIPLIER,
        'max_drawdown_dollars': drawdown.max(),
        'max_drawdown_pct': max_dd_pct,
        'sharpe_ratio': sharpe,
        'best_trade': pnl.max(),
        'worst_trade': pnl.min(),
        'avg_trade': pnl.mean()
    }

# Calculate metrics for all strategies
strategies = {
    'Gap Fill': gap_trades,
    'ORB Breakout': orb_trades,
    'IB Breakout': ib_trades,
    'Mean Reversion': mv_trades,
    'Event-Driven': ed_trades
}

all_metrics = []
for name, trades in strategies.items():
    metrics = calculate_metrics(trades, name)
    all_metrics.append(metrics)
    print(f"\n{name}:")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Total Return: {metrics['total_return_points']:.2f} pts (${metrics['total_return_dollars']:,.2f})")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown: ${metrics['max_drawdown_dollars']:,.2f} ({metrics['max_drawdown_pct']:.1f}%)")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Best Trade: {metrics['best_trade']:.2f} pts")
    print(f"  Worst Trade: {metrics['worst_trade']:.2f} pts")

metrics_df = pd.DataFrame(all_metrics)

# ============================================================
# VISUALIZATION
# ============================================================
print("\n" + "=" * 70)
print("GENERATING VISUALIZATIONS")
print("=" * 70)

fig = plt.figure(figsize=(20, 24))

# Color scheme
colors = {
    'Gap Fill': '#2ecc71',
    'ORB Breakout': '#3498db',
    'IB Breakout': '#e74c3c',
    'Mean Reversion': '#f39c12',
    'Event-Driven': '#9b59b6'
}

# 1. Equity Curves
ax1 = plt.subplot(4, 2, 1)
for name, trades in strategies.items():
    if not trades.empty:
        pnl = trades['pnl_points']
        equity = INITIAL_CAPITAL + pnl.cumsum() * CONTRACT_MULTIPLIER
        equity = np.insert(equity, 0, INITIAL_CAPITAL)
        ax1.plot(range(len(equity)), equity, label=name, color=colors[name], linewidth=2)
ax1.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--', alpha=0.5)
ax1.set_title('Equity Curves - All Strategies', fontsize=14, fontweight='bold')
ax1.set_xlabel('Trade Number')
ax1.set_ylabel('Account Value ($)')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.set_facecolor('#f8f9fa')

# 2. Win Rate Comparison
ax2 = plt.subplot(4, 2, 2)
strategies_list = metrics_df['strategy'].tolist()
win_rates = metrics_df['win_rate'].tolist()
bars = ax2.bar(strategies_list, win_rates, color=[colors[s] for s in strategies_list], edgecolor='black', linewidth=0.5)
ax2.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% line')
ax2.set_title('Win Rate by Strategy', fontsize=14, fontweight='bold')
ax2.set_ylabel('Win Rate (%)')
ax2.set_ylim(0, 100)
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')
for bar, wr in zip(bars, win_rates):
    ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
             f'{wr:.1f}%', ha='center', va='bottom', fontweight='bold')

# 3. Profit Factor
ax3 = plt.subplot(4, 2, 3)
pf_values = metrics_df['profit_factor'].tolist()
bars = ax3.bar(strategies_list, pf_values, color=[colors[s] for s in strategies_list], edgecolor='black', linewidth=0.5)
ax3.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Break-even')
ax3.set_title('Profit Factor by Strategy', fontsize=14, fontweight='bold')
ax3.set_ylabel('Profit Factor')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')
for bar, pf in zip(bars, pf_values):
    ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
             f'{pf:.2f}', ha='center', va='bottom', fontweight='bold')

# 4. Total Return ($)
ax4 = plt.subplot(4, 2, 4)
returns = metrics_df['total_return_dollars'].tolist()
bars = ax4.bar(strategies_list, returns, color=[colors[s] for s in strategies_list], edgecolor='black', linewidth=0.5)
ax4.axhline(y=0, color='red', linestyle='-', alpha=0.7)
ax4.set_title('Total Return ($) by Strategy', fontsize=14, fontweight='bold')
ax4.set_ylabel('Return ($)')
ax4.grid(True, alpha=0.3, axis='y')
for bar, ret in zip(bars, returns):
    ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 500,
             f'${ret:,.0f}', ha='center', va='bottom', fontweight='bold')

# 5. Drawdown Comparison
ax5 = plt.subplot(4, 2, 5)
dd_values = metrics_df['max_drawdown_dollars'].tolist()
bars = ax5.bar(strategies_list, dd_values, color=[colors[s] for s in strategies_list], edgecolor='black', linewidth=0.5)
ax5.set_title('Maximum Drawdown ($) by Strategy', fontsize=14, fontweight='bold')
ax5.set_ylabel('Max Drawdown ($)')
ax5.grid(True, alpha=0.3, axis='y')
for bar, dd in zip(bars, dd_values):
    ax5.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 200,
             f'${dd:,.0f}', ha='center', va='bottom', fontweight='bold')

# 6. Sharpe Ratio
ax6 = plt.subplot(4, 2, 6)
sharpe_values = metrics_df['sharpe_ratio'].tolist()
bars = ax6.bar(strategies_list, sharpe_values, color=[colors[s] for s in strategies_list], edgecolor='black', linewidth=0.5)
ax6.axhline(y=0, color='red', linestyle='-', alpha=0.7)
ax6.axhline(y=1, color='green', linestyle='--', alpha=0.7, label='Good (>1)')
ax6.set_title('Sharpe Ratio by Strategy', fontsize=14, fontweight='bold')
ax6.set_ylabel('Sharpe Ratio')
ax6.legend()
ax6.grid(True, alpha=0.3, axis='y')
for bar, sr in zip(bars, sharpe_values):
    ax6.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
             f'{sr:.2f}', ha='center', va='bottom', fontweight='bold')

# 7. Win/Loss Distribution
ax7 = plt.subplot(4, 2, 7)
for name, trades in strategies.items():
    if not trades.empty:
        pnl = trades['pnl_points']
        ax7.hist(pnl, bins=20, alpha=0.5, label=name, color=colors[name], edgecolor='black')
ax7.axvline(x=0, color='red', linestyle='--', linewidth=2)
ax7.set_title('P&L Distribution - All Strategies', fontsize=14, fontweight='bold')
ax7.set_xlabel('P&L (Points)')
ax7.set_ylabel('Frequency')
ax7.legend()
ax7.grid(True, alpha=0.3)

# 8. Risk-Reward Scatter
ax8 = plt.subplot(4, 2, 8)
for name, trades in strategies.items():
    if not trades.empty and 'pnl_points' in trades.columns:
        wins = trades[trades['pnl_points'] > 0]['pnl_points']
        losses = trades[trades['pnl_points'] <= 0]['pnl_points']
        if len(wins) > 0:
            ax8.scatter([name]*len(wins), wins, color=colors[name], alpha=0.6, s=50, marker='o', label=f'{name} Wins')
        if len(losses) > 0:
            ax8.scatter([name]*len(losses), losses, color=colors[name], alpha=0.6, s=50, marker='x')
ax8.axhline(y=0, color='red', linestyle='-', linewidth=2)
ax8.set_title('Individual Trade P&L by Strategy', fontsize=14, fontweight='bold')
ax8.set_ylabel('P&L (Points)')
ax8.grid(True, alpha=0.3)
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/backtest_overview.png', dpi=150, bbox_inches='tight')
print("Saved: backtest_overview.png")
plt.close()

# ============================================================
# STRATEGY-SPECIFIC CHARTS
# ============================================================

# IB Breakout Direction Analysis
if ib_direction_stats['long']['wins'] + ib_direction_stats['long']['losses'] > 0 or \
   ib_direction_stats['short']['wins'] + ib_direction_stats['short']['losses'] > 0:

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Direction win rates
    directions = ['Long', 'Short']
    long_wr = ib_direction_stats['long']['wins'] / (ib_direction_stats['long']['wins'] + ib_direction_stats['long']['losses']) * 100 if (ib_direction_stats['long']['wins'] + ib_direction_stats['long']['losses']) > 0 else 0
    short_wr = ib_direction_stats['short']['wins'] / (ib_direction_stats['short']['wins'] + ib_direction_stats['short']['losses']) * 100 if (ib_direction_stats['short']['wins'] + ib_direction_stats['short']['losses']) > 0 else 0

    axes[0].bar(directions, [long_wr, short_wr], color=['#2ecc71', '#e74c3c'], edgecolor='black')
    axes[0].axhline(y=50, color='gray', linestyle='--', alpha=0.7)
    axes[0].set_title('IB Breakout: Win Rate by Direction')
    axes[0].set_ylabel('Win Rate (%)')
    axes[0].set_ylim(0, 100)

    # Trade count by direction
    long_count = ib_direction_stats['long']['wins'] + ib_direction_stats['long']['losses']
    short_count = ib_direction_stats['short']['wins'] + ib_direction_stats['short']['losses']
    axes[1].bar(directions, [long_count, short_count], color=['#2ecc71', '#e74c3c'], edgecolor='black')
    axes[1].set_title('IB Breakout: Trade Count by Direction')
    axes[1].set_ylabel('Number of Trades')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/ib_breakout_analysis.png', dpi=150, bbox_inches='tight')
    print("Saved: ib_breakout_analysis.png")
    plt.close()

# ============================================================
# HEATMAP: Monthly Returns by Day
# ============================================================
print("\nGenerating Monthly Return Heatmap...")

# Aggregate daily returns across all strategies
daily_returns_all = pd.DataFrame()
for name, trades in strategies.items():
    if not trades.empty and 'date' in trades.columns:
        daily = trades.groupby('date')['pnl_points'].sum()
        daily_returns_all[name] = daily

if not daily_returns_all.empty:
    daily_returns_all = daily_returns_all.fillna(0)
    daily_returns_all['Total'] = daily_returns_all.sum(axis=1)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 6))

    # Pivot for calendar view
    daily_returns_all.index = pd.to_datetime(daily_returns_all.index)
    daily_returns_all['Day'] = daily_returns_all.index.day
    daily_returns_all['Weekday'] = daily_returns_all.index.day_name()

    # Weekly aggregation
    daily_returns_all['Week'] = daily_returns_all.index.isocalendar().week

    pivot_data = daily_returns_all.pivot_table(
        values='Total',
        index='Weekday',
        columns='Week',
        aggfunc='sum'
    )

    # Reorder weekdays
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    pivot_data = pivot_data.reindex([d for d in weekday_order if d in pivot_data.index])

    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='RdYlGn', center=0,
                ax=ax, linewidths=0.5, cbar_kws={'label': 'P&L (Points)'})
    ax.set_title('Weekly P&L Heatmap (All Strategies Combined)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Week Number')
    ax.set_ylabel('Day of Week')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/weekly_heatmap.png', dpi=150, bbox_inches='tight')
    print("Saved: weekly_heatmap.png")
    plt.close()

# ============================================================
# SUMMARY REPORT
# ============================================================
print("\n" + "=" * 70)
print("FINAL SUMMARY REPORT")
print("=" * 70)

report = f"""
{'='*70}
BACKTEST RESULTS: AUGUST 2026 - ES=F (E-mini S&P 500 Futures)
{'='*70}
Data Period: {START_DATE} to {END_DATE}
Initial Capital: ${INITIAL_CAPITAL:,.2f}
Contract: ES=F (Multiplier: ${CONTRACT_MULTIPLIER}, Tick: ${TICK_VALUE})

{'='*70}
STRATEGY PERFORMANCE SUMMARY
{'='*70}

"""

for _, row in metrics_df.iterrows():
    report += f"""
--- {row['strategy']} ---
  Total Trades:        {row['total_trades']}
  Total Return:        {row['total_return_points']:.2f} points (${row['total_return_dollars']:,.2f})
  Win Rate:            {row['win_rate']:.1f}%
  Avg Win:             {row['avg_win']:.2f} points
  Avg Loss:            {row['avg_loss']:.2f} points
  Profit Factor:       {row['profit_factor']:.2f}
  Max Drawdown:        ${row['max_drawdown_dollars']:,.2f} ({row['max_drawdown_pct']:.1f}%)
  Sharpe Ratio:        {row['sharpe_ratio']:.2f}
  Best Trade:          {row['best_trade']:.2f} points
  Worst Trade:         {row['worst_trade']:.2f} points
  Avg Trade:           {row['avg_trade']:.2f} points
"""

# Rankings
report += f"""
{'='*70}
RANKINGS
{'='*70}

Best Win Rate:     {metrics_df.loc[metrics_df['win_rate'].idxmax(), 'strategy']} ({metrics_df['win_rate'].max():.1f}%)
Best Profit Factor: {metrics_df.loc[metrics_df['profit_factor'].idxmax(), 'strategy']} ({metrics_df['profit_factor'].max():.2f})
Best Sharpe Ratio:  {metrics_df.loc[metrics_df['sharpe_ratio'].idxmax(), 'strategy']} ({metrics_df['sharpe_ratio'].max():.2f})
Best Total Return:  {metrics_df.loc[metrics_df['total_return_dollars'].idxmax(), 'strategy']} (${metrics_df['total_return_dollars'].max():,.2f})
Lowest Drawdown:    {metrics_df.loc[metrics_df['max_drawdown_dollars'].idxmin(), 'strategy']} (${metrics_df['max_drawdown_dollars'].min():,.2f})

{'='*70}
IB BREAKOUT DIRECTION ANALYSIS
{'='*70}
Long Win Rate:  {ib_direction_stats['long']['wins']}/{ib_direction_stats['long']['wins'] + ib_direction_stats['long']['losses']} trades
Short Win Rate: {ib_direction_stats['short']['wins']}/{ib_direction_stats['short']['wins'] + ib_direction_stats['short']['losses']} trades

{'='*70}
IMPORTANT DISCLAIMERS
{'='*70}
1. This is a BACKTEST on HISTORICAL/SIMULATED data, NOT live trading results
2. Past performance does NOT guarantee future results
3. Slippage, commissions, and market impact are NOT fully modeled
4. Data quality may vary - verify with your broker's data
5. This is for EDUCATIONAL purposes only - not financial advice
6. Always paper trade before risking real capital
7. Prop firms have specific rules - verify compatibility before live trading

{'='*70}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""

print(report)

# Save report to file
with open(f'{OUTPUT_DIR}/backtest_report.txt', 'w') as f:
    f.write(report)
print(f"Report saved to: {OUTPUT_DIR}/backtest_report.txt")

# Save metrics to CSV
metrics_df.to_csv(f'{OUTPUT_DIR}/backtest_metrics.csv', index=False)
print(f"Metrics CSV saved to: {OUTPUT_DIR}/backtest_metrics.csv")

# Save trade details
for name, trades in strategies.items():
    if not trades.empty:
        filename = f'{OUTPUT_DIR}/trades_{name.lower().replace(" ", "_")}.csv'
        trades.to_csv(filename, index=False)
        print(f"Trades saved to: {filename}")

print("\n" + "=" * 70)
print("BACKTEST COMPLETE!")
print("=" * 70)
