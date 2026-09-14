#!/usr/bin/env python3
"""
Improved Backtest: August 2026 Trading Strategies on ES=F
=========================================================
Handles 15-minute data granularity properly.
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
CONTRACT_MULTIPLIER = 50
OUTPUT_DIR = r"C:\Users\dgran\AppData\Local\Temp\opencode"

print("=" * 70)
print("DOWNLOADING DATA FOR", SYMBOL, ":", START_DATE, "to", END_DATE)
print("=" * 70)

# Download 15-minute data
data = yf.download(SYMBOL, start=START_DATE, end=END_DATE, interval="15m", progress=False)

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()
print(f"Data shape: {data.shape}")
print(f"Date range: {data.index.min()} to {data.index.max()}")

# ============================================================
# INDICATOR FUNCTIONS
# ============================================================

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

# ============================================================
# STRATEGY 1: GAP FILL
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 1: GAP FILL")
print("=" * 70)

def backtest_gap_fill(data):
    trades = []
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
        
        # Check if gap was filled
        if current_open > prev_close:
            # Gap up - look for price to come down to prev_close
            filled_bars = day_data[day_data['Low'] <= prev_close]
            if not filled_bars.empty:
                entry_price = prev_close
                target = entry_price - 1.5 * gap_size
                stop = entry_price + 2.0 * gap_size
                
                # Check outcome
                if day_data['Low'].min() <= target:
                    pnl = 1.5 * gap_size
                elif day_data['High'].max() >= stop:
                    pnl = -2.0 * gap_size
                else:
                    pnl = (entry_price - day_data['Close'].iloc[-1])
                
                trades.append({
                    'date': dates[i],
                    'direction': 'short',
                    'entry': entry_price,
                    'pnl_points': round(pnl, 2),
                    'gap_size': round(gap_size, 2)
                })
        else:
            # Gap down - look for price to come up to prev_close
            filled_bars = day_data[day_data['High'] >= prev_close]
            if not filled_bars.empty:
                entry_price = prev_close
                target = entry_price + 1.5 * gap_size
                stop = entry_price - 2.0 * gap_size
                
                if day_data['High'].max() >= target:
                    pnl = 1.5 * gap_size
                elif day_data['Low'].min() <= stop:
                    pnl = -2.0 * gap_size
                else:
                    pnl = (day_data['Close'].iloc[-1] - entry_price)
                
                trades.append({
                    'date': dates[i],
                    'direction': 'long',
                    'entry': entry_price,
                    'pnl_points': round(pnl, 2),
                    'gap_size': round(gap_size, 2)
                })
    
    return pd.DataFrame(trades) if trades else pd.DataFrame()

gap_trades = backtest_gap_fill(data)
print(f"Trades found: {len(gap_trades)}")
if not gap_trades.empty:
    print(gap_trades.to_string())

# ============================================================
# STRATEGY 2: OPENING RANGE BREAKOUT (ORB) - 15 min
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 2: OPENING RANGE BREAKOUT (ORB) - 15min")
print("=" * 70)

def backtest_orb(data):
    """ORB using first 2 bars (30 min total) as opening range for 15min data."""
    trades = []
    dates = data.index.normalize().unique()
    
    for date in dates:
        day_data = data[data.index.normalize() == date].copy()
        
        if len(day_data) < 6:
            continue
        
        # Use first 2 bars (30 min) as opening range
        or_data = day_data.iloc[:2]
        or_high = or_data['High'].max()
        or_low = or_data['Low'].min()
        or_range = or_high - or_low
        
        if or_range < 3:
            continue
        
        # Trade after opening range
        trade_data = day_data.iloc[2:]
        trade_taken = False
        
        for idx, bar in trade_data.iterrows():
            if trade_taken:
                break
            
            # Long breakout
            if bar['Close'] > or_high:
                entry = or_high
                target = entry + 1.5 * or_range
                stop = entry - or_range
                
                if bar['High'] >= target:
                    pnl = 1.5 * or_range
                elif bar['Low'] <= stop:
                    pnl = -or_range
                else:
                    pnl = bar['Close'] - entry
                
                trades.append({
                    'date': date,
                    'direction': 'long',
                    'entry': round(entry, 2),
                    'pnl_points': round(pnl, 2),
                    'orb_range': round(or_range, 2)
                })
                trade_taken = True
            
            # Short breakout
            elif bar['Close'] < or_low:
                entry = or_low
                target = entry - 1.5 * or_range
                stop = entry + or_range
                
                if bar['Low'] <= target:
                    pnl = 1.5 * or_range
                elif bar['High'] >= stop:
                    pnl = -or_range
                else:
                    pnl = entry - bar['Close']
                
                trades.append({
                    'date': date,
                    'direction': 'short',
                    'entry': round(entry, 2),
                    'pnl_points': round(pnl, 2),
                    'orb_range': round(or_range, 2)
                })
                trade_taken = True
    
    return pd.DataFrame(trades) if trades else pd.DataFrame()

orb_trades = backtest_orb(data)
print(f"Trades found: {len(orb_trades)}")
if not orb_trades.empty:
    print(orb_trades.to_string())

# ============================================================
# STRATEGY 3: INITIAL BALANCE (IB) BREAKOUT
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 3: INITIAL BALANCE (IB) BREAKOUT")
print("=" * 70)

def backtest_ib(data):
    """IB = first 30 min (2 bars on 15min chart)."""
    trades = []
    direction_stats = {'long': {'wins': 0, 'losses': 0, 'pnls': []}, 
                       'short': {'wins': 0, 'losses': 0, 'pnls': []}}
    dates = data.index.normalize().unique()
    
    for date in dates:
        day_data = data[data.index.normalize() == date].copy()
        
        if len(day_data) < 6:
            continue
        
        # IB = first 2 bars (30 min)
        ib_data = day_data.iloc[:2]
        ib_high = ib_data['High'].max()
        ib_low = ib_data['Low'].min()
        ib_range = ib_high - ib_low
        
        if ib_range < 4:
            continue
        
        # Trade after IB
        trade_data = day_data.iloc[2:]
        trade_taken = False
        
        for idx, bar in trade_data.iterrows():
            if trade_taken:
                break
            
            # Long breakout
            if bar['Close'] > ib_high + 1:
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
                    pnl = bar['Close'] - entry
                    if pnl > 0:
                        direction_stats['long']['wins'] += 1
                    else:
                        direction_stats['long']['losses'] += 1
                
                direction_stats['long']['pnls'].append(pnl)
                trades.append({
                    'date': date,
                    'direction': 'long',
                    'entry': round(entry, 2),
                    'pnl_points': round(pnl, 2),
                    'ib_range': round(ib_range, 2)
                })
                trade_taken = True
            
            # Short breakout
            elif bar['Close'] < ib_low - 1:
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
                    pnl = entry - bar['Close']
                    if pnl > 0:
                        direction_stats['short']['wins'] += 1
                    else:
                        direction_stats['short']['losses'] += 1
                
                direction_stats['short']['pnls'].append(pnl)
                trades.append({
                    'date': date,
                    'direction': 'short',
                    'entry': round(entry, 2),
                    'pnl_points': round(pnl, 2),
                    'ib_range': round(ib_range, 2)
                })
                trade_taken = True
    
    return pd.DataFrame(trades) if trades else pd.DataFrame(), direction_stats

ib_trades, ib_dir_stats = backtest_ib(data)
print(f"Trades found: {len(ib_trades)}")
if not ib_trades.empty:
    print(ib_trades.to_string())
print(f"\nDirection Stats: Long W/L={ib_dir_stats['long']['wins']}/{ib_dir_stats['long']['losses']}, "
      f"Short W/L={ib_dir_stats['short']['wins']}/{ib_dir_stats['short']['losses']}")

# ============================================================
# STRATEGY 4: MEAN REVERSION (RSI)
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 4: MEAN REVERSION (RSI-BASED)")
print("=" * 70)

def backtest_mean_reversion(data):
    trades = []
    data_with_rsi = data.copy()
    data_with_rsi['RSI'] = calculate_rsi(data_with_rsi['Close'], period=14)
    data_with_rsi['SMA_50'] = data_with_rsi['Close'].rolling(50).mean()
    data_with_rsi['Trend_Strength'] = abs(data_with_rsi['Close'] - data_with_rsi['SMA_50']) / data_with_rsi['SMA_50']
    
    in_trade = False
    trade_direction = None
    entry_price = 0
    entry_rsi = 0
    
    for i in range(50, len(data_with_rsi)):
        row = data_with_rsi.iloc[i]
        prev_row = data_with_rsi.iloc[i-1]
        
        if pd.isna(row['RSI']) or pd.isna(row['Trend_Strength']):
            continue
        
        if not in_trade:
            if row['RSI'] < 30:
                in_trade = True
                trade_direction = 'long'
                entry_price = row['Close']
                entry_rsi = row['RSI']
            elif row['RSI'] > 70:
                in_trade = True
                trade_direction = 'short'
                entry_price = row['Close']
                entry_rsi = row['RSI']
        else:
            if trade_direction == 'long' and row['RSI'] >= 50:
                pnl = row['Close'] - entry_price
                trades.append({
                    'date': data_with_rsi.index[i],
                    'direction': 'long',
                    'entry': round(entry_price, 2),
                    'exit': round(row['Close'], 2),
                    'pnl_points': round(pnl, 2),
                    'rsi_entry': round(entry_rsi, 1),
                    'rsi_exit': round(row['RSI'], 1),
                    'trend_strength': round(row['Trend_Strength'], 4)
                })
                in_trade = False
            elif trade_direction == 'short' and row['RSI'] <= 50:
                pnl = entry_price - row['Close']
                trades.append({
                    'date': data_with_rsi.index[i],
                    'direction': 'short',
                    'entry': round(entry_price, 2),
                    'exit': round(row['Close'], 2),
                    'pnl_points': round(pnl, 2),
                    'rsi_entry': round(entry_rsi, 1),
                    'rsi_exit': round(row['RSI'], 1),
                    'trend_strength': round(row['Trend_Strength'], 4)
                })
                in_trade = False
    
    if trades:
        df = pd.DataFrame(trades)
        avg_trend = df['trend_strength'].median()
        df['regime'] = np.where(df['trend_strength'] > avg_trend, 'trending', 'ranging')
        regime_perf = df.groupby('regime')['pnl_points'].agg(['mean', 'count', 'sum'])
        print(f"\nPerformance by Market Regime:\n{regime_perf}")
    
    return pd.DataFrame(trades) if trades else pd.DataFrame()

mv_trades = backtest_mean_reversion(data)
print(f"Trades found: {len(mv_trades)}")

# ============================================================
# STRATEGY 5: EVENT-DRIVEN
# ============================================================
print("\n" + "=" * 70)
print("STRATEGY 5: EVENT-DRIVEN (NEWS SIMULATION)")
print("=" * 70)

def backtest_event_driven(data):
    trades = []
    data_with_vol = data.copy()
    data_with_vol['Returns'] = data_with_vol['Close'].pct_change()
    data_with_vol['Volatility'] = data_with_vol['Returns'].rolling(20).std()
    data_with_vol['Vol_Spike'] = data_with_vol['Volatility'] > data_with_vol['Volatility'].quantile(0.9)
    
    event_days = data_with_vol[data_with_vol['Vol_Spike']].index.normalize().unique()
    
    for event_date in event_days[:8]:
        day_data = data[data.index.normalize() == event_date]
        
        if day_data.empty or len(day_data) < 4:
            continue
        
        # Find mid-day point (simulating 2 PM event)
        mid_idx = len(day_data) // 2
        entry_bar = day_data.iloc[mid_idx]
        exit_bar = day_data.iloc[-1]
        
        entry_price = entry_bar['Close']
        exit_price = exit_bar['Close']
        
        if exit_price > entry_price:
            direction = 'long'
            pnl = exit_price - entry_price
        else:
            direction = 'short'
            pnl = entry_price - exit_price
        
        trades.append({
            'date': event_date,
            'direction': direction,
            'entry': round(entry_price, 2),
            'exit': round(exit_price, 2),
            'pnl_points': round(pnl, 2)
        })
    
    return pd.DataFrame(trades) if trades else pd.DataFrame()

ed_trades = backtest_event_driven(data)
print(f"Trades found: {len(ed_trades)}")
if not ed_trades.empty:
    print(ed_trades.to_string())

# ============================================================
# METRICS CALCULATION
# ============================================================
print("\n" + "=" * 70)
print("COMPREHENSIVE PERFORMANCE METRICS")
print("=" * 70)

def calc_metrics(trades_df, name):
    if trades_df.empty:
        return {
            'strategy': name, 'trades': 0, 'total_return_pts': 0, 'total_return_usd': 0,
            'win_rate': 0, 'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0,
            'max_dd_usd': 0, 'max_dd_pct': 0, 'sharpe': 0,
            'best_trade': 0, 'worst_trade': 0, 'avg_trade': 0
        }
    
    pnl = trades_df['pnl_points']
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    
    equity = INITIAL_CAPITAL + pnl.cumsum() * CONTRACT_MULTIPLIER
    equity = np.insert(equity, 0, INITIAL_CAPITAL)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = dd.max()
    max_dd_pct = (dd / peak).max() * 100
    
    daily_ret = pnl * CONTRACT_MULTIPLIER / INITIAL_CAPITAL
    sharpe = (daily_ret.mean() / daily_ret.std()) * np.sqrt(252) if len(daily_ret) > 1 and daily_ret.std() > 0 else 0
    
    gross_profit = wins.sum() * CONTRACT_MULTIPLIER if len(wins) > 0 else 0
    gross_loss = abs(losses.sum() * CONTRACT_MULTIPLIER) if len(losses) > 0 else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    return {
        'strategy': name,
        'trades': len(pnl),
        'total_return_pts': round(pnl.sum(), 2),
        'total_return_usd': round(pnl.sum() * CONTRACT_MULTIPLIER, 2),
        'win_rate': round(len(wins) / len(pnl) * 100, 1) if len(pnl) > 0 else 0,
        'avg_win': round(wins.mean(), 2) if len(wins) > 0 else 0,
        'avg_loss': round(losses.mean(), 2) if len(losses) > 0 else 0,
        'profit_factor': round(pf, 2),
        'max_dd_usd': round(max_dd, 2),
        'max_dd_pct': round(max_dd_pct, 2),
        'sharpe': round(sharpe, 2),
        'best_trade': round(pnl.max(), 2),
        'worst_trade': round(pnl.min(), 2),
        'avg_trade': round(pnl.mean(), 2)
    }

strategies = {
    'Gap Fill': gap_trades,
    'ORB (15min)': orb_trades,
    'IB Breakout': ib_trades,
    'Mean Reversion': mv_trades,
    'Event-Driven': ed_trades
}

all_metrics = []
for name, trades in strategies.items():
    m = calc_metrics(trades, name)
    all_metrics.append(m)
    print(f"\n--- {name} ---")
    for k, v in m.items():
        if k != 'strategy':
            print(f"  {k:20s}: {v}")

metrics_df = pd.DataFrame(all_metrics)

# ============================================================
# VISUALIZATIONS - COMPREHENSIVE
# ============================================================
print("\n" + "=" * 70)
print("GENERATING COMPREHENSIVE VISUALIZATIONS")
print("=" * 70)

colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6']
strategy_names = list(strategies.keys())

# === FIGURE 1: Main Dashboard ===
fig = plt.figure(figsize=(22, 16))
fig.suptitle('August 2026 Backtest Dashboard - ES=F Strategies', fontsize=18, fontweight='bold', y=0.98)

# 1. Equity Curves
ax1 = fig.add_subplot(3, 3, 1)
for i, (name, trades) in enumerate(strategies.items()):
    if not trades.empty:
        pnl = trades['pnl_points']
        equity = INITIAL_CAPITAL + pnl.cumsum() * CONTRACT_MULTIPLIER
        equity = np.insert(equity, 0, INITIAL_CAPITAL)
        ax1.plot(range(len(equity)), equity, label=name, color=colors[i], linewidth=2, marker='o', markersize=3)
ax1.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--', alpha=0.5)
ax1.set_title('Equity Curves', fontweight='bold')
ax1.set_xlabel('Trade #')
ax1.set_ylabel('Account ($)')
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.set_facecolor('#f8f9fa')

# 2. Win Rate Comparison
ax2 = fig.add_subplot(3, 3, 2)
wr = metrics_df['win_rate'].tolist()
bars = ax2.bar(strategy_names, wr, color=colors, edgecolor='black', linewidth=0.5)
ax2.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50%')
ax2.set_title('Win Rate (%)', fontweight='bold')
ax2.set_ylim(0, 110)
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')
for b, v in zip(bars, wr):
    ax2.text(b.get_x() + b.get_width()/2., v + 2, f'{v:.1f}%', ha='center', fontweight='bold', fontsize=9)
ax2.tick_params(axis='x', rotation=45)

# 3. Profit Factor
ax3 = fig.add_subplot(3, 3, 3)
pf = metrics_df['profit_factor'].tolist()
bars = ax3.bar(strategy_names, pf, color=colors, edgecolor='black', linewidth=0.5)
ax3.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Break-even')
ax3.set_title('Profit Factor', fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')
for b, v in zip(bars, pf):
    ax3.text(b.get_x() + b.get_width()/2., v + 0.1, f'{v:.2f}', ha='center', fontweight='bold', fontsize=9)
ax3.tick_params(axis='x', rotation=45)

# 4. Total Return ($)
ax4 = fig.add_subplot(3, 3, 4)
ret = metrics_df['total_return_usd'].tolist()
bars = ax4.bar(strategy_names, ret, color=colors, edgecolor='black', linewidth=0.5)
ax4.axhline(y=0, color='red', linestyle='-', alpha=0.7)
ax4.set_title('Total Return ($)', fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')
for b, v in zip(bars, ret):
    offset = 200 if v >= 0 else -400
    ax4.text(b.get_x() + b.get_width()/2., v + offset, f'${v:,.0f}', ha='center', fontweight='bold', fontsize=9)
ax4.tick_params(axis='x', rotation=45)

# 5. Max Drawdown
ax5 = fig.add_subplot(3, 3, 5)
dd = metrics_df['max_dd_usd'].tolist()
bars = ax5.bar(strategy_names, dd, color=colors, edgecolor='black', linewidth=0.5)
ax5.set_title('Max Drawdown ($)', fontweight='bold')
ax5.grid(True, alpha=0.3, axis='y')
for b, v in zip(bars, dd):
    ax5.text(b.get_x() + b.get_width()/2., v + 100, f'${v:,.0f}', ha='center', fontweight='bold', fontsize=9)
ax5.tick_params(axis='x', rotation=45)

# 6. Sharpe Ratio
ax6 = fig.add_subplot(3, 3, 6)
sr = metrics_df['sharpe'].tolist()
bars = ax6.bar(strategy_names, sr, color=colors, edgecolor='black', linewidth=0.5)
ax6.axhline(y=0, color='red', linestyle='-', alpha=0.7)
ax6.axhline(y=1, color='green', linestyle='--', alpha=0.7, label='Good (>1)')
ax6.set_title('Sharpe Ratio', fontweight='bold')
ax6.legend()
ax6.grid(True, alpha=0.3, axis='y')
for b, v in zip(bars, sr):
    ax6.text(b.get_x() + b.get_width()/2., v + 0.1, f'{v:.2f}', ha='center', fontweight='bold', fontsize=9)
ax6.tick_params(axis='x', rotation=45)

# 7. P&L Distribution
ax7 = fig.add_subplot(3, 3, 7)
for i, (name, trades) in enumerate(strategies.items()):
    if not trades.empty:
        ax7.hist(trades['pnl_points'], bins=15, alpha=0.5, label=name, color=colors[i], edgecolor='black')
ax7.axvline(x=0, color='red', linestyle='--', linewidth=2)
ax7.set_title('P&L Distribution', fontweight='bold')
ax7.set_xlabel('P&L (Points)')
ax7.legend(fontsize=7)
ax7.grid(True, alpha=0.3)

# 8. Individual Trade Scatter
ax8 = fig.add_subplot(3, 3, 8)
for i, (name, trades) in enumerate(strategies.items()):
    if not trades.empty:
        x_pos = [i] * len(trades)
        ax8.scatter(x_pos, trades['pnl_points'], color=colors[i], alpha=0.7, s=60, edgecolors='black', linewidth=0.5, label=name)
ax8.axhline(y=0, color='red', linestyle='-', linewidth=2)
ax8.set_title('Trade P&L Scatter', fontweight='bold')
ax8.set_ylabel('P&L (Points)')
ax8.set_xticks(range(len(strategy_names)))
ax8.set_xticklabels(strategy_names, rotation=45, fontsize=8)
ax8.grid(True, alpha=0.3)

# 9. Summary Table
ax9 = fig.add_subplot(3, 3, 9)
ax9.axis('off')
table_data = metrics_df[['strategy', 'trades', 'win_rate', 'profit_factor', 'total_return_usd', 'sharpe']].copy()
table_data.columns = ['Strategy', 'Trades', 'Win%', 'PF', 'Return($)', 'Sharpe']
table = ax9.table(cellText=table_data.values, colLabels=table_data.columns, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.5)
ax9.set_title('Summary Table', fontweight='bold', pad=20)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(f'{OUTPUT_DIR}/backtest_dashboard.png', dpi=150, bbox_inches='tight')
print("Saved: backtest_dashboard.png")
plt.close()

# === FIGURE 2: Strategy Deep Dives ===
fig2, axes = plt.subplots(2, 2, figsize=(16, 12))
fig2.suptitle('Strategy Deep Dive Analysis', fontsize=16, fontweight='bold')

# Gap Fill Analysis
if not gap_trades.empty:
    ax = axes[0, 0]
    ax.bar(range(len(gap_trades)), gap_trades['pnl_points'], 
           color=['green' if x > 0 else 'red' for x in gap_trades['pnl_points']], edgecolor='black')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_title('Gap Fill: Trade P&L', fontweight='bold')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('P&L (Points)')
    ax.grid(True, alpha=0.3)

# Mean Reversion by Regime
if not mv_trades.empty:
    ax = axes[0, 1]
    mv_df = mv_trades.copy()
    if 'regime' in mv_df.columns:
        regimes = mv_df['regime'].unique()
        for r in regimes:
            subset = mv_df[mv_df['regime'] == r]
            ax.hist(subset['pnl_points'], bins=10, alpha=0.6, label=f'{r} (n={len(subset)})', edgecolor='black')
        ax.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax.set_title('Mean Reversion: By Market Regime', fontweight='bold')
        ax.set_xlabel('P&L (Points)')
        ax.legend()
        ax.grid(True, alpha=0.3)

# IB Breakout by Direction
if not ib_trades.empty:
    ax = axes[1, 0]
    ib_df = ib_trades.copy()
    long_pnl = ib_df[ib_df['direction'] == 'long']['pnl_points']
    short_pnl = ib_df[ib_df['direction'] == 'short']['pnl_points']
    
    x = np.arange(2)
    width = 0.35
    if len(long_pnl) > 0:
        ax.bar(x[0] - width/2, long_pnl.mean(), width, label=f'Long (n={len(long_pnl)})', color='green', alpha=0.7, edgecolor='black')
    if len(short_pnl) > 0:
        ax.bar(x[1] + width/2, short_pnl.mean(), width, label=f'Short (n={len(short_pnl)})', color='red', alpha=0.7, edgecolor='black')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_title('IB Breakout: Avg P&L by Direction', fontweight='bold')
    ax.set_ylabel('Avg P&L (Points)')
    ax.set_xticks(x)
    ax.set_xticklabels(['Long', 'Short'])
    ax.legend()
    ax.grid(True, alpha=0.3)

# Event-Driven Performance
if not ed_trades.empty:
    ax = axes[1, 1]
    ax.bar(range(len(ed_trades)), ed_trades['pnl_points'],
           color=['green' if x > 0 else 'red' for x in ed_trades['pnl_points']], edgecolor='black')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_title('Event-Driven: Trade P&L', fontweight='bold')
    ax.set_xlabel('Event #')
    ax.set_ylabel('P&L (Points)')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/strategy_deep_dive.png', dpi=150, bbox_inches='tight')
print("Saved: strategy_deep_dive.png")
plt.close()

# === FIGURE 3: Weekly Heatmap ===
print("\nGenerating Weekly Heatmap...")
daily_pnl = pd.DataFrame()
for name, trades in strategies.items():
    if not trades.empty and 'date' in trades.columns:
        daily = trades.groupby('date')['pnl_points'].sum()
        daily_pnl[name] = daily

if not daily_pnl.empty:
    daily_pnl = daily_pnl.fillna(0)
    daily_pnl['Total'] = daily_pnl.sum(axis=1)
    daily_pnl.index = pd.to_datetime(daily_pnl.index)
    daily_pnl['Weekday'] = daily_pnl.index.day_name()
    daily_pnl['Week'] = daily_pnl.index.isocalendar().week
    
    pivot = daily_pnl.pivot_table(values='Total', index='Weekday', columns='Week', aggfunc='sum')
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex([d for d in weekday_order if d in pivot.index])
    
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(pivot, annot=True, fmt='.0f', cmap='RdYlGn', center=0, ax=ax,
                linewidths=0.5, cbar_kws={'label': 'P&L (Points)'})
    ax.set_title('Weekly P&L Heatmap - All Strategies Combined', fontsize=14, fontweight='bold')
    ax.set_xlabel('Week Number')
    ax.set_ylabel('Day of Week')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/weekly_heatmap.png', dpi=150, bbox_inches='tight')
    print("Saved: weekly_heatmap.png")
    plt.close()

# ============================================================
# FINAL REPORT
# ============================================================
print("\n" + "=" * 70)
print("FINAL BACKTEST REPORT")
print("=" * 70)

report = f"""
{'='*70}
BACKTEST RESULTS: AUGUST 2026 - ES=F (E-mini S&P 500 Futures)
{'='*70}
Data Period: {START_DATE} to {END_DATE}
Data Source: Yahoo Finance (15-minute bars)
Initial Capital: ${INITIAL_CAPITAL:,.2f}
Contract: ES=F (Multiplier: ${CONTRACT_MULTIPLIER}, Tick: $12.50)

