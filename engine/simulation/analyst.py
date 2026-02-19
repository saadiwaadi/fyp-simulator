def generate_post_match_report(stats, home_name, away_name):
    h_struct = stats.get('home_integrity_final', 100)
    a_struct = stats.get('away_integrity_final', 100)
    
    # 1. TIERED RATINGS (Managerial Grade)
    def get_tier(val, threshold, label_high, label_low):
        return f"{label_high}" if val >= threshold else f"{label_low}"

    sys_grade = get_tier(h_struct, 60, "Resilient", "Fragile") if stats.get('home_score', 0) > stats.get('away_score', 0) else get_tier(a_struct, 60, "Resilient", "Fragile")
    
    ratings = {
        # Raw system_influence percentage removed for production
        'press_sustainability': get_tier(stats.get('fatigue_breach_min', 90), 70, "Optimal", "Overextended"),
        'structural_stability': f"{min(h_struct, a_struct)}% ({sys_grade})",
    }

    # 2. TURNING POINT DETECTION
    turning_point = "No singular critical failure event detected."
    if stats.get('struct_breach_min'):
        turning_point = f"Minute {stats.get('struct_breach_min')} – Structural Integrity dropped below 40%. Defensive cohesion entered critical failure state."
    elif stats.get('fatigue_breach_min'):
        turning_point = f"Minute {stats.get('fatigue_breach_min')} – Midfield energy levels critical. Pressing intensity collapsed."

    # 3. LUCK VS SYSTEM (Professionalized for UI)
    total_inf = stats.get('system_influence', 0) + stats.get('random_influence', 0) + 1
    sys_pct = int((stats.get('system_influence', 0) / total_inf) * 100)
    
    attribution = {
        'system': "High" if sys_pct > 60 else "Moderate" if sys_pct > 40 else "Low",
        'variance': "High" if sys_pct <= 40 else "Moderate" if sys_pct <= 60 else "Low"
    }

    # 4. ZONE DOMINANCE
    zones = []
    for z, data in stats.get('zone_control', {}).items():
        dom = home_name if data.get('home', 0) > data.get('away', 0) else away_name
        margin = abs(data.get('home', 0) - data.get('away', 0))
        zones.append({'name': z, 'winner': dom, 'margin': margin})

    # 5. DETAILED IMPACT PROCESSING
    raw_impact = stats.get('impact_detail', {})
    sorted_players = sorted(raw_impact.items(), key=lambda x: x[1].get('total', 0), reverse=True)[:4]
    
    processed_impact = []
    for p_name, data in sorted_players:
        details = []
        if data.get('goals', 0) > 0: details.append(f"+{data['goals']} Key Goal Contributions")
        if data.get('saves', 0) > 0: details.append(f"+{data['saves']} Critical Saves")
        if data.get('damage', 0) > 0: details.append(f"+{data['damage']} Structural Damage Dealt")
        if data.get('def_stops', 0) > 0: details.append(f"+{data['def_stops']} Defensive Holds")
        if data.get('breaks', 0) > 0: details.append(f"+{data['breaks']} Tactical Breaks")
        
        processed_impact.append({
            'name': p_name,
            'total': data.get('total', 0),
            'details': details[:3]
        })

    # 6. CAUSALITY CHAIN
    causality = []
    if stats.get('fatigue_breach_min'): causality.append(f"Fatigue Threshold Breach at {stats.get('fatigue_breach_min')}'")
    if stats.get('struct_breach_min'): causality.append("Structural Collapse (Integrity < 40%)")
    if not causality: causality.append("Sustainable System Performance")

    return {
        'outcome_type': "Systemic Victory" if sys_pct > 60 else "Variance-Based Result",
        'ratings': ratings,
        'turning_point': turning_point,
        'attribution': attribution,
        'zones': zones,
        'impact': processed_impact,
        'timeline': stats.get('timeline', []),
        'causality': causality
    }