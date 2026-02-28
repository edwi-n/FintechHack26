"""
Trading Arena — Game State
============================
Global game state, player factory, and state serialisation for the client.
"""

from server.config import MAX_ROUNDS, STARTING_NW
from server.cards import card_for_client

# ──────────────────────────────────────────────
# Player factory
# ──────────────────────────────────────────────


def fresh_player() -> dict:
    return {
        "sid": None,
        "connected": False,
        "net_worth": STARTING_NW,
        "hand": [],
        "bench": [],
        # Multi-action: one action per bench card
        "card_actions": {},       # { bench_index_str: "place"|"defense_put"|"call" }
        # Attack puts on opponent cards
        "attack_puts": [],        # [ opponent_card_id, ... ]
        "ready": False,
        "trade_history": [],
        "nw_history": [STARTING_NW],
        "options_played": 0,
        "options_won": 0,
    }


# ──────────────────────────────────────────────
# Global game dict
# ──────────────────────────────────────────────

game: dict = {
    "round": 0,
    "max_rounds": MAX_ROUNDS,
    "phase": "lobby",
    "date_idx": None,
    "current_date": "",
    "players": {
        "player_1": fresh_player(),
        "player_2": fresh_player(),
    },
}


def reset_game():
    """Reset game state for a new match."""
    global game
    game = {
        "round": 0,
        "max_rounds": MAX_ROUNDS,
        "phase": "lobby",
        "date_idx": None,
        "current_date": "",
        "players": {
            "player_1": fresh_player(),
            "player_2": fresh_player(),
        },
    }


# ──────────────────────────────────────────────
# State serialisation
# ──────────────────────────────────────────────

def player_state_for_client(pid: str) -> dict:
    """Return the game state visible to a specific player."""
    p = game["players"][pid]
    opp_id = "player_2" if pid == "player_1" else "player_1"
    opp = game["players"][opp_id]
    return {
        "round": game["round"],
        "max_rounds": game["max_rounds"],
        "phase": game["phase"],
        "player_id": pid,
        # Own data
        "net_worth": p["net_worth"],
        "hand": [card_for_client(c) for c in p["hand"]],
        "bench": [card_for_client(c) for c in p["bench"]],
        "ready": p["ready"],
        "card_actions": p["card_actions"],
        "attack_puts": list(p["attack_puts"]),
        # Opponent data (limited)
        "opponent_nw": opp["net_worth"],
        "opponent_bench": [
            {
                "id": c["id"],
                "ticker": c["ticker"],
                "s0": c["s0"],
                "put_premium": c["put_premium"],
                "start_idx": c.get("start_idx", 0),
            }
            for c in opp["bench"]
        ] if game["phase"] != "buy" else [],
        "opponent_ready": opp["ready"],
        "current_date": game.get("current_date", ""),
    }
