"""
Trading Arena — C++ AI Engine Bridge
======================================
Loads the backtester's compiled C++ engine and exposes the heuristic AI
decision function for use by the offline-mode bot.

The C++ AI uses a game-state-aware strategy:
  • Defense Put (dominant) — hedges downside, preserves bench growth
  • Attack Put — finisher when opponent NW is critically low
  • 2% exploration noise for AtkPut / DefPut

Move type mapping (C++ → game actions):
  0  ATTACK_PUT   →  attack_put on an opponent card
  1  DEFENSE_PUT  →  defense_put on own card
  2  CALL         →  call on own card
  3  PLACE        →  place (standard attack) on own card
"""

import ctypes
import sys
from pathlib import Path

# ── Move type constants (must match engine.cpp enum) ──────────
MOVE_ATTACK_PUT = 0
MOVE_DEFENSE_PUT = 1
MOVE_CALL = 2
MOVE_PLACE = 3

# Map C++ move codes → game action strings
MOVE_TO_ACTION = {
    MOVE_ATTACK_PUT: "attack_put",
    MOVE_DEFENSE_PUT: "defense_put",
    MOVE_CALL: "call",
    MOVE_PLACE: "place",
}

# ── Singleton engine handle ──────────────────────────────────
_engine = None


def _load_engine():
    """Locate and load the C++ engine shared library."""
    global _engine
    if _engine is not None:
        return _engine

    base = Path(__file__).resolve().parent.parent / "backtester"
    if sys.platform == "win32":
        lib_path = base / "engine.dll"
    else:
        lib_path = base / "engine.so"

    if not lib_path.exists():
        print(f"[ai_engine] WARNING: C++ engine not found at {lib_path}")
        print("[ai_engine] Bot will fall back to random moves.")
        return None

    try:
        lib = ctypes.CDLL(str(lib_path))

        # Declare get_ai_move_ex signature
        lib.get_ai_move_ex.restype = ctypes.c_int
        lib.get_ai_move_ex.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # prices array
            ctypes.c_int,                    # num_prices
            ctypes.c_float,                  # my_nw
            ctypes.c_float,                  # opp_nw
        ]

        _engine = lib
        print("[ai_engine] C++ backtesting engine loaded successfully.")
        return lib

    except OSError as e:
        print(f"[ai_engine] WARNING: Failed to load C++ engine: {e}")
        print("[ai_engine] Bot will fall back to random moves.")
        return None


def get_ai_move(prices: list[float], bot_nw: float, opp_nw: float) -> int:
    """
    Query the C++ AI heuristic for the best move.

    Parameters
    ----------
    prices : list[float]
        Lookback window of recent S0 prices (most recent last).
    bot_nw : float
        The bot's current net worth.
    opp_nw : float
        The opponent's current net worth.

    Returns
    -------
    int
        Move type code (0–3), or None if engine unavailable.
    """
    engine = _load_engine()
    if engine is None:
        return None

    arr = (ctypes.c_float * len(prices))(*prices)
    return engine.get_ai_move_ex(arr, len(prices), bot_nw, opp_nw)


def is_available() -> bool:
    """Return True if the C++ engine loaded successfully."""
    return _load_engine() is not None
