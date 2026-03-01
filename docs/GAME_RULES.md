# Game Rules & Combat

[← Back to Main README](../README.md)

Complete rules for Trading Arena — the strategic stock battle game.

---

## Table of Contents

- [Objective](#objective)
- [Setup](#setup)
- [The Game Board](#the-game-board)
- [Game Flow](#game-flow)
  - [Phase 1: Buy Phase](#phase-1-buy-phase)
  - [Phase 2: Action Phase](#phase-2-action-phase)
  - [Phase 3: Battle Phase](#phase-3-battle-phase)
- [Actions Reference](#actions-reference)
- [Combat Math](#combat-math)
  - [Bench Passive Growth (Omega)](#bench-passive-growth-omega)
  - [Attack Put](#attack-put)
  - [Defense Put](#defense-put)
  - [Call](#call)
  - [Place](#place)
- [Premiums (Black-Scholes)](#premiums-black-scholes)
- [Inflation](#inflation)
- [Win Conditions](#win-conditions)
- [End-Game Analytics](#end-game-analytics)
- [Strategy Guide](#strategy-guide)

---

## Objective

Start with **£1,000**. Outperform your opponent over **5 rounds** by buying stocks, deploying derivatives (Puts/Calls), and attacking their Net Worth while defending yours.

**Win by:**
- Having a higher Net Worth after 5 rounds, or
- Knocking your opponent's Net Worth to **£0 or below** (KO)

---

## Setup

1. Choose a game mode:
   - **Play vs AI** — offline against a C++ bot
   - **Multiplayer** — real-time against another player
2. A random historical market date (pre-2022) is selected
3. Each player starts with £1,000 and an empty portfolio

---

## The Game Board

| Zone | Description |
|------|-------------|
| **The Market (Shop)** | 5 randomly generated stock cards available for purchase. Changes every round. |
| **Holdings (Bench)** | Stocks you own. These passively grow or shrink based on real market movement. Max 10 slots. |
| **The Portfolio (Arena)** | Where you assign actions — deploy puts, calls, or place cards to attack/defend. |
| **Net Worth Tracker** | Your "health bar". Displays current NW and available cash. |
| **Opponent Zone** | Shows opponent's holdings (visible during action phase) and their NW. |
| **Trade Log** | Live feed of game events and server messages. |

---

## Game Flow

Each round represents a **3-month market quarter** and has three phases:

### Phase 1: Buy Phase

**What you see:** 5 stock cards in The Market, each showing:
- Ticker symbol (e.g., AAPL, MSFT)
- Current price (S₀)
- Date range
- Call and put premiums
- Historical volatility (σ)
- 📈 button to view 6 months of price history

**What you do:**
- **Buy** cards from The Market → moves to your Holdings
  - Cost: **5% of S₀** (transaction fee)
- **Sell** cards from your Holdings → returns to The Market
- Click **"Done Buying"** when finished

Both players must confirm before advancing.

### Phase 2: Action Phase

**What you see:** Your Holdings (with action buttons) and the opponent's Holdings.

**What you do — for each card in YOUR Holdings:**

| Action | Effect | Cost |
|--------|--------|------|
| **Place** | Deploy to arena — deals damage if stock rises | Free |
| **Defense Put** | Hedge against stock dropping — recover losses | Put premium |
| **Call** | Leveraged bet on stock rising — deals extra damage | Call premium |
| *(No action)* | Card stays on bench — passive growth/loss only | Free |

**What you do — for each card in OPPONENT's Holdings:**

| Action | Effect | Cost |
|--------|--------|------|
| **Attack Put** | Bet opponent's stock crashes — deals damage if it drops | Put premium |

Click **"Confirm Actions"** when finished. Both players must confirm before battle.

### Phase 3: Battle Phase

**What happens (automatically):**

1. **Time Jump** — 3 months pass. The hidden future price (S₁) is revealed for all cards.
2. **Arena Resolution** — All Placed, Called, Attack Put, and Defense Put actions resolve.
3. **Bench Growth** — All Holdings passively gain/lose based on $\omega = S_1 - S_0$.
4. **Inflation** — Cash sitting idle loses 2%.
5. **Cleanup** — Market regenerates for the next round.

An animated battle result overlay shows all events with damage/gain values.

---

## Actions Reference

### Summary Table

| Action | Target | Revenue When... | Cost |
|--------|--------|-----------------|------|
| **Place** | Own card → Arena | Stock rises ($S_1 > S_0$) | Free |
| **Call** | Own card → Arena | Stock rises ($S_1 > S_0$) | Call premium |
| **Defense Put** | Own card | Stock falls ($S_1 < S_0$) | Put premium |
| **Attack Put** | Opponent's card | Stock falls ($S_1 < S_0$) | Put premium |
| **Hold** | Own card (default) | — | Free |

---

## Combat Math

All combat uses real historical stock prices. S₀ is the price at the start of the quarter, S₁ is the actual price 3 months later.

### Bench Passive Growth (Omega)

Every stock in Holdings automatically grows or shrinks:

$$\omega = S_1 - S_0$$

- **Positive ω**: stock rose → owner gains NW
- **Negative ω**: stock fell → owner loses NW
- Applied to ALL bench cards, regardless of actions

### Attack Put

Betting an opponent's stock will crash.

$$\Delta = \max(0,\ S_0 - S_1)$$

- **Stock drops** (S₁ < S₀): $\Delta > 0$ → subtracted from opponent's NW
- **Stock rises** (S₁ ≥ S₀): $\Delta = 0$ → no effect (but you still paid the premium)

**Example:** Opponent holds TSLA at S₀ = £200. You buy an Attack Put (premium: £15). TSLA drops to S₁ = £160.
- $\Delta = \max(0, 200 - 160) = 40$
- Opponent loses £40. You paid £15 premium. Net profit: £25.

### Defense Put

Hedging your own stock against a crash.

$$\Delta = \max(0,\ S_0 - S_1)$$

- **Stock drops** (S₁ < S₀): $\Delta > 0$ → added to YOUR NW (offsets the $\omega$ loss)
- **Stock rises** (S₁ ≥ S₀): $\Delta = 0$ → no effect (premium lost, but $\omega$ gain compensates)

**Example:** You hold AAPL at S₀ = £150. You buy a Defense Put (premium: £10). AAPL drops to S₁ = £120.
- Bench loss: $\omega = 120 - 150 = -30$
- Defense Put: $\Delta = \max(0, 150 - 120) = 30$
- Net effect: £0 (the put perfectly hedges the loss). You only lost the £10 premium.

### Call

Leveraged bet on a stock surging.

$$\Delta = \max(0,\ S_1 - S_0)$$

- **Stock rises** (S₁ > S₀): $\Delta > 0$ → subtracted from opponent's NW
- **Stock falls** (S₁ ≤ S₀): $\Delta = 0$ → no effect (premium lost)

**Example:** You hold NVDA at S₀ = £100. You buy a Call (premium: £8). NVDA surges to S₁ = £140.
- $\Delta = \max(0, 140 - 100) = 40$
- Opponent loses £40. You paid £8 premium. Net: +£32 damage dealt.

### Place

Deploy a stock to the arena for standard damage (like a Call but free).

$$\Delta = \max(0,\ S_1 - S_0)$$

- Same formula as Call
- **No premium cost** — but also no Call premium leverage benefit in future rules

---

## Premiums (Black-Scholes)

When you play a Call or Put action, you pay a premium upfront, deducted immediately from your NW:

$$N.W. = N.W. - \text{Premium}$$

Premiums are calculated using the **Black-Scholes model** with:

| Parameter | Value | Source |
|-----------|-------|--------|
| $S$ (spot price) | Card's S₀ | Historical data |
| $K$ (strike price) | S₀ (at-the-money) | Equals spot |
| $T$ (time to expiry) | 0.25 years | 3-month quarter |
| $r$ (risk-free rate) | 5% annual | Config constant |
| $\sigma$ (volatility) | Computed from card | Historical log-returns |

**Call Premium:**
$$C = S \cdot N(d_1) - K e^{-rT} \cdot N(d_2)$$

**Put Premium:**
$$P = K e^{-rT} \cdot N(-d_2) - S \cdot N(-d_1)$$

Where:
$$d_1 = \frac{\ln(S/K) + (r + \frac{\sigma^2}{2})T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$

---

## Inflation

Each round, idle cash is penalised by **2% inflation**:

$$\text{Cash} = N.W. - \sum_{i} S_{1,i} \quad \text{(NW minus total stock value)}$$
$$\text{Inflation Penalty} = \text{Cash} \times 0.02$$

This incentivises players to stay fully invested rather than hoarding cash.

---

## Win Conditions

| Condition | Trigger |
|-----------|---------|
| **Round Limit** | After 5 rounds → highest NW wins |
| **KO** | Any player's NW drops to £0 or below → they lose immediately |
| **Draw** | Both players reach £0 in the same round, or equal NW at game end |

---

## End-Game Analytics

The post-game dashboard presents:

| Metric | Description |
|--------|-------------|
| **Total Profit** | Final NW − Starting NW (£1,000) |
| **Options Win Rate** | % of Calls/Puts that produced positive value |
| **Max Drawdown** | Largest peak-to-trough NW decline |
| **Final NW** | Ending net worth |
| **NW Over Time Chart** | Line chart tracking portfolio value per round |
| **Strategy Insights** | Rule-based analysis of your play |
| **AI Strategy Advisor** | LLM-powered personalised analysis (if API key configured) |

---

## Strategy Guide

### Key Principles

1. **Defense Put is the safest action** — It offsets bench losses for the cost of a premium. If the stock rises, you keep the bench gain. If it falls, the put pays out.

2. **Attack Puts are high-risk, high-reward** — You need the opponent's stock to drop. If it rises, you lose the premium for nothing.

3. **Calls are premium-costed Place cards** — Same upside as Place but costs a premium. Best used on high-volatility stocks you're confident will rise.

4. **Stay invested** — The 2% inflation penalty on cash means holding no stocks is actively losing money.

5. **Buy high-volatility stocks** — More volatile stocks (higher σ) have larger potential swings, meaning bigger omega gains AND bigger action payouts.

6. **Watch the 📈 charts** — 6 months of price history helps predict whether a stock is trending up or down.

### Common Mistakes

- **Hoarding cash** → inflation eats your NW every round
- **All-in Attack Puts** → if the market rises, you lose every premium
- **Ignoring Defense Puts** → a market crash without hedging can KO you
- **Buying low-vol stocks** → low σ means small premiums but also tiny payouts
