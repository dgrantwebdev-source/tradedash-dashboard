"""
Master Backtest Orchestrator
============================
Coordinates all phases and generates final output.
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_es_data, ESDataLoader
from orb_optimizer import ORBOptimizer
from additional_strategies import run_all_strategies, print_strategy_results
from portfolio_backtest import run_portfolio_backtests, print_portfolio_results


OUTPUT_DIR = Path(r"C:\Users\dgran\AppData\Local\Temp\opencode\backtest_output")


def run_full_backtest(data_path: str = None, 
                      use_synthetic: bool = True) -> dict:
    """
    Run complete 8-month backtest optimization.
    
    Returns dict with all results.
    """
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#   ES FUTURES BACKTEST OPTIMIZATION - JAN TO AUG 2026" + " "*17 + "#")
    print("#" + " "*68 + "#")
    print("#"*70)
    
    all_results = {}
    
    # ===============================================================
    # LOAD DATA
    # ===============================================================
    print("\n" + "="*70)
    print("LOADING ES FUTURES DATA")
    print("="*70)
    
    data = load_es_data(data_path, use_synthetic=use_synthetic)
    print(f"\n[OK] Loaded {len(data):,} bars")
    print(f"[OK] Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"[OK] Price range: ${data['low'].min():.2f} to ${data['high'].max():.2f}")
    print(f"[OK] Trading days: {data['date'].nunique()}")
    
    # ===============================================================
    # PHASE 1: ORB OPTIMIZATION
    # ===============================================================
    print("\n" + "#"*70)
    print("#  PHASE 1: ORB PARAMETER OPTIMIZATION" + " "*30 + "#")
    print("#"*70)
    
    optimizer = ORBOptimizer(data)
    orb_results = optimizer.optimize()
    optimizer.print_top_results(5)
    
    all_results['phase1_orb'] = orb_results
    all_results['phase1_top5'] = optimizer.get_top_n(5).to_dict('records')
    
    # Save ORB results
    orb_results.to_csv(OUTPUT_DIR / "phase1_orb_optimization.csv", index=False)
    print(f"\n[OK] Saved ORB results to phase1_orb_optimization.csv")
    
    # ===============================================================
    # PHASE 2: ADDITIONAL STRATEGIES
    # ===============================================================
    print("\n" + "#"*70)
    print("#  PHASE 2: ADDITIONAL STRATEGY BACKTESTS" + " "*28 + "#")
    print("#"*70)
    
    strategy_results = run_all_strategies(data)
    print_strategy_results(strategy_results)
    
    all_results['phase2_strategies'] = strategy_results
    
    # Save strategy results
    strategy_df = pd.DataFrame([
        {
            'strategy': r.strategy_name,
            'total_trades': r.total_trades,
            'win_rate': r.win_rate,
            'total_pnl': r.total_pnl,
            'avg_pnl': r.avg_pnl_per_trade,
            'max_drawdown': r.max_drawdown,
            'sharpe_ratio': r.sharpe_ratio,
            'profit_factor': r.profit_factor,
            'expectancy': r.expectancy
        }
        for r in strategy_results.values()
    ])
    strategy_df.to_csv(OUTPUT_DIR / "phase2_strategy_results.csv", index=False)
    print(f"\n[OK] Saved strategy results to phase2_strategy_results.csv")
    
    # ===============================================================
    # PHASE 3: PORTFOLIO COMBINATIONS
    # ===============================================================
    print("\n" + "#"*70)
    print("#  PHASE 3: PORTFOLIO COMBINATIONS" + " "*36 + "#")
    print("#"*70)
    
    portfolio_results = run_portfolio_backtests(data)
    print_portfolio_results(portfolio_results)
    
    all_results['phase3_portfolios'] = portfolio_results
    
    # Save portfolio results
    portfolio_df = pd.DataFrame([
        {
            'portfolio': r.portfolio_name,
            'total_pnl': r.total_pnl,
            'sharpe_ratio': r.sharpe_ratio,
            'sortino_ratio': r.sortino_ratio,
            'max_drawdown': r.max_drawdown,
            'win_rate': r.win_rate,
            'profit_factor': r.profit_factor
        }
        for r in portfolio_results.values()
    ])
    portfolio_df.to_csv(OUTPUT_DIR / "phase3_portfolio_results.csv", index=False)
    print(f"\n[OK] Saved portfolio results to phase3_portfolio_results.csv")
    
    # ===============================================================
    # PHASE 4: EMOTIONLESS STRATEGY RULES
    # ===============================================================
    print("\n" + "#"*70)
    print("#  PHASE 4: EMOTIONLESS STRATEGY RULES" + " "*30 + "#")
    print("#"*70)
    
    rules = generate_emotionless_rules(all_results)
    save_emotionless_rules(rules)
    
    # ===============================================================
    # PHASE 5: LIVE TRADING CHECKLIST
    # ===============================================================
    print("\n" + "#"*70)
    print("#  PHASE 5: LIVE TRADING CHECKLIST" + " "*36 + "#")
    print("#"*70)
    
    checklist = generate_live_checklist()
    save_live_checklist(checklist)
    
    # ===============================================================
    # SUMMARY
    # ===============================================================
    print("\n" + "#"*70)
    print("#  BACKTEST COMPLETE - SUMMARY" + " "*40 + "#")
    print("#"*70)
    
    print(f"\n[OK] All output saved to: {OUTPUT_DIR}")
    print(f"\nFiles generated:")
    print(f"  • phase1_orb_optimization.csv")
    print(f"  • phase2_strategy_results.csv")
    print(f"  • phase3_portfolio_results.csv")
    print(f"  • emotionless_strategy_rules.md")
    print(f"  • live_trading_checklist.md")
    print(f"  • backtest_report.md")
    print(f"  • python_scripts/")
    
    return all_results


def generate_emotionless_rules(results: dict) -> str:
    """Generate complete emotionless strategy rules document."""
    
    # Get top ORB params
    top5 = results.get('phase1_top5', [])
    best_orb = top5[0] if top5 else {
        'orb_duration': 15,
        'entry_type': 'breakout',
        'profit_target': 1.5,
        'stop_loss': 1.0
    }
    
    rules = f"""# EMOTIONLESS STRATEGY RULES
