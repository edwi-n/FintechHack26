# FintechHack26

* [ ] generate llm insights after game end
* [ ] bigger text
* [ ] news tab
* [ ] redo ui so looks slightly better

Category 1:
Data in Finance - Financial markets generate vast amounts of data, yet turning that information into meaningful insight remains a challenge.
<br>
Build a tool using financial data to inform decision-making or identify opportunities.


# FintechHack26

Category 1:
Data in Finance - Financial markets generate vast amounts of data, yet turning that information into meaningful insight remains a challenge.
<br>
Build a tool using financial data to inform decision-making or identify opportunities.

## 1. Core Architecture & Game Board

The game revolves around managing a portfolio and deploying derivatives to attack/defend.

**The Layout:**

* **The Market (Shop):** A pool of 5 randomly generated stocks available for purchase.
* **Holdings (Owned):** Slots for stocks the player currently owns. Stocks sitting here passively grow/shrink based on market movement ($\omega$).
* **The Portfolio (Arena):** The active zone where players assign actions (Puts, Calls, or Place/Hold) to attack their opponent or defend their Net Worth (N.W.).
* **Net Worth (N.W.) Tracker:** The player's health bar. If it hits zero, they lose.

## 2. The Game Loop (State Machine)

The game is split into two distinct phases.
In the beginning, a random time before 2022 (this can be changed depending on the mode chosen at the start of the game) is chosen. Then 5 random stocks at that time are placed in each player's market. Then the game continues by going forward 3 months in that stock.

### A. Ready Phase (Player Setup)

1. **Initialize:** Define Game Mode and # of Rounds.
2. **Buy Phase:** P1 and P2 can buy stocks from their "Market" and move them to their "Holdings".
3. **Action Phase:** Players choose what to do in the Portfolio, they have the following options for every asset in their holdings:
* *Place Card:* Deploy a standard stock to the portfolio.
* *Attack Put* Hedge your own stock.
* *Call:* Deploy a Call option.
* *Hold State:* Pass/Wait.
  The player has the following options for every asset in the opponent's holdings:
* *Attack Put* Target an opponent's stock.

  Each player can see the past 6 months' stock data for each stock.


4. **Premium Calculation:** If an Option (Call/Put) is chosen, the game calculates the Premium using the Black-Scholes (B-S) Model.
* **State Update:** $N.W. = N.W. - \text{Premium}$



### B. Battle Phase (3 Months Later)

1. **Time Jump:** The backend fetches updated stock prices ($S_1$).
2. **Calculate Arena $\Delta$:** The game calculates the damage/shield value for P1 and P2 based on their deployed assets.
3. **Calculate Bench $\omega$:** The intrinsic growth/loss of held stocks is calculated and added to the player's Net Worth.
4. **Inflation:** Deduct a flat inflation penalty from cash holdings.
5. **Cleanup:** Return played assets to holdings and regenerate the Market for the next round.

---

## 3. Combat Math & Equations

### 1. The Holdings (Passive Growth)

Stocks in holdings do not trigger options math, they just grow or shrink based on standard price movement.

* **Formula:** $\omega = S_1 - S_0$ 
* **Action:** Add $\omega$ to the owner's Net Worth.

### 2. Attack Put (Targeting Opponent's Stock)

You are betting the opponent's stock will crash.

* **Formula:** $\Delta = \min(S_1 - S_0, 0)$
* **Action:** Subtract from opponent's N.W.
* *Example:* If their stock drops from £100 to £80, $\Delta = -20$. You subtract -20 from their N.W. (dealing 20 damage).

### 3. Defense Put (Hedging Your Own Stock)

You are protecting your held stock from a crash.

* **Formula:** $\Delta = \min(0, S_1 - S_0)$
* **Action:** Add to your N.W.
* *Example:* If your stock drops from £100 to £80, $\Delta = -20$. By adding this absolute value back to your N.W., it cancels out the $\omega$ loss you took on the bench.

### 4. Call (Leveraged Upward Bet)

You are betting a stock will surge.

* **Formula:** $\Delta = \min(0, S_0 - S_1)$
* **Action:** Subtract from opponent's N.W.
* *Example:* If the stock surges from £100 to £130, $S_0 - S_1 = -30$. $\Delta = -30$. Subtract -30 from the opponent's N.W. (dealing 30 damage).

### 5. Place (Standard Attack)

Deploying a raw stock to the arena for standard damage.

* **Formula:** $\Delta = \min(0, S_0 - S_1)$

---

## 4. End of Game: Analytics Dashboard (Category 1 Focus)

When the round limit is reached, the game renders the Category 1 Analytics Dashboard containing:

* **Total Profit**
* **Options Win Rate** (Percentage of Calls/Puts that resulted in positive damage/defense).
* **Max Drawdown** (Peak-to-trough drop in N.W.).
* **Graph of Portfolio Value** (Line chart tracking N.W. over the rounds).

---

## 5. Installation & Setup

### Prerequisites

- **Python 3.10+**
- **g++ (64-bit)** — required only for the offline AI backtester

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd FintechHack26
pip install -r requirements.txt
```

### 2. Compile the C++ backtesting engine (optional — offline mode AI)

The offline bot is powered by a C++ heuristic engine. Compile it to enable the smart AI opponent:

**Windows (MinGW-w64):**

```powershell
# Install a 64-bit compiler if you only have 32-bit MinGW:
winget install BrechtSanders.WinLibs.POSIX.UCRT

# Compile (must match your Python architecture — typically 64-bit):
cd backtester
x86_64-w64-mingw32-g++ -shared -O2 -o engine.dll engine.cpp
```

**Linux / macOS:**

```bash
cd backtester
g++ -shared -fPIC -O2 -o engine.so engine.cpp
```

> **Note:** If the DLL/SO is missing, offline mode falls back to a random-move bot.

### 3. Run the server

```bash
python app.py
```

The game starts at [http://localhost:5000](http://localhost:5000).

### 4. Run the backtester (standalone)

```bash
cd backtester
python backtest.py
```

This runs 10,000 simulated games and prints AI win rate, average profit, and max drawdown.
