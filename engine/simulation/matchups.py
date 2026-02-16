import random

def get_active_players(team, role_group, mode="5v5"):
    """
    [RETAINED] Filters the team to find players currently relevant to the play phase.
    """
    if mode == "5v5":
        return [p for p in team if p.role != 'GK']
    
    # 11v11 Logic
    candidates = [p for p in team if p.role in role_group]
    return candidates if candidates else [p for p in team if p.role != 'GK']

def select_duellists(att_team, def_team, mode="5v5"):
    """
    [v2.6 FINAL]
    - Retains: Phase Logic (60/40 Split).
    - Retains: GK identification.
    - Implements: Spatial Zone selection (30/40/30).
    - Implements: Weighted Positional Selection.
    """
    # 1. Pick the Spatial Zone (LEFT/CENTER/RIGHT)
    if mode == "11v11":
        # Using your 0.3 / 0.4 / 0.3 distribution
        zone = random.choices(['L', 'C', 'R'], weights=[0.3, 0.4, 0.3], k=1)[0]
    else:
        # 5v5 remains central to avoid unnecessary complexity in small-sided games
        zone = 'C'

    # 2. Identify the Phase [RETAINED]
    # 60% Midfield Battle / 40% Final Third Attack
    is_midfield_battle = random.random() < 0.6

    if is_midfield_battle: 
        active_att = get_active_players(att_team, ['MID', 'DEF'], mode)
        active_def = get_active_players(def_team, ['MID', 'FWD'], mode)
    else:
        active_att = get_active_players(att_team, ['FWD', 'MID'], mode)
        active_def = get_active_players(def_team, ['DEF', 'MID'], mode)

    # 3. Weighted Selection (The Zone Check)
    def get_weights(players, target_zone):
        # A player whose preferred_zone matches the target_zone is 4x more likely 
        # to be selected for the duel. This creates "Natural Positioning".
        return [4.0 if getattr(p, 'preferred_zone', 'C') == target_zone else 1.0 for p in players]

    carrier = random.choices(active_att, weights=get_weights(active_att, zone), k=1)[0]
    defender = random.choices(active_def, weights=get_weights(active_def, zone), k=1)[0]
    
    # 4. Identify GK [RETAINED]
    gk = [p for p in def_team if p.role == 'GK'][0]

    return carrier, defender, gk, zone