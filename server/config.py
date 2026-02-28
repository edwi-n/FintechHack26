"""
Trading Arena — Configuration
==============================
All game constants and ticker pool definitions.
"""

STARTING_NW = 1000
MAX_ROUNDS = 5
HAND_SIZE = 5
MAX_BENCH = 10
INFLATION_RATE = 0.02      # 2 % per quarter
RISK_FREE_RATE = 0.05      # 5 % annual
OPTION_TERM = 0.25      # 3 months
TRADING_DAYS_QTR = 63        # ~3 months of trading days
CARD_BUY_COST_PCT = 0.05      # 5 % of S0 to buy a card

TICKER_POOL = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NFLX", "META", "NVDA",
    "JPM", "BAC", "WMT", "DIS", "PYPL", "AMD", "INTC", "CSCO",
    "PEP", "KO", "NKE", "SBUX", "BA", "GE", "F", "GM",
    "XOM", "CVX", "PFE", "JNJ", "UNH", "V",
]
