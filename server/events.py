"""
Trading Arena — Socket.IO Event Handlers
==========================================
All client-server event handlers for the game.
"""

from flask_socketio import emit

from server.config import CARD_BUY_COST_PCT, MAX_BENCH, TRADING_DAYS_QTR
from server.game_state import game, reset_game
from server.game_logic import (
    advance_to_action_phase,
    broadcast_state,
    resolve_battle,
    start_new_round,
)
from server.stock_data import stock_cache


def register_events(app, socketio):
    """Register all Socket.IO and HTTP route handlers."""

    @app.route("/")
    def index():
        from flask import render_template
        return render_template("index.html")

    # ── Connection ──

    @socketio.on("connect")
    def handle_connect():
        from flask import request
        sid = request.sid
        print(f"[connect] Client connected (sid={sid})")

    @socketio.on("disconnect")
    def handle_disconnect():
        from flask import request
        sid = request.sid
        for pid in ("player_1", "player_2"):
            if game["players"][pid]["sid"] == sid:
                game["players"][pid]["connected"] = False
                game["players"][pid]["sid"] = None
                print(f"[disconnect] {pid} left")
                socketio.emit("server_message", {
                              "msg": f"{pid} disconnected."})
                break

    # ── Mode Selection ──

    @socketio.on("select_mode")
    def handle_select_mode(data):
        """Player selects offline or multiplayer mode."""
        from flask import request
        sid = request.sid
        mode = data.get("mode", "multiplayer")

        if mode == "offline":
            p1 = game["players"]["player_1"]
            if p1["connected"]:
                emit("error", {"msg": "Game already in progress!"})
                return

            # Assign human as player_1
            p1["connected"] = True
            p1["sid"] = sid
            emit("player_assigned", {"player_id": "player_1", "player_num": 1})

            # Create bot for player_2
            p2 = game["players"]["player_2"]
            p2["connected"] = True
            p2["is_bot"] = True

            game["mode"] = "offline"

            socketio.emit("server_message", {
                "msg": "Offline mode! Playing against Trading Bot …"
            })
            socketio.sleep(1)
            start_new_round(socketio)

        else:
            # Multiplayer: assign as next available player
            assigned = None
            for pid in ("player_1", "player_2"):
                p = game["players"][pid]
                if not p["connected"]:
                    p["connected"] = True
                    p["sid"] = sid
                    assigned = pid
                    break

            if assigned is None:
                emit("error", {
                     "msg": "Game is full! Two players already connected."})
                return

            num = 1 if assigned == "player_1" else 2
            emit("player_assigned", {"player_id": assigned,
                 "player_num": num})
            print(f"[select_mode] {assigned} joined multiplayer (sid={sid})")

            game["mode"] = "multiplayer"

            socketio.emit("server_message", {
                "msg": f"Player {num} has entered the arena!"
            })

            if all(game["players"][p]["connected"] for p in ("player_1", "player_2")):
                socketio.emit("server_message", {
                    "msg": "Both players connected! Starting game …"
                })
                socketio.sleep(1)
                start_new_round(socketio)
            else:
                emit("server_message", {
                     "msg": "Waiting for opponent to connect …"})

    # ── Buy Phase ──

    @socketio.on("buy_stock")
    def handle_buy_stock(data):
        """Player buys a stock from their hand -> bench."""
        pid = data.get("player_id")
        idx = data.get("card_index")
        if game["phase"] != "buy":
            emit("error", {"msg": "Not in buy phase!"})
            return
        p = game["players"].get(pid)
        if p is None or idx is None:
            emit("error", {"msg": "Invalid request."})
            return
        if idx < 0 or idx >= len(p["hand"]):
            emit("error", {"msg": "Invalid card index."})
            return
        if len(p["bench"]) >= MAX_BENCH:
            emit("error", {"msg": "Bench is full!"})
            return

        card = p["hand"].pop(idx)
        cost = round(card["s0"] * CARD_BUY_COST_PCT, 2)
        p["net_worth"] -= cost
        p["bench"].append(card)
        broadcast_state(socketio)
        emit("server_message", {
            "msg": f"You bought {card['ticker']} for £{cost:,.2f}"
        })

    @socketio.on("end_buy_phase")
    def handle_end_buy(data):
        """Player signals they are done buying."""
        pid = data.get("player_id")
        if game["phase"] != "buy":
            return
        game["players"][pid]["ready"] = True
        broadcast_state(socketio)
        if all(game["players"][p]["ready"] for p in ("player_1", "player_2")):
            advance_to_action_phase(socketio)

    # ── Action Phase: Per-card action assignment ──

    @socketio.on("set_card_action")
    def handle_set_card_action(data):
        """Set or clear an action for a specific bench card.
        data: { player_id, card_index: int, action: "place"|"defense_put"|"call"|null }
        """
        pid = data.get("player_id")
        card_index = data.get("card_index")
        action = data.get("action")  # None to clear

        if game["phase"] != "action":
            emit("error", {"msg": "Not in action phase!"})
            return
        p = game["players"].get(pid)
        if p is None:
            emit("error", {"msg": "Invalid player."})
            return
        if p["ready"]:
            emit("error", {"msg": "Already confirmed actions!"})
            return
        if card_index is None or card_index < 0 or card_index >= len(p["bench"]):
            emit("error", {"msg": "Invalid bench card index."})
            return

        idx_str = str(card_index)
        card = p["bench"][card_index]

        # If changing from a previous action, refund its premium
        old_action = p["card_actions"].get(idx_str)
        if old_action == "call":
            p["net_worth"] += card["call_premium"]
            p["net_worth"] = round(p["net_worth"], 2)
        elif old_action == "defense_put":
            p["net_worth"] += card["put_premium"]
            p["net_worth"] = round(p["net_worth"], 2)

        if action is None:
            # Clear action
            p["card_actions"].pop(idx_str, None)
        else:
            if action not in ("place", "defense_put", "call"):
                emit("error", {"msg": f"Invalid action: {action}"})
                return

            # Charge premium for options
            if action == "call":
                p["net_worth"] -= card["call_premium"]
                p["net_worth"] = round(p["net_worth"], 2)
                emit("server_message", {
                    "msg": f"Assigned CALL on {card['ticker']} "
                    f"(premium: £{card['call_premium']:,.2f})"
                })
            elif action == "defense_put":
                p["net_worth"] -= card["put_premium"]
                p["net_worth"] = round(p["net_worth"], 2)
                emit("server_message", {
                    "msg": f"Assigned DEFENSE PUT on {card['ticker']} "
                    f"(premium: £{card['put_premium']:,.2f})"
                })

            p["card_actions"][idx_str] = action

        broadcast_state(socketio)

    # ── Action Phase: Toggle attack put on opponent card ──

    @socketio.on("toggle_attack_put")
    def handle_toggle_attack_put(data):
        """Toggle attack put on an opponent's bench card.
        data: { player_id, target_card_id: str }
        """
        pid = data.get("player_id")
        target_id = data.get("target_card_id")

        if game["phase"] != "action":
            emit("error", {"msg": "Not in action phase!"})
            return
        p = game["players"].get(pid)
        if p is None:
            emit("error", {"msg": "Invalid player."})
            return
        if p["ready"]:
            emit("error", {"msg": "Already confirmed actions!"})
            return

        opp_id = "player_2" if pid == "player_1" else "player_1"
        opp = game["players"][opp_id]

        # Find the target card
        target_card = None
        for c in opp["bench"]:
            if c["id"] == target_id:
                target_card = c
                break
        if target_card is None:
            emit("error", {"msg": "Target asset not found in opponent holdings."})
            return

        if target_id in p["attack_puts"]:
            # Remove: refund premium
            p["attack_puts"].remove(target_id)
            p["net_worth"] += target_card["put_premium"]
            p["net_worth"] = round(p["net_worth"], 2)
            emit("server_message", {
                "msg": f"Cancelled ATTACK PUT on {target_card['ticker']}"
            })
        else:
            # Add: charge premium
            p["attack_puts"].append(target_id)
            p["net_worth"] -= target_card["put_premium"]
            p["net_worth"] = round(p["net_worth"], 2)
            emit("server_message", {
                "msg": f"Placed ATTACK PUT on {target_card['ticker']} "
                f"(premium: £{target_card['put_premium']:,.2f})"
            })

        broadcast_state(socketio)

    # ── Action Phase: Confirm all actions ──

    @socketio.on("confirm_actions")
    def handle_confirm_actions(data):
        """Player confirms all their actions are set."""
        pid = data.get("player_id")
        if game["phase"] != "action":
            return
        p = game["players"].get(pid)
        if p is None:
            return
        p["ready"] = True
        broadcast_state(socketio)

        if all(game["players"][pp]["ready"] for pp in ("player_1", "player_2")):
            resolve_battle(socketio)

    # ── Stock Chart ──

    @socketio.on("request_stock_chart")
    def handle_request_stock_chart(data):
        """Return ~6 months of price data for a ticker around a card's start date.
        data: { ticker: str, start_idx: int }
        """
        ticker = data.get("ticker")
        start_idx = data.get("start_idx", 0)

        if ticker not in stock_cache:
            emit("error", {"msg": f"Unknown ticker: {ticker}"})
            return

        series = stock_cache[ticker]
        # Show only the last 6 months BEFORE the card start (no future data)
        lookback = TRADING_DAYS_QTR * 2  # 126 trading days = ~6 months
        chart_start = max(0, start_idx - lookback)
        chart_end = start_idx + 1  # Up to and including start_idx only

        chart_series = series.iloc[chart_start:chart_end]
        dates = [str(d.date()) for d in chart_series.index]
        prices = [round(float(p), 2) for p in chart_series.values]
        s0_position = start_idx - chart_start  # index within the chart data

        emit("stock_chart_data", {
            "ticker": ticker,
            "dates": dates,
            "prices": prices,
            "s0_position": s0_position,
        })

    # ── Restart ──

    @socketio.on("restart_game")
    def handle_restart(data=None):
        """Reset and start a new game."""
        reset_game()
        socketio.emit("server_message", {
                      "msg": "Game reset! Waiting for players …"})
        socketio.emit("game_reset", {})

 # ── LLM Insights ──

    @socketio.on("request_llm_insights")
    def handle_request_llm_insights(data):
        """Generate LLM-powered post-game strategy analysis."""
        from flask import request as flask_request
        from server.llm_insights import generate_llm_insights

        pid = data.get("player_id")
        if game["phase"] != "end":
            emit("error", {"msg": "Game is not over yet."})
            return
        if pid not in ("player_1", "player_2"):
            emit("error", {"msg": "Invalid player."})
            return

        opp_id = "player_2" if pid == "player_1" else "player_1"
        p = game["players"][pid]
        opp = game["players"][opp_id]

        # Build analytics dicts (same as end_game)
        def _build_analytics(player):
            nw_hist = player["nw_history"]
            total_profit = nw_hist[-1] - nw_hist[0]
            peak = nw_hist[0]
            max_dd = 0
            for nw in nw_hist:
                if nw > peak:
                    peak = nw
                dd = peak - nw
                if dd > max_dd:
                    max_dd = dd
            win_rate = (
                round(player["options_won"] / player["options_played"] * 100, 1)
                if player["options_played"] > 0 else 0
            )
            return {
                "total_profit": round(total_profit, 2),
                "options_win_rate": win_rate,
                "max_drawdown": round(max_dd, 2),
                "nw_history": nw_hist,
                "trade_history": player["trade_history"],
                "final_nw": nw_hist[-1],
            }

        analytics = _build_analytics(p)
        opp_analytics = _build_analytics(opp)

        # Determine winner
        if p["net_worth"] > opp["net_worth"]:
            winner = pid
        elif opp["net_worth"] > p["net_worth"]:
            winner = opp_id
        else:
            winner = "draw"

        result = generate_llm_insights(pid, analytics, opp_analytics, winner)
        emit("llm_insights", {"player_id": pid, "content": result})