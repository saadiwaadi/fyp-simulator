import random

def select_duellists(att_team, def_team, mode="5v5"):
    """
    [v2.8 STABLE]
    - FIX: Uses 'preferred_zone' instead of 'zone' to match Database.
    - FIX: Handles missing GKs safely.
    - LOGIC: Calculates duel zone based on mode, not carrier.
    """
    
    # --- 1. DETERMINE MATCHUP ZONE ---
    # Instead of asking the carrier "Where are you?", the engine decides 
    # where the play is happening.
    if mode == "11v11":
        # Weighted: 30% Left, 40% Center, 30% Right
        match_zone = random.choices(['L', 'C', 'R'], weights=[0.3, 0.4, 0.3], k=1)[0]
    else:
        # 5v5 is mostly central
        match_zone = 'C'

    # --- 2. PHASE LOGIC ---
    is_midfield_battle = random.random() < 0.6
    
    # Helper to find players by role safely
    def get_role_players(team, roles):
        candidates = [p for p in team if p.role in roles]
        return candidates if candidates else team

    if is_midfield_battle: 
        active_att = get_role_players(att_team, ['MID', 'DEF'])
        active_def = get_role_players(def_team, ['MID', 'FWD'])
    else:
        active_att = get_role_players(att_team, ['FWD', 'MID'])
        active_def = get_role_players(def_team, ['DEF', 'MID'])

    # --- 3. WEIGHTED SELECTION ---
    def get_weights(players, target_zone):
        weights = []
        for p in players:
            # FIX: Use 'preferred_zone' (Database Name) not 'zone'
            # We use getattr() to be 100% safe if the attribute is missing
            p_zone = getattr(p, 'preferred_zone', 'C') 
            
            # Players in the correct zone are 4x more likely to be involved
            weight = 4.0 if p_zone == target_zone else 1.0
            weights.append(weight)
        return weights

    # Pick Carrier and Defender based on the Zone weights
    carrier = random.choices(active_att, weights=get_weights(active_att, match_zone), k=1)[0]
    defender = random.choices(active_def, weights=get_weights(active_def, match_zone), k=1)[0]
    
    # --- 4. IDENTIFY GK (Crash Proof) ---
    gks = [p for p in def_team if p.role == 'GK']
    
    if gks:
        gk = gks[0]
    else:
        # Emergency: First player becomes GK
        gk = def_team[0]

    return carrier, defender, gk, match_zone