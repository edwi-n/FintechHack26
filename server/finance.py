"""
Trading Arena — Finance Helpers
================================
Historical volatility calculation and Black-Scholes option pricing.
"""

import math

import numpy as np
import pandas as pd
from scipy.stats import norm


def historical_volatility(series: pd.Series) -> float:
    """Annualised volatility from daily log-returns."""
    log_ret = np.log(series / series.shift(1)).dropna()
    return float(log_ret.std() * math.sqrt(252))


def black_scholes_premium(
    S: float, K: float, T: float, r: float,
    sigma: float, option_type: str = "call",
) -> float:
    """Return Black-Scholes option premium.  ATM => K = S."""
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return float(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))
    else:  # put
        return float(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
