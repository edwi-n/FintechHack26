"""
Trading Arena — Combat Math
=============================
Functions to calculate passive growth (omega) and arena effects (delta).
"""


def calc_omega(card: dict) -> float:
    """Bench passive growth/loss: omega = S1 - S0"""
    return round(card["s1"] - card["s0"], 2)


def calc_delta(action: str, card: dict) -> float:
    """Arena effect based on action type.
    - place / call  -> damage when stock goes UP   : max(0, S1 - S0)
    - attack_put    -> damage when stock goes DOWN  : max(0, S0 - S1)
    - defense_put   -> recovery when stock goes DOWN: max(0, S0 - S1)
    - hold          -> 0
    """
    s0, s1 = card["s0"], card["s1"]
    if action in ("place", "call"):
        return round(max(0.0, s1 - s0), 2)
    elif action in ("attack_put", "defense_put"):
        return round(max(0.0, s0 - s1), 2)
    return 0.0
