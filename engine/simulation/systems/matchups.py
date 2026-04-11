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


def select_duellists(att_team, def_team, mode='5v5', att_style=None, def_style=None, mode_config=None):
    att_style = att_style or {}
    def_style = def_style or {}
    mode_config = mode_config or {}

    att_width = int(att_style.get('width', 3))
    att_width = max(1, min(5, att_width))

    default_width_weights = _WIDTH_ZONE_WEIGHTS_11V11 if mode == '11v11' else _WIDTH_ZONE_WEIGHTS_5V5
    width_weights = mode_config.get('width_zone_weights', default_width_weights)
    weights = width_weights.get(att_width, width_weights[3])

    match_zone = random.choices(['C', 'L', 'R'], weights=weights, k=1)[0]
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

    def get_weights(players, target_zone):
        weights = []
        for p in players:
            p_zone = getattr(p, 'preferred_zone', 'C')
            p_zone_char = p_zone[0].upper() if p_zone else 'C'
            weights.append(4.0 if p_zone_char == target_zone else 1.0)
        return weights

    carrier = random.choices(active_att, weights=get_weights(active_att, match_zone), k=1)[0]
    defender = random.choices(active_def, weights=get_weights(active_def, match_zone), k=1)[0]

    gks = [p for p in def_team if p.role == 'GK']
    gk = gks[0] if gks else def_team[0]

    return carrier, defender, gk, match_zone