{'='*70}
STRATEGY PERFORMANCE SUMMARY
{'='*70}
"""

for _, row in metrics_df.iterrows():
    report += f"""
--- {row['strategy']} ---
  Total Trades:        {row['trades']}
  Total Return:        {row['total_return_pts']:.2f} pts (${row['total_return_usd']:,.2f})
  Win Rate:            {row['win_rate']:.1f}%
  Avg Win:             {row['avg_win']:.2f} pts
  Avg Loss:            {row['avg_loss']:.2f} pts
  Profit Factor:       {row['profit_factor']:.2f}
  Max Drawdown:        ${row['max_dd_usd']:,.2f} ({row['max_dd_pct']:.2f}%)
  Sharpe Ratio:        {row['sharpe']:.2f}
  Best Trade:          {row['best_trade']:.2f} pts
  Worst Trade:         {row['worst_trade']:.2f} pts
  Avg Trade:           {row['avg_trade']:.2f} pts
"""

valid = metrics_df[metrics_df['trades'] > 0]
if not valid.empty:
    report += f"""
{'='*70}
RANKINGS ( strategies with trades only)
{'='*70}
Best Win Rate:      {valid.loc[valid['win_rate'].idxmax(), 'strategy']} ({valid['win_rate'].max():.1f}%)
Best Profit Factor: {valid.loc[valid['profit_factor'].idxmax(), 'strategy']} ({valid['profit_factor'].max():.2f})
Best Sharpe Ratio:  {valid.loc[valid['sharpe'].idxmax(), 'strategy']} ({valid['sharpe'].max():.2f})
Best Total Return:  {valid.loc[valid['total_return_usd'].idxmax(), 'strategy']} (${valid['total_return_usd'].max():,.2f})
Lowest Drawdown:    {valid.loc[valid['max_dd_usd'].idxmin(), 'strategy']} (${valid['max_dd_usd'].min():,.2f})
"""

report += f"""
{'='*70}
IB BREAKOUT DIRECTION ANALYSIS
{'='*70}
Long:  {ib_dir_stats['long']['wins']}W / {ib_dir_stats['long']['losses']}L
Short: {ib_dir_stats['short']['wins']}W / {ib_dir_stats['short']['losses']}L

{'='*70}
IMPORTANT DISCLAIMERS
{'='*70}
1. BACKTEST on HISTORICAL data - NOT live trading
2. Past performance does NOT guarantee future results
3. Slippage and commissions NOT fully modeled
4. For EDUCATIONAL purposes only - not financial advice
5. Always paper trade before risking real capital
6. Verify prop firm compatibility before live trading

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""

print(report)

with open(f'{OUTPUT_DIR}/backtest_report_v2.txt', 'w') as f:
    f.write(report)
print(f"Report saved to: {OUTPUT_DIR}/backtest_report_v2.txt")

metrics_df.to_csv(f'{OUTPUT_DIR}/backtest_metrics_v2.csv', index=False)
print(f"Metrics saved to: {OUTPUT_DIR}/backtest_metrics_v2.csv")

for name, trades in strategies.items():
    if not trades.empty:
        fname = f'{OUTPUT_DIR}/trades_{name.lower().replace(" ", "_").replace("(", "").replace(")", "")}.csv'
        trades.to_csv(fname, index=False)
        print(f"Trades saved: {fname}")

print("\n" + "=" * 70)
print("BACKTEST COMPLETE!")
print("=" * 70)
