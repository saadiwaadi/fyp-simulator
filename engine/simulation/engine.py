# engine/simulation/engine.py
# ============================================================
# PHASE A — ZONAL STRUCTURE PROPAGATION
#
# WHAT CHANGED FROM V4:
#   1. regen_structure() helper REMOVED — all regen goes through state methods.
#      Single writer rule: state.py is the only thing that touches structure.
#   2. All degrade_structure() calls now pass zone_key.
#   3. All regen calls now pass zone_key where contextually appropriate.
#   4. get_structure_mult() calls pass zone_key for combat math.
#   5. opp_struct_val now reads the ZONE's health (not global overall).
#      Shot quality depends on how damaged the ATTACKED zone is.
#   6. Timeline snapshots now include per-zone data.
#   7. Finalize captures zone_finals in stats for Deep Scan.
#   8. zone_pressure_counter added (Phase B groundwork — not yet wired).
#   9. ZONE_MAP added at top — single place to update L/C/R → full names.
#
# RULE: Never write to state.home_structure or state.away_structure directly.
#       Always go through state.degrade_structure() or state.regen_structure().
# ============================================================

import random
import uuid
from collections import defaultdict

from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator
from .tactics import get_tactical_profile
from .environment import FIVE_V_FIVE, ELEVEN_V_ELEVEN
from .matchups import select_duellists


# ============================================================
# ZONE NORMALIZATION MAP
# Matchups returns single-char zones ('L', 'C', 'R').
# Everything else uses full names. This is the single translation point.
# ============================================================
ZONE_MAP = {
    'L': 'Left',
    'C': 'Center',
    'R': 'Right',
}