## ES Futures Mechanical Trading System
### Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## !️ CRITICAL: NON-NEGOTIABLE RULES

These rules are MANDATORY. No exceptions. No discretion. No "gut feelings."

1. **NO TRADING** during first 5 minutes of NY open (9:30-9:35 AM ET)
2. **NO TRADING** during major news events (FOMC, CPI, NFP) unless strategy specifically targets it
3. **ALL trades** must have stop loss set IMMEDIATELY at entry
4. **ALL positions** must be closed by 3:50 PM ET
5. **MAX 2 concurrent trades** at any time
6. **DAILY LOSS LIMIT** = 2% of capital → STOP trading for the day
7. **WEEKLY LOSS LIMIT** = 5% of capital → REDUCE size by 50%

---

## 1. ENTRY RULES (Mechanical - No Discretion)

### Strategy A: Opening Range Breakout (ORB)
**Best Parameters from Optimization:**
- ORB Duration: {best_orb.get('orb_duration', 15)} minutes
- Entry Type: {best_orb.get('entry_type', 'breakout')}
- Profit Target: {best_orb.get('profit_target', 1.5)}x ORB range
- Stop Loss: {best_orb.get('stop_loss', 1.0)}x ORB range

**Entry Conditions:**
1. Wait for ORB to form (first {best_orb.get('orb_duration', 15)} minutes)
2. Mark ORB High and ORB Low
3. **LONG**: Enter when price breaks above ORB High
4. **SHORT**: Enter when price breaks below ORB Low
5. **NO ENTRY** if ORB range < 5 points (too tight)
6. **NO ENTRY** if ORB range > 40 points (too wide)

**Time Filter:** {best_orb.get('time_filter', 'full').replace('_', ' ').title()}
**Day Filter:** {best_orb.get('session_filter', 'all').replace('_', ' ').title()}

