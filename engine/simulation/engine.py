import random
import uuid # Add this import at the top
from collections import defaultdict
from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator
from .tactics import get_tactical_profile
from .environment import FIVE_V_FIVE, ELEVEN_V_ELEVEN
from .matchups import select_duellists


def play_match(home_team, away_team, h_players, a_players, mode="5v5", sys_style=None, match_seed=None):
    if match_seed:
        random.seed(match_seed)
    else:
        # Reset to true random if no seed is passed
        random.seed()
    # ====================================================
    # 1. ENVIRONMENT & SETUP
    # ====================================================
    env = ELEVEN_V_ELEVEN if mode == "11v11" else FIVE_V_FIVE

    team_home = [SimPlayer(p) for p in h_players]
    team_away = [SimPlayer(p) for p in a_players]

    if len(team_home) < env.squad_size or len(team_away) < env.squad_size:
        return ["ERROR: Squads too small."], {}

    h_profile = get_tactical_profile(getattr(home_team, 'tactical_mode', 'Standard'))
    a_profile = get_tactical_profile(getattr(away_team, 'tactical_mode', 'Standard'))

    state = MatchState(home_team.name, away_team.name)

    h_style = getattr(home_team, 'sys_style', sys_style or {})
    a_style = getattr(away_team, 'sys_style', {})

    # ---> ADD THESE TWO LINES HERE <---
    # Calculate Base Team OVR directly from the DB models to avoid wrapper missing attributes
    # FIXED: Actually divide by 4.0 so a 95-rated player evaluates as 95, not 380!
    h_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0 for p in h_players]) / max(len(h_players), 1)
    a_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0 for p in a_players]) / max(len(a_players), 1)


    # RESTORED: All tracking metrics are back in the dictionary
    # RESTORED: All tracking metrics are back in the dictionary
    state.stats.update({
        'home_score': 0, 'away_score': 0,
        'home_possession_count': 0, 'away_possession_count': 0,
        'h_tempo': h_style.get('tempo', 3), 'h_press': h_style.get('press', 3),
        'h_risk':  h_style.get('risk', 3),  'h_depth': h_style.get('depth', 3),
        'a_tempo': a_style.get('tempo', 3), 'a_press': a_style.get('press', 3),
        'a_risk':  a_style.get('risk', 3),  'a_depth': a_style.get('depth', 3),
        'timeline': [],
        'fatigue_breach_min': None,
        'struct_breach_min': None,
        'break_timestamps': [],  # <--- ADD THIS LINE HERE
        'zone_control': {'Center': {'home':0, 'away':0}, 'Left': {'home':0, 'away':0}, 'Right': {'home':0, 'away':0}},
        'system_influence': 0, 'random_influence': 0,
        'impact_detail': defaultdict(lambda: {
            'total': 0, 'breaks': 0, 'damage': 0, 'saves': 0, 'goals': 0, 'def_stops': 0
        })
    })

    log = []
    log.append(f"MATCH STARTED: {home_team.name} vs {away_team.name} ({mode})")
    home_has_ball = True

    def add_impact(name, category, points):
        state.stats['impact_detail'][name]['total'] += points
        state.stats['impact_detail'][name][category] += 1

    # ====================================================
    # 3. MATCH LOOP
    # ====================================================
    # ==========================================
    # --- CORE MATCH LOOP ---
    # ==========================================
    
    # FIX: Dynamically set match length based on the game mode
    max_minutes = 40 if mode == '5v5' else 90

    # Start the simulation timer
    for minute in range(1, max_minutes + 1):
        
        # 1. Apply Fatigue (Drains faster in 5v5 because they run more!)
        fatigue_drain = 2 if mode == '5v5' else 1
        
      

        # --- RESTORED: FORENSICS & TIMELINE ---
        avg_h_stam = sum(p.current_stamina for p in team_home) / len(team_home)
        avg_a_stam = sum(p.current_stamina for p in team_away) / len(team_away)
        
        # Track exact minute the team gasses out
        if (avg_h_stam < 50 or avg_a_stam < 50) and state.stats['fatigue_breach_min'] is None:
            state.stats['fatigue_breach_min'] = minute

        # Track exact minute the tactical structure collapses
        if (state.home_structure["overall"] < 40 or state.away_structure["overall"] < 40) and state.stats['struct_breach_min'] is None:
            state.stats['struct_breach_min'] = minute

        # Record timeline data for UI graphing
        if minute % 15 == 1 or minute == 88:
            state.stats['timeline'].append({
                'min': minute,
                'h_struct': int(state.home_structure["overall"]),
                'a_struct': int(state.away_structure["overall"]),
            })

        # --- Possession Tracking ---
        if home_has_ball: state.stats['home_possession_count'] += 1
        else: state.stats['away_possession_count'] += 1

        att_team, def_team = (team_home, team_away) if home_has_ball else (team_away, team_home)
        att_side, def_side = ('home', 'away') if home_has_ball else ('away', 'home')
        att_profile = h_profile if att_side == 'home' else a_profile
        def_profile = a_profile if att_side == 'home' else h_profile

        try:
            carrier, defender, gk, match_zone = select_duellists(att_team, def_team, mode)
        except:
            continue

        # --- RESTORED: ZONE TRACKING ---
        zone_key = "Center"
        if "Left" in match_zone: zone_key = "Left"
        elif "Right" in match_zone: zone_key = "Right"
        state.stats['zone_control'][zone_key][att_side] += 1

        # ====================================================
        # 4. FATIGUE & ESCALATION
        # ====================================================
        h_burn = (state.stats['h_tempo'] + state.stats['h_press']) / 6.0
        a_burn = (state.stats['a_tempo'] + state.stats['a_press']) / 6.0

        score_diff = state.stats['home_score'] - state.stats['away_score']
        escalation_boost = 1.0

        if score_diff != 0:
            trailing = 'home' if score_diff < 0 else 'away'
            if att_side == trailing:
                escalation_boost = 1.10 if mode == "5v5" else 1.05
                if att_side == 'home': h_burn *= 1.15
                else: a_burn *= 1.15

        # --- NEW FATIGUE LOGIC (Sledgehammer) ---
        # Dialed back to 1.0. High press teams will gas out around 60' instead of 34'
        passive_h_drain = 1.0 * h_burn 
        passive_a_drain = 1.0 * a_burn
        for p in team_home: p.drain_stamina(passive_h_drain)
        for p in team_away: p.drain_stamina(passive_a_drain)

        # Active duellist drain: ~3.5 per duel
        carrier.drain_stamina(3.5 * (h_burn if att_side == 'home' else a_burn))
        defender.drain_stamina(3.5 * (h_burn if def_side == 'home' else a_burn))
        
        # ====================================================
        # 5. GRANULAR MATH (Unmuted Structure & Mismatches)
        # ====================================================
        raw_att_struct = state.get_structure_mult(att_side)
        raw_def_struct = state.get_structure_mult(def_side)
        struct_att = 0.6 + (raw_att_struct * 0.4) 
        struct_def = 0.6 + (raw_def_struct * 0.4)

        mismatch_scale = 0.07 if mode == "5v5" else 0.04
        att_tempo = state.stats['h_tempo'] if att_side == 'home' else state.stats['a_tempo']
        def_press = state.stats['h_press'] if def_side == 'home' else state.stats['a_press']
        att_risk  = state.stats['h_risk']  if att_side == 'home' else state.stats['a_risk']
        def_depth = state.stats['h_depth'] if def_side == 'home' else state.stats['a_depth']

        m_poss_att, m_poss_def = 1.0, 1.0
        m_break_att, m_break_def = 1.0, 1.0

        if def_press > att_tempo: m_poss_def += (def_press - att_tempo) * mismatch_scale
        elif att_tempo > def_press: m_poss_att += (att_tempo - def_press) * mismatch_scale

        if att_risk > def_depth: m_break_att += (att_risk - def_depth) * mismatch_scale
        elif def_depth > att_risk: m_break_def += (def_depth - att_risk) * mismatch_scale

       # ====================================================
        # FINAL MULTIPLIERS
        # ====================================================
        att_fit = carrier.get_tactical_fit(att_profile)
        def_fit = defender.get_tactical_fit(def_profile)

        stat_adv = (h_ovr - a_ovr) if att_side == 'home' else (a_ovr - h_ovr)
        
        # Dialed back divisor to 75.0 for a realistic curve
        stat_multiplier = max(0.5, 1.0 + (stat_adv / 75.0))

        # +0.20 Attacker Advantage so evenly matched games don't end 0-0
        base_att_adv = 0.20

        poss_att = min((struct_att * att_fit * escalation_boost * m_poss_att * stat_multiplier) + base_att_adv, 3.5)
        poss_def = min(struct_def * def_fit * m_poss_def * (1.0 if stat_adv > 0 else (1.0 + abs(stat_adv)/75.0)), 3.5)
        
        break_att = min((struct_att * att_fit * escalation_boost * m_break_att * stat_multiplier) + base_att_adv, 3.5)
        break_def = min(struct_def * def_fit * m_break_def * (1.0 if stat_adv > 0 else (1.0 + abs(stat_adv)/75.0)), 3.5)

        state.stats['system_influence'] += abs(break_att - break_def)
        state.stats['random_influence'] += 0.1

        # ====================================================
        # PHASE 1 – POSSESSION
        # ====================================================
        if not mechanics.resolve_possession(carrier, defender, poss_att, poss_def):
            log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name, zone=match_zone))
            add_impact(defender.name, 'def_stops', 3)
            home_has_ball = not home_has_ball
            continue

        # ====================================================
        # PHASE 2 – BREAK 
        # ====================================================
        if not mechanics.resolve_tactical_break(carrier, defender, break_att, break_def):
            log.append(narrator.announce(minute, 'BLOCK', player=defender.name))
            add_impact(defender.name, 'def_stops', 2)
            home_has_ball = not home_has_ball
            continue

        state.stats['break_timestamps'].append(minute)

        opp_struct_val = state.home_structure["overall"] if def_side == 'home' else state.away_structure["overall"]
        # 3.0x Multiplier: A successful tactical break genuinely shatters the line
        damage = mechanics.calculate_damage(defender.current_stamina, opp_struct_val, base_damage=env.base_damage) * 3.0
        state.degrade_structure(def_side, damage)
        
        log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(), damage=damage, zone=match_zone))
        add_impact(carrier.name, 'breaks', 4)
        add_impact(carrier.name, 'damage', int(damage))

        # ====================================================
        # PHASE 3 – SHOT 
        # ====================================================
        # +0.20 Base Boost so attackers actually get shots off. 
        # Punish broken structures/tired defenders slightly more (+0.15).
        # Base 0.65 means 65% of breaks turn into shots (instead of 20%)
        d_density = 0.65 
        if opp_struct_val < 60: d_density += 0.20 # Avalanche!
        if defender.current_stamina < 45: d_density += 0.15

        if random.random() > min(d_density, 0.95):
            log.append(f"{minute}' [RECOVERY] {defender.name} tracks back to snuff out the danger!")
            home_has_ball = not home_has_ball
            continue

        striker = max([p for p in att_team if p.role != 'GK'], key=lambda p: p.finishing + random.randint(0, 15))
        
        # Dialed back the divisor to 15.0 so the bonus is strong but not guaranteed-goal strong
        bonus = ((100 - opp_struct_val) / 6.0) + (stat_adv / 15.0)

        
        result = mechanics.resolve_finish(striker, gk, break_att, bonus, minute)

        if result == 'GOAL':
            state.stats[f'{att_side}_score'] += 1
            add_impact(striker.name, 'goals', 15)
            log.append(narrator.announce(minute, 'GOAL', player=striker.name, score=f"{state.stats['home_score']}-{state.stats['away_score']}"))
            home_has_ball = not home_has_ball
        elif result == 'SAVE':
            log.append(narrator.announce(minute, 'SAVE', player=gk.name))
            add_impact(gk.name, 'saves', 8)
            if random.random() < 0.5: home_has_ball = not home_has_ball
        else:
            log.append(narrator.announce(minute, 'MISS', player=striker.name))
            if random.random() < 0.5: home_has_ball = not home_has_ball

    # ====================================================
    # 8. FINALIZE
    # ====================================================
    total = max(state.stats['home_possession_count'] + state.stats['away_possession_count'], 1)
    state.stats['home_possession_pct'] = int((state.stats['home_possession_count'] / total) * 100)
    state.stats['home_integrity_final'] = int(state.home_structure["overall"])
    state.stats['away_integrity_final'] = int(state.away_structure["overall"])
    log.append("FULL TIME.")
    return log, state.stats