"""
Phase 2: Additional Strategy Backtests
======================================
Strategies A-F for ES futures, Jan-Aug 2026.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import time
import warnings
warnings.filterwarnings('ignore')


POINT_VALUE = 50.0  # ES = $50/point


@dataclass
class StrategyResult:
    """Results from a strategy backtest."""
    strategy_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_losses: int = 0
    trading_days: int = 0
    pnl_per_day: float = 0.0
    long_trades: int = 0
    short_trades: int = 0


class StrategyBacktester:
    """Base class for strategy backtesting."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
    
    def _calculate_metrics(self, trades: List[Dict], 
                           result: StrategyResult) -> StrategyResult:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return result
        
        pnls = [t['pnl'] for t in trades]
        
        result.total_trades = len(trades)
        result.winning_trades = sum(1 for p in pnls if p > 0)
        result.losing_trades = sum(1 for p in pnls if p <= 0)
        result.win_rate = result.winning_trades / result.total_trades
        result.total_pnl = sum(pnls)
        result.avg_pnl_per_trade = np.mean(pnls)
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        result.avg_win = np.mean(wins) if wins else 0
        result.avg_loss = np.mean(losses) if losses else 0
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        result.expectancy = (result.win_rate * result.avg_win + 
                            (1 - result.win_rate) * result.avg_loss)
        
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        result.max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        if len(pnls) > 1 and np.std(pnls) > 0:
            result.sharpe_ratio = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)
        
        max_consec = 0
        current_consec = 0
        for p in pnls:
            if p <= 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        result.max_consecutive_losses = max_consec
        
        if trades:
            dates = set()
            for t in trades:
                if hasattr(t['entry_time'], 'date'):
                    dates.add(t['entry_time'].date())
            result.trading_days = len(dates)
            result.pnl_per_day = result.total_pnl / result.trading_days
        
        result.long_trades = sum(1 for t in trades if t.get('direction') == 'long')
        result.short_trades = sum(1 for t in trades if t.get('direction') == 'short')
        
        return result