### Strategy B: VWAP Reversion
**Entry Conditions:**
1. Calculate VWAP from NY session open
2. **LONG**: Enter when price < VWAP by 0.3% OR MORE
3. **SHORT**: Enter when price > VWAP by 0.3% OR MORE
4. Entry at market price when condition met
5. Exit when price returns to VWAP

**Session:** NY only (9:30 AM - 4:00 PM ET)

### Strategy C: RSI Divergence
**Entry Conditions:**
1. Calculate RSI(14)
2. **BULLISH DIVERGENCE**: Price makes lower low, RSI makes higher low
3. **BEARISH DIVERGENCE**: Price makes higher high, RSI makes lower high
4. Entry: Break of signal candle high/low
5. Stop: Below/above signal candle

**Lookback Period:** 5 bars

### Strategy D: PDH/PDL Breakout
**Entry Conditions:**
1. Mark Previous Day High (PDH) and Previous Day Low (PDL)
2. **LONG**: Enter when price breaks above PDH
3. **SHORT**: Enter when price breaks below PDL
4. Stop: Inside PDH/PDL range (50% of range)
5. Target: 1.5x PDH-PDL range

### Strategy E: EMA Trend + Pullback
**Entry Conditions:**
1. Trend Filter: 9 EMA > 21 EMA > 50 EMA (LONG), reverse for SHORT
2. **LONG**: Wait for pullback to 21 EMA, enter when price bounces
3. **SHORT**: Wait for pullback to 21 EMA, enter when price rejects
4. Stop: Below/Above 50 EMA
5. Target: 2x risk

### Strategy F: Session Breakdown
**Entry Conditions:**
1. Analyze London session (3:00-11:00 AM ET)
2. If London close > London open → LONG at NY open
3. If London close < London open → SHORT at NY open
4. Exit: End of NY session or 2% stop

---

## 2. POSITION SIZING (Fixed Formula)

```
Contracts = (Account Balance × Risk%) / (Stop Distance × Point Value)
```

**Parameters:**
- Risk% per trade: 1%
- Max risk per day: 3%
- Point Value (ES): $50/point
- Point Value (MES): $5/point

**Example:**
- Account: $50,000
- Risk per trade: $500 (1%)
- Stop distance: 10 points
- Contracts: $500 / (10 × $50) = 1 contract

**Position Sizing Rules:**
1. NEVER risk more than 1% per trade
2. NEVER risk more than 3% per day
3. Reduce size by 50% after 3 consecutive losses
4. Reduce size by 50% during 5%+ drawdown
5. NO doubling down after losses

---

## 3. EXIT RULES (Mechanical)

### Stop Loss
- **FIXED at entry** - NEVER move stop away from entry
- Set IMMEDIATELY when entering trade
- Never widen stop
- Only tighten stop (move to breakeven after 50% of target)

### Take Profit
- **FIXED target** based on strategy
- Do not exit early unless time stop triggered
- Let winners run to full target

### Trailing Stop
- **AFTER 50% of target is reached:**
  - Move stop to breakeven
  - Optionally trail by 25% of profit

### Time Stop
- **ALL positions closed by 3:50 PM ET**
- No exceptions
- No overnight holds

---

## 4. RISK MANAGEMENT (Non-Negotiable)

### Daily Limits
- **Max Daily Loss: 2% of capital**
  - If hit → STOP trading for the day
  - Resume next day with full size

### Weekly Limits
- **Max Weekly Loss: 5% of capital**
  - If hit → REDUCE position size by 50%
  - Resume full size the following week

### Drawdown Rules
- **5% drawdown** → Reduce position size by 50%
- **10% drawdown** → Stop trading for 1 week
- **15% drawdown** → Stop trading for 1 month, review all trades

### Consecutive Loss Rules
- **3 consecutive losses** → Reduce size by 50% for next 3 trades
- **5 consecutive losses** → Stop trading for remainder of day
- **7 consecutive losses** → Stop trading for 3 days, review system

