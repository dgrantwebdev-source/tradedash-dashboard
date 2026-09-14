# EMOTIONLESS STRATEGY RULES
## ES Futures Mechanical Trading System
### Generated: 2026-09-14

---

## CRITICAL: NON-NEGOTIABLE RULES

These rules are MANDATORY. No exceptions. No discretion. No "gut feelings."

1. **NO TRADING** during first 5 minutes of NY open (9:30-9:35 AM ET)
2. **NO TRADING** during major news events (FOMC, CPI, NFP) unless strategy specifically targets it
3. **ALL trades** must have stop loss set IMMEDIATELY at entry
4. **ALL positions** must be closed by 3:50 PM ET
5. **MAX 2 concurrent trades** at any time
6. **DAILY LOSS LIMIT** = 2% of capital - STOP trading for the day
7. **WEEKLY LOSS LIMIT** = 5% of capital - REDUCE size by 50%

---

## 1. ENTRY RULES (Mechanical - No Discretion)

### Strategy A: Opening Range Breakout (ORB)
**Best Parameters from Optimization:**
- ORB Duration: 10 minutes
- Entry Type: breakout
- Profit Target: 1.5x ORB range
- Stop Loss: 0.75x ORB range

**Entry Conditions:**
1. Wait for ORB to form (first 10 minutes of session)
2. Mark ORB High and ORB Low
3. **LONG**: Enter when price breaks above ORB High
4. **SHORT**: Enter when price breaks below ORB Low
5. **NO ENTRY** if ORB range < 5 points (too tight)
6. **NO ENTRY** if ORB range > 40 points (too wide)

**Time Filter:** Full session
**Day Filter:** Wednesday-Friday

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
2. If London close > London open - LONG at NY open
3. If London close < London open - SHORT at NY open
4. Exit: End of NY session or 2% stop

---

## 2. POSITION SIZING (Fixed Formula)

```
Contracts = (Account Balance x Risk%) / (Stop Distance x Point Value)
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
- Contracts: $500 / (10 x $50) = 1 contract

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
  - If hit - STOP trading for the day
  - Resume next day with full size

### Weekly Limits
- **Max Weekly Loss: 5% of capital**
  - If hit - REDUCE position size by 50%
  - Resume full size the following week

### Drawdown Rules
- **5% drawdown** - Reduce position size by 50%
- **10% drawdown** - Stop trading for 1 week
- **15% drawdown** - Stop trading for 1 month, review all trades

### Consecutive Loss Rules
- **3 consecutive losses** - Reduce size by 50% for next 3 trades
- **5 consecutive losses** - Stop trading for remainder of day
- **7 consecutive losses** - Stop trading for 3 days, review system

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
- Wednesday-Friday

### Best Times (from optimization):
- Full session

---

## 6. NEWS EVENTS

### NEVER TRADE During:
- FOMC announcements
- CPI releases
- NFP (Non-Farm Payrolls)
- Major earnings reports (if holding related stocks)

### OK to Trade:
- Strategy specifically designed for news events
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
- 50% consistency rule (best day <= 50% of total profits)
- Max 20 accounts
- MAE rule removed Mar 2026

### Position Sizing for Prop Firms:
- Risk is % of DRAWDOWN limit, not account balance
- $50K with $2K drawdown - risk $20-40/trade max
- Formula: Contracts = (Drawdown_Limit x Risk_Pct) / (ATR_Stop x Point_Value)

---

## FINAL REMINDER

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
