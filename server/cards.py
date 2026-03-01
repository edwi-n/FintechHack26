"""
Trading Arena — Asset / Stock Helpers
======================================
Generates stock assets from historical data, manages round dates,
and prepares asset data for the client.
"""

import random

from server.config import (
    HAND_SIZE,
    MAX_ROUNDS,
    OPTION_TERM,
    RISK_FREE_RATE,
    TRADING_DAYS_QTR,
)
from server.finance import black_scholes_premium, historical_volatility
from server.stock_data import stock_cache


def generate_stock_card(ticker: str | None = None, target_date=None) -> dict:
    """Pick a 3-month window and return a card dict.
    If target_date is given, snap to the nearest available date for this ticker.
    """
    if ticker is None:
        ticker = random.choice(list(stock_cache.keys()))

    series = stock_cache[ticker]
    max_idx = len(series) - TRADING_DAYS_QTR - 1
    if max_idx < 1:
        max_idx = 1

    if target_date is not None:
        # Find nearest index to the target date
        idx = series.index.searchsorted(target_date)
        idx = int(min(idx, max_idx))
        idx = max(0, idx)
    else:
        idx = random.randint(0, max_idx)

    s0 = round(float(series.iloc[idx]), 2)
    s1 = round(float(series.iloc[idx + TRADING_DAYS_QTR]), 2)
    sigma = historical_volatility(series)

    date_start = str(series.index[idx].date())
    date_end = str(series.index[idx + TRADING_DAYS_QTR].date())

    call_premium = round(
        black_scholes_premium(s0, s0, OPTION_TERM,
                              RISK_FREE_RATE, sigma, "call"), 2
    )
    put_premium = round(
        black_scholes_premium(s0, s0, OPTION_TERM,
                              RISK_FREE_RATE, sigma, "put"), 2
    )

    return {
        "id": f"{ticker}_{idx}_{random.randint(1000, 9999)}",
        "ticker": ticker,
        "s0": s0,
        "s1": s1,             # hidden from client until battle
        "start_idx": idx,     # for chart lookups
        "date_start": date_start,
        "date_end": date_end,
        "sigma": round(sigma, 4),
        "call_premium": call_premium,
        "put_premium": put_premium,
    }


def pick_round_date(advance_from=None):
    """Pick a date for the round's cards.
    If advance_from is given (an index), advance by one quarter (~63 trading days).
    Otherwise pick a random starting date, leaving room for MAX_ROUNDS quarters.
    """
    ref_series = next(iter(stock_cache.values()))
    total_len = len(ref_series)
    # Need room for: current quarter + (MAX_ROUNDS-1) future quarters + 1 quarter for S1
    room_needed = TRADING_DAYS_QTR * (MAX_ROUNDS + 1)
    max_start = total_len - room_needed
    if max_start < 1:
        max_start = 1

    if advance_from is not None:
        idx = advance_from + TRADING_DAYS_QTR
        # Clamp so we don't go past available data
        abs_max = total_len - TRADING_DAYS_QTR - 1
        if abs_max < 1:
            abs_max = 1
        idx = min(idx, abs_max)
    else:
        idx = random.randint(0, max_start)

    return idx, ref_series.index[idx]


def generate_hand(n: int = HAND_SIZE, target_date=None) -> list[dict]:
    """Generate *n* random stock cards using distinct tickers, all at the same date."""
    tickers = random.sample(list(stock_cache.keys()), min(n, len(stock_cache)))
    return [generate_stock_card(t, target_date=target_date) for t in tickers]


def card_for_client(card: dict) -> dict:
    """Strip server-only fields before sending to the client."""
    return {k: v for k, v in card.items() if k not in ("s1",)}
