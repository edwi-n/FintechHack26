# Trading Arena — Strategic Stock Battle

> **Hackathon Category:** Data in Finance — *Financial markets generate vast amounts of data, yet turning that information into meaningful insight remains a challenge. Build a tool using financial data to inform decision-making or identify opportunities.*

**Trading Arena** is a two-player strategy card game where players manage stock portfolios and deploy derivatives (Puts, Calls) to attack opponents and defend their Net Worth. It uses **real historical stock data** (10 years via Yahoo Finance), **Black-Scholes option pricing**, and a **C++ AI engine** — turning financial market analysis into a competitive, strategic experience.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Game](#running-the-game)
- [Detailed Documentation](#detailed-documentation)
- [Tech Stack](#tech-stack)
- [Configuration](#configuration)

---

## Overview

Players start with **£1,000** and compete over **5 rounds**, each representing a **3-month market quarter**. Every round has three phases:

1. **Buy Phase** — Purchase stock cards from a randomly generated market.
2. **Action Phase** — Assign derivative actions (Place, Call, Defense Put, Attack Put) to your holdings and target opponent assets.
3. **Battle Phase** — Time jumps 3 months forward, stock prices reveal, combat resolves, and Net Worth updates.

The player with the highest Net Worth at the end wins — or knock your opponent to £0 for an early KO.

### Game Modes

| Mode | Description |
|------|-------------|
| **Play vs AI** | Offline single-player against a C++ heuristic bot |
| **Multiplayer** | Real-time two-player via Socket.IO |

---

## How It Works

### The Game Board

| Zone | Purpose |
|------|---------|
| **The Market (Shop)** | 5 randomly generated stock cards available for purchase each round |
| **Holdings (Bench)** | Stocks the player owns — passively grow/shrink via market movement ($\omega$) |
| **The Portfolio (Arena)** | Where players assign actions to attack opponents or defend their Net Worth |
| **Net Worth Tracker** | The player's "health bar" — hits zero and you lose |

### Combat Math

| Action | Formula | Effect |
|--------|---------|--------|
| **Bench (Passive)** | $\omega = S_1 - S_0$ | Added to owner's NW automatically |
| **Place / Call** | $\Delta = \max(0, S_1 - S_0)$ | Subtracted from opponent's NW |
| **Attack Put** | $\Delta = \max(0, S_0 - S_1)$ | Subtracted from opponent's NW |
| **Defense Put** | $\Delta = \max(0, S_0 - S_1)$ | Added to owner's NW (offsets bench losses) |

Options (Call, Put) charge a **Black-Scholes premium** upfront, deducted from your NW.

### End-of-Game Analytics

The game renders a full analytics dashboard:
- **Total Profit** — net gain/loss from starting £1,000
- **Options Win Rate** — percentage of derivatives that produced positive value
- **Max Drawdown** — peak-to-trough drop in NW
- **NW Over Time Chart** — line chart tracking portfolio value per round
- **AI Strategy Advisor** — LLM-powered post-game analysis (Groq or OpenAI)

---

## Project Structure

```
FintechHack26/
├── app.py                  # Entry point — Flask + SocketIO server
├── requirements.txt        # Python dependencies
├── README.md               # This file
│
├── server/                 # Backend game engine
│   ├── config.py           # Game constants & ticker pool
│   ├── game_state.py       # Global mutable game state
│   ├── game_logic.py       # Round lifecycle & phase transitions
│   ├── events.py           # Socket.IO event handlers
│   ├── combat.py           # Delta & omega calculations
│   ├── cards.py            # Stock card generation & Black-Scholes
│   ├── finance.py          # Financial math (volatility, B-S pricing)
│   ├── stock_data.py       # Yahoo Finance data loader + GBM fallback
│   ├── ai_engine.py        # Python ↔ C++ bridge (ctypes)
│   └── llm_insights.py     # Post-game LLM analysis (Groq/OpenAI)
│
├── backtester/             # Standalone AI backtesting suite
│   ├── engine.cpp          # C++ AI engine & batch simulator
│   └── backtest.py         # Python harness for 10k-game simulations
│
├── templates/
│   └── index.html          # Main game HTML (Jinja2 template)
│
└── static/
    ├── css/
    │   └── styles.css      # Brutalist Bloomberg Terminal aesthetic
    └── js/
        ├── socket.js       # Socket.IO connection & event wiring
        ├── renderer.js     # DOM rendering engine (state → UI)
        ├── actions.js      # UI action dispatchers → socket emits
        ├── analytics.js    # Battle animations, sounds, analytics display
        ├── charts.js       # Chart.js wrappers (stock history, NW chart)
        └── log.js          # Trade log panel utility
```

---

## Installation & Setup

### Prerequisites

- **Python 3.10+**
- **g++ (64-bit)** — only needed for the offline AI bot & backtester

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd FintechHack26
pip install -r requirements.txt
```

### 2. Compile the C++ engine (optional — enables smart AI)

The offline bot uses a compiled C++ heuristic engine. Without it, the bot falls back to random moves.

**Windows (MinGW-w64):**

```powershell
# Install a 64-bit compiler if needed:
winget install BrechtSanders.WinLibs.POSIX.UCRT

# Compile (must match Python architecture — typically 64-bit):
cd backtester
x86_64-w64-mingw32-g++ -shared -O2 -o engine.dll engine.cpp
```

**Linux / macOS:**

```bash
cd backtester
g++ -shared -fPIC -O2 -o engine.so engine.cpp
```

### 3. Set up LLM insights (optional)

For AI-powered post-game strategy analysis, set one of these environment variables:

```bash
# Groq (free, recommended — uses llama-3.1-8b-instant)
export GROQ_API_KEY=your_key_here

# OR OpenAI (uses gpt-4o-mini)
export OPENAI_API_KEY=your_key_here
```

---

## Running the Game

### Start the server

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### Run the backtester (standalone)

```bash
cd backtester
python backtest.py
```

Runs **10,000 simulated games** (AI vs random) and reports win rate, average profit, and max drawdown.

---

## Detailed Documentation

| Document | Description |
|----------|-------------|
| [Server Architecture](docs/SERVER.md) | Backend modules, game state, round lifecycle, financial math |
| [Frontend Guide](docs/FRONTEND.md) | UI components, rendering pipeline, animations, sound engine |
| [Game Rules & Combat](docs/GAME_RULES.md) | Complete game rules, phase breakdown, combat math with examples |
| [AI Engine & Backtester](docs/AI_ENGINE.md) | C++ engine design, AI strategy, backtesting methodology |
| [API Reference](docs/API.md) | All Socket.IO events, payloads, and data flow |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Server** | Python, Flask, Flask-SocketIO |
| **Real-time** | Socket.IO (WebSocket) |
| **Stock Data** | Yahoo Finance (`yfinance`) with GBM simulation fallback |
| **Financial Math** | NumPy, Pandas, SciPy (Black-Scholes, historical volatility) |
| **AI Engine** | C++ (compiled to DLL/SO), loaded via Python `ctypes` |
| **LLM Insights** | Groq (llama-3.1-8b-instant) or OpenAI (gpt-4o-mini) |
| **Frontend** | Vanilla JS, Chart.js, Web Audio API |
| **Styling** | Custom CSS — Brutalist Bloomberg Terminal aesthetic |

---

## Configuration

All game constants are in [`server/config.py`](server/config.py):

| Constant | Default | Description |
|----------|---------|-------------|
| `STARTING_NW` | 1000 | Starting net worth (£) |
| `MAX_ROUNDS` | 5 | Number of rounds per game |
| `HAND_SIZE` | 5 | Cards generated per round |
| `MAX_BENCH` | 10 | Maximum holdings slots |
| `INFLATION_RATE` | 0.02 | Per-quarter inflation on idle cash (2%) |
| `RISK_FREE_RATE` | 0.05 | Annual risk-free rate for Black-Scholes (5%) |
| `OPTION_TERM` | 0.25 | Option term in years (3 months) |
| `TRADING_DAYS_QTR` | 63 | Trading days per quarter |
| `CARD_BUY_COST_PCT` | 0.05 | Cost to buy a card (5% of S₀) |
| `TICKER_POOL` | 30 tickers | Pool of real stocks (AAPL, MSFT, GOOGL, ...) |
