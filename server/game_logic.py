"""
Trading Arena — Game Logic
============================
Round lifecycle: starting rounds, advancing phases,
resolving battles, and ending the game.
"""

import random

from server.config import CARD_BUY_COST_PCT, HAND_SIZE, INFLATION_RATE, MAX_BENCH, TRADING_DAYS_QTR
from server.cards import generate_hand, generate_stock_card, pick_round_date
from server.combat import calc_delta, calc_omega
from server.game_state import game, player_state_for_client


def broadcast_state(socketio):
    """Send each player their personalised view of the game."""
    for pid in ("player_1", "player_2"):
        p = game["players"][pid]
        if p["sid"]:
            socketio.emit(
                "state_update",
                player_state_for_client(pid),
                to=p["sid"],
            )


def start_new_round(socketio):
    """Advance to the next round's buy phase."""
    game["round"] += 1
    game["phase"] = "buy"
    # Advance date by one quarter, or pick random start for round 1
    date_idx, round_date = pick_round_date(advance_from=game["date_idx"])
    game["date_idx"] = date_idx
    game["current_date"] = str(round_date.date())
    for pid in ("player_1", "player_2"):
        p = game["players"][pid]
        p["hand"] = generate_hand(HAND_SIZE, target_date=round_date)
        # Re-roll existing bench cards to the new date
        new_bench = []
        for card in p["bench"]:
            new_card = generate_stock_card(
                card["ticker"], target_date=round_date)
            new_bench.append(new_card)
        p["bench"] = new_bench
        p["card_actions"] = {}
        p["attack_puts"] = []
        p["ready"] = False
    broadcast_state(socketio)
    socketio.emit("server_message", {
        "msg": f"Round {game['round']}/{game['max_rounds']} — Buy Phase! "
        f"Market Date: {game['current_date']}"
    })
    # Bot auto-play in offline mode
    if game.get("mode") == "offline":
        bot_play_buy_phase(socketio)


def advance_to_action_phase(socketio):
    """Move from buy -> action phase."""
    game["phase"] = "action"
    for pid in ("player_1", "player_2"):
        game["players"][pid]["ready"] = False
        game["players"][pid]["card_actions"] = {}
        game["players"][pid]["attack_puts"] = []
    broadcast_state(socketio)
    socketio.emit("server_message", {
        "msg": "Action Phase! Assign actions to your bench cards and target opponent cards."
    })
    # Bot auto-play in offline mode
    if game.get("mode") == "offline":
        bot_play_action_phase(socketio)


