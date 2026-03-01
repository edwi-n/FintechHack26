# AI Engine & Backtester

[← Back to Main README](../README.md)

The AI system consists of a **C++ heuristic engine** (compiled to a shared library) and a **Python backtesting harness** that validates the AI over thousands of simulated games.

---

## Table of Contents

- [Architecture](#architecture)
- [C++ Engine (engine.cpp)](#c-engine-enginecpp)
  - [Game State](#game-state)
  - [AI Decision Algorithm](#ai-decision-algorithm)
  - [Move Application](#move-application)
  - [Turn Resolution](#turn-resolution)
  - [Batch Simulation](#batch-simulation)
  - [Exported C API](#exported-c-api)
- [Python Bridge (ai\_engine.py)](#python-bridge-ai_enginepy)
- [Backtester (backtest.py)](#backtester-backtestpy)
  - [Price Window Generation](#price-window-generation)
  - [Simulation Modes](#simulation-modes)
  - [Running the Backtester](#running-the-backtester)
  - [Sample Output](#sample-output)
- [Compilation](#compilation)

---

## Architecture

```
Python Game Server
    ↓ ctypes FFI
ai_engine.py (Bridge)
    ↓ loads
engine.dll / engine.so (Compiled C++)
    ↑
backtest.py (Standalone harness)
```

The C++ engine handles:
- AI decision-making for the offline bot
- Fast batch simulation for backtesting (10,000+ games/sec)

The Python bridge loads the library via `ctypes` and provides a clean API to the game logic.

---

## C++ Engine (engine.cpp)

~413 lines of C++ implementing the core simulation and AI.

### Game State

```cpp
struct GameState {
    float p1_nw;              // Player 1 net worth
    float p2_nw;              // Player 2 net worth
    int   turn;               // Current turn number
    float p1_peak_nw;         // P1 peak NW (for drawdown)
    float p2_peak_nw;         // P2 peak NW (for drawdown)
    float p1_max_drawdown;    // P1 max drawdown
    float p2_max_drawdown;    // P2 max drawdown
};
```

### AI Decision Algorithm

```cpp
static int compute_ai_decision(
    const float *lookback,     // Recent price history
    int lb_count,              // Number of lookback prices
    float my_nw,               // Bot's current NW
    float opp_nw               // Opponent's current NW
)
```

The AI uses a **heuristic strategy** (not ML):

1. **Exploration (2%)** — With 2% probability, picks a random Attack Put or Defense Put to prevent full predictability.

2. **KO Finisher** — If the opponent's NW < £200 and the bot is ahead, it plays **Attack Put** aggressively to attempt a knockout.

3. **Default: Defense Put** — The dominant strategy. Defense Put hedges bench losses for free (the put payout offsets the omega loss on the same stock), making it the empirically optimal choice against random opponents.

#### Why Defense Put Dominates

In the game's combat math:
- Bench stocks passively lose/gain $\omega = S_1 - S_0$
- Defense Put recovers $\Delta = \max(0, S_0 - S_1)$ on the same stock
- When stock drops: the omega loss is perfectly offset by the put payout
- When stock rises: the omega gain is kept, and the put costs only the premium
- Net result: near-zero downside with full upside retention

### Move Application

```cpp
static void apply_move(
    float S0, float S1,
    int move_type,
    float *owner_nw,
    float *opponent_nw
)
```

Applies delta effects based on move type:

| Move | Effect |
|------|--------|
| `MOVE_PLACE` (3) | Owner gains/opponent loses $\max(0, S_1 - S_0)$ |
| `MOVE_CALL` (2) | Same as Place (leveraged upward bet) |
| `MOVE_ATTACK_PUT` (0) | Opponent loses $\max(0, S_0 - S_1)$ |
| `MOVE_DEFENSE_PUT` (1) | Owner gains $\max(0, S_0 - S_1)$ |

### Turn Resolution

`resolve_turn()` processes a complete turn:

1. Apply bench growth (omega) to both players
2. Charge call premiums (simplified: 5% of S₀)
3. Apply P1's move
4. Apply P2's move
5. Update peak NW and max drawdown
6. Check for KO (NW ≤ 0)

Returns:
- `0` — game continues
- `1` — Player 1 wins (KO)
- `2` — Player 2 wins (KO)

### Batch Simulation

```cpp
EXPORT void batch_simulate(
    float *s0_arr,              // Array of S₀ values
    float *s1_arr,              // Array of S₁ values
    int turns_per_game,         // Turns per game (e.g., 12)
    int num_games,              // Total games to simulate
    int *results                // Output: [p1_wins, p2_wins, draws]
)
```

Runs N complete games entirely in C++ for maximum throughput:
- Player 1 uses `compute_ai_decision()` (the heuristic AI)
- Player 2 uses random moves
- Tracks wins, losses, and draws
- Can process 10,000+ games per second

### Exported C API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `init_game()` | `void → void` | Reset to 1000/1000 starting state |
| `resolve_turn()` | `(S0, S1, p1_move, p2_move) → int` | Process one turn, return KO status |
| `get_ai_move()` | `(float*, int) → int` | AI decision using global state |
| `get_ai_move_ex()` | `(float*, int, float, float) → int` | AI decision with explicit NW |
| `get_p1_nw()` | `void → float` | Current P1 net worth |
| `get_p2_nw()` | `void → float` | Current P2 net worth |
| `get_turn()` | `void → int` | Current turn number |
| `get_p1_max_drawdown()` | `void → float` | P1's maximum drawdown |
| `get_p2_max_drawdown()` | `void → float` | P2's maximum drawdown |
| `batch_simulate()` | `(float*, float*, int, int, int*) → void` | Run N games in C++ |

---

## Python Bridge (ai_engine.py)

Loads the compiled shared library via `ctypes`:

```python
# Windows
lib = ctypes.CDLL("backtester/engine.dll")

# Linux/macOS
lib = ctypes.CDLL("backtester/engine.so")
```

### Move Code Mapping

```python
MOVE_ATTACK_PUT  = 0    → "attack_put"
MOVE_DEFENSE_PUT = 1    → "defense_put"
MOVE_CALL        = 2    → "call"
MOVE_PLACE       = 3    → "place"
```

### Graceful Fallback

If the shared library is not compiled/available:
- `is_available()` returns `False`
- The game logic falls back to **random moves** for the bot
- A warning is logged at startup

---

## Backtester (backtest.py)

Standalone Python script (~317 lines) for validating the AI strategy.

### Price Window Generation

```python
generate_price_windows(num_windows, base_price=120.0, volatility=0.15, dt=0.25, seed=42)
```

Generates synthetic (S₀, S₁) pairs using **Geometric Brownian Motion** (GBM):

$$S_1 = S_0 \cdot \exp\left((\mu - \frac{\sigma^2}{2})\Delta t + \sigma \sqrt{\Delta t} \cdot Z\right)$$

Where $Z \sim \mathcal{N}(0, 1)$.

### Simulation Modes

#### 1. Batch Simulation (C++-native)

```python
run_batch_simulation(engine, num_games=10_000, turns_per_game=12)
```

- Passes all price data to C++ `batch_simulate()` in one call
- Maximum throughput — no Python overhead per turn
- Returns: `{p1_wins, p2_wins, draws, win_rate}`

#### 2. Detailed Backtest (Python-loop)

```python
run_detailed_backtest(engine, num_games=10_000, turns_per_game=12)
```

- Python controls the game loop, calling C++ per-turn
- Collects per-game statistics: profit, drawdown, final NW
- Returns: `{avg_profit, median_profit, std_profit, max_drawdown, avg_drawdown, ...}`

### Running the Backtester

```bash
cd backtester
python backtest.py
```

Runs two phases:
1. **Phase 1:** 10,000 batch C++ games → AI win rate
2. **Phase 2:** 10,000 detailed Python-loop games → profit/drawdown statistics

### Sample Output

```
╔══════════════════════════════════════╗
║     BATCH SIMULATION RESULTS        ║
╠══════════════════════════════════════╣
║  Games:         10,000              ║
║  AI Wins:        7,234              ║
║  Opponent Wins:  2,422              ║
║  Draws:            344              ║
║  AI Win Rate:    72.34%             ║
║  Throughput:   12,450 games/sec     ║
╠══════════════════════════════════════╣
║     DETAILED BACKTEST RESULTS       ║
╠══════════════════════════════════════╣
║  Avg Profit:      £142.50           ║
║  Max Drawdown:    £287.30           ║
║  Avg Drawdown:     £89.20           ║
╚══════════════════════════════════════╝
```

*(Values are representative — actual results vary with random seed.)*

---

## Compilation

### Windows (MinGW-w64)

```powershell
# Install 64-bit compiler if needed:
winget install BrechtSanders.WinLibs.POSIX.UCRT

cd backtester
x86_64-w64-mingw32-g++ -shared -O2 -o engine.dll engine.cpp
```

### Linux / macOS

```bash
cd backtester
g++ -shared -fPIC -O2 -o engine.so engine.cpp
```

### Build Flags

| Flag | Purpose |
|------|---------|
| `-shared` | Build as shared library (DLL/SO) |
| `-fPIC` | Position-independent code (required on Linux) |
| `-O2` | Optimisation level 2 |

> **Important:** The compiled library must match your Python's architecture (typically 64-bit). A 32-bit library will fail to load.