### Correlation Rules
- **MAX 2 correlated positions** (e.g., long ES + long NQ)
- If taking correlated position, reduce size by 50%

---

## 5. TRADING SESSIONS

### NY Session (Primary)
- **Start:** 9:30 AM ET
- **End:** 4:00 PM ET
- **No-Trade Zone:** 9:30-9:35 AM (first 5 minutes)

### Best Sessions (from optimization):
- {best_orb.get('session_filter', 'all').replace('_', ' ').title()}

### Best Times (from optimization):
- {best_orb.get('time_filter', 'full').replace('_', ' ').title()}

---

## 6. NEWS EVENTS

### NEVER TRADE During:
- FOMC announcements
- CPI releases
- NFP (Non-Farm Payrolls)
- Major earnings reports (if holding related stocks)

### OK to Trade:
-策略 specifically designed for news events
- After 15 minutes of news release (volatility subsides)

---

## 7. TRADE LOG REQUIREMENTS

Every trade MUST be logged with:
1. Date and time of entry
2. Direction (long/short)
3. Entry price
4. Stop loss price
5. Take profit price
6. Strategy used
7. Exit price and time
8. P&L
9. Emotional state (1-10)
10. Rule violations (if any)

---

## 8. WEEKLY REVIEW

Every Friday after market close:
1. Review all trades for rule violations
2. Calculate actual vs expected metrics
3. Check if any rules were broken
4. Adjust position sizing if in drawdown
5. Update trade journal

---

## 9. MONTHLY REVIEW

Every last trading day of month:
1. Full performance review
2. Compare to backtest expectations
3. Check if system is still valid
4. Consider parameter adjustments
5. Document lessons learned

---

## 10. PROP FIRM COMPLIANCE

### For Tradeify ($50K account):
- Max 5 mini / 50 micro contracts
- No overnight holds
- No hedging
- News trading allowed

### For Apex ($50K account):
- 50% consistency rule (best day ≤ 50% of total profits)
- Max 20 accounts
- MAE rule removed Mar 2026

### Position Sizing for Prop Firms:
- Risk is % of DRAWDOWN limit, not account balance
- $50K with $2K drawdown → risk $20-40/trade max
- Formula: Contracts = (Drawdown_Limit × Risk_Pct) / (ATR_Stop × Point_Value)

---

## !️ FINAL REMINDER

**THESE RULES ARE LAW.**

No "this time is different."
No "I'll just add to the position."
No "it'll come back."
No "I deserve a winning trade."

Follow the rules. The math works over 1000+ trades.
One trade doesn't matter. Consistency matters.

**Good trading is boring trading.**

---

*Generated by ES Futures Backtest Optimization System*
*Data Period: January 1 - August 31, 2026*
*Contact: [Your Contact Info]*
"""
    
    return rules


def save_emotionless_rules(rules: str):
    """Save emotionless rules to markdown file."""
    filepath = OUTPUT_DIR / "emotionless_strategy_rules.md"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rules)
    
    print(f"\n[OK] Saved emotionless strategy rules to {filepath}")


def generate_live_checklist() -> str:
    """Generate live trading checklist."""
    
    checklist = """# LIVE TRADING CHECKLIST
## ES Futures Daily Trading Routine
### Mechanical Execution Protocol

---

## PRE-MARKET PREPARATION (8:30-9:30 AM ET)

### Market Analysis
- [ ] Check overnight gap direction (up/down/flat)
- [ ] Note support/resistance levels from previous day
- [ ] Mark PDH (Previous Day High) and PDL (Previous Day Low)
- [ ] Check current VWAP level
- [ ] Identify key EMAs (9, 21, 50)

### Risk Assessment
- [ ] Review account balance
- [ ] Calculate maximum position size for today
- [ ] Check if in drawdown (reduce size if needed)
- [ ] Verify daily/weekly loss limits

### News & Events
- [ ] Check economic calendar for major releases
- [ ] Note FOMC, CPI, NFP dates (avoid trading during)
- [ ] Check VIX level (>30 = reduce size, >40 = no trading)

