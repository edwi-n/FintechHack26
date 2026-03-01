# Frontend Guide

[← Back to Main README](../README.md)

The frontend is a single-page application built with vanilla JavaScript, Socket.IO for real-time communication, and Chart.js for data visualisation. It uses a **Brutalist Bloomberg Terminal** aesthetic.

---

## Table of Contents

- [Architecture](#architecture)
- [HTML Template](#html-template)
- [Styling](#styling)
- [JavaScript Modules](#javascript-modules)
  - [socket.js — Connection & Events](#socketjs--connection--events)
  - [renderer.js — DOM Rendering Engine](#rendererjs--dom-rendering-engine)
  - [actions.js — Action Dispatchers](#actionsjs--action-dispatchers)
  - [analytics.js — Battle Animations & Analytics](#analyticsjs--battle-animations--analytics)
  - [charts.js — Chart.js Wrappers](#chartsjs--chartjs-wrappers)
  - [log.js — Trade Log Utility](#logjs--trade-log-utility)
- [UI Components](#ui-components)
- [Animations & Sound](#animations--sound)
- [CDN Dependencies](#cdn-dependencies)

---

## Architecture

```
templates/index.html          ← Jinja2 template (served by Flask)
  ↓ loads
static/js/
  ├── log.js                  ← Lowest dependency (utilities)
  ├── charts.js               ← Chart.js wrappers
  ├── renderer.js             ← DOM rendering (depends on log, charts)
  ├── actions.js              ← UI → Socket dispatchers
  ├── analytics.js            ← Battle overlays, sounds, analytics
  └── socket.js               ← Socket.IO connection (depends on all above)
```

Scripts are loaded in strict dependency order at the bottom of `index.html`. All modules communicate through global functions and a shared `socket` variable.

---

## HTML Template

`templates/index.html` is a Jinja2 template with these major sections:

| Section | Element ID | Purpose |
|---------|-----------|---------|
| **Top Bar** | `#topBar` | Game title, round counter, current date |
| **Mode Selection** | `#modeMenu` | "Play vs AI" and "Multiplayer" buttons |
| **Lobby** | `#lobby` | Waiting screen for multiplayer matchmaking |
| **Game Board** | `#gameBoard` | Two-column grid: player zone + opponent zone |
| **Stock Chart Modal** | `#chartModal` | Overlay with Chart.js canvas for price history |
| **Battle Result Overlay** | `#battleOverlay` | Animated round results |
| **Analytics Overlay** | `#analyticsOverlay` | Post-game analysis dashboard |

### Game Board Layout

```
┌─────────────────────────────────────────────┐
│                  Top Bar                    │
├──────────────────────┬──────────────────────┤
│   Player Zone        │   Opponent Zone      │
│  ┌────────────────┐  │  ┌────────────────┐  │
│  │ Market (Shop)  │  │  │ Opp. Holdings  │  │
│  │ 5 stock cards  │  │  │ with Atk Put   │  │
│  ├────────────────┤  │  ├────────────────┤  │
│  │ Holdings       │  │  │ Trade Log      │  │
│  │ Owned stocks   │  │  │ Event feed     │  │
│  ├────────────────┤  │  │                │  │
│  │ Action Panel   │  │  │                │  │
│  │ Phase controls │  │  │                │  │
│  └────────────────┘  │  └────────────────┘  │
└──────────────────────┴──────────────────────┘
```

---

## Styling

`static/css/styles.css` (~1,040 lines) implements the Bloomberg Terminal look:

### Design Tokens (CSS Custom Properties)

```css
:root {
    --bg:       #0a0a0a;     /* Near-black background */
    --surface:  #141414;     /* Card/panel backgrounds */
    --border:   #2a2a2a;     /* Subtle borders */
    --text:     #e0e0e0;     /* Primary text */
    --accent:   #00FF41;     /* Terminal green — primary accent */
    --red:      #FF3131;     /* Damage / negative values */
    --gold:     #FFD700;     /* Highlights / premium info */
    --blue:     #4169E1;     /* Secondary accent */
}
```

### Key Visual Features

- **Monospace typography** — `'Courier New', monospace` throughout
- **Zero border-radius** — sharp corners on all elements (brutalist)
- **CRT scanline overlay** — `body::after` pseudo-element with repeating gradient lines
- **Vibrant colour coding** — green for gains, red for losses, gold for highlights
- **Action badges** — colour-coded indicators for Place (gold), Attack Put (red), Defense Put (blue), Call (green)

### Button Variants

| Class | Colour | Use Case |
|-------|--------|----------|
| `.btn-primary` | Green | General primary actions |
| `.btn-place` | Gold | Place card action |
| `.btn-attack` | Red | Attack put action |
| `.btn-defense` | Blue | Defense put action |
| `.btn-call` | Green | Call option action |
| `.btn-sell` | Orange | Sell from holdings |
| `.btn-ready` | Green | Confirm/ready buttons |
| `.btn-restart` | Red | Restart game |

### Responsive Breakpoint

At `768px`, the two-column game board stacks vertically.

---

## JavaScript Modules

### socket.js — Connection & Events

Establishes the Socket.IO connection and wires all incoming server events to handler functions.

**Global State:**

```javascript
var myPlayerId   = null;    // "player_1" or "player_2"
var myPlayerNum  = null;    // 1 or 2
var currentState = null;    // Latest game state from server
var gameMode     = null;    // "offline" or "multiplayer"
```

**Incoming Event → Handler Mapping:**

| Server Event | Handler | Description |
|-------------|---------|-------------|
| `connect` | — | Logs connection |
| `disconnect` | — | Logs disconnection |
| `player_assigned` | Stores player ID | Assigns player slot |
| `server_message` | `addLog()` | Displays server messages in trade log |
| `error` | `addLog()` | Shows errors |
| `state_update` | `renderState()` | Full UI re-render |
| `battle_result` | `showBattleResult()` | Animated battle overlay |
| `game_over` | `showAnalytics()` | End-game analytics |
| `game_reset` | `location.reload()` | Full page reload |
| `stock_chart_data` | `showStockChart()` | Price history chart |
| `llm_insights` | `handleLLMInsights()` | AI strategy analysis |

---

### renderer.js — DOM Rendering Engine

The main rendering pipeline. Takes game state objects and updates all DOM elements.

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `renderState(s)` | Master render — updates round info, NW displays, shows/hides panels, delegates to sub-renderers |
| `updateNW(id, value)` | Updates net worth display with colour coding (red < 0, gold, green ≥ 100k) and flash animation |
| `renderHand(hand, phase)` | Renders market cards with ticker, price (S₀), date range, premiums, and buy button |
| `renderBench(bench, phase, cardActions, ready)` | Renders holdings with action badges and phase-specific buttons |
| `renderArena(s)` | Summarises assigned actions in the arena panel |
| `renderOpponentBench(bench, phase, attackPuts, ready)` | Renders opponent holdings with attack put toggle buttons |
| `renderActions(s)` | Updates the action control panel per phase |

**Net Worth Colour Logic:**
- Red: NW < 0
- Gold: default
- Green: NW ≥ 100,000

**Card Rendering includes:**
- Ticker symbol and date range
- Current price (S₀)
- Call/put premiums
- Volatility (σ)
- Historical chart button (📈)
- Action-specific badges and buttons

---

### actions.js — Action Dispatchers

Thin layer mapping UI button clicks to Socket.IO `emit()` calls:

| Function | Emits | Payload |
|----------|-------|---------|
| `selectMode(mode)` | `select_mode` | `{mode}` |
| `buyStock(i)` | `buy_stock` | `{player_id, index}` |
| `sellStock(i)` | `sell_stock` | `{player_id, index}` |
| `endBuyPhase()` | `end_buy_phase` | `{player_id}` |
| `setCardAction(idx, action)` | `set_card_action` | `{player_id, card_index, action}` |
| `toggleAttackPut(cardId)` | `toggle_attack_put` | `{player_id, target_id}` |
| `confirmActions()` | `confirm_actions` | `{player_id}` |
| `restartGame()` | `restart_game` | — |

---

### analytics.js — Battle Animations & Analytics

Handles all animated overlays, sound effects, and post-game rendering.

#### Sound Engine

Uses the **Web Audio API** with synthesised oscillator tones — no audio files needed:

| Sound | Trigger |
|-------|---------|
| `damage` | Opponent takes damage |
| `gain` | Player gains NW |
| `critical` | Large delta (> £50) |
| `victory` | Player wins |
| `defeat` | Player loses |
| `buy` | Stock purchased |
| `confirm` | Actions confirmed |

#### Battle Result Overlay

`showBattleResult(result)` orchestrates an animated round summary:

1. Displays NW for both players with smooth counter animation
2. Sequentially reveals battle events with staggered delays
3. Detects **critical hits** (delta > £50) and triggers screen shake
4. Auto-dismisses after all events are shown

#### End-Game Analytics

`showAnalytics(data)` renders the post-game dashboard:

- Winner banner (or draw)
- Stat cards: Total Profit, Options Win Rate, Max Drawdown, Final NW
- NW over time chart (Chart.js)
- Rule-based strategy insights
- LLM AI Advisor section (loads asynchronously)

#### Markdown Renderer

`renderMarkdown(md)` — a lightweight markdown-to-HTML converter supporting:
- Headers (`#`, `##`, `###`)
- Bold (`**text**`)
- Italic (`*text*`)
- Unordered lists (`- item`)
- Horizontal rules (`---`)
- Paragraphs

---

### charts.js — Chart.js Wrappers

Two chart types:

#### Stock Price History Chart

`showStockChart(data)` — modal overlay showing ~6 months of historical prices for a stock card:

- Line chart with the current price highlighted in gold
- Sparse date labels (every 8th date)
- Opens via the 📈 button on each card

#### Net Worth Over Time Chart

`renderNWChart(my, opp)` — dual-line chart shown in the analytics overlay:

- Green solid line = player's NW per round
- Red dashed line = opponent's NW per round

---

### log.js — Trade Log Utility

Minimal utility for the on-screen trade log in the opponent zone:

```javascript
addLog(msg, cls)  // cls: "info" | "damage" | "gain"
```

- Prepends new entries to the log panel
- Caps display at 50 entries (trims oldest)
- Colour-coded by CSS class

---

## UI Components

### Stock Card

```
┌──────────────────────────┐
│ [ACTION BADGE]           │
│ AAPL                     │
│ 2021-01-04 → 2021-03-31 │
│ Price: £150.25    📈     │
│ Call: £12.45 Put: £8.73  │
│ σ: 32.1%                 │
│ [Buy Asset] / [Actions]  │
└──────────────────────────┘
```

### Net Worth Display

```
┌─────────────────┐
│ YOUR N.W.       │
│ £1,247.50       │  ← Gold text, flashes on change
│ Cash: £420.25   │
├─────────────────┤
│ OPP. N.W.       │
│ £892.30         │  ← Red if losing
└─────────────────┘
```

---

## Animations & Sound

### CSS Animations

| Animation | Use |
|-----------|-----|
| `fadeIn` | General element entrance |
| `scaleIn` | Modal/overlay entrance |
| `slideInLeft` | Card appearance |
| `glowPulse` | Critical hit highlight |
| `criticalFlash` | Screen flash on big hits |
| `screenShake` | Screen shake on critical |
| `cardAppear` | Staggered card entrance |
| `nwFlash` | NW value change highlight |
| `pulse` | Button/element attention |

### Sound Effects

All sounds are synthesised in real-time using the Web Audio API (`OscillatorNode` + `GainNode`). No external audio files are loaded, keeping the app lightweight.

---

## CDN Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **Socket.IO Client** | 4.x | Real-time bidirectional communication |
| **Chart.js** | 4.x | Stock price charts and NW-over-time charts |
