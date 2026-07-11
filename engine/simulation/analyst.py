"""Post-match Deep Scan analysis.

Reads the same threshold constants the engine flags breaches with, so the
narrative can never disagree with the simulation (audit A4). Attribution is
computed from per-duel roll margins recorded by mechanics._record_attribution
(audit B7), and draws are graded explicitly instead of defaulting to the away
team (audit B5).
"""

from .constants import (
    FATIGUE_BREACH_STAMINA,
    STRUCT_BREACH_INTEGRITY,
    PRESS_SUSTAINABLE_FRACTION,
)


def generate_post_match_report(stats, home_name, away_name):
    """Generates the full Deep Scan analysis object from raw match stats.

    Returns a dict with keys:
      outcome_type, ratings, turning_point, attribution,
      zones, zone_breakdown, impact, timeline, causality
    """
    h_struct = stats.get('home_integrity_final', 100)
    a_struct = stats.get('away_integrity_final', 100)
    max_minutes = stats.get('max_minutes', 90)

    home_score = stats.get('home_score', 0)
    away_score = stats.get('away_score', 0)

    # ============================================================
    # 1. TIERED RATINGS (Managerial Grade)
    # ============================================================
    if home_score > away_score:
        graded_struct, graded_name = h_struct, home_name
    elif away_score > home_score:
        graded_struct, graded_name = a_struct, away_name
    else:
        # Draw: grade whichever system held together better.
        graded_struct, graded_name = max(
            (h_struct, home_name), (a_struct, away_name)
        )

    sys_grade = "Resilient" if graded_struct >= 60 else "Fragile"

    breach_min = stats.get('fatigue_breach_min')
    sustainable_after = max_minutes * PRESS_SUSTAINABLE_FRACTION
    press_rating = "Optimal" if breach_min is None or breach_min >= sustainable_after else "Overextended"

    ratings = {
        'press_sustainability': press_rating,
        'structural_stability': f"{min(h_struct, a_struct)}% ({sys_grade}: {graded_name})",
    }

    # ============================================================
    # 2. TURNING POINT DETECTION
    # ============================================================
    turning_point = "No singular critical failure event detected."
    if stats.get('struct_breach_min'):
        turning_point = (
            f"Minute {stats['struct_breach_min']} — Structural Integrity "
            f"dropped below {STRUCT_BREACH_INTEGRITY}%. Defensive cohesion entered critical failure state."
        )
    elif stats.get('fatigue_breach_min'):
        turning_point = (
            f"Minute {stats['fatigue_breach_min']} — Squad energy fell below "
            f"{FATIGUE_BREACH_STAMINA}%. Pressing intensity collapsed."
        )

    # ============================================================
    # 3. LUCK VS SYSTEM ATTRIBUTION
    # Measured from per-duel roll margins: how much of each contested roll
    # was decided by stats/tactics vs by the dice.
    # ============================================================
    sys_inf = stats.get('system_influence', 0.0)
    rand_inf = stats.get('random_influence', 0.0)
    total_inf = sys_inf + rand_inf
    sys_pct = int((sys_inf / total_inf) * 100) if total_inf > 0 else 50

    attribution = {
        'system': "High" if sys_pct > 60 else "Moderate" if sys_pct > 40 else "Low",
        'variance': "High" if sys_pct <= 40 else "Moderate" if sys_pct <= 60 else "Low",
        'system_pct': sys_pct,
    }

    # ============================================================
    # 4. ZONE DOMINANCE (action counts)
    # ============================================================
    zones = []
    for z, data in stats.get('zone_control', {}).items():
        h_count = data.get('home', 0)
        a_count = data.get('away', 0)
        if h_count > a_count:
            dom = home_name
        elif a_count > h_count:
            dom = away_name
        else:
            dom = "Contested"
        zones.append({'name': z, 'winner': dom, 'margin': abs(h_count - a_count)})

    # ============================================================
    # 5. ZONE INTEGRITY BREAKDOWN
    # ============================================================
    h_zone_finals = stats.get('home_zone_finals', {'Left': 100, 'Center': 100, 'Right': 100})
    a_zone_finals = stats.get('away_zone_finals', {'Left': 100, 'Center': 100, 'Right': 100})

    def classify(val):
        if val >= 70:
            return "solid"
        if val >= 50:
            return "stressed"
        if val >= 30:
            return "broken"
        return "collapsed"

    zone_breakdown = []
    for z in ['Left', 'Center', 'Right']:
        h_val = h_zone_finals.get(z, 100)
        a_val = a_zone_finals.get(z, 100)
        zone_breakdown.append({
            'zone': z,
            'home_val': h_val,
            'away_val': a_val,
            'home_state': classify(h_val),
            'away_state': classify(a_val),
            'home_worse': h_val < a_val,
        })

    # ============================================================
    # 6. PLAYER IMPACT LEADERBOARD (signed contributions)
    # ============================================================
    raw_impact = stats.get('impact_detail', {})
    sorted_players = sorted(
        raw_impact.items(),
        key=lambda x: x[1].get('total', 0),
        reverse=True
    )[:4]

    processed_impact = []
    for p_name, data in sorted_players:
        details = []
        if data.get('goals', 0) > 0:
            details.append(f"+{data['goals']} Key Goal Contributions")
        if data.get('saves', 0) > 0:
            details.append(f"+{data['saves']} Critical Saves")
        if data.get('damage', 0) > 0:
            details.append(f"+{data['damage']} Structural Damage Dealt")
        if data.get('def_stops', 0) > 0:
            details.append(f"+{data['def_stops']} Defensive Holds")
        if data.get('breaks', 0) > 0:
            details.append(f"+{data['breaks']} Tactical Breaks")
        if data.get('misses', 0) > 0:
            details.append(f"-{data['misses']} Chances Squandered")
        if data.get('turnovers', 0) > 0:
            details.append(f"-{data['turnovers']} Possession Losses")

        processed_impact.append({
            'name': p_name,
            'total': data.get('total', 0),
            'details': details[:3],
        })

    # ============================================================
    # 7. CAUSALITY CHAIN
    # ============================================================
    causality = []
    if stats.get('fatigue_breach_min'):
        causality.append(f"Fatigue Threshold Breach at {stats['fatigue_breach_min']}'")
    if stats.get('struct_breach_min'):
        causality.append(f"Structural Breach (Integrity < {STRUCT_BREACH_INTEGRITY}%) at {stats['struct_breach_min']}'")
    if not causality:
        causality.append("Sustainable System Performance")

    # ============================================================
    # 8. ASSEMBLE AND RETURN
    # ============================================================
    return {
        'outcome_type': "Systemic Result" if sys_pct > 60 else "Variance-Influenced Result",
        'ratings': ratings,
        'turning_point': turning_point,
        'attribution': attribution,
        'zones': zones,
        'zone_breakdown': zone_breakdown,
        'impact': processed_impact,
        'timeline': stats.get('timeline', []),
        'causality': causality,
    }
