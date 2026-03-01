# Server Architecture

[← Back to Main README](../README.md)

The backend is a Python Flask application using Socket.IO for real-time communication. All server code lives in the `server/` package.

---

## Table of Contents

- [Module Overview](#module-overview)
- [Entry Point (app.py)](#entry-point-apppy)
- [Configuration (config.py)](#configuration-configpy)
- [Game State (game\_state.py)](#game-state-game_statepy)
- [Game Logic (game\_logic.py)](#game-logic-game_logicpy)
- [Combat System (combat.py)](#combat-system-combatpy)
- [Card Generation (cards.py)](#card-generation-cardspy)
- [Financial Math (finance.py)](#financial-math-financepy)
- [Stock Data Loader (stock\_data.py)](#stock-data-loader-stock_datapy)
- [AI Engine Bridge (ai\_engine.py)](#ai-engine-bridge-ai_enginepy)
- [LLM Insights (llm\_insights.py)](#llm-insights-llm_insightspy)
- [Data Flow](#data-flow)

---

## Module Overview

```
server/
├── __init__.py       # Package marker
├── config.py         # Constants & ticker pool
├── game_state.py     # Global mutable game dict
├── game_logic.py     # Round lifecycle engine
├── events.py         # Socket.IO event handlers
├── combat.py         # Delta & omega math
├── cards.py          # Stock card factory
├── finance.py        # Black-Scholes & volatility
├── stock_data.py     # Yahoo Finance loader
├── ai_engine.py      # Python ↔ C++ ctypes bridge
└── llm_insights.py   # Post-game LLM analysis
```

---

## Entry Point (app.py)

The top-level `app.py` creates the Flask application and Socket.IO instance:

```python
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
register_events(app, socketio)
```

On startup (`__main__`):
1. Calls `load_stock_data()` — downloads 10 years of historical prices for all 30 tickers
2. Starts the Flask-SocketIO server on `0.0.0.0:5000`

---

## Configuration (config.py)

Centralised constants used across all modules:

| Constant | Value | Purpose |
|----------|-------|---------|
| `STARTING_NW` | 1000 | Initial net worth (£) |
| `MAX_ROUNDS` | 5 | Rounds per game |
| `HAND_SIZE` | 5 | Cards generated per round |
| `MAX_BENCH` | 10 | Maximum holdings slots |
| `INFLATION_RATE` | 0.02 | 2% per-quarter inflation on idle cash |
| `RISK_FREE_RATE` | 0.05 | 5% annual risk-free rate (for B-S pricing) |
| `OPTION_TERM` | 0.25 | Option term in years (1 quarter) |
| `TRADING_DAYS_QTR` | 63 | ~3 months of trading days |
| `CARD_BUY_COST_PCT` | 0.05 | 5% of S₀ cost to buy a card |
| `TICKER_POOL` | 30 tickers | Real stock symbols (AAPL, MSFT, GOOGL, ...) |

---

## Game State (game_state.py)

Manages the single global mutable `game` dictionary that holds all state:

### Game Dict Structure

```python
game = {
    "round": 0,              # Current round number
    "max_rounds": 5,          # Total rounds
    "phase": "lobby",         # lobby | buy | action | battle
    "mode": None,             # offline | multiplayer
    "date_idx": None,         # Index into stock price series
    "current_date": "",       # Human-readable market date
    "players": {
        "player_1": { ... },
        "player_2": { ... },
    },
}
```

### Player Dict Structure

```python
{
    "sid": None,              # Socket.IO session ID
    "connected": False,       # Connection status
    "is_bot": False,          # True for AI opponent
    "net_worth": 1000,        # Current NW (£)
    "hand": [],               # Available market cards
    "bench": [],              # Owned holdings
    "card_actions": {},       # {index: action} for current round
    "attack_puts": [],        # IDs of opponent cards targeted
    "ready": False,           # Phase-ready flag
    "trade_history": [],      # Per-round trade records
    "nw_history": [1000],     # NW at end of each round
    "options_played": 0,      # Total options deployed
    "options_won": 0,         # Options that produced positive value
}
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `fresh_player()` | Factory — returns a default player dict |
| `reset_game()` | Resets the global `game` to initial state |
| `player_state_for_client(pid)` | Serialises a personalised state view for one player, **stripping hidden data** (opponent's S₁ prices, bench details during buy phase) |

---

## Game Logic (game_logic.py)

The round lifecycle engine. Manages all phase transitions and combat resolution.

### Round Lifecycle

```
lobby → buy → action → battle → (next round or end)
                                    ↑           ↓
                                    └───────────┘
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `broadcast_state(socketio)` | Emits personalised `state_update` to each player |
| `start_new_round(socketio)` | Increments round, picks market date, generates hands, refreshes bench prices, enters buy phase |
| `advance_to_action_phase(socketio)` | Transitions to action phase, resets ready flags, triggers bot AI in offline mode |
| `resolve_battle(socketio)` | The core combat resolver (see [Battle Resolution](#battle-resolution)) |
| `end_game(socketio)` | Computes analytics (profit, drawdown, win rate), generates insights, emits `game_over` |
| `bot_play_buy_phase(socketio)` | AI buys cards greedily by volatility (σ) when C++ engine available |
| `bot_play_action_phase(socketio)` | AI assigns actions per bench card using C++ `get_ai_move()` |

### Battle Resolution

`resolve_battle()` processes each player's actions:

1. **Card Actions** — Iterates `card_actions` dict, computes `calc_delta()` for each action (place, call, defense_put), applies NW changes
2. **Attack Puts** — Resolves attack puts targeting opponent cards
3. **Bench Omega** — Applies passive `calc_omega()` growth/loss to ALL bench cards
4. **Inflation Penalty** — Calculates cash portion (NW minus stock value), deducts 2%
5. **History Update** — Records NW and trade history
6. **Game Over Check** — Ends if any player's NW ≤ 0 or round limit reached

---

## Combat System (combat.py)

Two pure mathematical functions with no side effects:

### `calc_omega(card) → float`

Passive bench growth/loss — the stock's natural price movement.

$$\omega = S_1 - S_0$$

### `calc_delta(action, card) → float`

Arena damage or recovery based on the action type:

| Action | Formula |
|--------|---------|
| `place` / `call` | $\Delta = \max(0, S_1 - S_0)$ |
| `attack_put` / `defense_put` | $\Delta = \max(0, S_0 - S_1)$ |
| `hold` | $\Delta = 0$ |

---

## Card Generation (cards.py)

Creates stock cards with real historical price data and Black-Scholes option premiums.

### `generate_stock_card(ticker, target_date) → dict`

1. Looks up the ticker in `stock_cache`
2. Finds the closest index to `target_date`
3. Extracts a 3-month (63 trading days) window: S₀ (start) and S₁ (end)
4. Computes annualised volatility (σ) from the window
5. Calculates ATM Black-Scholes call and put premiums
6. Returns the card dict:

```python
{
    "id": "AAPL_1234567890",
    "ticker": "AAPL",
    "s0": 150.25,            # Start price (visible to player)
    "s1": 162.80,            # End price (HIDDEN from client)
    "start_idx": 1500,
    "date_start": "2021-01-04",
    "date_end": "2021-03-31",
    "sigma": 0.32,           # Annualised volatility
    "call_premium": 12.45,   # Black-Scholes call price
    "put_premium": 8.73,     # Black-Scholes put price
}
```

### `pick_round_date(advance_from)`

Manages date progression across rounds — advances by one quarter (63 trading days) from the prior date index, or picks a random starting point for round 1.

### `card_for_client(card) → dict`

Strips the `s1` field before sending card data to the client, preventing players from seeing future prices.

---

## Financial Math (finance.py)

### `historical_volatility(series) → float`

Computes annualised volatility from a Pandas Series of daily prices:

$$\sigma = \text{std}(\ln(S_t / S_{t-1})) \times \sqrt{252}$$

### `black_scholes_premium(S, K, T, r, σ, option_type) → float`

Standard Black-Scholes European option pricing (ATM: K = S):

$$d_1 = \frac{\ln(S/K) + (r + \frac{\sigma^2}{2})T}{\sigma\sqrt{T}}$$

$$d_2 = d_1 - \sigma\sqrt{T}$$

**Call:** $C = S \cdot N(d_1) - K e^{-rT} \cdot N(d_2)$

**Put:** $P = K e^{-rT} \cdot N(-d_2) - S \cdot N(-d_1)$

Where $N(\cdot)$ is the standard normal CDF.

---

## Stock Data Loader (stock_data.py)

### `load_stock_data()`

Called once at boot. Downloads 10 years of daily close prices for all 30 tickers using `yfinance`:

```python
raw = yf.download(TICKER_POOL, period="10y", auto_adjust=True, threads=True)
```

For any ticker that fails to download, falls back to a synthetic GBM (Geometric Brownian Motion) simulation:

```python
# ~2,520 trading days, random base price 30-400
prices[i] = prices[i-1] * (1 + gauss(0.0004, 0.018))
```

All data is stored in `stock_cache: dict[str, pd.Series]`.

---

## AI Engine Bridge (ai_engine.py)

Python bridge to the compiled C++ AI engine via `ctypes`.

### Move Codes

| Code | Constant | Game Action |
|------|----------|-------------|
| 0 | `MOVE_ATTACK_PUT` | `attack_put` |
| 1 | `MOVE_DEFENSE_PUT` | `defense_put` |
| 2 | `MOVE_CALL` | `call` |
| 3 | `MOVE_PLACE` | `place` |

### `get_ai_move(prices, bot_nw, opp_nw) → int`

Calls the C++ `get_ai_move_ex` function with:
- A price lookback array
- The bot's current NW
- The opponent's current NW

Returns a move code (0–3).

### `is_available() → bool`

Returns `True` if the C++ shared library (`engine.dll` / `engine.so`) was successfully loaded. If unavailable, offline mode falls back to random moves.

---

## LLM Insights (llm_insights.py)

Generates post-game AI analysis using an LLM.

### Supported Providers

| Provider | Model | API Key |
|----------|-------|---------|
| **Groq** (recommended) | `llama-3.1-8b-instant` | `GROQ_API_KEY` |
| **OpenAI** | `gpt-4o-mini` | `OPENAI_API_KEY` |

Both use the `openai` Python SDK (Groq is API-compatible).

### `generate_llm_insights(player_id, analytics, opponent_analytics, winner) → str | None`

1. Checks for API key availability
2. Builds a structured prompt with:
   - Game result (win/loss/draw)
   - NW trajectory over all rounds
   - Round-by-round action breakdown
   - Opponent statistics summary
3. Sends to the LLM with a "Direct financial analyst" system prompt
4. Returns markdown-formatted analysis (< 600 words) or `None` on failure

---

## Data Flow

```
Browser (Client)
    ↕ Socket.IO
events.py (Event Handlers)
    ↓
game_logic.py (Phase Manager)
    ↓
    ├── cards.py → finance.py → stock_data.py
    │     (Card generation → B-S pricing → Price data)
    │
    ├── combat.py
    │     (Delta & omega calculations)
    │
    ├── ai_engine.py → engine.dll/so
    │     (Bot decisions via C++ heuristics)
    │
    └── llm_insights.py → Groq/OpenAI
          (Post-game analysis)
    ↓
game_state.py (State mutations)
    ↓
player_state_for_client() (Serialisation)
    ↕ Socket.IO
Browser (Client)
```
