#!/usr/bin/env python3
"""
Cloud Paper Trading System for ES=F (E-mini S&P 500 Futures)
=============================================================
Runs on GitHub Actions (cloud). Fetches real market data from Yahoo Finance,
runs the 4 developed strategies (Gap Fill, ORB, IB Breakout, Mean Reversion),
simulates paper trades with 1% risk per trade, and tracks portfolio equity.

Designed to run after market close (4:15pm ET / 20:15 UTC) on weekdays so it
can evaluate the day's signals against actual price action and generate
signals for the next trading day.

Output files (committed to repo):
  data/paper_trades.csv        - All paper trades with entry/exit/P&L
  data/paper_portfolio.json    - Portfolio state + equity curve
  data/signals_next_day.csv    - Signals for tomorrow's session
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta, timezone

import yfinance as yf
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================
SYMBOL = "ES=F"
INITIAL_CAPITAL = 100000
CONTRACT_MULTIPLIER = 50      # ES futures multiplier
TICK_SIZE = 0.25
RISK_PER_TRADE = 0.01         # 1% of capital per trade
DATA_DIR = "data"

PAPER_TRADES_FILE = os.path.join(DATA_DIR, "paper_trades.csv")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "paper_portfolio.json")
SIGNALS_FILE = os.path.join(DATA_DIR, "signals_next_day.csv")

ET = timezone(timedelta(hours=-5))  # Approximate ET (no DST handling for simplicity)


def log(msg):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")


# ============================================================
# DATA ACQUISITION
# ============================================================
def fetch_recent_data(days_back=5):
    """Fetch recent ES=F 15-minute data from Yahoo Finance."""
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)
    log(f"Downloading {SYMBOL} 15m data from {start.date()} to {end.date()}")

    data = yf.download(
        SYMBOL,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="15m",
        progress=False,
    )

    if data.empty:
        log("No 15-minute data. Falling back to daily.")
        data = yf.download(
            SYMBOL,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
        )

    if data.empty:
        log("ERROR: No data returned from Yahoo Finance.", file=sys.stderr)
        sys.exit(1)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()
    log(f"Fetched {len(data)} bars: {data.index.min()} to {data.index.max()}")
    return data


def get_trading_days(data):
    """Return sorted list of unique trading dates."""
    return sorted(data.index.normalize().unique())


def get_day_bars(data, date):
    """Return bars for a specific trading date (normalized)."""
    return data[data.index.normalize() == pd.Timestamp(date)].copy()


# ============================================================
# PORTFOLIO STATE
# ============================================================
def load_portfolio():
    """Load existing portfolio state or initialize."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {
        "initial_capital": INITIAL_CAPITAL,
        "cash": INITIAL_CAPITAL,
        "equity": INITIAL_CAPITAL,
        "daily_pnl": [],
        "equity_curve": [{"date": None, "equity": INITIAL_CAPITAL}],
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl_usd": 0.0,
        "created_at": datetime.utcnow().isoformat(),
    }


def save_portfolio(portfolio):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)


def load_paper_trades():
    """Load existing paper trades."""
    if os.path.exists(PAPER_TRADES_FILE):
        return pd.read_csv(PAPER_TRADES_FILE)
    return pd.DataFrame(columns=[
        "date", "strategy", "direction", "entry", "target", "stop",
        "exit", "pnl_points", "pnl_usd", "status", "risk_usd", "shares"
    ])


def save_paper_trades(df):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(PAPER_TRADES_FILE, index=False)


# ============================================================
# STRATEGY FUNCTIONS (adapted from backtest_improved.py)
# ============================================================

