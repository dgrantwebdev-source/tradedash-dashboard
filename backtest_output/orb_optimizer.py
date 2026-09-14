"""
Phase 1: Opening Range Breakout (ORB) Parameter Optimization
============================================================
Tests all combinations of ORB parameters on ES 5-minute data.
Target: Jan 1 - Aug 31, 2026
"""

import pandas as pd
import numpy as np
from itertools import product
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ORBParams:
    """ORB strategy parameters."""
    orb_duration_min: int       # 5, 10, 15, 30
    entry_type: str             # 'breakout' or 'breakout_retest'
    profit_target_mult: float   # 1.0, 1.5, 2.0, 2.5, 3.0
    stop_loss_mult: float       # 0.5, 0.75, 1.0, 'atr'
    session_filter: str         # 'all', 'monday', 'tue_fri', 'wed_fri', 'thu_fri'
    time_filter: str            # 'full', 'morning', 'afternoon', 'first_90'


@dataclass
class BacktestResult:
    """Results from a single backtest run."""
    params: ORBParams
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    max_consecutive_losses: int = 0
    trading_days: int = 0
    pnl_per_day: float = 0.0


class ORBOptimizer:
    """
    Optimize ORB parameters across all combinations.
    
    ORB Logic:
    1. Define opening range (first N minutes of session)
    2. Entry: Price breaks above ORB high (long) or below ORB low (short)
    3. Stop: Based on ORB range or ATR
    4. Target: Multiple of ORB range
    """
    
    POINT_VALUE = 50.0  # ES = $50/point
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        self.results: List[BacktestResult] = []
    
    def calculate_orb_levels(self, df: pd.DataFrame, 
                              duration_min: int) -> pd.DataFrame:
        """Calculate ORB high/low for each trading day."""
        df = df.copy()
        
        # Group by date and calculate ORB
        dates = df['date'].unique()
        
        for date in dates:
            day_mask = df['date'] == date
            day_data = df[day_mask]
            
            if len(day_data) == 0:
                continue
            
            # Find ORB bars (first N minutes of session)
            session_start = day_data['datetime'].iloc[0]
            orb_end = session_start + pd.Timedelta(minutes=duration_min)
            
            orb_mask = (day_data['datetime'] >= session_start) & \
                       (day_data['datetime'] < orb_end)
            
            orb_data = day_data[orb_mask]
            
            if len(orb_data) == 0:
                continue
            
            # ORB levels
            orb_high = orb_data['high'].max()
            orb_low = orb_data['low'].min()
            orb_range = orb_high - orb_low
            
            # Set ORB levels for all bars after ORB forms
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_high'] = orb_high
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_low'] = orb_low
            df.loc[day_mask & (df['datetime'] >= orb_end), 'orb_range'] = orb_range
        
        return df
    
    def run_backtest(self, df: pd.DataFrame, params: ORBParams) -> BacktestResult:
        """Run backtest for a single parameter set."""
        result = BacktestResult(params=params)
        
        # Apply filters
        filtered_df = self._apply_filters(df, params)
        
        if len(filtered_df) == 0:
            return result
        
        # Calculate ORB levels
        filtered_df = self.calculate_orb_levels(filtered_df, params.orb_duration_min)
        
        # Drop bars where ORB not yet formed
        valid_df = filtered_df.dropna(subset=['orb_high', 'orb_low', 'orb_range'])
        
        if len(valid_df) == 0:
            return result
        
        # Simulate trades
        trades = self._simulate_trades(valid_df, params)
        
        if len(trades) == 0:
            return result
        
        # Calculate metrics
        result = self._calculate_metrics(trades, result)
        
        return result
    
    def _apply_filters(self, df: pd.DataFrame, params: ORBParams) -> pd.DataFrame:
        """Apply session and time filters."""
        filtered = df.copy()
        
        # Session filter (day of week)
        dow = filtered['datetime'].dt.dayofweek
        
        if params.session_filter == 'monday':
            filtered = filtered[dow == 0]
        elif params.session_filter == 'tue_fri':
            filtered = filtered[dow >= 1]
        elif params.session_filter == 'wed_fri':
            filtered = filtered[dow >= 2]
        elif params.session_filter == 'thu_fri':
            filtered = filtered[dow >= 3]
        
        # Time filter
        time_col = filtered['datetime'].dt.time
        from datetime import time
        
        if params.time_filter == 'morning':
            filtered = filtered[time_col <= time(12, 0)]
        elif params.time_filter == 'afternoon':
            filtered = filtered[time_col >= time(12, 0)]
        elif params.time_filter == 'first_90':
            filtered = filtered[time_col <= time(11, 0)]
        
        return filtered
    
    def _simulate_trades(self, df: pd.DataFrame, 
                          params: ORBParams) -> List[Dict]:
        """Simulate ORB trades."""
        trades = []
        
        # Group by date to handle daily resets
        dates = df['date'].unique()
        
        for date in dates:
            day_data = df[df['date'] == date].copy()
            
            if len(day_data) == 0:
                continue
            
            # Find ORB formation end
            session_start = day_data['datetime'].iloc[0]
            orb_end = session_start + pd.Timedelta(minutes=params.orb_duration_min)
            
            # Get post-ORB data
            post_orb = day_data[day_data['datetime'] >= orb_end].copy()
            
            if len(post_orb) == 0:
                continue
            
            # Get ORB levels for this day
            orb_high = post_orb['orb_high'].iloc[0]
            orb_low = post_orb['orb_low'].iloc[0]
            orb_range = post_orb['orb_range'].iloc[0]
            
            if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(orb_range):
                continue
            
            if orb_range <= 0:
                continue
            
            # Initialize trade tracking
            in_trade = False
            trade_direction = None
            entry_price = 0
            stop_price = 0
            target_price = 0
            retest_pending = False
            
            for idx, row in post_orb.iterrows():
                bar_time = row['datetime'].time()
                
                # Check time stop (close by 3:50 PM)
                from datetime import time
                if bar_time >= time(15, 50):
                    if in_trade:
                        # Close position
                        exit_price = row['close']
                        pnl = self._calculate_pnl(entry_price, exit_price, 
                                                   trade_direction, params)
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'time_stop'
                        })
                        in_trade = False
                    continue
                
                if in_trade:
                    # Check stop loss
                    if trade_direction == 'long' and row['low'] <= stop_price:
                        exit_price = stop_price
                        pnl = self._calculate_pnl(entry_price, exit_price,
                                                   trade_direction, params)
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
                        continue
                    
                    if trade_direction == 'short' and row['high'] >= stop_price:
                        exit_price = stop_price
                        pnl = self._calculate_pnl(entry_price, exit_price,
                                                   trade_direction, params)
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
                        continue
                    
                    # Check take profit
                    if trade_direction == 'long' and row['high'] >= target_price:
                        exit_price = target_price
                        pnl = self._calculate_pnl(entry_price, exit_price,
                                                   trade_direction, params)
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'take_profit'
                        })
                        in_trade = False
                        continue
                    
                    if trade_direction == 'short' and row['low'] <= target_price:
                        exit_price = target_price
                        pnl = self._calculate_pnl(entry_price, exit_price,
                                                   trade_direction, params)
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': row['datetime'],
                            'direction': trade_direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'take_profit'
                        })
                        in_trade = False
                        continue
                
                else:
                    # No position - look for entry
                    if params.entry_type == 'breakout':
                        # Long breakout
                        if row['high'] > orb_high:
                            entry_price = orb_high
                            stop_price = self._calculate_stop(entry_price, 
                                                               orb_range, params)
                            target_price = self._calculate_target(entry_price,
                                                                   orb_range, params)
                            trade_direction = 'long'
                            entry_time = row['datetime']
                            in_trade = True
                        
                        # Short breakout
                        elif row['low'] < orb_low:
                            entry_price = orb_low
                            stop_price = self._calculate_stop(entry_price,
                                                               orb_range, params)
                            target_price = self._calculate_target(entry_price,
                                                                   orb_range, params)
                            trade_direction = 'short'
                            entry_time = row['datetime']
                            in_trade = True
                    
                    elif params.entry_type == 'breakout_retest':
                        # Wait for breakout, then retest
                        if not retest_pending:
                            if row['high'] > orb_high:
                                retest_pending = True
                                retest_direction = 'long'
                                retest_level = orb_high
                            elif row['low'] < orb_low:
                                retest_pending = True
                                retest_direction = 'short'
                                retest_level = orb_low
                        else:
                            # Check for retest
                            if retest_direction == 'long':
                                if row['low'] <= retest_level and row['close'] > retest_level:
                                    entry_price = retest_level
                                    stop_price = self._calculate_stop(entry_price,
                                                                       orb_range, params)
                                    target_price = self._calculate_target(entry_price,
                                                                           orb_range, params)
                                    trade_direction = 'long'
                                    entry_time = row['datetime']
                                    in_trade = True
                                    retest_pending = False
                            elif retest_direction == 'short':
                                if row['high'] >= retest_level and row['close'] < retest_level:
                                    entry_price = retest_level
                                    stop_price = self._calculate_stop(entry_price,
                                                                       orb_range, params)
                                    target_price = self._calculate_target(entry_price,
                                                                           orb_range, params)
                                    trade_direction = 'short'
                                    entry_time = row['datetime']
                                    in_trade = True
                                    retest_pending = False
        
        return trades
    
    def _calculate_stop(self, entry_price: float, 
                         orb_range: float, params: ORBParams) -> float:
        """Calculate stop loss price."""
        if params.stop_loss_mult == 'atr':
            # Use ATR-based stop (would need ATR column)
            # For now, use 1.5x orb range as proxy
            stop_distance = 1.5 * orb_range
        else:
            stop_distance = params.stop_loss_mult * orb_range
        
        return stop_distance
    
    def _calculate_target(self, entry_price: float,
                           orb_range: float, params: ORBParams) -> float:
        """Calculate take profit price."""
        return params.profit_target_mult * orb_range
    
    def _calculate_pnl(self, entry_price: float, exit_price: float,
                        direction: str, params: ORBParams) -> float:
        """Calculate P&L in dollars."""
        if direction == 'long':
            points = exit_price - entry_price
        else:
            points = entry_price - exit_price
        
        return points * self.POINT_VALUE
    
    def _calculate_metrics(self, trades: List[Dict], 
                            result: BacktestResult) -> BacktestResult:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return result
        
        pnls = [t['pnl'] for t in trades]
        
        result.total_trades = len(trades)
        result.winning_trades = sum(1 for p in pnls if p > 0)
        result.losing_trades = sum(1 for p in pnls if p <= 0)
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        result.total_pnl = sum(pnls)
        result.avg_pnl_per_trade = np.mean(pnls) if pnls else 0
        
        # Win/loss averages
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        result.avg_win = np.mean(wins) if wins else 0
        result.avg_loss = np.mean(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Expectancy
        result.expectancy = (result.win_rate * result.avg_win + 
                            (1 - result.win_rate) * result.avg_loss)
        
        # Drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        result.max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Sharpe Ratio (annualized, assuming 252 trading days)
        if len(pnls) > 1 and np.std(pnls) > 0:
            daily_returns = np.array(pnls)
            result.sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
        
        # Max consecutive losses
        max_consec = 0
        current_consec = 0
        for p in pnls:
            if p <= 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        result.max_consecutive_losses = max_consec
        
        # Trading days
        if trades:
            dates = set()
            for t in trades:
                if hasattr(t['entry_time'], 'date'):
                    dates.add(t['entry_time'].date())
            result.trading_days = len(dates)
            result.pnl_per_day = result.total_pnl / result.trading_days if result.trading_days > 0 else 0
        
        return result
    
    def optimize(self) -> pd.DataFrame:
        """
        Run optimization across all parameter combinations.
        
        Returns DataFrame of results sorted by Sharpe Ratio.
        """
        # Define parameter grid
        orb_durations = [5, 10, 15, 30]
        entry_types = ['breakout', 'breakout_retest']
        profit_targets = [1.0, 1.5, 2.0, 2.5, 3.0]
        stop_losses = [0.5, 0.75, 1.0, 'atr']
        session_filters = ['all', 'monday', 'tue_fri', 'wed_fri', 'thu_fri']
        time_filters = ['full', 'morning', 'afternoon', 'first_90']
        
        # Generate all combinations
        param_combinations = list(product(
            orb_durations, entry_types, profit_targets,
            stop_losses, session_filters, time_filters
        ))
        
        total_combos = len(param_combinations)
        print(f"\n{'='*60}")
        print(f"ORB OPTIMIZATION: Testing {total_combos} parameter combinations")
        print(f"{'='*60}\n")
        
        results = []
        
        for i, combo in enumerate(param_combinations):
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{total_combos} ({((i+1)/total_combos)*100:.1f}%)")
            
            params = ORBParams(
                orb_duration_min=combo[0],
                entry_type=combo[1],
                profit_target_mult=combo[2],
                stop_loss_mult=combo[3],
                session_filter=combo[4],
                time_filter=combo[5]
            )
            
            result = self.run_backtest(self.data, params)
            results.append(result)
        
        self.results = results
        
        # Convert to DataFrame
        results_df = self._results_to_dataframe(results)
        
        # Sort by Sharpe Ratio
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)
        
        return results_df
    
    def _results_to_dataframe(self, results: List[BacktestResult]) -> pd.DataFrame:
        """Convert results to DataFrame."""
        rows = []
        for r in results:
            rows.append({
                'orb_duration': r.params.orb_duration_min,
                'entry_type': r.params.entry_type,
                'profit_target': r.params.profit_target_mult,
                'stop_loss': r.params.stop_loss_mult,
                'session_filter': r.params.session_filter,
                'time_filter': r.params.time_filter,
                'total_trades': r.total_trades,
                'win_rate': r.win_rate,
                'total_pnl': r.total_pnl,
                'avg_pnl': r.avg_pnl_per_trade,
                'max_drawdown': r.max_drawdown,
                'sharpe_ratio': r.sharpe_ratio,
                'profit_factor': r.profit_factor,
                'expectancy': r.expectancy,
                'max_consecutive_losses': r.max_consecutive_losses,
                'trading_days': r.trading_days,
                'pnl_per_day': r.pnl_per_day
            })
        
        return pd.DataFrame(rows)
    
    def get_top_n(self, n: int = 5, 
                   sort_by: str = 'sharpe_ratio') -> pd.DataFrame:
        """Get top N parameter combinations."""
        if not self.results:
            return pd.DataFrame()
        
        results_df = self._results_to_dataframe(self.results)
        return results_df.sort_values(sort_by, ascending=False).head(n)
    
    def print_top_results(self, n: int = 5):
        """Print formatted top results."""
        top = self.get_top_n(n)
        
        print(f"\n{'='*80}")
        print(f"TOP {n} ORB PARAMETER COMBINATIONS (by Sharpe Ratio)")
        print(f"{'='*80}\n")
        
        for idx, row in top.iterrows():
            print(f"\n{'─'*60}")
            print(f"RANK #{top.index.get_loc(idx) + 1}")
            print(f"{'─'*60}")
            print(f"  ORB Duration:     {row['orb_duration']} minutes")
            print(f"  Entry Type:       {row['entry_type']}")
            print(f"  Profit Target:    {row['profit_target']}x ORB range")
            print(f"  Stop Loss:        {row['stop_loss']}x ORB range")
            print(f"  Session Filter:   {row['session_filter']}")
            print(f"  Time Filter:      {row['time_filter']}")
            print(f"\n  PERFORMANCE METRICS:")
            print(f"  {'─'*40}")
            print(f"  Total Trades:     {row['total_trades']}")
            print(f"  Win Rate:         {row['win_rate']*100:.1f}%")
            print(f"  Total P&L:        ${row['total_pnl']:,.2f}")
            print(f"  Avg P&L/Trade:    ${row['avg_pnl']:,.2f}")
            print(f"  Max Drawdown:     ${row['max_drawdown']:,.2f}")
            print(f"  Sharpe Ratio:     {row['sharpe_ratio']:.2f}")
            print(f"  Profit Factor:    {row['profit_factor']:.2f}")
            print(f"  Expectancy:       ${row['expectancy']:,.2f}")
            print(f"  Max Consec Loss:  {row['max_consecutive_losses']}")
            print(f"  Trading Days:     {row['trading_days']}")
            print(f"  P&L/Day:          ${row['pnl_per_day']:,.2f}")


if __name__ == "__main__":
    # Test with synthetic data
    from data_loader import load_es_data
    
    data = load_es_data(use_synthetic=True)
    optimizer = ORBOptimizer(data)
    
    # Run optimization (reduced for testing)
    results = optimizer.optimize()
    optimizer.print_top_results(5)

