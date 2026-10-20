#!/usr/bin/env python3
"""
Fetch recent ES=F (E-mini S&P 500 Futures) market data via Yahoo Finance.
Designed to run on GitHub Actions (ubuntu-latest, Python 3.11).
Saves OHLCV data to data/ directory for the TradeDash dashboard.
"""

import os
import sys
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

SYMBOL = "ES=F"
OUTPUT_DIR = "data"
DAYS_BACK = 90  # Fetch last 90 days of data


def fetch_es_data(days_back: int = DAYS_BACK) -> pd.DataFrame:
    """Download recent ES=F data from Yahoo Finance."""
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    print(f"Downloading {SYMBOL} data from {start.date()} to {end.date()} ...")

    # Try 15-minute intraday first, fall back to daily
    data = yf.download(
        SYMBOL,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="15m",
        progress=False,
    )

    if data.empty:
        print("No 15-minute data available. Falling back to daily data.")
        data = yf.download(
            SYMBOL,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
        )

    if data.empty:
        print("ERROR: No data returned from Yahoo Finance.", file=sys.stderr)
        sys.exit(1)

    # Flatten MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()
    print(f"Fetched {len(data)} bars: {data.index.min()} to {data.index.max()}")
    return data


def save_data(data: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> None:
    """Save OHLCV data to CSV files in the output directory."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full intraday/daily data
    full_path = os.path.join(output_dir, "es_data_full.csv")
    data.to_csv(full_path)
    print(f"Saved full data to {full_path}")

    # Save a daily-resampled version for the dashboard
    if isinstance(data.index, pd.DatetimeIndex):
        daily = data.resample("1D").agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        ).dropna()
        daily_path = os.path.join(output_dir, "es_data_daily.csv")
        daily.to_csv(daily_path)
        print(f"Saved daily data to {daily_path} ({len(daily)} days)")

    # Save a last-updated timestamp
    ts_path = os.path.join(output_dir, "last_updated.txt")
    with open(ts_path, "w") as f:
        f.write(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"Wrote timestamp to {ts_path}")


def main() -> None:
    data = fetch_es_data(DAYS_BACK)
    save_data(data)
    print("Data fetch complete.")


if __name__ == "__main__":
    main()