def resolve_battle(socketio):
    """Both players locked in — resolve ALL actions for ALL cards."""
    game["phase"] = "battle"
    results = {"round": game["round"], "events": [],
               "player_1": {}, "player_2": {}}

    for pid in ("player_1", "player_2"):
        opp_id = "player_2" if pid == "player_1" else "player_1"
        p = game["players"][pid]
        opp = game["players"][opp_id]

        total_arena_delta = 0.0

        # ── 1. Process card_actions (place, defense_put, call on own bench) ──
        for idx_str, action in p["card_actions"].items():
            idx = int(idx_str)
            if idx < 0 or idx >= len(p["bench"]):
                continue
            card = p["bench"][idx]
            delta = calc_delta(action, card)

            if action in ("place", "call"):
                opp["net_worth"] -= delta
                total_arena_delta += delta
                results["events"].append(
                    f"{pid} used {action.upper()} on {card['ticker']} "
                    f"(£{card['s0']}->£{card['s1']}). Dealt £{delta:,.2f} damage!"
                )
                if action == "call":
                    p["options_played"] += 1
                    if delta > 0:
                        p["options_won"] += 1

            elif action == "defense_put":
                p["net_worth"] += delta
                total_arena_delta += delta
                results["events"].append(
                    f"{pid} used DEFENSE PUT on {card['ticker']} "
                    f"(£{card['s0']}->£{card['s1']}). Recovered £{delta:,.2f}!"
                )
                p["options_played"] += 1
                if delta > 0:
                    p["options_won"] += 1

        # ── 2. Process attack_puts (targeting opponent cards by ID) ──
        for target_id in p["attack_puts"]:
            target_card = None
            for c in opp["bench"]:
                if c["id"] == target_id:
                    target_card = c
                    break
            if target_card is None:
                continue
            delta = calc_delta("attack_put", target_card)
            opp["net_worth"] -= delta
            total_arena_delta += delta
            results["events"].append(
                f"{pid} used ATTACK PUT on {target_card['ticker']} "
                f"(£{target_card['s0']}->£{target_card['s1']}). Dealt £{delta:,.2f} damage!"
            )
            p["options_played"] += 1
            if delta > 0:
                p["options_won"] += 1

        if len(p["card_actions"]) == 0 and len(p["attack_puts"]) == 0:
            results["events"].append(f"{pid} chose to HOLD all cards.")

        # ── 3. Bench omega (passive movement for ALL bench cards) ──
        bench_total_omega = 0.0
        bench_details = []
        for card in p["bench"]:
            omega = calc_omega(card)
            p["net_worth"] += omega
            bench_total_omega += omega
            bench_details.append({
                "ticker": card["ticker"],
                "s0": card["s0"],
                "s1": card["s1"],
                "omega": omega,
            })

        results["events"].append(
            f"{pid} bench movement: £{bench_total_omega:+,.2f}"
        )

        # ── 4. Inflation penalty (cash only, not stocks) ──
        bench_stock_value = sum(c["s1"] for c in p["bench"])
        cash_portion = max(0.0, p["net_worth"] - bench_stock_value)
        inflation_penalty = round(cash_portion * INFLATION_RATE, 2)
        p["net_worth"] -= inflation_penalty
        p["net_worth"] = round(p["net_worth"], 2)
        results["events"].append(
            f"{pid} inflation penalty (on £{cash_portion:,.2f} cash): -£{inflation_penalty:,.2f}"
        )

        results[pid] = {
            "arena_delta": total_arena_delta,
            "bench_omega": round(bench_total_omega, 2),
            "inflation": inflation_penalty,
            "new_nw": p["net_worth"],
            "bench_details": bench_details,
        }

        # ── 5. Trade history ──
        p["nw_history"].append(p["net_worth"])
        actions_summary = dict(p["card_actions"])
        actions_summary["attack_puts"] = len(p["attack_puts"])
        p["trade_history"].append({
            "round": game["round"],
            "actions": actions_summary,
            "arena_delta": total_arena_delta,
            "bench_omega": round(bench_total_omega, 2),
            "inflation": inflation_penalty,
            "nw_after": p["net_worth"],
        })

    # ── 6. Return placed cards to bench ──
    for pid in ("player_1", "player_2"):
        p = game["players"][pid]
        for idx_str, action in p["card_actions"].items():
            if action == "place":
                idx = int(idx_str)
                if idx < len(p["bench"]):
                    card = p["bench"][idx]
                    card["s0"] = card["s1"]
                    card["s1"] = None

    # Broadcast battle results
    socketio.emit("battle_result", results)

    # Check game over
    game_over = False
    for pid in ("player_1", "player_2"):
        if game["players"][pid]["net_worth"] <= 0:
            game_over = True
    if game["round"] >= game["max_rounds"]:
        game_over = True

    if game_over:
        end_game(socketio)
    else:
        socketio.sleep(8)
        start_new_round(socketio)


# ──────────────────────────────────────────────
# Bot AI (offline mode)
# ──────────────────────────────────────────────

def bot_play_buy_phase(socketio):
    """Bot randomly buys cards during buy phase."""
    bot = game["players"]["player_2"]
    if not bot.get("is_bot"):
        return

    if bot["hand"]:
        num_to_buy = random.randint(1, min(3, len(bot["hand"])))
        for _ in range(num_to_buy):
            if not bot["hand"] or len(bot["bench"]) >= MAX_BENCH:
                break
            idx = random.randint(0, len(bot["hand"]) - 1)
            card = bot["hand"].pop(idx)
            cost = round(card["s0"] * CARD_BUY_COST_PCT, 2)
            bot["net_worth"] -= cost
            bot["bench"].append(card)

    bot["ready"] = True
    broadcast_state(socketio)


def bot_play_action_phase(socketio):
    """Bot randomly assigns actions during action phase."""
    bot = game["players"]["player_2"]
    if not bot.get("is_bot"):
        return

    opp = game["players"]["player_1"]
    possible_actions = ["place", "defense_put", "call"]

    for i, card in enumerate(bot["bench"]):
        if random.random() < 0.7:
            action = random.choice(possible_actions)
            if action == "call" and bot["net_worth"] > card["call_premium"]:
                bot["net_worth"] -= card["call_premium"]
                bot["net_worth"] = round(bot["net_worth"], 2)
                bot["card_actions"][str(i)] = action
            elif action == "defense_put" and bot["net_worth"] > card["put_premium"]:
                bot["net_worth"] -= card["put_premium"]
                bot["net_worth"] = round(bot["net_worth"], 2)
                bot["card_actions"][str(i)] = action
            elif action == "place":
                bot["card_actions"][str(i)] = action

    for card in opp["bench"]:
        if random.random() < 0.3 and bot["net_worth"] > card["put_premium"]:
            bot["attack_puts"].append(card["id"])
            bot["net_worth"] -= card["put_premium"]
            bot["net_worth"] = round(bot["net_worth"], 2)

    bot["ready"] = True
    broadcast_state(socketio)


