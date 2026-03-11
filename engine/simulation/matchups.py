# engine/simulation/matchups.py
# ============================================================
# PHASE B — WIDTH-DRIVEN ZONE SELECTION
#
# WHAT CHANGED FROM PHASE A:
#   select_duellists() now accepts sys_style dicts for both teams.
#   Zone weights are a direct function of the attacking team's WIDTH slider.
#   5v5 is no longer hardcoded to 'C' every minute.
#
# ZONE WEIGHT PHILOSOPHY:
#   Width 1-2 (Narrow)   → 65% C, 17.5% L, 17.5% R
#   Width 3   (Standard) → 50% C, 25% L,   25% R
#   Width 4   (Wide)     → 30% C, 35% L,   35% R
#   Width 5   (Stretch)  → 20% C, 40% L,   40% R
#
#   5v5 is still center-biased but no longer center-ONLY.
#   11v11 has the same logic but slightly more balanced by default.
#
# PLAYER SELECTION:
#   Carrier weighted toward players whose preferred_zone matches match_zone.
#   Defender weighted toward players whose preferred_zone matches match_zone.
#   This means wide attacks pull wide players into duels — spatially honest.
# ============================================================

import random


# Zone weight tables per width slider value
# Format: [center_weight, left_weight, right_weight]
_WIDTH_ZONE_WEIGHTS_5V5 = {
    1: [0.65, 0.175, 0.175],
    2: [0.60, 0.20,  0.20],
    3: [0.50, 0.25,  0.25],
    4: [0.30, 0.35,  0.35],
    5: [0.20, 0.40,  0.40],
}

_WIDTH_ZONE_WEIGHTS_11V11 = {
    1: [0.55, 0.225, 0.225],
    2: [0.50, 0.25,  0.25],
    3: [0.40, 0.30,  0.30],
    4: [0.28, 0.36,  0.36],
    5: [0.18, 0.41,  0.41],
}


def select_duellists(att_team, def_team, mode="5v5",
                     att_style=None, def_style=None):
    """
    PHASE B: Selects carrier, defender, GK, and match zone.

    Parameters
    ----------
    att_team   : list of SimPlayer for the attacking team
    def_team   : list of SimPlayer for the defending team
    mode       : '5v5' or '11v11'
    att_style  : dict with slider values for attacker (needs 'width')
    def_style  : dict with slider values for defender (not used here, reserved for Phase C)

    Returns
    -------
    (carrier, defender, gk, match_zone)  where match_zone is 'L', 'C', or 'R'
    """
    att_style = att_style or {}
    def_style = def_style or {}

    # ============================================================
    # 1. ZONE SELECTION — Width-Driven
    # ============================================================
    att_width = int(att_style.get('width', 3))
    att_width = max(1, min(5, att_width))  # Safety clamp

    if mode == "11v11":
        weights = _WIDTH_ZONE_WEIGHTS_11V11.get(att_width, _WIDTH_ZONE_WEIGHTS_11V11[3])
    else:
        weights = _WIDTH_ZONE_WEIGHTS_5V5.get(att_width, _WIDTH_ZONE_WEIGHTS_5V5[3])

    # Randomly pick zone based on width-driven distribution
    match_zone = random.choices(['C', 'L', 'R'], weights=weights, k=1)[0]

    # ============================================================
    # 2. PHASE SELECTION — Midfield battle or direct attack
    # ============================================================
    is_midfield_battle = random.random() < 0.6

    def get_role_players(team, roles):
        candidates = [p for p in team if p.role in roles]
        return candidates if candidates else team

    if is_midfield_battle:
        active_att = get_role_players(att_team, ['MID', 'DEF'])
        active_def = get_role_players(def_team, ['MID', 'FWD'])
    else:
        active_att = get_role_players(att_team, ['FWD', 'MID'])
        active_def = get_role_players(def_team, ['DEF', 'MID'])

    # ============================================================
    # 3. WEIGHTED PLAYER SELECTION — Zone-aware
    # Players in the correct zone are 4x more likely to be involved.
    # This means wide attacks pull wide specialists into duels.
    # ============================================================
    def get_weights(players, target_zone):
        weights = []
        for p in players:
            p_zone = getattr(p, 'preferred_zone', 'C')
            # Normalize DB zone names to single chars for comparison
            p_zone_char = p_zone[0].upper() if p_zone else 'C'
            weight = 4.0 if p_zone_char == target_zone else 1.0
            weights.append(weight)
        return weights

    carrier  = random.choices(active_att, weights=get_weights(active_att, match_zone), k=1)[0]
    defender = random.choices(active_def, weights=get_weights(active_def, match_zone), k=1)[0]

    # ============================================================
    # 4. GK SELECTION — Crash-proof
    # ============================================================
    gks = [p for p in def_team if p.role == 'GK']
    gk  = gks[0] if gks else def_team[0]

    return carrier, defender, gk, match_zone