class VWAPReversionStrategy(StrategyBacktester):
    """
    Strategy A: VWAP Reversion
    - Long when price < VWAP by 0.3%
    - Short when price > VWAP by 0.3%
    - Exit when price returns to VWAP
    - Session: NY only (9:30 AM - 4:00 PM)
    """
    
    def backtest(self, deviation_pct: float = 0.003) -> StrategyResult:
        result = StrategyResult(strategy_name="VWAP Reversion")
        
        if 'vwap' not in self.data.columns:
            self.data['vwap'] = self._calculate_vwap()
        
        trades = []
        in_trade = False
        trade_direction = None
        entry_price = 0
        entry_time = None
        
        for idx, row in self.data.iterrows():
            if in_trade:
                # Check exit: price returns to VWAP
                if trade_direction == 'long' and row['close'] >= row['vwap']:
                    exit_price = row['vwap']
                    pnl = (exit_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'vwap_return'
                    })
                    in_trade = False
                
                elif trade_direction == 'short' and row['close'] <= row['vwap']:
                    exit_price = row['vwap']
                    pnl = (entry_price - exit_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'vwap_return'
                    })
                    in_trade = False
            
            else:
                # Check entry conditions
                if pd.isna(row['vwap']) or row['vwap'] == 0:
                    continue
                
                deviation = (row['close'] - row['vwap']) / row['vwap']
                
                # Long: price below VWAP by threshold
                if deviation < -deviation_pct:
                    entry_price = row['close']
                    entry_time = row['datetime']
                    trade_direction = 'long'
                    in_trade = True
                
                # Short: price above VWAP by threshold
                elif deviation > deviation_pct:
                    entry_price = row['close']
                    entry_time = row['datetime']
                    trade_direction = 'short'
                    in_trade = True
        
        return self._calculate_metrics(trades, result)
    
    def _calculate_vwap(self) -> pd.Series:
        """Calculate VWAP."""
        df = self.data.copy()
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_vol'] = df['typical_price'] * df['volume']
        
        df['cum_tp_vol'] = df.groupby('date')['tp_vol'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        
        return df['cum_tp_vol'] / df['cum_vol']


class RSIDivergenceStrategy(StrategyBacktester):
    """
    Strategy B: RSI Divergence
    - Long: Price makes lower low but RSI makes higher low
    - Short: Price makes higher high but RSI makes lower high
    - Entry: Break of signal candle high/low
    - Stop: Below/above signal candle
    """
    
    def backtest(self, rsi_period: int = 14, 
                 lookback: int = 5) -> StrategyResult:
        result = StrategyResult(strategy_name="RSI Divergence")
        
        # Calculate RSI
        if 'rsi' not in self.data.columns:
            self.data['rsi'] = self._calculate_rsi(rsi_period)
        
        trades = []
        in_trade = False
        trade_direction = None
        entry_price = 0
        entry_time = None
        stop_price = 0
        
        prices = self.data['close'].values
        rsi_values = self.data['rsi'].values
        highs = self.data['high'].values
        lows = self.data['low'].values
        
        for i in range(lookback + rsi_period, len(self.data)):
            row = self.data.iloc[i]
            
            if in_trade:
                # Check stop loss
                if trade_direction == 'long' and row['low'] <= stop_price:
                    exit_price = stop_price
                    pnl = (exit_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
                
                elif trade_direction == 'short' and row['high'] >= stop_price:
                    exit_price = stop_price
                    pnl = (entry_price - exit_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
            
            else:
                # Look for divergence
                # Bullish divergence: price lower low, RSI higher low
                if (prices[i] < prices[i-lookback] and 
                    rsi_values[i] > rsi_values[i-lookback] and
                    not np.isnan(rsi_values[i])):
                    
                    # Entry on break of signal candle high
                    if row['high'] > highs[i-1]:
                        entry_price = highs[i-1]
                        stop_price = lows[i-1]
                        entry_time = row['datetime']
                        trade_direction = 'long'
                        in_trade = True
                
                # Bearish divergence: price higher high, RSI lower high
                elif (prices[i] > prices[i-lookback] and 
                      rsi_values[i] < rsi_values[i-lookback] and
                      not np.isnan(rsi_values[i])):
                    
                    # Entry on break of signal candle low
                    if row['low'] < lows[i-1]:
                        entry_price = lows[i-1]
                        stop_price = highs[i-1]
                        entry_time = row['datetime']
                        trade_direction = 'short'
                        in_trade = True
        
        return self._calculate_metrics(trades, result)
    
    def _calculate_rsi(self, period: int) -> pd.Series:
        """Calculate RSI."""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))


class SessionBreakdownStrategy(StrategyBacktester):
    """
    Strategy C: Session Breakdown (London vs NY)
    - Trade direction based on London session close vs open
    - If London up → Long at NY open
    - If London down → Short at NY open
    - Exit: End of NY session or 2% stop
    """
    
    def backtest(self, stop_pct: float = 0.02) -> StrategyResult:
        result = StrategyResult(strategy_name="Session Breakdown")
        
        trades = []
        dates = self.data['date'].unique()
        
        for date in dates:
            day_data = self.data[self.data['date'] == date].copy()
            
            if len(day_data) < 2:
                continue
            
            # Get NY session data (9:30 AM - 4:00 PM)
            ny_data = day_data[day_data['datetime'].dt.time >= time(9, 30)]
            
            if len(ny_data) < 2:
                continue
            
            # Determine London direction from previous price action
            # (In real trading, use actual London session data)
            # Here we use first few bars of NY as proxy
            first_bar = ny_data.iloc[0]
            
            # Use opening range vs previous close for direction
            if len(day_data) > 1:
                prev_close = day_data.iloc[0]['close']
            else:
                continue
            
            # London direction (simplified: compare current open to previous close)
            london_direction = 'up' if first_bar['open'] > prev_close else 'down'
            
            # Entry at NY open
            entry_price = first_bar['open']
            entry_time = first_bar['datetime']
            
            # Set stop
            stop_distance = entry_price * stop_pct
            
            if london_direction == 'up':
                # Long trade
                stop_price = entry_price - stop_distance
                # Find exit
                for idx, row in ny_data.iterrows():
                    if row['low'] <= stop_price:
                        exit_price = stop_price
                        pnl = (exit_price - entry_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': 'long',
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'stop_loss'
                        })
                        break
                else:
                    # Exit at session end
                    exit_price = ny_data.iloc[-1]['close']
                    pnl = (exit_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': ny_data.iloc[-1]['datetime'],
                        'direction': 'long',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'session_end'
                    })
            
            else:
                # Short trade
                stop_price = entry_price + stop_distance
                for idx, row in ny_data.iterrows():
                    if row['high'] >= stop_price:
                        exit_price = stop_price
                        pnl = (entry_price - exit_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': 'short',
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'stop_loss'
                        })
                        break
                else:
                    exit_price = ny_data.iloc[-1]['close']
                    pnl = (entry_price - exit_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': ny_data.iloc[-1]['datetime'],
                        'direction': 'short',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'exit_reason': 'session_end'
                    })
        
        return self._calculate_metrics(trades, result)


