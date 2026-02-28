"""
Trading Arena — Stock Data
===========================
Downloads and caches historical price data for every ticker in the pool.
Falls back to synthetic/simulated data when real data is unavailable.
"""

import random
from datetime import datetime

import pandas as pd
import yfinance as yf

from server.config import TICKER_POOL, TRADING_DAYS_QTR

# ──────────────────────────────────────────────
# Stock-data cache  (filled once at startup)
# ──────────────────────────────────────────────
stock_cache: dict[str, pd.Series] = {}


def _generate_simulated_series(ticker: str) -> pd.Series:
    """Fallback: generate a synthetic price series."""
    dates = pd.bdate_range(end=datetime.now(), periods=2520)  # ~10 yr
    base = random.uniform(30, 400)
    prices = [base]
    for _ in range(len(dates) - 1):
        prices.append(prices[-1] * (1 + random.gauss(0.0004, 0.018)))
    return pd.Series(prices, index=dates, name=ticker)


def load_stock_data():
    """Download historical closes for every ticker in the pool."""
    global stock_cache
    print("[boot] Downloading stock data …")
    try:
        raw = yf.download(
            TICKER_POOL,
            period="10y",
            progress=False,
            auto_adjust=True,
            threads=True,
        )
        close_df = raw["Close"] if "Close" in raw.columns.get_level_values(
            0) else raw
        for ticker in TICKER_POOL:
            try:
                series = close_df[ticker].dropna()
                if len(series) >= TRADING_DAYS_QTR + 10:
                    stock_cache[ticker] = series
            except Exception:
                pass
    except Exception as exc:
        print(f"[boot] Bulk download failed: {exc}")

    # Fill any gaps with simulated data
    for ticker in TICKER_POOL:
        if ticker not in stock_cache:
            print(f"[boot] Simulating data for {ticker}")
            stock_cache[ticker] = _generate_simulated_series(ticker)

    print(f"[boot] Ready — {len(stock_cache)} tickers loaded.")