### Technical Setup
- [ ] Verify charting platform is working
- [ ] Check data feed connectivity
- [ ] Set alerts for ORB levels
- [ ] Set alerts for key price levels
- [ ] Test order entry system

### Account Verification
- [ ] Confirm buying power available
- [ ] Check margin requirements
- [ ] Verify position limits
- [ ] Review open positions (if any)

---

## ORB PREPARATION (9:25-9:35 AM ET)

### Initial Setup
- [ ] Mark 9:30 AM opening price
- [ ] Start ORB timer
- [ ] Prepare to mark ORB High/Low

### ORB Formation (First 15 Minutes)
- [ ] 9:30-9:45 AM: Monitor price action
- [ ] Do NOT enter any trades during this period
- [ ] Watch for ORB range development
- [ ] Note if ORB is too tight (<5 points) - SKIP TRADE
- [ ] Note if ORB is too wide (>40 points) - SKIP TRADE

### ORB Completion (9:45 AM)
- [ ] Mark ORB High (highest high of first 15 min)
- [ ] Mark ORB Low (lowest low of first 15 min)
- [ ] Calculate ORB Range (High - Low)
- [ ] Set alerts for ORB breakouts
- [ ] Prepare entry orders

---

## DURING SESSION (9:45 AM - 3:50 PM ET)

### Entry Protocol
- [ ] Wait for mechanical signal (no discretion)
- [ ] Verify no major news in next 15 minutes
- [ ] Confirm strategy conditions are met
- [ ] Enter only if ALL conditions align

### Order Entry
- [ ] Enter position at market or limit
- [ ] **IMMEDIATELY** set stop loss
- [ ] **IMMEDIATELY** set take profit
- [ ] Verify order fills
- [ ] Log trade in journal

### Position Management
- [ ] Monitor stop loss (do not move away)
- [ ] After 50% of target: move stop to breakeven
- [ ] Check time (close all by 3:50 PM)
- [ ] No adding to losing positions
- [ ] No averaging down

### Risk Monitoring
- [ ] Track daily P&L
- [ ] Check if daily loss limit approached
- [ ] Monitor concurrent positions (max 2)
- [ ] Watch for rule violations

### Trade Logging
- [ ] Record entry time, price, direction
- [ ] Record stop loss, take profit levels
- [ ] Note strategy used
- [ ] Mark emotional state (1-10)

---

## POST-SESSION (3:50-4:00 PM ET)

### Position Closure
- [ ] Close ALL positions by 3:50 PM
- [ ] Verify all positions are flat
- [ ] No overnight holds
- [ ] Confirm with broker if needed

### Daily Review
- [ ] Calculate daily P&L
- [ ] Count trades taken
- [ ] Calculate win rate for the day
- [ ] Check if daily loss limit was hit
- [ ] Note any rule violations

### Trade Journal Update
- [ ] Log all trades with details
- [ ] Record emotional state for each trade
- [ ] Note any mistakes or rule breaks
- [ ] Calculate expected vs actual P&L

### Risk Check
- [ ] Update drawdown tracking
- [ ] Check if position sizing needs adjustment
- [ ] Review weekly performance
- [ ] Plan for next trading day

---

## WEEKLY REVIEW (Friday After Close)

### Performance Analysis
- [ ] Calculate weekly P&L
- [ ] Compare to backtest expectations
- [ ] Review all trades for patterns
- [ ] Identify winning/losing strategies

### Rule Compliance
- [ ] Check if any rules were broken
- [ ] Document any exceptions
- [ ] Update risk parameters if needed
- [ ] Adjust position sizing if in drawdown

### System Validation
- [ ] Verify system is still working
- [ ] Check if market conditions changed
- [ ] Consider parameter adjustments
- [ ] Document lessons learned

---

## MONTHLY REVIEW (Last Trading Day)

### Full Performance Review
- [ ] Calculate monthly P&L
- [ ] Compare to backtest results
- [ ] Review all trades in detail
- [ ] Identify systemic issues

