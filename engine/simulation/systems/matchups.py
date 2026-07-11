import math
import random


_WIDTH_ZONE_WEIGHTS_5V5 = {
    1: [0.65, 0.175, 0.175],
    2: [0.60, 0.20, 0.20],
    3: [0.50, 0.25, 0.25],
    4: [0.30, 0.35, 0.35],
    5: [0.20, 0.40, 0.40],
}

_WIDTH_ZONE_WEIGHTS_11V11 = {
    1: [0.55, 0.225, 0.225],
    2: [0.50, 0.25, 0.25],
    3: [0.40, 0.30, 0.30],
    4: [0.28, 0.36, 0.36],
    5: [0.18, 0.41, 0.41],
}


def _distance(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def select_duellists(att_team, def_team, mode='5v5', att_style=None, def_style=None,
                     mode_config=None, rng=None, discourage_center=False):
    rng = rng or random
    att_style = att_style or {}
    def_style = def_style or {}
    mode_config = mode_config or {}

    att_width = int(att_style.get('width', 3))
    att_width = max(1, min(5, att_width))

    default_width_weights = _WIDTH_ZONE_WEIGHTS_11V11 if mode == '11v11' else _WIDTH_ZONE_WEIGHTS_5V5
    width_weights = mode_config.get('width_zone_weights', default_width_weights)
    weights = list(width_weights.get(att_width, width_weights[3]))

    # Anti-repetition: after sustained central play the attack looks wide.
    # Applied to the zone odds BEFORE selection so carrier/defender weighting
    # matches the zone actually played (audit B6).
    if discourage_center:
        weights[0] *= 0.3

    match_zone = rng.choices(['C', 'L', 'R'], weights=weights, k=1)[0]
    is_midfield_battle = rng.random() < 0.6

    def get_role_players(team, roles):
        candidates = [p for p in team if p.role in roles]
        return candidates if candidates else team

    if is_midfield_battle:
        active_att = get_role_players(att_team, ['MID', 'DEF'])
        active_def = get_role_players(def_team, ['MID', 'DEF'])
    else:
        active_att = get_role_players(att_team, ['FWD', 'MID'])
        active_def = get_role_players(def_team, ['DEF', 'MID'])

    def get_weights(players, target_zone):
        weights = []
        for p in players:
            p_zone = getattr(p, 'preferred_zone', 'C')
            p_zone_char = p_zone[0].upper() if p_zone else 'C'
            weights.append(4.0 if p_zone_char == target_zone else 1.0)
        return weights

    carrier = rng.choices(active_att, weights=get_weights(active_att, match_zone), k=1)[0]

    positioned_defenders = [
        p for p in active_def
        if p.x is not None and p.y is not None and (p.x != 0 or p.y != 0)
    ]

    if positioned_defenders and carrier.x is not None and carrier.y is not None:
        distances = [_distance(carrier, d) for d in positioned_defenders]
        max_dist = max(distances) + 0.1

        proximity_weights = []
        for i, d in enumerate(positioned_defenders):
            proximity = (max_dist - distances[i]) / max_dist
            zone_bonus = 2.0 if getattr(d, 'preferred_zone', 'C')[0].upper() == match_zone else 1.0
            proximity_weights.append((proximity * 3.0 + 0.5) * zone_bonus)

        defender = rng.choices(positioned_defenders, weights=proximity_weights, k=1)[0]
    else:
        defender = rng.choices(active_def, weights=get_weights(active_def, match_zone), k=1)[0]

    gks = [p for p in def_team if p.role == 'GK']
    gk = gks[0] if gks else def_team[0]

    return carrier, defender, gk, match_zone