def end_game(socketio):
    """Calculate analytics and broadcast game over."""
    game["phase"] = "end"
    analytics = {}
    for pid in ("player_1", "player_2"):
        p = game["players"][pid]
        nw_hist = p["nw_history"]
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
            round(p["options_won"] / p["options_played"] * 100, 1)
            if p["options_played"] > 0 else 0
        )

        analytics[pid] = {
            "total_profit": round(total_profit, 2),
            "options_win_rate": win_rate,
            "max_drawdown": round(max_dd, 2),
            "nw_history": nw_hist,
            "trade_history": p["trade_history"],
            "final_nw": nw_hist[-1],
        }

    p1_nw = game["players"]["player_1"]["net_worth"]
    p2_nw = game["players"]["player_2"]["net_worth"]
    if p1_nw > p2_nw:
        winner = "player_1"
    elif p2_nw > p1_nw:
        winner = "player_2"
    else:
        winner = "draw"

    # Generate LLM-style insights for each player
    insights = {}
    for pid in ("player_1", "player_2"):
        insights[pid] = _generate_insights(pid, analytics[pid], winner)

    socketio.emit("game_over", {
        "winner": winner,
        "analytics": analytics,
        "insights": insights,
    })


def _generate_insights(pid: str, analytics: dict, winner: str) -> list[str]:
    """Generate LLM-style analytical insights based on game performance."""
    insights = []
    profit = analytics["total_profit"]
    win_rate = analytics["options_win_rate"]
    max_dd = analytics["max_drawdown"]
    final_nw = analytics["final_nw"]
    nw_hist = analytics["nw_history"]
    trades = analytics["trade_history"]

    # Overall performance
    if profit > 0:
        insights.append(
            f"Strong portfolio growth of £{profit:,.2f} — "
            f"a {profit / nw_hist[0] * 100:.1f}% return on starting capital."
        )
    elif profit < 0:
        insights.append(
            f"Portfolio declined by £{abs(profit):,.2f} — "
            f"a {abs(profit) / nw_hist[0] * 100:.1f}% loss. "
            f"Consider more defensive strategies next time."
        )
    else:
        insights.append("Flat performance — perfectly hedged or no action taken.")

    # Options strategy
    if win_rate >= 70:
        insights.append(
            f"Exceptional options accuracy at {win_rate}% win rate. "
            f"Your derivatives timing was superb."
        )
    elif win_rate >= 50:
        insights.append(
            f"Solid options play with a {win_rate}% win rate. "
            f"Slightly above coin-flip odds indicates good market reads."
        )
    elif win_rate > 0:
        insights.append(
            f"Options win rate of {win_rate}% suggests room for improvement. "
            f"Focus on reading stock momentum before committing premiums."
        )

    # Drawdown analysis
    if max_dd > nw_hist[0] * 0.3:
        insights.append(
            f"Maximum drawdown of £{max_dd:,.2f} was significant — "
            f"over 30% of starting capital. Consider using defense puts "
            f"more aggressively to limit downside."
        )
    elif max_dd > 0:
        insights.append(
            f"Drawdown kept to £{max_dd:,.2f} — "
            f"solid risk management throughout the game."
        )

    # Momentum analysis
    if len(nw_hist) >= 3:
        early_trend = nw_hist[len(nw_hist) // 2] - nw_hist[0]
        late_trend = nw_hist[-1] - nw_hist[len(nw_hist) // 2]
        if early_trend < 0 and late_trend > 0:
            insights.append(
                "Impressive comeback! Recovered from an early decline to "
                "finish strong in the later rounds."
            )
        elif early_trend > 0 and late_trend < 0:
            insights.append(
                "Started strong but lost momentum in later rounds. "
                "Adapting strategy mid-game could have preserved gains."
            )

    # Aggression analysis
    total_attacks = sum(
        t["actions"].get("attack_puts", 0) for t in trades
    )
    total_calls = sum(
        1 for t in trades
        for k, v in t["actions"].items()
        if k != "attack_puts" and v == "call"
    )
    total_defenses = sum(
        1 for t in trades
        for k, v in t["actions"].items()
        if k != "attack_puts" and v == "defense_put"
    )

    if total_attacks >= 3:
        insights.append(
            f"Highly aggressive playstyle with {total_attacks} attack puts deployed. "
            f"{'It paid off!' if winner == pid else 'Sometimes offense alone isnt enough — balance with defense.'}"
        )
    if total_defenses >= 3:
        insights.append(
            f"Defensive strategist — {total_defenses} defense puts used to "
            f"protect your net worth. A classic risk-averse approach."
        )
    if total_calls >= 3:
        insights.append(
            f"Bullish conviction with {total_calls} call options. "
            f"You bet heavily on upward momentum."
        )

    # Win/Loss insight
    if winner == pid:
        insights.append(
            "Congratulations on the victory! Your mix of offense and "
            "risk management outperformed your opponent."
        )
    elif winner == "draw":
        insights.append(
            "A draw demonstrates equally matched strategies. "
            "Next time, a single well-timed play could tip the balance."
        )
    else:
        insights.append(
            "Despite the loss, every round is a learning opportunity. "
            "Review which rounds had the biggest swings and adjust."
        )

    return insights