def signal_gap_fill(day_data, prev_day_data):
    """Gap Fill: fade the gap toward previous close."""
    if day_data.empty or prev_day_data.empty:
        return None

    prev_close = float(prev_day_data["Close"].iloc[-1])
    current_open = float(day_data["Open"].iloc[0])
    gap_size = abs(current_open - prev_close)

    if gap_size < 2:
        return None

    signals = []
    if current_open > prev_close:
        # Gap up - short fade toward prev_close
        entry = prev_close
        target = entry - 1.5 * gap_size
        stop = entry + 2.0 * gap_size
        signals.append({
            "strategy": "Gap Fill",
            "direction": "short",
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop": round(stop, 2),
            "gap_size": round(gap_size, 2),
        })
    else:
        # Gap down - long fade toward prev_close
        entry = prev_close
        target = entry + 1.5 * gap_size
        stop = entry - 2.0 * gap_size
        signals.append({
            "strategy": "Gap Fill",
            "direction": "long",
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop": round(stop, 2),
            "gap_size": round(gap_size, 2),
        })

    return signals


def signal_orb(day_data, orb_duration_bars=2):
    """Opening Range Breakout: first N bars define range, trade breakout."""
    if len(day_data) < orb_duration_bars + 2:
        return []

    or_data = day_data.iloc[:orb_duration_bars]
    or_high = float(or_data["High"].max())
    or_low = float(or_data["Low"].min())
    or_range = or_high - or_low

    if or_range < 3:
        return []

    signals = [
        {
            "strategy": "ORB Breakout",
            "direction": "long",
            "entry": round(or_high, 2),
            "target": round(or_high + 1.5 * or_range, 2),
            "stop": round(or_high - or_range, 2),
            "orb_range": round(or_range, 2),
        },
        {
            "strategy": "ORB Breakout",
            "direction": "short",
            "entry": round(or_low, 2),
            "target": round(or_low - 1.5 * or_range, 2),
            "stop": round(or_low + or_range, 2),
            "orb_range": round(or_range, 2),
        },
    ]
    return signals


def signal_ib_breakout(day_data, ib_duration_bars=2):
    """Initial Balance Breakout: first 30 min defines IB, trade breakout."""
    if len(day_data) < ib_duration_bars + 2:
        return []

    ib_data = day_data.iloc[:ib_duration_bars]
    ib_high = float(ib_data["High"].max())
    ib_low = float(ib_data["Low"].min())
    ib_range = ib_high - ib_low

    if ib_range < 4:
        return []

    signals = [
        {
            "strategy": "IB Breakout",
            "direction": "long",
            "entry": round(ib_high + 1, 2),
            "target": round(ib_high + 1 + 1.5 * ib_range, 2),
            "stop": round(ib_high + 1 - 0.5 * ib_range, 2),
            "ib_range": round(ib_range, 2),
        },
        {
            "strategy": "IB Breakout",
            "direction": "short",
            "entry": round(ib_low - 1, 2),
            "target": round(ib_low - 1 - 1.5 * ib_range, 2),
            "stop": round(ib_low - 1 + 0.5 * ib_range, 2),
            "ib_range": round(ib_range, 2),
        },
    ]
    return signals


