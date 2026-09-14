"""
ES Futures Backtest Runner
==========================
Execute this script to run the complete 8-month backtest optimization.

Usage:
    python run_backtest.py                    # Use synthetic data (for testing)
    python run_backtest.py --data path.csv    # Use real ES data
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Add script directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

OUTPUT_DIR = Path(r"C:\Users\dgran\AppData\Local\Temp\opencode\backtest_output")


def main():
    parser = argparse.ArgumentParser(description='ES Futures Backtest Optimization')
    parser.add_argument('--data', type=str, help='Path to ES 5-min data CSV')
    parser.add_argument('--synthetic', action='store_true', 
                        help='Use synthetic data for testing')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick test with reduced parameter grid')
    
    args = parser.parse_args()
    
    # Determine data source
    use_synthetic = args.synthetic or (args.data is None)
    
    if use_synthetic:
        print("\n" + "!"*35)
        print("!  USING SYNTHETIC DATA FOR FRAMEWORK TESTING")
        print("!  For real backtests, supply actual ES data with --data")
        print("!"*35)
    
    # Import and run
    from main_backtest import run_full_backtest, generate_backtest_report
    from prop_firm_deployer import PropFirmDeployer, save_deployment_plan
    
    # Run full backtest
    results = run_full_backtest(
        data_path=args.data,
        use_synthetic=use_synthetic
    )
    
    # Generate backtest report
    generate_backtest_report(results)
    
    # Generate prop firm deployment plan
    deployer = PropFirmDeployer(results)
    plan = deployer.generate_deployment_plan()
    save_deployment_plan(plan, str(OUTPUT_DIR))
    
    # Final summary
    print("\n" + "█"*70)
    print("█  BACKTEST OPTIMIZATION COMPLETE" + " "*37 + "█")
    print("█"*70)
    
    print(f"\nAll output saved to: {OUTPUT_DIR}")
    print(f"\nFiles generated:")
    print(f"   1. phase1_orb_optimization.csv    - 3,200 ORB parameter combinations")
    print(f"   2. phase2_strategy_results.csv    - 6 additional strategies")
    print(f"   3. phase3_portfolio_results.csv    - 4 portfolio combinations")
    print(f"   4. emotionless_strategy_rules.md   - Complete mechanical trading system")
    print(f"   5. live_trading_checklist.md       - Daily trading routine")
    print(f"   6. backtest_report.md              - Full backtest report")
    print(f"   7. prop_firm_deployment_plan.md    - Prop firm specific guidance")
    
    print(f"\nPython scripts available:")
    print(f"   - data_loader.py                  - Load ES data from various sources")
    print(f"   - orb_optimizer.py                - ORB parameter optimization")
    print(f"   - additional_strategies.py        - Strategies A-F implementation")
    print(f"   - portfolio_backtest.py           - Portfolio combination testing")
    print(f"   - main_backtest.py                - Master orchestrator")
    print(f"   - prop_firm_deployer.py           - Prop firm calculations")
    print(f"   - run_backtest.py                 - This script")
    
    print(f"\nNext Steps:")
    print(f"   1. Obtain real ES 5-min data (NinjaTrader/Tradovate export)")
    print(f"   2. Run: python run_backtest.py --data your_data.csv")
    print(f"   3. Paper trade for 2-4 weeks")
    print(f"   4. Deploy to prop firm with MES (micro)")
    
    print(f"\nIMPORTANT DISCLAIMERS:")
    print(f"   - Synthetic data used - not for actual trading decisions")
    print(f"   - Past performance does not guarantee future results")
    print(f"   - Trading futures involves substantial risk of loss")
    print(f"   - Always verify prop firm rules before deployment")
    print(f"   - This is for educational purposes only")


if __name__ == "__main__":
    main()
