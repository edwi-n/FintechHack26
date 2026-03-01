# API Reference — Socket.IO Events

[← Back to Main README](../README.md)

Complete reference for all Socket.IO events exchanged between the client and server.

---

## Table of Contents

- [Connection Lifecycle](#connection-lifecycle)
- [Game Setup](#game-setup)
- [Buy Phase](#buy-phase)
- [Action Phase](#action-phase)
- [Battle & Game End](#battle--game-end)
- [Data Requests](#data-requests)
- [Server → Client Events](#server--client-events)
- [State Object Schema](#state-object-schema)
- [Card Object Schema](#card-object-schema)

---

## Connection Lifecycle

### `connect` (built-in)

**Direction:** Client → Server

Triggered automatically when the browser connects via Socket.IO.

**Server behaviour:** Logs the connection. No game state is assigned until `select_mode` is emitted.

---

### `disconnect` (built-in)

**Direction:** Client → Server

Triggered when a player disconnects (browser close, network loss).

**Server behaviour:** Marks the player as disconnected. In multiplayer, notifies the remaining player.

---

## Game Setup

### `select_mode`

**Direction:** Client → Server

**Payload:**
```json
{
    "mode": "offline"    // "offline" or "multiplayer"
}
```

**Server behaviour:**

| Mode | Action |
|------|--------|
| `offline` | Assigns client as `player_1`, creates bot `player_2`, starts game immediately |
| `multiplayer` | Assigns next available slot; starts game when both players connected |

**Response events:**
- `player_assigned` → to the connecting client
- `server_message` → lobby status update
- `state_update` → when game starts

---

### `player_assigned`

**Direction:** Server → Client

**Payload:**
```json
{
    "player_id": "player_1",
    "player_num": 1
}
```

Sent immediately after `select_mode`. The client stores `myPlayerId` and `myPlayerNum` for all subsequent emits.

---

## Buy Phase

### `buy_stock`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1",
    "index": 2               // Index in the hand (market) array
}
```

**Server behaviour:**
1. Validates it's the buy phase and the index is valid
2. Pops the card from `hand[index]`
3. Charges **5% of S₀** from the player's NW
4. Pushes the card to `bench` (if under MAX_BENCH limit)
5. Emits `state_update` to both players

**Error cases:**
- Wrong phase → `error` event
- Invalid index → `error` event
- Bench full (10 slots) → `error` event
- Insufficient funds → `error` event

---

### `sell_stock`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1",
    "index": 0               // Index in the bench (holdings) array
}
```

**Server behaviour:**
1. Validates it's the buy phase
2. Pops the card from `bench[index]`
3. Returns card to `hand`
4. Emits `state_update`

---

### `end_buy_phase`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1"
}
```

**Server behaviour:**
1. Sets `player.ready = True`
2. If **both** players ready → calls `advance_to_action_phase()`
3. If only one ready → emits `server_message` ("Waiting for opponent")
4. Emits `state_update`

---

## Action Phase

### `set_card_action`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1",
    "card_index": 1,
    "action": "defense_put"    // "place" | "defense_put" | "call" | "clear"
}
```

**Server behaviour:**
1. Validates it's the action phase and the card index is valid
2. If action is `"clear"` → removes any assigned action, refunds any charged premium
3. If action is `"defense_put"` → charges put premium from NW
4. If action is `"call"` → charges call premium from NW
5. If action is `"place"` → free (no charge)
6. Stores in `player.card_actions[card_index] = action`
7. Emits `state_update`

**Error cases:**
- Wrong phase → `error` event
- Insufficient NW for premium → `error` event
- Invalid card index → `error` event

---

### `toggle_attack_put`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1",
    "target_id": "TSLA_1234567890"    // ID of the opponent's card
}
```

**Server behaviour:**
1. Validates it's the action phase
2. If card ID already in `attack_puts` → removes it, **refunds** put premium
3. If card ID not in `attack_puts` → adds it, **charges** put premium from NW
4. Emits `state_update`

**Error cases:**
- Wrong phase → `error` event
- Invalid target ID → `error` event
- Insufficient NW for premium → `error` event

---

### `confirm_actions`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1"
}
```

**Server behaviour:**
1. Sets `player.ready = True`
2. If **both** players ready → calls `resolve_battle()`
3. If only one ready → emits `server_message` ("Waiting for opponent")
4. Emits `state_update`

---

## Battle & Game End

### `battle_result`

**Direction:** Server → Client

**Payload:**
```json
{
    "round": 3,
    "events": [
        {
            "type": "delta",
            "player": "player_1",
            "action": "call",
            "ticker": "NVDA",
            "delta": 42.50,
            "description": "NVDA Call → +£42.50 damage to opponent"
        },
        {
            "type": "omega",
            "player": "player_1",
            "ticker": "AAPL",
            "omega": -12.30,
            "description": "AAPL bench → -£12.30"
        },
        {
            "type": "inflation",
            "player": "player_1",
            "penalty": 8.20,
            "description": "Inflation: -£8.20 on idle cash"
        }
    ],
    "player_1": {
        "nw_before": 1050.00,
        "nw_after": 1072.00,
        "delta_total": 42.50,
        "omega_total": -12.30,
        "inflation": 8.20
    },
    "player_2": {
        "nw_before": 980.00,
        "nw_after": 937.50,
        "delta_total": 0.00,
        "omega_total": -15.00,
        "inflation": 12.50
    }
}
```

Triggers the animated battle result overlay on the client.

---

### `game_over`

**Direction:** Server → Client

**Payload:**
```json
{
    "winner": "player_1",            // or "player_2" or "draw"
    "player_1": {
        "net_worth": 1247.50,
        "total_profit": 247.50,
        "options_win_rate": 0.67,
        "max_drawdown": 85.20,
        "nw_history": [1000, 1050, 980, 1100, 1200, 1247.50],
        "insights": ["Strong defense put usage", "..."]
    },
    "player_2": {
        "net_worth": 892.30,
        "total_profit": -107.70,
        "options_win_rate": 0.33,
        "max_drawdown": 190.40,
        "nw_history": [1000, 920, 870, 950, 910, 892.30],
        "insights": ["Over-reliance on attack puts", "..."]
    }
}
```

Triggers the end-game analytics overlay.

---

### `game_reset`

**Direction:** Server → Client

No payload. Triggers a full page reload on the client.

---

## Data Requests

### `request_stock_chart`

**Direction:** Client → Server

**Payload:**
```json
{
    "ticker": "AAPL",
    "start_idx": 1500
}
```

**Response event:** `stock_chart_data`

---

### `stock_chart_data`

**Direction:** Server → Client

**Payload:**
```json
{
    "ticker": "AAPL",
    "dates": ["2020-07-01", "2020-07-02", ...],
    "prices": [350.25, 352.40, ...],
    "current_price": 150.25
}
```

Returns ~6 months (~126 trading days) of historical prices **before** the card's start date.

---

### `request_llm_insights`

**Direction:** Client → Server

**Payload:**
```json
{
    "player_id": "player_1"
}
```

**Response event:** `llm_insights`

---

### `llm_insights`

**Direction:** Server → Client

**Payload:**
```json
{
    "insights": "## Strategy Analysis\n\nYour portfolio showed...",
    "error": null
}
```

Returns markdown-formatted LLM analysis. The `error` field is set if no API key is configured or the call failed.

---

## Server → Client Events

### `state_update`

**Direction:** Server → Client (per-player, personalised)

Sent after every state change. The full schema is below.

---

### `server_message`

**Direction:** Server → Client (broadcast)

**Payload:**
```json
{
    "msg": "Round 3/5 — Buy Phase! Market Date: 2019-07-15"
}
```

Displayed in the trade log.

---

### `error`

**Direction:** Server → Client (to requestor)

**Payload:**
```json
{
    "msg": "Not enough funds to buy this card"
}
```

---

## State Object Schema

Sent via `state_update`. Personalised per player (opponent's S₁ values are hidden):

```json
{
    "round": 3,
    "max_rounds": 5,
    "phase": "action",
    "player_id": "player_1",
    "net_worth": 1050.00,
    "hand": [ /* Card objects (no s1) */ ],
    "bench": [ /* Card objects (no s1) */ ],
    "ready": false,
    "card_actions": { "0": "defense_put", "2": "place" },
    "attack_puts": ["TSLA_1234567890"],
    "opponent_nw": 980.00,
    "opponent_bench": [
        {
            "id": "TSLA_1234567890",
            "ticker": "TSLA",
            "s0": 200.00,
            "put_premium": 15.50,
            "start_idx": 1500
        }
    ],
    "opponent_ready": false,
    "current_date": "2019-07-15"
}
```

**Note:** `opponent_bench` is empty during the buy phase to prevent information leakage.

---

## Card Object Schema

### Full card (server-side only)

```json
{
    "id": "AAPL_1704067200",
    "ticker": "AAPL",
    "s0": 150.25,
    "s1": 162.80,
    "start_idx": 1500,
    "date_start": "2021-01-04",
    "date_end": "2021-03-31",
    "sigma": 0.32,
    "call_premium": 12.45,
    "put_premium": 8.73
}
```

### Client card (s1 stripped)

```json
{
    "id": "AAPL_1704067200",
    "ticker": "AAPL",
    "s0": 150.25,
    "start_idx": 1500,
    "date_start": "2021-01-04",
    "date_end": "2021-03-31",
    "sigma": 0.32,
    "call_premium": 12.45,
    "put_premium": 8.73
}
```

The `s1` field is **never** sent to the client — it's the hidden future price that gets revealed during the battle phase.