def signal_mean_reversion(day_data, rsi_period=14):
    """Mean Reversion: RSI extremes with reversion target."""
    if len(day_data) < rsi_period + 2:
        return []

    close = day_data["Close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    signals = []
    latest_rsi = float(rsi.iloc[-1])
    latest_close = float(close.iloc[-1])

    if latest_rsi >= 70:
        # Overbought - short mean reversion
        entry = latest_close
        target = entry - 2.0
        stop = entry + 2.0
        signals.append({
            "strategy": "Mean Reversion",
            "direction": "short",
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop": round(stop, 2),
            "rsi": round(latest_rsi, 1),
        })
    elif latest_rsi <= 30:
        # Oversold - long mean reversion
        entry = latest_close
        target = entry + 2.0
        stop = entry - 2.0
        signals.append({
            "strategy": "Mean Reversion",
            "direction": "long",
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop": round(stop, 2),
            "rsi": round(latest_rsi, 1),
        })

    return signals


# ============================================================
# SIGNAL EVALUATION (check if target/stop hit during the day)
# ============================================================

def evaluate_signal(signal, day_bars):
    """Given a signal and the day's bars, determine exit price and P&L."""
    entry = signal["entry"]
    target = signal["target"]
    stop = signal["stop"]
    direction = signal["direction"]

    # Check bar by bar for target/stop hit
    for _, bar in day_bars.iterrows():
        high = float(bar["High"])
        low = float(bar["Low"])
        close = float(bar["Close"])

        if direction == "long":
            if low <= stop:
                return {"exit": stop, "pnl_points": stop - entry, "status": "stopped"}
            if high >= target:
                return {"exit": target, "pnl_points": target - entry, "status": "target"}
        else:  # short
            if high >= stop:
                return {"exit": stop, "pnl_points": entry - stop, "status": "stopped"}
            if low <= target:
                return {"exit": target, "pnl_points": entry - target, "status": "target"}

    # No target/stop hit - exit at end of day close
    last_close = float(day_bars["Close"].iloc[-1])
    if direction == "long":
        pnl = last_close - entry
    else:
        pnl = entry - last_close
    return {"exit": round(last_close, 2), "pnl_points": round(pnl, 2), "status": "eod"}


# ============================================================
# POSITION SIZING
# ============================================================

def calculate_position_size(portfolio, entry, stop, direction):
    """1% risk per trade. Returns (shares/contracts, risk_usd)."""
    risk_amt = portfolio["cash"] * RISK_PER_TRADE
    risk_per_point = abs(entry - stop)
    if risk_per_point == 0:
        return 0, 0.0
    contracts = int(risk_amt / (risk_per_point * CONTRACT_MULTIPLIER))
    if contracts < 1:
        contracts = 1
    risk_usd = contracts * risk_per_point * CONTRACT_MULTIPLIER
    return contracts, risk_usd


# ============================================================
# MAIN
# ============================================================

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing state
    portfolio = load_portfolio()
    trades_df = load_paper_trades()

    # Fetch data
    data = fetch_recent_data(days_back=5)
    trading_days = get_trading_days(data)

    if len(trading_days) < 2:
        log("ERROR: Need at least 2 trading days of data.")
        sys.exit(1)

    # Most recent complete trading day (yesterday or today if market closed)
    recent_day = trading_days[-1]
    prev_day = trading_days[-2]

    log(f"Recent trading day: {recent_day.date()}")
    log(f"Previous trading day: {prev_day.date()}")

    recent_bars = get_day_bars(data, recent_day)
    prev_bars = get_day_bars(data, prev_day)

    if recent_bars.empty:
        log("ERROR: No data for recent trading day.")
        sys.exit(1)

    # ============================================================
    # GENERATE SIGNALS FOR THE RECENT DAY
    # ============================================================
    all_signals = []

    # Gap Fill (needs previous day)
    gf_signals = signal_gap_fill(recent_bars, prev_bars)
    if gf_signals:
        all_signals.extend(gf_signals)

    # ORB
    orb_signals = signal_orb(recent_bars)
    all_signals.extend(orb_signals)

    # IB Breakout
    ib_signals = signal_ib_breakout(recent_bars)
    all_signals.extend(ib_signals)

    # Mean Reversion
    mr_signals = signal_mean_reversion(recent_bars)
    all_signals.extend(mr_signals)

    log(f"Generated {len(all_signals)} signals for {recent_day.date()}")

    # ============================================================
    # EVALUATE SIGNALS AGAINST ACTUAL PRICE ACTION
    # ============================================================
    new_trades = []

    for signal in all_signals:
        result = evaluate_signal(signal, recent_bars)
        contracts, risk_usd = calculate_position_size(
            portfolio, signal["entry"], signal["stop"], signal["direction"]
        )
        pnl_usd = result["pnl_points"] * contracts * CONTRACT_MULTIPLIER

        trade = {
            "date": str(recent_day.date()),
            "strategy": signal["strategy"],
            "direction": signal["direction"],
            "entry": signal["entry"],
            "target": signal["target"],
            "stop": signal["stop"],
            "exit": result["exit"],
            "pnl_points": result["pnl_points"],
            "pnl_usd": round(pnl_usd, 2),
            "status": result["status"],
            "risk_usd": round(risk_usd, 2),
            "contracts": contracts,
        }
        new_trades.append(trade)

        log(
            f"  {signal['strategy']} {signal['direction']} "
            f"entry={signal['entry']} exit={result['exit']} "
            f"pnl={result['pnl_points']}pts (${pnl_usd:.2f}) [{result['status']}]"
        )

    # ============================================================
    # UPDATE PORTFOLIO
    # ============================================================
    if new_trades:
        new_trades_df = pd.DataFrame(new_trades)
        trades_df = pd.concat([trades_df, new_trades_df], ignore_index=True)

        day_pnl = sum(t["pnl_usd"] for t in new_trades)
        portfolio["cash"] += day_pnl
        portfolio["equity"] = portfolio["cash"]
        portfolio["total_trades"] += len(new_trades)
        portfolio["total_pnl_usd"] = round(
            portfolio["total_pnl_usd"] + day_pnl, 2
        )
        wins = sum(1 for t in new_trades if t["pnl_usd"] > 0)
        losses = sum(1 for t in new_trades if t["pnl_usd"] < 0)
        portfolio["winning_trades"] = portfolio.get("winning_trades", 0) + wins
        portfolio["losing_trades"] = portfolio.get("losing_trades", 0) + losses

        portfolio["daily_pnl"].append({
            "date": str(recent_day.date()),
            "pnl_usd": round(day_pnl, 2),
            "trades": len(new_trades),
        })

        portfolio["equity_curve"].append({
            "date": str(recent_day.date()),
            "equity": round(portfolio["equity"], 2),
        })

        save_paper_trades(trades_df)
        log(f"Day P&L: ${day_pnl:.2f} | Portfolio Equity: ${portfolio['equity']:.2f}")
    else:
        log("No new trades recorded.")

    save_portfolio(portfolio)

    # ============================================================
    # GENERATE SIGNALS FOR NEXT TRADING DAY
    # ============================================================
    # Use the most recent day's data to generate tomorrow's signals
    # (Gap Fill uses prev_close, ORB/IB use opening range, MR uses latest RSI)
    next_day_signals = []

    # Gap Fill signal for tomorrow (based on today's close)
    # We'll mark these as "pending" - to be evaluated tomorrow
    gf_next = signal_gap_fill(recent_bars, prev_bars)
    if gf_next:
        for s in gf_next:
            s["status"] = "pending_next_day"
            next_day_signals.append(s)

    # ORB and IB signals can't be pre-computed (need tomorrow's opening range)
    # Mean Reversion signal for tomorrow based on latest RSI
    mr_next = signal_mean_reversion(recent_bars)
    if mr_next:
        for s in mr_next:
            s["status"] = "pending_next_day"
            next_day_signals.append(s)

    if next_day_signals:
        signals_df = pd.DataFrame(next_day_signals)
        signals_df.insert(0, "signal_date", str((recent_day + timedelta(days=1)).date()))
        signals_df.to_csv(SIGNALS_FILE, index=False)
        log(f"Generated {len(next_day_signals)} signals for next trading day")
    else:
        # Write empty signals file
        pd.DataFrame(columns=["signal_date", "strategy", "direction", "entry",
                              "target", "stop", "status"]).to_csv(SIGNALS_FILE, index=False)
        log("No signals for next trading day.")

    # ============================================================
    # COMMIT AND PUSH TO GITHUB
    # ============================================================
    log("Committing and pushing results to GitHub...")
    try:
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "data/"], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode == 0:
            log("No changes to commit.")
        else:
            commit_msg = f"Update paper trading data {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            log("Pushed to GitHub successfully.")
    except Exception as e:
        log(f"Git error (non-fatal): {e}")

    log("Paper trading run complete.")


if __name__ == "__main__":
    main()