def play_match(home_team, away_team, h_players, a_players, mode="5v5",
               sys_style=None, match_seed=None):

    # --- SEED CONTROL ---
    if match_seed:
        random.seed(match_seed)
    else:
        random.seed()  # True random if no seed

    # ============================================================
    # 1. ENVIRONMENT & SQUAD SETUP
    # ============================================================
    env = ELEVEN_V_ELEVEN if mode == "11v11" else FIVE_V_FIVE

    team_home = [SimPlayer(p) for p in h_players]
    team_away = [SimPlayer(p) for p in a_players]

    if len(team_home) < env.squad_size or len(team_away) < env.squad_size:
        return ["ERROR: Squads too small."], {}

    # Tactical profiles (High Press, Tiki Taka, etc.)
    h_profile = get_tactical_profile(getattr(home_team, 'tactical_mode', 'Standard'))
    a_profile = get_tactical_profile(getattr(away_team, 'tactical_mode', 'Standard'))

    # Match state — the live data store
    state = MatchState(home_team.name, away_team.name)

    # Slider styles (tempo, press, risk, depth, width)
    h_style = getattr(home_team, 'sys_style', sys_style or {})
    a_style = getattr(away_team, 'sys_style', {})

    # Team OVR — used for stat_advantage calculation
    # FIXED: /4.0 so a 95-rated player reads as 95, not 380
    h_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0
                 for p in h_players]) / max(len(h_players), 1)
    a_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0
                 for p in a_players]) / max(len(a_players), 1)

    # ============================================================
    # 2. STATS INITIALIZATION
    # ============================================================
    state.stats.update({
        'home_score': 0, 'away_score': 0,
        'home_possession_count': 0, 'away_possession_count': 0,

        # Slider snapshot (for analyst + Deep Scan display)
        'h_tempo': h_style.get('tempo', 3), 'h_press': h_style.get('press', 3),
        'h_risk':  h_style.get('risk',  3), 'h_depth': h_style.get('depth', 3),
        'a_tempo': a_style.get('tempo', 3), 'a_press': a_style.get('press', 3),
        'a_risk':  a_style.get('risk',  3), 'a_depth': a_style.get('depth', 3),

        # Match event trackers
        'timeline':          [],
        'fatigue_breach_min': None,
        'struct_breach_min':  None,
        'break_timestamps':   [],

        # PHASE A: Zone control action counts (how many attacks per zone per side)
        'zone_control': {
            'Center': {'home': 0, 'away': 0},
            'Left':   {'home': 0, 'away': 0},
            'Right':  {'home': 0, 'away': 0},
        },

        # Attribution trackers
        'system_influence': 0,
        'random_influence': 0,

        # Per-player impact tracking (for MVP calculation)
        'impact_detail': defaultdict(lambda: {
            'total': 0, 'breaks': 0, 'damage': 0,
            'saves': 0, 'goals': 0, 'def_stops': 0
        }),

        # PHASE A: Zone finals (populated in FINALIZE section)
        'home_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},
        'away_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},

        # PHASE B GROUNDWORK: zone pressure counters (not yet wired into math)
        # When Phase B is implemented, these feed the density redistribution.
        '_zone_pressure': {
            'home': {'Left': 0, 'Center': 0, 'Right': 0},
            'away': {'Left': 0, 'Center': 0, 'Right': 0},
        },
    })

    log = []
    log.append(f"MATCH STARTED: {home_team.name} vs {away_team.name} ({mode})")
    home_has_ball = True

    # Impact helper — clean accumulator for MVP scores
    def add_impact(name, category, points):
        state.stats['impact_detail'][name]['total'] += points
        state.stats['impact_detail'][name][category] += 1

    # ============================================================
    # 3. STATE TRACKERS
    # ============================================================
    max_minutes = 40 if mode == '5v5' else 90

    # Zone congestion cooldown (prevents center spam — V4 logic preserved)
    consecutive_center = {'home': 0, 'away': 0}

    # Player influence cap (prevents one player dominating every minute)
    player_influence = defaultdict(int)

    # ============================================================
    # 4. MAIN MATCH LOOP
    # ============================================================
    for minute in range(1, max_minutes + 1):

        # --- FATIGUE BREACH CHECK ---
        avg_h_stam = sum(p.current_stamina for p in team_home) / len(team_home)
        avg_a_stam = sum(p.current_stamina for p in team_away) / len(team_away)

        if (avg_h_stam < 50 or avg_a_stam < 50) and state.stats['fatigue_breach_min'] is None:
            state.stats['fatigue_breach_min'] = minute

        # --- STRUCTURAL BREACH CHECK (uses overall for narrative trigger) ---
        if (state.home_structure["overall"] < 40 or
                state.away_structure["overall"] < 40) and \
                state.stats['struct_breach_min'] is None:
            state.stats['struct_breach_min'] = minute

        # --- PHASE SHIFT NARRATIVE ---
        # Check both teams every minute — broadcasts dramatic alerts to log
        for side, name, team in [('home', home_team.name, team_home),
                                   ('away', away_team.name, team_away)]:
            phase_msg = state.check_phase_shift(side, name)
            if phase_msg:
                log.append(phase_msg)

        # --- TIMELINE SNAPSHOT ---
        # PHASE A: Now includes per-zone data for the integrity chart
        if minute % 15 == 1 or minute == max_minutes - 2:
            state.stats['timeline'].append({
                'min':     minute,
                # Overall (for the line chart)
                'h_struct': int(state.home_structure["overall"]),
                'a_struct': int(state.away_structure["overall"]),
                # PHASE A: Zonal breakdown (for future zone integrity chart)
                'h_zones': state.get_zone_snapshot('home'),
                'a_zones': state.get_zone_snapshot('away'),
            })

        # --- POSSESSION TRACKING ---
        if home_has_ball:
            state.stats['home_possession_count'] += 1
        else:
            state.stats['away_possession_count'] += 1

        # Assign attacker/defender sides for this minute
        att_team  = team_home  if home_has_ball else team_away
        def_team  = team_away  if home_has_ball else team_home
        att_side  = 'home'     if home_has_ball else 'away'
        def_side  = 'away'     if home_has_ball else 'home'
        att_profile = h_profile if att_side == 'home' else a_profile
        def_profile = a_profile if att_side == 'home' else h_profile

        # --- DUELLIST SELECTION ---
        try:
            duellists = select_duellists(att_team, def_team, mode)
            if not duellists:
                home_has_ball = not home_has_ball
                continue
            carrier, defender, gk, raw_zone = duellists
        except Exception:
            home_has_ball = not home_has_ball
            continue

        # --- ZONE NORMALIZATION ---
        # Translate matchups' single-char zone to full name
        # e.g. 'L' → 'Left', 'C' → 'Center', 'R' → 'Right'
        zone_key = ZONE_MAP.get(raw_zone, 'Center')

        # ============================================================
        # ZONE CONGESTION COOLDOWN (V4 preserved)
        # If center is attacked 3+ consecutive times, force wide play.
        # ============================================================
        if zone_key == "Center":
            consecutive_center[att_side] += 1
            if consecutive_center[att_side] > 2:
                zone_key = random.choice(["Left", "Right"])
                consecutive_center[att_side] = 0
        else:
            consecutive_center[att_side] = 0

        # Track zone actions for stats + PHASE B groundwork
        state.stats['zone_control'][zone_key][att_side] += 1
        state.stats['_zone_pressure'][att_side][zone_key] += 1  # Phase B

        # ============================================================
        # PLAYER INFLUENCE CAP (V4 preserved)
        # Over-involved player takes fatigue spike + decision penalty.
        # ============================================================
        player_influence[carrier.name] += 1
        influence_penalty = 1.0

        if player_influence[carrier.name] > (max_minutes / 4):
            influence_penalty = 0.75   # Decision quality drops 25%
            carrier.drain_stamina(2.0) # Overexertion fatigue spike

        # ============================================================
        # 5. FATIGUE & ESCALATION
        # ============================================================
        h_burn = (state.stats['h_tempo'] + state.stats['h_press']) / 6.0
        a_burn = (state.stats['a_tempo'] + state.stats['a_press']) / 6.0

        score_diff      = state.stats['home_score'] - state.stats['away_score']
        escalation_boost = 1.0

        if score_diff != 0:
            trailing = 'home' if score_diff < 0 else 'away'
            if att_side == trailing:
                # Trailing team presses harder — burns more
                escalation_boost = 1.10 if mode == "5v5" else 1.05
                if att_side == 'home': h_burn *= 1.15
                else:                  a_burn *= 1.15

        # Passive drain for all players this minute
        passive_h_drain = 0.5 * h_burn
        passive_a_drain = 0.5 * a_burn
        for p in team_home: p.drain_stamina(passive_h_drain)
        for p in team_away: p.drain_stamina(passive_a_drain)

        # Active drain for duellists (more intense than passive)
        carrier.drain_stamina(1.2 * (h_burn if att_side == 'home' else a_burn))
        defender.drain_stamina(1.0 * (h_burn if def_side == 'home' else a_burn))

        # ============================================================
        # 6. GRANULAR MATH — MULTIPLIER CALCULATION
        # ============================================================

        # PHASE A: Use zone-specific structure values for combat math
        # This is the core change: combat effectiveness is now spatial
        raw_att_struct = state.get_structure_mult(att_side, zone=zone_key)
        raw_def_struct = state.get_structure_mult(def_side, zone=zone_key)

        # Floor the multipliers so shape is never irrelevant
        struct_att = 0.6 + (raw_att_struct * 0.4)
        struct_def = 0.6 + (raw_def_struct * 0.4)

        # Tactical slider mismatches
        mismatch_scale = 0.07 if mode == "5v5" else 0.04
        att_tempo = state.stats['h_tempo'] if att_side == 'home' else state.stats['a_tempo']
        def_press = state.stats['h_press'] if def_side == 'home' else state.stats['a_press']
        att_risk  = state.stats['h_risk']  if att_side == 'home' else state.stats['a_risk']
        def_depth = state.stats['h_depth'] if def_side == 'home' else state.stats['a_depth']

        m_poss_att, m_poss_def = 1.0, 1.0
        m_break_att, m_break_def = 1.0, 1.0

        if def_press > att_tempo:
            m_poss_def += (def_press - att_tempo) * mismatch_scale
        elif att_tempo > def_press:
            m_poss_att += (att_tempo - def_press) * mismatch_scale

        if att_risk > def_depth:
            m_break_att += (att_risk - def_depth) * mismatch_scale
        elif def_depth > att_risk:
            m_break_def += (def_depth - att_risk) * mismatch_scale

        # Tactical fit + influence penalty applied to attacker
        att_fit = carrier.get_tactical_fit(att_profile) * influence_penalty
        def_fit = defender.get_tactical_fit(def_profile)

        # OVR stat advantage (dampened — stats define difficulty, not destiny)
        stat_adv       = (h_ovr - a_ovr) if att_side == 'home' else (a_ovr - h_ovr)
        stat_multiplier = max(0.5, 1.0 + (stat_adv / 75.0))
        base_att_adv    = 0.10  # Slight default advantage to attackers

        # Final phase multipliers (capped to prevent runaway values)
        poss_att = min(
            (struct_att * att_fit * escalation_boost * m_poss_att * stat_multiplier) + base_att_adv, 3.5
        )
        poss_def = min(
            struct_def * def_fit * m_poss_def * (1.0 if stat_adv > 0 else (1.0 + abs(stat_adv) / 75.0)), 3.5
        )
        break_att = min(
            (struct_att * att_fit * escalation_boost * m_break_att * stat_multiplier) + base_att_adv, 3.5
        )
        break_def = min(
            struct_def * def_fit * m_break_def * (1.0 if stat_adv > 0 else (1.0 + abs(stat_adv) / 75.0)), 3.5
        )

        state.stats['system_influence'] += abs(break_att - break_def)
        state.stats['random_influence'] += 0.1

        # ============================================================
        # PHASE 1 — POSSESSION
        # ============================================================
        if not mechanics.resolve_possession(carrier, defender, poss_att, poss_def):
            log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name, zone=raw_zone))
            add_impact(defender.name, 'def_stops', 3)

            # PHASE A: Targeted zone regen — defender won ball in this zone
            state.regen_structure(def_side, 1.5, zone=zone_key)
            home_has_ball = not home_has_ball
            continue

        # ============================================================
        # PHASE 2 — TACTICAL BREAK
        # ============================================================
        if not mechanics.resolve_tactical_break(carrier, defender, break_att, break_def):
            log.append(narrator.announce(minute, 'BLOCK', player=defender.name))
            add_impact(defender.name, 'def_stops', 2)

            # PHASE A: Zone regen — defender halted the attack in this zone
            state.regen_structure(def_side, 2.5, zone=zone_key)
            home_has_ball = not home_has_ball
            continue

        # --- BREAK SUCCEEDED — record timestamp and apply damage ---
        state.stats['break_timestamps'].append(minute)

        # PHASE A: Read zone-specific health for damage calculation
        # The attacked zone's health is what matters — not the global overall
        def_struct = state.home_structure if def_side == 'home' else state.away_structure
        zone_health = def_struct["zones"][zone_key]

        # Enforce floor silently before reading (prevents negative readings)
        zone_health = max(40.0, zone_health)

        # Calculate and cap damage
        damage = mechanics.calculate_damage(
            defender.current_stamina,
            zone_health,                 # PHASE A: Zone-specific health
            base_damage=env.base_damage
        ) * 1.2
        damage = min(damage, 4.0)

        # PHASE A: Degrade the specific zone that was attacked
        state.degrade_structure(def_side, damage, zone=zone_key)

        log.append(narrator.announce(
            minute, 'TACTIC',
            player=carrier.name,
            team=def_side.title(),
            damage=round(damage, 1),
            zone=raw_zone
        ))
        add_impact(carrier.name, 'breaks', 4)
        add_impact(carrier.name, 'damage', int(damage))

        # ============================================================
        # PHASE 3 — SHOT RESOLUTION
        # ============================================================

        # Defensive density check — based on zone health and defender fatigue
        d_density = 0.40
        if zone_health < 60:  d_density += 0.15   # Broken zone = more shots
        if defender.current_stamina < 45: d_density += 0.10  # Tired = more shots

        if random.random() > min(d_density, 0.85):
            log.append(f"{minute}' [RECOVERY] {defender.name} tracks back to snuff out the danger!")
            # Zone regen for recovery
            state.regen_structure(def_side, 2.0, zone=zone_key)
            home_has_ball = not home_has_ball
            continue

        # Pick striker (best finisher with some randomness)
        striker = max(
            [p for p in att_team if p.role != 'GK'],
            key=lambda p: p.finishing + random.randint(0, 15)
        )

        # FATIGUE PRECISION PENALTY (V4 preserved)
        # Below 60% stamina = sloppy shots
        precision_penalty = 0
        if striker.current_stamina < 60:
            precision_penalty = (60 - striker.current_stamina) / 100.0

        # Integrity bonus: broken zone = better chance, but tired striker negates it
        bonus = ((100 - zone_health) / 20.0) + (stat_adv / 15.0) - precision_penalty

        result = mechanics.resolve_finish(striker, gk, break_att, bonus, minute)

        if result == 'GOAL':
            state.stats[f'{att_side}_score'] += 1
            add_impact(striker.name, 'goals', 15)
            log.append(narrator.announce(
                minute, 'GOAL',
                player=striker.name,
                score=f"{state.stats['home_score']}-{state.stats['away_score']}"
            ))

            # Goal reset: structure recovers, but scaled by remaining stamina
            # (A tired team can't instantly reform after conceding)
            avg_def_stam   = sum(p.current_stamina for p in def_team) / len(def_team)
            regen_amount   = 15.0 * (max(avg_def_stam, 10.0) / 100.0)

            # PHASE A: Spread recovery across all zones after goal
            state.regen_structure(def_side, regen_amount, zone=None)
            home_has_ball = not home_has_ball

        elif result == 'SAVE':
            log.append(narrator.announce(minute, 'SAVE', player=gk.name))
            add_impact(gk.name, 'saves', 8)
            if random.random() < 0.5: home_has_ball = not home_has_ball

        else:  # MISS
            log.append(narrator.announce(minute, 'MISS', player=striker.name))
            if random.random() < 0.5: home_has_ball = not home_has_ball

    # ============================================================
    # 8. FINALIZE — Write all stats for analyst and template
    # ============================================================
    total = max(
        state.stats['home_possession_count'] + state.stats['away_possession_count'], 1
    )
    state.stats['home_possession_pct']  = int((state.stats['home_possession_count'] / total) * 100)

    # Overall integrity finals (backwards compat)
    state.stats['home_integrity_final'] = int(state.home_structure["overall"])
    state.stats['away_integrity_final'] = int(state.away_structure["overall"])

    # PHASE A: Zonal integrity finals for Deep Scan zone breakdown
    state.stats['home_zone_finals'] = state.get_zone_snapshot('home')
    state.stats['away_zone_finals'] = state.get_zone_snapshot('away')

    log.append("FULL TIME.")
    return log, state.stats