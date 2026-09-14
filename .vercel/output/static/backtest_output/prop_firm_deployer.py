"""
Prop Firm Deployment Recommendations
====================================
Specific guidance for deploying backtested strategies to prop firms.
"""

import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PropFirmConfig:
    """Configuration for a specific prop firm."""
    name: str
    account_size: int
    drawdown_limit: int
    drawdown_type: str  # 'EOD_trailing', 'intraday', 'static'
    max_contracts_mini: int
    max_contracts_micro: int
    automation_allowed: bool
    overnight_holds: bool
    consistency_rule: bool
    consistency_pct: float
    min_trading_days: int
    profit_target: int
    monthly_fee: float


# Prop Firm Configurations (2026)
PROP_FIRMS = {
    'tradeify_50k': PropFirmConfig(
        name="Tradeify",
        account_size=50000,
        drawdown_limit=2000,
        drawdown_type="EOD_trailing",
        max_contracts_mini=5,
        max_contracts_micro=50,
        automation_allowed=True,
        overnight_holds=False,
        consistency_rule=False,
        consistency_pct=0.0,
        min_trading_days=0,
        profit_target=3000,
        monthly_fee=150
    ),
    'apex_50k': PropFirmConfig(
        name="Apex",
        account_size=50000,
        drawdown_limit=2500,
        drawdown_type="EOD",
        max_contracts_mini=10,
        max_contracts_micro=100,
        automation_allowed=True,
        overnight_holds=False,
        consistency_rule=True,
        consistency_pct=50.0,
        min_trading_days=7,
        profit_target=3000,
        monthly_fee=165
    ),
    'topstep_50k': PropFirmConfig(
        name="Topstep",
        account_size=50000,
        drawdown_limit=2000,
        drawdown_type="intraday",
        max_contracts_mini=5,
        max_contracts_micro=50,
        automation_allowed=False,
        overnight_holds=False,
        consistency_rule=True,
        consistency_pct=0.0,
        min_trading_days=5,
        profit_target=3000,
        monthly_fee=165
    )
}


