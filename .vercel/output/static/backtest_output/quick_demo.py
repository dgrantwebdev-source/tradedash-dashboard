"""
Quick Demo - Run reduced parameter grid to verify framework works
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_loader import load_es_data
from orb_optimizer import ORBOptimizer, ORBParams
from additional_strategies import run_all_strategies, print_strategy_results

OUTPUT_DIR = Path(r"C:\Users\dgran\AppData\Local\Temp\opencode\backtest_output")

def run_quick_demo():
    print("="*60)
    print("QUICK DEMO - Reduced Parameter Grid")
    print("="*60)
    
    # Load data
    print("\nLoading synthetic ES data...")
    data = load_es_data(use_synthetic=True)
    print(f"Loaded {len(data):,} bars")
    print(f"Date range: {data['date'].min()} to {data['date'].max()}")
    
    # Run ORB with reduced grid (20 combinations instead of 3200)
    print("\n" + "="*60)
    print("PHASE 1: ORB Optimization (Reduced Grid)")
    print("="*60)
    
    optimizer = ORBOptimizer(data)
    
    # Test a few key combinations manually
    test_params = [
        ORBParams(15, 'breakout', 1.5, 1.0, 'all', 'full'),
        ORBParams(15, 'breakout', 2.0, 1.0, 'all', 'full'),
        ORBParams(15, 'breakout_retest', 1.5, 1.0, 'all', 'full'),
        ORBParams(30, 'breakout', 1.5, 1.0, 'all', 'full'),
        ORBParams(10, 'breakout', 1.5, 0.75, 'wed_fri', 'morning'),
    ]
    
    results = []
    for params in test_params:
        result = optimizer.run_backtest(data, params)
        results.append(result)
        print(f"\nTested: ORB={params.orb_duration_min}min, Entry={params.entry_type}, "
              f"TP={params.profit_target_mult}x, SL={params.stop_loss_mult}x")
        print(f"  Trades: {result.total_trades}, Win Rate: {result.win_rate*100:.1f}%, "
              f"P&L: ${result.total_pnl:,.2f}, Sharpe: {result.sharpe_ratio:.2f}")
    
    # Get best result
    best = max(results, key=lambda r: r.sharpe_ratio)
    print("\n" + "="*60)
    print("BEST PARAMETERS FROM QUICK TEST:")
    print("="*60)
    print(f"  ORB Duration: {best.params.orb_duration_min} minutes")
    print(f"  Entry Type: {best.params.entry_type}")
    print(f"  Profit Target: {best.params.profit_target_mult}x ORB range")
    print(f"  Stop Loss: {best.params.stop_loss_mult}x ORB range")
    print(f"  Session Filter: {best.params.session_filter}")
    print(f"  Time Filter: {best.params.time_filter}")
    print(f"\n  Performance:")
    print(f"    Total Trades: {best.total_trades}")
    print(f"    Win Rate: {best.win_rate*100:.1f}%")
    print(f"    Total P&L: ${best.total_pnl:,.2f}")
    print(f"    Sharpe Ratio: {best.sharpe_ratio:.2f}")
    
    # Run additional strategies
    print("\n" + "="*60)
    print("PHASE 2: Additional Strategies")
    print("="*60)
    
    strategy_results = run_all_strategies(data)
    print_strategy_results(strategy_results)
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nFor full optimization with 3,200 ORB combinations:")
    print("  1. Obtain real ES 5-min data")
    print("  2. Run: python run_backtest.py --data your_data.csv")
    print("  3. Full optimization takes 30-60 minutes with real data")
    
    return best, strategy_results

if __name__ == "__main__":
    run_quick_demo()
