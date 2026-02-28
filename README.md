# FintechHack26

* [ ] inflation only occurs on cash and not stocks
* [ ] generate llm insights after game end
* [ ] animations & sound effects ( )
* [ ] change icons
* [ ] change button in the top right
* [ ] bigger text
* [ ] implement a simple quant algorithm for ai player
* [ ] news tab
* [ ] don't show results immediately, instead the screen darkens and have animations for net worth and critical hits...
* [ ] emotes

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

* **The Hand (Shop):** A pool of 5 randomly generated stocks available for purchase.
* **The Bench (Owned):** Slots for stocks the player currently owns. Stocks sitting here passively grow/shrink based on market movement ($\omega$).
* **The Battlefield (Arena):** The active zone where players place cards (Puts, Calls, or Place/Hold) to attack their opponent or defend their Net Worth (N.W.).
* **Net Worth (N.W.) Tracker:** The player's health bar. If it hits zero, they lose.

## 2. The Game Loop (State Machine)

The game is split into two distinct phases.
In the beginning, a random time before 2022 (this can be changed depending on the mode chosen at the start of the game) is chosen. Then 5 random stock at that time are placed on each player's hand. Then the game continues by going forward 3 months in that stock.

### A. Ready Phase (Player Setup)

1. **Initialize:** Define Game Mode and # of Rounds.
2. **Buy Phase:** P1 and P2 can buy stocks from their "Hand" and move them to their "Bench".
3. **Action Phase:** Players choose what to do in the Arena, they have the following options for every card in their bench:
* *Place Card:* Deploy a standard stock to the battlefield.
* *Attack Put* Hedge your own stock.
* *Call:* Deploy a Call option.
* *Hold State:* Pass/Wait.
  The player has the following options for every card in the opponents bench:
* *Attack Put* Target an opponent's stock.

  Each player can see the past 6 months' stock data for each stock.


4. **Premium Calculation:** If an Option (Call/Put) is chosen, the game calculates the Premium using the Black-Scholes (B-S) Model.
* **State Update:** $N.W. = N.W. - \text{Premium}$



### B. Battle Phase (3 Months Later)

1. **Time Jump:** The backend fetches updated stock prices ($S_1$).
2. **Calculate Arena $\Delta$:** The game calculates the damage/shield value for P1 and P2 based on their deployed cards.
3. **Calculate Bench $\omega$:** The intrinsic growth/loss of benched stocks is calculated and added to the player's Net Worth.
4. **Inflation:** Deduct a flat inflation penalty from cash holdings.
5. **Cleanup:** Return played cards to the bench (if applicable) and regenerate the Hand for the next round.

---

## 3. Combat Math & Equations

*Note: $S_0$ = Starting Price, $S_1$ = New Price after 3 months)*

### 1. The Bench (Passive Growth)

Stocks on the bench do not trigger options math, they just grow or shrink based on standard price movement.

* **Formula:** $\omega = S_1 - S_0$ 
* **Action:** Add $\omega$ to the owner's Net Worth.

### 2. Attack Put (Targeting Opponent's Stock)

You are betting the opponent's stock will crash.

* **Formula:** $\Delta = \min(S_1 - S_0, 0)$
* **Action:** Subtract from opponent's N.W.
* *Example:* If their stock drops from £100 to £80, $\Delta = -20$. You subtract -20 from their N.W. (dealing 20 damage).

### 3. Defense Put (Hedging Your Own Stock)

You are protecting your benched stock from a crash.

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