class PropFirmDeployer:
    """
    Calculate position sizing and strategy recommendations for prop firms.
    """
    
    POINT_VALUE_ES = 50.0  # $50/point for ES
    POINT_VALUE_MES = 5.0  # $5/point for MES
    
    def __init__(self, backtest_results: dict):
        self.results = backtest_results
    
    def calculate_position_size(self, firm: PropFirmConfig,
                                 strategy_risk_pct: float = 0.01,
                                 stop_distance_pts: float = 10.0,
                                 instrument: str = 'MES') -> dict:
        """
        Calculate position size for prop firm account.
        
        Key insight: Risk is % of DRAWDOWN LIMIT, not account balance.
        """
        point_value = self.POINT_VALUE_MES if instrument == 'MES' else self.POINT_VALUE_ES
        
        # Risk per trade (based on drawdown limit, not account)
        max_risk_per_trade = firm.drawdown_limit * strategy_risk_pct
        
        # Contracts calculation
        risk_per_contract = stop_distance_pts * point_value
        max_contracts = int(max_risk_per_trade / risk_per_contract)
        
        # Apply firm limits
        if instrument == 'MES':
            max_contracts = min(max_contracts, firm.max_contracts_micro)
        else:
            max_contracts = min(max_contracts, firm.max_contracts_mini)
        
        return {
            'firm': firm.name,
            'account_size': firm.account_size,
            'drawdown_limit': firm.drawdown_limit,
            'instrument': instrument,
            'risk_per_trade': max_risk_per_trade,
            'risk_pct_of_drawdown': strategy_risk_pct * 100,
            'stop_distance_pts': stop_distance_pts,
            'point_value': point_value,
            'max_contracts': max_contracts,
            'max_loss_per_trade': max_contracts * stop_distance_pts * point_value,
            'max_daily_loss': firm.drawdown_limit * 0.02,  # 2% daily limit
            'daily_loss_contracts': int((firm.drawdown_limit * 0.02) / 
                                        (stop_distance_pts * point_value))
        }
    
    def recommend_strategy_for_firm(self, firm: PropFirmConfig) -> dict:
        """Recommend best strategy组合 for a specific prop firm."""
        
        recommendations = {
            'firm': firm.name,
            'account_size': firm.account_size,
            'automation_allowed': firm.automation_allowed,
            'strategies': [],
            'position_sizing': {},
            'risk_parameters': {}
        }
        
        if not firm.automation_allowed:
            recommendations['strategies'].append({
                'name': 'Manual Only',
                'note': 'Automation NOT allowed. Manual trading required.',
                'recommended_strategies': [
                    'ORB (manual execution)',
                    'VWAP Reversion (manual)',
                    'PDH/PDL Breakout (manual)'
                ]
            })
        else:
            # Automated strategies
            recommendations['strategies'] = [
                {
                    'name': 'ORB',
                    'allocation': '40%',
                    'parameters': 'Best from Phase 1 optimization',
                    'notes': 'Primary strategy for automation'
                },
                {
                    'name': 'VWAP Reversion',
                    'allocation': '25%',
                    'parameters': '0.3% deviation, NY session',
                    'notes': 'Good for ranging days'
                },
                {
                    'name': 'EMA Trend + Pullback',
                    'allocation': '20%',
                    'parameters': '9/21/50 EMA, pullback entry',
                    'notes': 'Trending day strategy'
                },
                {
                    'name': 'PDH/PDL Breakout',
                    'allocation': '15%',
                    'parameters': '1.5x target, 50% range stop',
                    'notes': 'Breakout strategy'
                }
            ]
        
        # Position sizing
        pos_size = self.calculate_position_size(
            firm, 
            strategy_risk_pct=0.01,  # 1% risk
            stop_distance_pts=10.0,
            instrument='MES'
        )
        recommendations['position_sizing'] = pos_size
        
        # Risk parameters
        recommendations['risk_parameters'] = {
            'max_risk_per_trade': f"${pos_size['risk_per_trade']:.2f}",
            'max_daily_loss': f"${pos_size['max_daily_loss']:.2f}",
            'max_concurrent_trades': 2,
            'daily_loss_contracts': pos_size['daily_loss_contracts'],
            'drawdown_usage_per_trade': f"{(pos_size['risk_per_trade'] / firm.drawdown_limit) * 100:.1f}%"
        }
        
        return recommendations
    
    def generate_deployment_plan(self) -> str:
        """Generate complete deployment plan for all prop firms."""
        
        plan = """# PROP FIRM DEPLOYMENT PLAN
## ES Futures Automated Trading Systems

---

## CRITICAL CONCEPT: Risk is % of DRAWDOWN, Not Account Balance

```
WRONG: Risk 1% of $50,000 = $500 per trade
RIGHT: Risk 1% of $2,000 drawdown = $20 per trade
```

**Why?** Because you only get $2,000 of drawdown before you fail.
$500 risk per trade = 4 trades to failure.
$20 risk per trade = 100 trades to failure.

---

"""
        
        for firm_key, firm in PROP_FIRMS.items():
            rec = self.recommend_strategy_for_firm(firm)
            
            plan += f"""
## {firm.name.upper()} (${'{:,}'.format(firm.account_size)} Account)

### Account Parameters
- **Drawdown Limit:** ${firm.drawdown_limit:,} ({firm.drawdown_type})
- **Max Mini Contracts:** {firm.max_contracts_mini}
- **Max Micro Contracts:** {firm.max_contracts_micro}
- **Automation:** {'✅ Allowed' if firm.automation_allowed else '❌ NOT Allowed'}
- **Overnight Holds:** {'✅ Allowed' if firm.overnight_holds else '❌ NOT Allowed'}
- **Consistency Rule:** {'✅ Yes (' + str(firm.consistency_pct) + '%)' if firm.consistency_rule else '❌ None'}
- **Min Trading Days:** {firm.min_trading_days}
- **Profit Target:** ${firm.profit_target:,}
- **Monthly Fee:** ${firm.monthly_fee}

### Position Sizing (MES Recommended)
- **Risk per Trade:** ${rec['position_sizing']['risk_per_trade']:.2f}
- **Risk % of Drawdown:** {rec['position_sizing']['risk_pct_of_drawdown']:.1f}%
- **Stop Distance:** {rec['position_sizing']['stop_distance_pts']} points
- **Max Contracts:** {rec['position_sizing']['max_contracts']}
- **Max Loss per Trade:** ${rec['position_sizing']['max_loss_per_trade']:.2f}
- **Max Daily Loss (2%):** ${rec['position_sizing']['max_daily_loss']:.2f}

### Recommended Strategies
"""
            
            for strat in rec['strategies']:
                plan += f"- **{strat['name']}** ({strat['allocation']}): {strat['notes']}\n"
            
            plan += f"""
### Risk Parameters
- **Max Concurrent Trades:** 2
- **Daily Loss Limit:** {rec['risk_parameters']['max_daily_loss']}
- **Drawdown per Trade:** {rec['risk_parameters']['drawdown_usage_per_trade']}

---

"""
        
        # Add general recommendations
        plan += """
## GENERAL RECOMMENDATIONS

### Instrument Selection: MES vs ES

| Factor | MES | ES |
|--------|-----|-----|
| Point Value | $5 | $50 |
| Tick Size | 0.25 ($1.25) | 0.25 ($12.50) |
| Margin | ~$1,200 | ~$12,000 |
| Best For | Prop firms, small accounts | Large accounts, max leverage |

**Recommendation:** Use MES for prop firms.
- Lower risk per contract
- More granular position sizing
- Same strategies work on both

### Strategy Allocation by Firm

**Tradeify (No Consistency Rule):**
- Aggressive allocation OK
- Can concentrate on best strategy
- ORB 50% + VWAP 30% + EMA 20%

**Apex (50% Consistency Rule):**
- Must spread profits across days
- Best day ≤ 50% of total profits
- Diversified approach recommended
- ORB 30% + VWAP 25% + EMA 25% + PDH/PDL 20%

**Topstep (No Automation):**
- Manual execution only
- Simplest strategies preferred
- ORB + PDH/PDL (easy to execute manually)

### Automation Stack

For firms that allow automation:

1. **Data Feed:** NinjaTrader or Tradeovate API
2. **Execution:** NinjaTrader Automated Strategies
3. **Alternative:** Python + Interactive Brokers API
4. **Alternative:** PickMyTrade (relay service)

### Testing Protocol

1. **Week 1-2:** Paper trading in sim
2. **Week 3-4:** 1 contract live testing
3. **Month 2:** 2 contracts if Week 1-2 successful
4. **Month 3+:** Full position sizing

### Monitoring

Daily checks:
- [ ] Verify all trades executed correctly
- [ ] Check for slippage > expected
- [ ] Confirm stop losses triggered at correct levels
- [ ] Review daily P&L vs backtest expectations

Weekly checks:
- [ ] Compare actual metrics to backtest
- [ ] Check for rule violations
- [ ] Adjust position sizing if needed

### Failure Criteria

Stop trading if:
- 3 consecutive losing days
- Drawdown exceeds 50% of limit
- System behaving differently than backtest
- Execution issues not resolved

---

## BACKTEST VALIDATION

Before deploying real money:

1. **Run backtest with real data** (not synthetic)
2. **Paper trade for 2-4 weeks**
3. **Compare metrics:**
   - Win rate should be within 5% of backtest
   - Profit factor should be within 0.3 of backtest
   - Max drawdown should be < 150% of backtest

4. **If metrics diverge significantly:**
   - Check data quality
   - Verify strategy logic
   - Consider parameter adjustment
   - Paper trade longer before live

---

*Generated by ES Futures Backtest Optimization System*
*Always verify current prop firm rules before deployment*
"""
        
        return plan


def save_deployment_plan(plan: str, output_dir: str):
    """Save deployment plan to file."""
    from pathlib import Path
    
    filepath = Path(output_dir) / "prop_firm_deployment_plan.md"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(plan)
    
    print(f"\n✓ Saved prop firm deployment plan to {filepath}")


if __name__ == "__main__":
    from pathlib import Path
    
    OUTPUT_DIR = Path(r"C:\Users\dgran\AppData\Local\Temp\opencode\backtest_output")
    
    deployer = PropFirmDeployer({})
    plan = deployer.generate_deployment_plan()
    save_deployment_plan(plan, str(OUTPUT_DIR))
    
    print("\nProp firm configurations:")
    for name, firm in PROP_FIRMS.items():
        print(f"\n{firm.name}:")
        print(f"  Account: ${firm.account_size:,}")
        print(f"  Drawdown: ${firm.drawdown_limit:,} ({firm.drawdown_type})")
        print(f"  Automation: {'Yes' if firm.automation_allowed else 'No'}")
        print(f"  Consistency: {firm.consistency_pct}%")