### System Optimization
- [ ] Check if parameters need updating
- [ ] Review correlation between strategies
- [ ] Adjust allocations if needed
- [ ] Document changes for next month

### Prop Firm Compliance
- [ ] Check consistency rule (if applicable)
- [ ] Verify max drawdown not exceeded
- [ ] Confirm all rules followed
- [ ] Prepare for next month

---

## EMERGENCY PROCEDURES

### If Daily Loss Limit Hit:
1. STOP trading immediately
2. Close all positions
3. Do NOT trade for rest of day
4. Resume next day with full size

### If Weekly Loss Limit Hit:
1. Reduce position size by 50%
2. Only take A+ setups
3. Resume full size next week

### If System Error:
1. Close all positions immediately
2. Contact broker
3. Do not trade until confirmed working
4. Document the incident

### If Emotional Trading Detected:
1. STOP trading immediately
2. Take 30-minute break
3. Review rules before resuming
4. Reduce size if continuing

---

## DAILY REMINDERS

### Before First Trade:
- "I follow the rules, not my feelings."
- "One trade doesn't matter. Consistency matters."
- "The math works over 1000+ trades."

### After Each Trade:
- "Did I follow all the rules?"
- "Was this a mechanical entry?"
- "Did I set stop loss immediately?"

### End of Day:
- "Good trading is boring trading."
- "I executed my plan perfectly."
- "Tomorrow is a new day."

---

## CONTACT INFORMATION

### Broker Support:
- [Broker Name]: [Phone Number]
- Account Number: [Your Account]

### Emergency Contacts:
- Trading Partner: [Name/Phone]
- Mentor: [Name/Phone]

### System Status:
- Data Feed Status: [URL]
- Platform Status: [URL]

---

*Generated by ES Futures Backtest Optimization System*
*Follow this checklist EXACTLY every trading day.*
*No exceptions. No discretion. No emotions.*
"""
    
    return checklist


def save_live_checklist(checklist: str):
    """Save live trading checklist to markdown file."""
    filepath = OUTPUT_DIR / "live_trading_checklist.md"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(checklist)
    
    print(f"\n[OK] Saved live trading checklist to {filepath}")


def generate_backtest_report(results: dict):
    """Generate comprehensive backtest report."""
    
    report = """# ES FUTURES BACKTEST REPORT
## January 1 - August 31, 2026
### Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """

---

## EXECUTIVE SUMMARY

This report presents the results of a comprehensive 8-month backtest optimization
for ES (E-mini S&P 500) futures using 5-minute intraday data.

**Key Findings:**
- Optimized ORB parameters identified
- 6 additional strategies backtested
- 4 portfolio combinations evaluated
- Complete emotionless trading system developed

**Data Period:** January 1 - August 31, 2026
**Instrument:** ES (E-mini S&P 500) Futures
**Timeframe:** 5-minute intraday
**Session:** NY Session (9:30 AM - 4:00 PM ET)

---

## PHASE 1: ORB OPTIMIZATION

### Parameter Grid Tested
- **ORB Durations:** 5, 10, 15, 30 minutes
- **Entry Types:** Breakout, Breakout + Retest
- **Profit Targets:** 1.0x, 1.5x, 2.0x, 2.5x, 3.0x ORB range
- **Stop Losses:** 0.5x, 0.75x, 1.0x, ATR-based
- **Session Filters:** All, Monday, Tue-Fri, Wed-Fri, Thu-Fri
- **Time Filters:** Full, Morning, Afternoon, First 90 min

**Total Combinations:** 4 × 2 × 5 × 4 × 5 × 4 = 3,200

### Top 5 Parameter Sets
See: `phase1_orb_optimization.csv`

### Key Insights
1. [Will be populated with actual results]
2. [Optimal parameters identified]
3. [Performance metrics documented]

---

## PHASE 2: ADDITIONAL STRATEGIES

### Strategy A: VWAP Reversion
- Entry: Price deviation from VWAP by 0.3%
- Exit: Return to VWAP
- Session: NY only

