"""
Trading Arena — LLM-Powered Post-Game Insights
================================================
Uses an LLM to generate personalised strategy analysis
and advice based on post-game statistics.

Supports two providers (checks in order):
  1. GROQ_API_KEY   → Groq (free, uses llama-3.1-8b-instant)
  2. OPENAI_API_KEY → OpenAI (uses gpt-4o-mini)

Falls back to None when no key is set or the call fails.
"""

import os
import json

def generate_llm_insights(
    player_id: str,
    analytics: dict,
    opponent_analytics: dict,
    winner: str,
) -> str | None:
    """Call the LLM with a rich prompt built from game statistics.

    Returns the LLM-generated markdown string, or None on failure.
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not groq_key and not openai_key:
        print("[LLM] No API key set (GROQ_API_KEY or OPENAI_API_KEY) — skipping LLM insights")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("[LLM] openai package not installed — skipping LLM insights")
        return None

    prompt = _build_prompt(player_id, analytics, opponent_analytics, winner)

    try:
        if groq_key:
            client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1",
            )
            model = "llama-3.1-8b-instant"
            print("[LLM] Using Groq (llama-3.1-8b-instant)")
        else:
            client = OpenAI(api_key=openai_key)
            model = "gpt-4o-mini"
            print("[LLM] Using OpenAI (gpt-4o-mini)")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as exc:
        print(f"[LLM] Error generating insights: {exc}")
        return None


# ──────────────────────────────────────────────
# Prompt construction
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a direct, no-nonsense trading coach reviewing a player's performance \
in Trading Arena, a stock-trading card game. Speak directly to the player — \
use "you" and "your" throughout.

Game rules (for context only — do NOT repeat these back):
- £1,000 starting cash, 5 rounds (quarterly), highest net worth wins.
- Buy stock cards (5% of price), deploy actions: PLACE (bullish bet), \
CALL (leveraged bull, Black-Scholes premium), DEFENSE PUT (hedge), HOLD, \
or ATTACK PUT (bet opponent's stock drops).
- Bench stocks move with real historical prices. 2% inflation penalty on idle cash.

Your job: cut straight to what matters. Briefly tell the player exactly what they did \
right, what they got wrong, and what to do differently next game. Name specific \
tickers, rounds, and pound amounts. Make the bulk of the response be insights on trading strategy/mindset. \
And how they can become better traders in real-life too, not just in the game. \
No fluff, no generic advice. \
Use markdown with headers and bullet points. Keep it under 600 words.\
"""


def _build_prompt(
    player_id: str,
    analytics: dict,
    opponent_analytics: dict,
    winner: str,
) -> str:
    """Assemble all game stats into a detailed prompt."""
    is_winner = winner == player_id
    result_str = "WON" if is_winner else ("DREW" if winner == "draw" else "LOST")

    trades = analytics.get("trade_history", [])
    opp_trades = opponent_analytics.get("trade_history", [])

    # Build round-by-round breakdown
    round_details = []
    for t in trades:
        actions = dict(t.get("actions", {}))
        num_attack_puts = actions.pop("attack_puts", 0)
        action_list = [
            f"  - Bench slot {k}: {v.upper()}" for k, v in actions.items()
        ]
        if num_attack_puts:
            action_list.append(f"  - Attack Puts deployed: {num_attack_puts}")
        if not action_list:
            action_list.append("  - No actions taken (HOLD)")
        round_details.append(
            f"Round {t['round']}:\n"
            + "\n".join(action_list)
            + f"\n  Arena delta: £{t['arena_delta']:+,.2f}"
            f"  |  Bench growth: £{t['bench_omega']:+,.2f}"
            f"  |  Inflation: -£{t['inflation']:,.2f}"
            f"  |  NW after: £{t['nw_after']:,.2f}"
        )

    nw_history = analytics.get("nw_history", [])
    opp_nw_history = opponent_analytics.get("nw_history", [])

    prompt = f"""\
## Player Performance Report

**Result**: {result_str}
**Starting Net Worth**: £{nw_history[0]:,.2f}
**Final Net Worth**: £{analytics['final_nw']:,.2f}
**Total Profit/Loss**: £{analytics['total_profit']:+,.2f} \
({analytics['total_profit'] / nw_history[0] * 100:+.1f}%)
**Options Played**: {_count_options(trades)} \
(Win Rate: {analytics['options_win_rate']}%)
**Max Drawdown**: £{analytics['max_drawdown']:,.2f}

### Net Worth Trajectory
Player: {' → '.join(f'£{nw:,.2f}' for nw in nw_history)}
Opponent: {' → '.join(f'£{nw:,.2f}' for nw in opp_nw_history)}

### Round-by-Round Actions
{chr(10).join(round_details)}

### Opponent Summary
- Final NW: £{opponent_analytics['final_nw']:,.2f}
- Total Profit: £{opponent_analytics['total_profit']:+,.2f}
- Options Win Rate: {opponent_analytics['options_win_rate']}%

---
Please provide:
1. **Strategy Summary** — classify this player's overall approach in 2-3 sentences.
2. **Key Strengths** — what the player did well (reference specific rounds/actions).
3. **Mistakes & Missed Opportunities** — what went wrong or could have been better.
4. **Actionable Advice** — 3-4 concrete tips for the next game.
"""
    return prompt


def _count_options(trades: list) -> int:
    """Count total option actions (calls, puts) across all rounds."""
    count = 0
    for t in trades:
        actions = t.get("actions", {})
        for k, v in actions.items():
            if k == "attack_puts":
                count += v if isinstance(v, int) else 0
            elif v in ("call", "defense_put"):
                count += 1
    return count
