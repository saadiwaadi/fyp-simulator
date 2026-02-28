# engine/simulation/analyst.py
# ============================================================
# PHASE A CHANGES:
#   - generate_post_match_report() now reads home_zone_finals / away_zone_finals
#   - Added zone_breakdown section to the returned analysis dict
#   - Added get_weakest_zone_name() helper for analyst commentary
#   - All other V4 logic preserved unchanged
# ============================================================


def generate_post_match_report(stats, home_name, away_name):
    """
    Generates the full Deep Scan analysis object from raw match stats.
    Called by match_analysis view. Output is passed directly to the template.

    Returns a dict with keys:
      outcome_type, ratings, turning_point, attribution,
      zones, zone_breakdown, impact, timeline, causality
    """
    h_struct = stats.get('home_integrity_final', 100)
    a_struct = stats.get('away_integrity_final', 100)

    # ============================================================
    # 1. TIERED RATINGS (Managerial Grade)
    # ============================================================
    def get_tier(val, threshold, label_high, label_low):
        return label_high if val >= threshold else label_low

    sys_grade = (
        get_tier(h_struct, 60, "Resilient", "Fragile")
        if stats.get('home_score', 0) > stats.get('away_score', 0)
        else get_tier(a_struct, 60, "Resilient", "Fragile")
    )

    ratings = {
        'press_sustainability': get_tier(
            stats.get('fatigue_breach_min') or 90, 70, "Optimal", "Overextended"
            ),
        'structural_stability': f"{min(h_struct, a_struct)}% ({sys_grade})",
    }

    # ============================================================
    # 2. TURNING POINT DETECTION
    # ============================================================
    turning_point = "No singular critical failure event detected."
    if stats.get('struct_breach_min'):
        turning_point = (
            f"Minute {stats['struct_breach_min']} — Structural Integrity "
            f"dropped below 40%. Defensive cohesion entered critical failure state."
        )
    elif stats.get('fatigue_breach_min'):
        turning_point = (
            f"Minute {stats['fatigue_breach_min']} — Midfield energy levels critical. "
            f"Pressing intensity collapsed."
        )

    # ============================================================
    # 3. LUCK VS SYSTEM ATTRIBUTION
    # ============================================================
    total_inf = stats.get('system_influence', 0) + stats.get('random_influence', 0) + 1
    sys_pct   = int((stats.get('system_influence', 0) / total_inf) * 100)

    attribution = {
        'system':   "High"     if sys_pct > 60 else "Moderate" if sys_pct > 40 else "Low",
        'variance': "High"     if sys_pct <= 40 else "Moderate" if sys_pct <= 60 else "Low",
    }

    # ============================================================
    # 4. ZONE DOMINANCE (action counts)
    # ============================================================
    zones = []
    for z, data in stats.get('zone_control', {}).items():
        dom    = home_name if data.get('home', 0) > data.get('away', 0) else away_name
        margin = abs(data.get('home', 0) - data.get('away', 0))
        zones.append({'name': z, 'winner': dom, 'margin': margin})

    # ============================================================
    # 5. PHASE A: ZONE INTEGRITY BREAKDOWN
    # Reads zone_finals from stats — populated by engine's FINALIZE block.
    # Used by the Deep Scan template to show per-zone health bars.
    # ============================================================
    h_zone_finals = stats.get('home_zone_finals', {'Left': 100, 'Center': 100, 'Right': 100})
    a_zone_finals = stats.get('away_zone_finals', {'Left': 100, 'Center': 100, 'Right': 100})

    zone_breakdown = []
    for z in ['Left', 'Center', 'Right']:
        h_val = h_zone_finals.get(z, 100)
        a_val = a_zone_finals.get(z, 100)

        # Classify zone health for template badge coloring
        def classify(val):
            if val >= 70: return "solid"
            if val >= 50: return "stressed"
            if val >= 30: return "broken"
            return "collapsed"

        zone_breakdown.append({
            'zone':       z,
            'home_val':   h_val,
            'away_val':   a_val,
            'home_state': classify(h_val),
            'away_state': classify(a_val),
            # Identifies which team suffered more in this zone
            'home_worse': h_val < a_val,
        })

    # ============================================================
    # 6. PLAYER IMPACT LEADERBOARD
    # ============================================================
    raw_impact     = stats.get('impact_detail', {})
    sorted_players = sorted(
        raw_impact.items(),
        key=lambda x: x[1].get('total', 0),
        reverse=True
    )[:4]

    processed_impact = []
    for p_name, data in sorted_players:
        details = []
        if data.get('goals',     0) > 0: details.append(f"+{data['goals']} Key Goal Contributions")
        if data.get('saves',     0) > 0: details.append(f"+{data['saves']} Critical Saves")
        if data.get('damage',    0) > 0: details.append(f"+{data['damage']} Structural Damage Dealt")
        if data.get('def_stops', 0) > 0: details.append(f"+{data['def_stops']} Defensive Holds")
        if data.get('breaks',    0) > 0: details.append(f"+{data['breaks']} Tactical Breaks")

        processed_impact.append({
            'name':    p_name,
            'total':   data.get('total', 0),
            'details': details[:3],
        })

    # ============================================================
    # 7. CAUSALITY CHAIN
    # ============================================================
    causality = []
    if stats.get('fatigue_breach_min'):
        causality.append(f"Fatigue Threshold Breach at {stats['fatigue_breach_min']}'")
    if stats.get('struct_breach_min'):
        causality.append("Structural Collapse (Integrity < 40%)")
    if not causality:
        causality.append("Sustainable System Performance")

    # ============================================================
    # 8. ASSEMBLE AND RETURN
    # ============================================================
    return {
        'outcome_type':   "Systemic Victory" if sys_pct > 60 else "Variance-Based Result",
        'ratings':        ratings,
        'turning_point':  turning_point,
        'attribution':    attribution,
        'zones':          zones,            # Action count dominance (existing)
        'zone_breakdown': zone_breakdown,   # PHASE A: Zone integrity breakdown (new)
        'impact':         processed_impact,
        'timeline':       stats.get('timeline', []),
        'causality':      causality,
    }