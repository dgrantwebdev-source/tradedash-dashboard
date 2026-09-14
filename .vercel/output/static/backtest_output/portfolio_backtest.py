"""
Phase 3: Portfolio Combinations
================================
Multi-strategy portfolio backtesting with correlation analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import time
import warnings
warnings.filterwarnings('ignore')


POINT_VALUE = 50.0


@dataclass
class PortfolioResult:
    """Results from a portfolio backtest."""
    portfolio_name: str
    strategies: Dict[str, float]  # strategy_name: weight
    total_pnl: float = 0.0
    daily_returns: List[float] = None
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_daily_return: float = 0.0
    volatility: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    information_ratio: float = 0.0
    
    def __post_init__(self):
        if self.daily_returns is None:
            self.daily_returns = []


class PortfolioBacktester:
    """
    Backtest portfolio combinations of strategies.
    Uses equal-weighted allocation within portfolio constraints.
    """
    
    def __init__(self, data: pd.DataFrame, 
                 strategy_results: Dict[str, pd.DataFrame]):
        """
        Args:
            data: OHLCV data with indicators
            strategy_results: Dict of strategy_name -> daily P&L Series
        """
        self.data = data
        self.strategy_results = strategy_results
    
    def backtest_portfolio(self, name: str,
                           allocations: Dict[str, float]) -> PortfolioResult:
        """
        Backtest a portfolio with given allocations.
        
        Args:
            name: Portfolio name
            allocations: Dict of strategy_name -> weight (0.0 to 1.0)
        """
        result = PortfolioResult(
            portfolio_name=name,
            strategies=allocations
        )
        
        # Get daily returns for each strategy
        daily_returns = {}
        for strat_name, weight in allocations.items():
            if strat_name in self.strategy_results:
                daily_returns[strat_name] = self.strategy_results[strat_name] * weight
        
        if not daily_returns:
            return result
        
        # Combine daily returns
        returns_df = pd.DataFrame(daily_returns)
        portfolio_daily = returns_df.sum(axis=1)
        
        result.daily_returns = portfolio_daily.tolist()
        result.total_pnl = portfolio_daily.sum()
        result.total_trades = len(portfolio_daily)
        
        # Calculate metrics
        if len(portfolio_daily) > 1:
            result.avg_daily_return = portfolio_daily.mean()
            result.volatility = portfolio_daily.std()
            
            if result.volatility > 0:
                result.sharpe_ratio = (result.avg_daily_return / result.volatility) * np.sqrt(252)
            
            # Sortino ratio (downside deviation)
            downside_returns = portfolio_daily[portfolio_daily < 0]
            if len(downside_returns) > 0:
                downside_std = downside_returns.std()
                if downside_std > 0:
                    result.sortino_ratio = (result.avg_daily_return / downside_std) * np.sqrt(252)
            
            # Max drawdown
            cumulative = np.cumsum(portfolio_daily)
            peak = np.maximum.accumulate(cumulative)
            drawdown = peak - cumulative
            result.max_drawdown = np.max(drawdown)
            
            # Calmar ratio
            if result.max_drawdown > 0:
                result.calmar_ratio = result.total_pnl / result.max_drawdown
            
            # Win rate
            result.win_rate = (portfolio_daily > 0).sum() / len(portfolio_daily)
            
            # Profit factor
            gross_profit = portfolio_daily[portfolio_daily > 0].sum()
            gross_loss = abs(portfolio_daily[portfolio_daily < 0].sum())
            result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return result


class StrategyTracker:
    """
    Track individual strategy P&L across all strategies.
    Used to build portfolio combinations.
    """
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.strategy_daily_pnl = {}
    
    def run_orb_strategy(self, params: Dict) -> pd.Series:
        """Run ORB strategy and return daily P&L."""
        from orb_optimizer import ORBOptimizer, ORBParams
        
        orb_params = ORBParams(
            orb_duration_min=params.get('orb_duration', 15),
            entry_type=params.get('entry_type', 'breakout'),
            profit_target_mult=params.get('profit_target', 1.5),
            stop_loss_mult=params.get('stop_loss', 1.0),
            session_filter=params.get('session_filter', 'all'),
            time_filter=params.get('time_filter', 'full')
        )
        
        optimizer = ORBOptimizer(self.data)
        result = optimizer.run_backtest(self.data, orb_params)
        
        # Convert to daily P&L series
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_vwap_reversion(self) -> pd.Series:
        """Run VWAP Reversion and return daily P&L."""
        from additional_strategies import VWAPReversionStrategy
        
        strat = VWAPReversionStrategy(self.data)
        result = strat.backtest()
        
        # Convert to daily P&L
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_rsi_divergence(self) -> pd.Series:
        """Run RSI Divergence and return daily P&L."""
        from additional_strategies import RSIDivergenceStrategy
        
        strat = RSIDivergenceStrategy(self.data)
        result = strat.backtest()
        
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_session_breakdown(self) -> pd.Series:
        """Run Session Breakdown and return daily P&L."""
        from additional_strategies import SessionBreakdownStrategy
        
        strat = SessionBreakdownStrategy(self.data)
        result = strat.backtest()
        
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_pdh_pdl_breakout(self) -> pd.Series:
        """Run PDH/PDL Breakout and return daily P&L."""
        from additional_strategies import PDHPDLBreakoutStrategy
        
        strat = PDHPDLBreakoutStrategy(self.data)
        result = strat.backtest()
        
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_ema_trend_pullback(self) -> pd.Series:
        """Run EMA Trend + Pullback and return daily P&L."""
        from additional_strategies import EMATrendPullbackStrategy
        
        strat = EMATrendPullbackStrategy(self.data)
        result = strat.backtest()
        
        daily_pnl = pd.Series(dtype=float)
        if hasattr(result, 'trades') and result.trades:
            for trade in result.trades:
                date = trade['entry_time'].date()
                daily_pnl[date] = daily_pnl.get(date, 0) + trade['pnl']
        
        return daily_pnl
    
    def run_gap_fill(self) -> pd.Series:
        """Run Gap Fill strategy (simplified) and return daily P&L."""
        daily_pnl = pd.Series(dtype=float)
        
        # Simplified gap fill logic
        dates = self.data['date'].unique()
        
        for i in range(1, len(dates)):
            prev_day = self.data[self.data['date'] == dates[i-1]]
            curr_day = self.data[self.data['date'] == dates[i]]
            
            if len(prev_day) == 0 or len(curr_day) == 0:
                continue
            
            prev_close = prev_day.iloc[-1]['close']
            curr_open = curr_day.iloc[0]['open']
            
            gap = curr_open - prev_close
            
            if abs(gap) < 5:  # Minimum gap threshold
                continue
            
            # Trade to fill gap
            target = prev_close
            stop = curr_open + (gap * 0.5) if gap < 0 else curr_open - (gap * 0.5)
            
            # Simplified: assume gap fills 60% of the time
            if np.random.random() < 0.6:
                pnl = abs(gap) * POINT_VALUE * 0.5  # Partial fill
            else:
                pnl = -abs(gap * 0.3) * POINT_VALUE
            
            date = dates[i]
            daily_pnl[date] = daily_pnl.get(date, 0) + pnl
        
        return daily_pnl
    
    def run_event_driven(self) -> pd.Series:
        """Run Event-Driven strategy (simplified) and return daily P&L."""
        daily_pnl = pd.Series(dtype=float)
        
        # Simplified event-driven logic
        dates = self.data['date'].unique()
        
        for date in dates:
            day_data = self.data[self.data['date'] == date]
            
            if len(day_data) < 10:
                continue
            
            # Look for large moves (simulating event reaction)
            first_30 = day_data.head(6)  # First 30 min
            price_range = first_30['high'].max() - first_30['low'].min()
            
            if price_range > 20:  # Large range day
                # Trend continuation
                direction = 1 if day_data.iloc[6]['close'] > day_data.iloc[0]['open'] else -1
                entry = day_data.iloc[6]['close']
                
                # Target 50% of morning range
                target_move = price_range * 0.5
                pnl = direction * target_move * POINT_VALUE * 0.3  # Partial capture
                
                daily_pnl[date] = daily_pnl.get(date, 0) + pnl
        
        return daily_pnl


def run_portfolio_backtests(data: pd.DataFrame) -> Dict[str, PortfolioResult]:
    """Run all portfolio backtests."""
    print("\n" + "="*60)
    print("PHASE 3: PORTFOLIO BACKTESTS")
    print("="*60)
    
    # First, get individual strategy daily P&L
    tracker = StrategyTracker(data)
    
    print("\nCalculating individual strategy P&L...")
    
    # Run all strategies
    strategy_daily = {}
    
    # ORB (using best params from Phase 1 - placeholder)
    strategy_daily['ORB'] = tracker.run_orb_strategy({
        'orb_duration': 15,
        'entry_type': 'breakout',
        'profit_target': 1.5,
        'stop_loss': 1.0,
        'session_filter': 'all',
        'time_filter': 'full'
    })
    
    strategy_daily['VWAP Reversion'] = tracker.run_vwap_reversion()
    strategy_daily['RSI Divergence'] = tracker.run_rsi_divergence()
    strategy_daily['Session Breakdown'] = tracker.run_session_breakdown()
    strategy_daily['PDH/PDL Breakout'] = tracker.run_pdh_pdl_breakout()
    strategy_daily['EMA Trend + Pullback'] = tracker.run_ema_trend_pullback()
    strategy_daily['Gap Fill'] = tracker.run_gap_fill()
    strategy_daily['Event-Driven'] = tracker.run_event_driven()
    
    # Create backtester
    backtester = PortfolioBacktester(data, strategy_daily)
    
    # Define portfolios
    portfolios = {
        'Conservative': {
            'ORB': 0.50,
            'Gap Fill': 0.30,
            'PDH/PDL Breakout': 0.20
        },
        'Aggressive': {
            'Event-Driven': 0.40,
            'ORB': 0.30,
            'Session Breakdown': 0.30
        },
        'Diversified': {
            'ORB': 0.30,
            'VWAP Reversion': 0.25,
            'EMA Trend + Pullback': 0.25,
            'PDH/PDL Breakout': 0.20
        },
        'Emotionless Robot': {
            'ORB': 0.20,
            'VWAP Reversion': 0.15,
            'RSI Divergence': 0.15,
            'Session Breakdown': 0.10,
            'PDH/PDL Breakout': 0.15,
            'EMA Trend + Pullback': 0.15,
            'Gap Fill': 0.05,
            'Event-Driven': 0.05
        }
    }
    
    results = {}
    
    for name, allocations in portfolios.items():
        print(f"\nBacktesting {name} portfolio...")
        results[name] = backtester.backtest_portfolio(name, allocations)
    
    return results


def print_portfolio_results(results: Dict[str, PortfolioResult]):
    """Print formatted portfolio results."""
    print(f"\n{'='*80}")
    print("PORTFOLIO BACKTEST RESULTS")
    print(f"{'='*80}\n")
    
    for name, result in results.items():
        print(f"\n{'─'*60}")
        print(f"PORTFOLIO: {result.portfolio_name}")
        print(f"{'─'*60}")
        
        print(f"\n  ALLOCATIONS:")
        for strat, weight in result.strategies.items():
            print(f"    {strat}: {weight*100:.0f}%")
        
        print(f"\n  PERFORMANCE METRICS:")
        print(f"  {'─'*40}")
        print(f"  Total P&L:         ${result.total_pnl:,.2f}")
        print(f"  Sharpe Ratio:      {result.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio:     {result.sortino_ratio:.2f}")
        print(f"  Calmar Ratio:      {result.calmar_ratio:.2f}")
        print(f"  Max Drawdown:      ${result.max_drawdown:,.2f}")
        print(f"  Win Rate:          {result.win_rate*100:.1f}%")
        print(f"  Profit Factor:     {result.profit_factor:.2f}")
        print(f"  Avg Daily Return:  ${result.avg_daily_return:,.2f}")
        print(f"  Daily Volatility:  ${result.volatility:,.2f}")
        print(f"  Annual Volatility: ${result.volatility * np.sqrt(252):,.2f}")


def calculate_correlation_matrix(data: pd.DataFrame, 
                                  strategy_daily: Dict[str, pd.Series]) -> pd.DataFrame:
    """Calculate correlation matrix between strategies."""
    returns_df = pd.DataFrame(strategy_daily)
    return returns_df.corr()


if __name__ == "__main__":
    from data_loader import load_es_data
    
    data = load_es_data(use_synthetic=True)
    results = run_portfolio_backtests(data)
    print_portfolio_results(results)

