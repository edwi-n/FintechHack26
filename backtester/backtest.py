"""
TRADING ARENA — Backtesting Wrapper
===================================
Loads the C++ engine (.dll / .so) via ctypes, generates synthetic 3-month
price windows, and runs 10 000 simulated games to evaluate the heuristic
AI against a random-move opponent.

Outputs:
  • AI Win Rate (%)
  • AI Average Profit (NW delta vs starting 1000)
  • AI Max Drawdown (worst peak-to-trough %)
  • Histogram of final NW spread
"""

import ctypes
import os
import sys
import random
import math
import time
from pathlib import Path

# ────────────────────────────────────────────────────────────────
#  1. Load the compiled C++ shared library
# ────────────────────────────────────────────────────────────────


def _load_engine():
    """Locate and load engine.dll / engine.so next to this script."""
    base = Path(__file__).resolve().parent
    if sys.platform == "win32":
        lib_path = base / "engine.dll"
    else:
        lib_path = base / "engine.so"

    if not lib_path.exists():
        print(f"[ERROR] Shared library not found at {lib_path}")
        print("  Compile first:")
        if sys.platform == "win32":
            print("    g++ -shared -O2 -o engine.dll engine.cpp")
        else:
            print("    g++ -shared -fPIC -O2 -o engine.so engine.cpp")
        sys.exit(1)

    lib = ctypes.CDLL(str(lib_path))

    # ── Declare function signatures ──────────────────────────────
    lib.init_game.restype = None
    lib.init_game.argtypes = []

    lib.resolve_turn.restype = ctypes.c_int
    lib.resolve_turn.argtypes = [
        ctypes.c_float,  # S0
        ctypes.c_float,  # S1
        ctypes.c_int,    # p1_move_type
        ctypes.c_int,    # p2_move_type
    ]

    lib.get_ai_move.restype = ctypes.c_int
    lib.get_ai_move.argtypes = [
        ctypes.POINTER(ctypes.c_float),  # prices array
        ctypes.c_int,                    # num_prices
    ]

    lib.get_p1_nw.restype = ctypes.c_float
    lib.get_p2_nw.restype = ctypes.c_float
    lib.get_turn.restype = ctypes.c_int
    lib.get_p1_max_drawdown.restype = ctypes.c_float
    lib.get_p2_max_drawdown.restype = ctypes.c_float

    # Batch simulation (runs entirely in C++ for speed)
    lib.batch_simulate.restype = None
    lib.batch_simulate.argtypes = [
        ctypes.POINTER(ctypes.c_float),  # s0_arr
        ctypes.POINTER(ctypes.c_float),  # s1_arr
        ctypes.c_int,                    # turns_per_game
        ctypes.c_int,                    # num_games
        ctypes.POINTER(ctypes.c_int),    # results (output)
    ]

    return lib


# ────────────────────────────────────────────────────────────────
#  2. Synthetic price data generator
# ────────────────────────────────────────────────────────────────

def generate_price_windows(num_windows: int,
                           base_price: float = 120.0,
                           volatility: float = 0.15,
                           dt: float = 0.25,
                           seed: int = 42) -> list[tuple[float, float]]:
    """
    Generate (S0, S1) pairs using Geometric Brownian Motion.

    Each pair represents a 3-month (dt = 0.25 yr) price jump.

      S1 = S0 * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)

    with Z ~ N(0,1), mu drawn from a mild distribution, and S0
    slowly drifting to simulate regime changes.

    Returns list of (S0, S1) tuples.
    """
    rng = random.Random(seed)
    windows: list[tuple[float, float]] = []
    price = base_price

    for _ in range(num_windows):
        S0 = price
        mu = rng.gauss(0.06, 0.04)          # annualised drift
        sigma = abs(rng.gauss(volatility, 0.05))
        Z = rng.gauss(0, 1)
        S1 = S0 * math.exp((mu - 0.5 * sigma**2) * dt +
                           sigma * math.sqrt(dt) * Z)
        S1 = round(S1, 2)
        windows.append((round(S0, 2), S1))

        # Drift the base price slowly for the next window
        price = S1 * rng.uniform(0.97, 1.03)
        price = max(price, 10.0)  # floor to avoid degenerate prices

    return windows


# ────────────────────────────────────────────────────────────────
#  3. Single-game simulation (Python-side loop via ctypes)
# ────────────────────────────────────────────────────────────────

def run_single_game(engine, windows: list[tuple[float, float]],
                    turns: int = 12) -> dict:
    """
    Play one full game (P1 = AI, P2 = random) for `turns` turns.

    Returns dict with final NW, profit, drawdowns.
    """
    engine.init_game()
    lookback: list[float] = []

    for t in range(min(turns, len(windows))):
        S0, S1 = windows[t]
        lookback.append(S0)

        # AI move via the C++ heuristic
        arr = (ctypes.c_float * len(lookback))(*lookback)
        ai_move = engine.get_ai_move(arr, len(lookback))

        # Random opponent
        rand_move = random.randint(0, 3)

        alive = engine.resolve_turn(S0, S1, ai_move, rand_move)
        if not alive:
            break

    p1_nw = engine.get_p1_nw()
    p2_nw = engine.get_p2_nw()

    return {
        "p1_nw": p1_nw,
        "p2_nw": p2_nw,
        "p1_profit": p1_nw - 1000.0,
        "p1_drawdown": engine.get_p1_max_drawdown(),
        "p2_drawdown": engine.get_p2_max_drawdown(),
        "turns": engine.get_turn(),
        "winner": "AI" if p1_nw > p2_nw else ("Random" if p2_nw > p1_nw else "Draw"),
    }