class PDHPDLBreakoutStrategy(StrategyBacktester):
    """
    Strategy D: Previous Day High/Low Breakout
    - Long if price breaks above PDH
    - Short if price breaks below PDL
    - Stop: Inside PDH/PDL range
    - Target: 1.5x range
    """
    
    def backtest(self, target_mult: float = 1.5) -> StrategyResult:
        result = StrategyResult(strategy_name="PDH/PDL Breakout")
        
        trades = []
        in_trade = False
        trade_direction = None
        entry_price = 0
        entry_time = None
        stop_price = 0
        target_price = 0
        
        for idx, row in self.data.iterrows():
            if in_trade:
                # Check stop
                if trade_direction == 'long' and row['low'] <= stop_price:
                    pnl = (stop_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': stop_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
                    continue
                
                if trade_direction == 'short' and row['high'] >= stop_price:
                    pnl = (entry_price - stop_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': stop_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
                    continue
                
                # Check target
                if trade_direction == 'long' and row['high'] >= target_price:
                    pnl = (target_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': target_price,
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    in_trade = False
                    continue
                
                if trade_direction == 'short' and row['low'] <= target_price:
                    pnl = (entry_price - target_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': target_price,
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    in_trade = False
                    continue
            
            else:
                # Check for entry
                if pd.isna(row.get('pdh')) or pd.isna(row.get('pdl')):
                    continue
                
                pdh = row['pdh']
                pdl = row['pdl']
                range_size = pdh - pdl
                
                if range_size <= 0:
                    continue
                
                # Long breakout above PDH
                if row['high'] > pdh:
                    entry_price = pdh
                    stop_price = pdh - (range_size * 0.5)  # Half range stop
                    target_price = pdh + (range_size * target_mult)
                    trade_direction = 'long'
                    entry_time = row['datetime']
                    in_trade = True
                
                # Short breakout below PDL
                elif row['low'] < pdl:
                    entry_price = pdl
                    stop_price = pdl + (range_size * 0.5)
                    target_price = pdl - (range_size * target_mult)
                    trade_direction = 'short'
                    entry_time = row['datetime']
                    in_trade = True
        
        return self._calculate_metrics(trades, result)


class ORBVWAPConfluenceStrategy(StrategyBacktester):
    """
    Strategy E: ORB + VWAP Confluence
    - Only take ORB breakout if:
      - Long AND price above VWAP
      - Short AND price below VWAP
    """
    
    def backtest(self, orb_duration: int = 15) -> StrategyResult:
        result = StrategyResult(strategy_name="ORB + VWAP Confluence")
        
        # Calculate VWAP
        if 'vwap' not in self.data.columns:
            self.data['vwap'] = self._calculate_vwap()
        
        # Calculate ORB levels
        self.data = self._calculate_orb_levels(orb_duration)
        
        trades = []
        in_trade = False
        trade_direction = None
        entry_price = 0
        entry_time = None
        stop_price = 0
        target_price = 0
        
        for idx, row in self.data.iterrows():
            if pd.isna(row.get('orb_high')) or pd.isna(row.get('vwap')):
                continue
            
            if in_trade:
                # Check stop/target
                if trade_direction == 'long':
                    if row['low'] <= stop_price:
                        pnl = (stop_price - entry_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': stop_price,
                            'pnl': pnl,
                            'exit_reason': 'stop_loss'
                        })
                        in_trade = False
                    elif row['high'] >= target_price:
                        pnl = (target_price - entry_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': target_price,
                            'pnl': pnl,
                            'exit_reason': 'take_profit'
                        })
                        in_trade = False
                
                elif trade_direction == 'short':
                    if row['high'] >= stop_price:
                        pnl = (entry_price - stop_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': stop_price,
                            'pnl': pnl,
                            'exit_reason': 'stop_loss'
                        })
                        in_trade = False
                    elif row['low'] <= target_price:
                        pnl = (entry_price - target_price) * POINT_VALUE
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': target_price,
                            'pnl': pnl,
                            'exit_reason': 'take_profit'
                        })
                        in_trade = False
            
            else:
                orb_range = row['orb_range']
                if orb_range <= 0:
                    continue
                
                # Long: Break ORB high AND price above VWAP
                if row['high'] > row['orb_high'] and row['close'] > row['vwap']:
                    entry_price = row['orb_high']
                    stop_price = entry_price - orb_range
                    target_price = entry_price + (orb_range * 1.5)
                    trade_direction = 'long'
                    entry_time = row['datetime']
                    in_trade = True
                
                # Short: Break ORB low AND price below VWAP
                elif row['low'] < row['orb_low'] and row['close'] < row['vwap']:
                    entry_price = row['orb_low']
                    stop_price = entry_price + orb_range
                    target_price = entry_price - (orb_range * 1.5)
                    trade_direction = 'short'
                    entry_time = row['datetime']
                    in_trade = True
        
        return self._calculate_metrics(trades, result)
    
    def _calculate_vwap(self) -> pd.Series:
        df = self.data.copy()
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_vol'] = df['typical_price'] * df['volume']
        df['cum_tp_vol'] = df.groupby('date')['tp_vol'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        return df['cum_tp_vol'] / df['cum_vol']
    
    def _calculate_orb_levels(self, duration_min: int) -> pd.DataFrame:
        df = self.data.copy()
        dates = df['date'].unique()
        
        for date in dates:
            day_mask = df['date'] == date
            day_data = df[day_mask]
            
            if len(day_data) == 0:
                continue
            
            session_start = day_data['datetime'].iloc[0]
            orb_end = session_start + pd.Timedelta(minutes=duration_min)
            
            orb_mask = (day_data['datetime'] >= session_start) & \
                       (day_data['datetime'] < orb_end)
            orb_data = day_data[orb_mask]
            
            if len(orb_data) == 0:
                continue
            
            orb_high = orb_data['high'].max()
            orb_low = orb_data['low'].min()
            orb_range = orb_high - orb_low
            
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_high'] = orb_high
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_low'] = orb_low
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_range'] = orb_range
        
        return df


class EMATrendPullbackStrategy(StrategyBacktester):
    """
    Strategy F: EMA Trend + Pullback
    - Trend: 9 EMA > 21 EMA > 50 EMA (long), reverse for short
    - Entry: Pullback to 21 EMA
    - Stop: Below 50 EMA
    - Target: 2x risk
    """
    
    def backtest(self) -> StrategyResult:
        result = StrategyResult(strategy_name="EMA Trend + Pullback")
        
        # Ensure EMAs are calculated
        if 'ema_9' not in self.data.columns:
            self.data['ema_9'] = self.data['close'].ewm(span=9, adjust=False).mean()
            self.data['ema_21'] = self.data['close'].ewm(span=21, adjust=False).mean()
            self.data['ema_50'] = self.data['close'].ewm(span=50, adjust=False).mean()
        
        trades = []
        in_trade = False
        trade_direction = None
        entry_price = 0
        entry_time = None
        stop_price = 0
        target_price = 0
        
        for idx, row in self.data.iterrows():
            if pd.isna(row['ema_50']):
                continue
            
            ema_9 = row['ema_9']
            ema_21 = row['ema_21']
            ema_50 = row['ema_50']
            
            if in_trade:
                # Check stop
                if trade_direction == 'long' and row['low'] <= stop_price:
                    pnl = (stop_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': stop_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
                    continue
                
                if trade_direction == 'short' and row['high'] >= stop_price:
                    pnl = (entry_price - stop_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': stop_price,
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    in_trade = False
                    continue
                
                # Check target
                if trade_direction == 'long' and row['high'] >= target_price:
                    pnl = (target_price - entry_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': target_price,
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    in_trade = False
                    continue
                
                if trade_direction == 'short' and row['low'] <= target_price:
                    pnl = (entry_price - target_price) * POINT_VALUE
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': row['datetime'],
                        'direction': trade_direction,
                        'entry_price': entry_price,
                        'exit_price': target_price,
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    in_trade = False
                    continue
            
            else:
                # Check for trend + pullback setup
                long_trend = ema_9 > ema_21 > ema_50
                short_trend = ema_9 < ema_21 < ema_50
                
                if long_trend:
                    # Look for pullback to 21 EMA
                    if row['low'] <= ema_21 and row['close'] > ema_21:
                        entry_price = row['close']
                        stop_price = ema_50
                        risk = entry_price - stop_price
                        target_price = entry_price + (risk * 2)
                        trade_direction = 'long'
                        entry_time = row['datetime']
                        in_trade = True
                
                elif short_trend:
                    # Look for pullback to 21 EMA
                    if row['high'] >= ema_21 and row['close'] < ema_21:
                        entry_price = row['close']
                        stop_price = ema_50
                        risk = stop_price - entry_price
                        target_price = entry_price - (risk * 2)
                        trade_direction = 'short'
                        entry_time = row['datetime']
                        in_trade = True
        
        return self._calculate_metrics(trades, result)


def run_all_strategies(data: pd.DataFrame) -> Dict[str, StrategyResult]:
    """Run all strategies and return results."""
    print("\n" + "="*60)
    print("PHASE 2: ADDITIONAL STRATEGY BACKTESTS")
    print("="*60)
    
    results = {}
    
    # Strategy A: VWAP Reversion
    print("\n[1/6] Running VWAP Reversion...")
    strat = VWAPReversionStrategy(data)
    results['VWAP Reversion'] = strat.backtest()
    
    # Strategy B: RSI Divergence
    print("[2/6] Running RSI Divergence...")
    strat = RSIDivergenceStrategy(data)
    results['RSI Divergence'] = strat.backtest()
    
    # Strategy C: Session Breakdown
    print("[3/6] Running Session Breakdown...")
    strat = SessionBreakdownStrategy(data)
    results['Session Breakdown'] = strat.backtest()
    
    # Strategy D: PDH/PDL Breakout
    print("[4/6] Running PDH/PDL Breakout...")
    strat = PDHPDLBreakoutStrategy(data)
    results['PDH/PDL Breakout'] = strat.backtest()
    
    # Strategy E: ORB + VWAP Confluence
    print("[5/6] Running ORB + VWAP Confluence...")
    strat = ORBVWAPConfluenceStrategy(data)
    results['ORB + VWAP Confluence'] = strat.backtest()
    
    # Strategy F: EMA Trend + Pullback
    print("[6/6] Running EMA Trend + Pullback...")
    strat = EMATrendPullbackStrategy(data)
    results['EMA Trend + Pullback'] = strat.backtest()
    
    return results


def print_strategy_results(results: Dict[str, StrategyResult]):
    """Print formatted strategy results."""
    print(f"\n{'='*80}")
    print("STRATEGY BACKTEST RESULTS (Jan-Aug 2026)")
    print(f"{'='*80}\n")
    
    for name, result in results.items():
        print(f"\n{'-'*60}")
        print(f"STRATEGY: {result.strategy_name}")
        print(f"{'-'*60}")
        print(f"  Total Trades:      {result.total_trades}")
        print(f"  Win Rate:          {result.win_rate*100:.1f}%")
        print(f"  Total P&L:         ${result.total_pnl:,.2f}")
        print(f"  Avg P&L/Trade:     ${result.avg_pnl_per_trade:,.2f}")
        print(f"  Max Drawdown:      ${result.max_drawdown:,.2f}")
        print(f"  Sharpe Ratio:      {result.sharpe_ratio:.2f}")
        print(f"  Profit Factor:     {result.profit_factor:.2f}")
        print(f"  Expectancy:        ${result.expectancy:,.2f}")
        print(f"  Avg Win:           ${result.avg_win:,.2f}")
        print(f"  Avg Loss:          ${result.avg_loss:,.2f}")
        print(f"  Max Consec Loss:   {result.max_consecutive_losses}")
        print(f"  Long Trades:       {result.long_trades}")
        print(f"  Short Trades:      {result.short_trades}")
        print(f"  Trading Days:      {result.trading_days}")
        print(f"  P&L/Day:           ${result.pnl_per_day:,.2f}")


if __name__ == "__main__":
    from data_loader import load_es_data
    
    data = load_es_data(use_synthetic=True)
    results = run_all_strategies(data)
    print_strategy_results(results)