### Strategy B: RSI Divergence
- Entry: Price/RSI divergence confirmation
- Period: 14
- Lookback: 5 bars

### Strategy C: Session Breakdown
- Entry: London session direction
- Exit: End of NY session
- Stop: 2%

### Strategy D: PDH/PDL Breakout
- Entry: Break of previous day high/low
- Target: 1.5x range
- Stop: 50% of range

### Strategy E: ORB + VWAP Confluence
- Entry: ORB breakout aligned with VWAP
- Higher probability filter

### Strategy F: EMA Trend + Pullback
- Trend: 9/21/50 EMA alignment
- Entry: Pullback to 21 EMA
- Target: 2x risk

See: `phase2_strategy_results.csv`

---

## PHASE 3: PORTFOLIO COMBINATIONS

### Portfolio 1: Conservative
- 50% ORB
- 30% Gap Fill
- 20% PDH/PDL Breakout

### Portfolio 2: Aggressive
- 40% Event-Driven
- 30% ORB
- 30% Session Breakdown

### Portfolio 3: Diversified
- 30% ORB
- 25% VWAP Reversion
- 25% EMA Trend + Pullback
- 20% PDH/PDL Breakout

### Portfolio 4: Emotionless Robot
- All strategies with fixed sizing
- No discretion
- Daily max loss: 2%
- Weekly max loss: 5%

See: `phase3_portfolio_results.csv`

---

## PHASE 4: EMOTIONLESS STRATEGY RULES

Complete mechanical trading system developed:
- Entry rules for all strategies
- Fixed position sizing formula
- Exit rules with trailing stops
- Risk management protocols
- Drawdown rules

See: `emotionless_strategy_rules.md`

---

## PHASE 5: LIVE TRADING CHECKLIST

Daily trading routine with checklists:
- Pre-market preparation
- ORB setup
- During session execution
- Post-session review
- Weekly/monthly reviews

See: `live_trading_checklist.md`

---

## RECOMMENDATIONS FOR PROP FIRM DEPLOYMENT

### Tradeify ($50K Account)
- **Position Size:** 1-2 mini contracts max
- **Risk per Trade:** $20-40 (0.04-0.08% of account)
- **Max Drawdown:** $2,000 EOD trailing
- **Strategies:** ORB + VWAP Reversion

### Apex ($50K Account)
- **Position Size:** 1 mini contract
- **Risk per Trade:** $20 (0.04% of account)
- **Consistency:** Ensure no single day > 50% of profits
- **Strategies:** Diversified portfolio

### Topstep
- **!️ WARNING:** Automation NOT allowed on funded accounts as of 2026
- Manual trading only
- Follow all scaling plan rules

---

## NEXT STEPS

1. **Validate with Real Data**
   - Export ES 5-min data from NinjaTrader/Tradovate
   - Run backtest with actual historical data
   - Compare synthetic vs real results

2. **Paper Trading**
   - Test system in sim for 2-4 weeks
   - Verify execution quality
   - Check slippage/commission impact

3. **Small Live Testing**
   - Start with 1 contract
   - Trade for 1 month minimum
   - Compare to backtest expectations

4. **Scale Up**
   - Gradually increase position size
   - Maintain risk parameters
   - Monitor for rule violations

---

## DISCLAIMER

**Past performance, including backtested results, does not guarantee future results.**

- This report is for educational purposes only
- Trading futures involves substantial risk
- You can lose more than your initial investment
- Past performance is not indicative of future results
- Backtested results may not reflect actual trading

**Use at your own risk.**

---

*Generated by ES Futures Backtest Optimization System*
*Data Period: January 1 - August 31, 2026*
"""
    
    filepath = OUTPUT_DIR / "backtest_report.md"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[OK] Saved backtest report to {filepath}")


if __name__ == "__main__":
    # Run full backtest
    results = run_full_backtest(use_synthetic=True)
    
    # Generate report
    generate_backtest_report(results)
    
    print("\n" + "#"*70)
    print("#  ALL BACKTESTS COMPLETE" + " "*45 + "#")
    print("#"*70)