# ────────────────────────────────────────────────────────────────
#  4. Batch simulation (runs entirely in C++ — fastest path)
# ────────────────────────────────────────────────────────────────

def run_batch_simulation(engine,
                         num_games: int = 10_000,
                         turns_per_game: int = 12) -> dict:
    """
    Run `num_games` complete games inside the C++ engine in one call.

    Returns aggregate analytics dict.
    """
    total_turns = num_games * turns_per_game

    # Generate all price data up-front
    all_windows = generate_price_windows(total_turns, seed=12345)

    s0_arr = (ctypes.c_float * total_turns)()
    s1_arr = (ctypes.c_float * total_turns)()
    for i, (s0, s1) in enumerate(all_windows):
        s0_arr[i] = s0
        s1_arr[i] = s1

    results = (ctypes.c_int * num_games)()

    t0 = time.perf_counter()
    engine.batch_simulate(s0_arr, s1_arr, turns_per_game, num_games, results)
    elapsed = time.perf_counter() - t0

    # ── Analytics ────────────────────────────────────────────────
    wins = sum(1 for r in results if r == 1)
    losses = sum(1 for r in results if r == -1)
    draws = sum(1 for r in results if r == 0)

    win_rate = wins / num_games * 100.0

    return {
        "num_games": num_games,
        "turns_per_game": turns_per_game,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "elapsed_sec": round(elapsed, 4),
        "games_per_sec": round(num_games / elapsed, 0),
    }


# ────────────────────────────────────────────────────────────────
#  5. Detailed per-game analytics (Python loop path)
# ────────────────────────────────────────────────────────────────

def run_detailed_backtest(engine,
                          num_games: int = 10_000,
                          turns_per_game: int = 12) -> dict:
    """
    Run num_games using the Python-side loop so we can collect
    per-game drawdown + profit statistics.
    """
    profits: list[float] = []
    drawdowns: list[float] = []
    wins = losses = draws = 0

    t0 = time.perf_counter()
    for g in range(num_games):
        windows = generate_price_windows(turns_per_game, seed=g * 7 + 1)
        result = run_single_game(engine, windows, turns=turns_per_game)

        profits.append(result["p1_profit"])
        drawdowns.append(result["p1_drawdown"])

        if result["winner"] == "AI":
            wins += 1
        elif result["winner"] == "Random":
            losses += 1
        else:
            draws += 1

    elapsed = time.perf_counter() - t0

    avg_profit = sum(profits) / len(profits)
    max_dd = max(drawdowns) * 100.0  # convert to %
    win_rate = wins / num_games * 100.0

    return {
        "num_games": num_games,
        "turns_per_game": turns_per_game,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate_pct": round(win_rate, 2),
        "avg_profit": round(avg_profit, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "elapsed_sec": round(elapsed, 4),
        "games_per_sec": round(num_games / elapsed, 0),
    }


# ────────────────────────────────────────────────────────────────
#  6. Pretty-print report
# ────────────────────────────────────────────────────────────────

def print_report(title: str, stats: dict):
    bar = "═" * 58
    print(f"\n╔{bar}╗")
    print(f"║  {title:^54}  ║")
    print(f"╠{bar}╣")
    for k, v in stats.items():
        label = k.replace("_", " ").title()
        print(f"║  {label:<30} {str(v):>22}  ║")
    print(f"╚{bar}╝\n")


# ────────────────────────────────────────────────────────────────
#  7. Main
# ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  TRADING ARENA — AI Backtesting Engine")
    print("=" * 60)

    engine = _load_engine()

    # ── Phase 1: Fast batch (C++-only loop) ──────────────────────
    print("\n[Phase 1] Running 10,000 games (batch C++ mode)...")
    batch_stats = run_batch_simulation(
        engine, num_games=10_000, turns_per_game=12)
    print_report("Batch Simulation (C++ fast path)", batch_stats)

    # ── Phase 2: Detailed per-game analytics (Python loop) ───────
    print("[Phase 2] Running 10,000 games (detailed Python loop)...")
    detailed = run_detailed_backtest(
        engine, num_games=10_000, turns_per_game=12)
    print_report("Detailed Backtest Analytics", detailed)

    # ── Summary ──────────────────────────────────────────────────
    print("SUMMARY")
    print(f"  AI Win Rate        : {detailed['win_rate_pct']:.1f}%")
    print(f"  AI Avg Profit      : {detailed['avg_profit']:+.2f} NW")
    print(f"  AI Max Drawdown    : {detailed['max_drawdown_pct']:.2f}%")
    print(
        f"  Batch throughput   : {batch_stats['games_per_sec']:.0f} games/sec")
    print()


if __name__ == "__main__":
    main()
