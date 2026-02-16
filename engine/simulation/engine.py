import random
from collections import defaultdict
from engine.models import Player as DBPlayer, Team as DBTeam
from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator
from .tactics import get_tactical_profile
from .environment import get_environment, FIVE_V_FIVE, ELEVEN_V_ELEVEN
from .matchups import select_duellists 

# ==========================================
# THE ENGINE (v2.6 - Spatial & Modular)
# ==========================================
def play_match(home_team_name, away_team_name, mode="5v5"): 
    
    # --- SETUP PHASE ---
    if mode == "11v11": env = ELEVEN_V_ELEVEN
    else: env = FIVE_V_FIVE

    try:
        home_db = DBTeam.objects.get(name=home_team_name)
        away_db = DBTeam.objects.get(name=away_team_name)
    except DBTeam.DoesNotExist:
        return [f"ERROR: Teams not found."], {}

    h_players = list(home_db.player_set.all())
    a_players = list(away_db.player_set.all())

    if len(h_players) < env.squad_size or len(a_players) < env.squad_size:
        return [f"ERROR: Squads too small for {mode}. Need {env.squad_size}."], {}

    team_home = [SimPlayer(p) for p in h_players]
    team_away = [SimPlayer(p) for p in a_players]

    h_profile = get_tactical_profile(home_db.tactical_mode)
    a_profile = get_tactical_profile(away_db.tactical_mode)

    state = MatchState(home_team_name, away_team_name)
    log = [] 
    log.append(f"MATCH STARTED: {home_team_name} vs {away_team_name} (Mode: {mode})")
    
    dominance_tracker = defaultdict(int)
    home_has_ball = True 

    # --- THE LOOP ---
    for minute in range(1, 91, 3): 
        # A. Possession Tracking
        if home_has_ball: state.stats['home_possession_count'] += 1
        else: state.stats['away_possession_count'] += 1
        
        # B. Define Side Context
        att_team, def_team = (team_home, team_away) if home_has_ball else (team_away, team_home)
        att_side, def_side = ('home', 'away') if home_has_ball else ('away', 'home')
        att_profile = h_profile if home_has_ball else a_profile
        def_profile = a_profile if home_has_ball else h_profile
        
        # [v2.6] Spatial Selection
        # matchups.py now handles the 30/40/30 zone logic
        carrier, defender, gk, match_zone = select_duellists(att_team, def_team, mode)

        # Track Player Dominance
        dominance_tracker[carrier.name] += 1
        dominance_tracker[defender.name] += 1
        
        # C. Calculate Tactical Fit & Position Tax
        att_fit = carrier.get_tactical_fit(att_profile)
        def_fit = defender.get_tactical_fit(def_profile)
        
        # [v2.6] Position DNA lookup
        zone_att_mod = carrier.zone_coverage.get(match_zone, 1.0)
        zone_def_mod = defender.zone_coverage.get(match_zone, 1.0)

        # D. Fatigue Scaling (Environment Conscious)
        carrier.drain_stamina(env.fatigue_scale * att_profile.stam_burn * (1.0 / att_fit))
        defender.drain_stamina(env.fatigue_scale * def_profile.stam_burn * (1.0 / def_fit))

        # E. Calculate Final Multipliers (The "Chain of Logic")
        state.stats[f'{att_side}_passes_attempted'] += 1
        
        integ_att = state.get_structure_mult(att_side)
        integ_def = state.get_structure_mult(def_side)

        dom_att = 0.95 if dominance_tracker[carrier.name] > 4 else 1.0
        dom_def = 0.95 if dominance_tracker[defender.name] > 4 else 1.0

        # [v2.6] Final Combined Multipliers - Capped at 1.15 for balance
        # Sequence: Integrity * Tactic * Personality Fit * Dominance * Position
        raw_att = integ_att * att_profile.att_mult * att_fit * dom_att * zone_att_mod
        final_att_mult = min(raw_att, 1.15)
        
        raw_def = integ_def * def_profile.def_mult * def_fit * dom_def * zone_def_mod
        final_def_mult = min(raw_def, 1.15)

        raw_int = integ_def * def_profile.int_mult * def_fit * dom_def * zone_def_mod
        final_int_mult = min(raw_int, 1.15)

        # PHASE 1: The Possession Duel
        if mechanics.resolve_possession(carrier, defender, final_att_mult, final_int_mult):
            state.stats[f'{att_side}_passes_completed'] += 1
        else:
            log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name, zone=match_zone))
            home_has_ball = not home_has_ball
            continue 

        # PHASE 2: The Tactical Break
        if mechanics.resolve_tactical_break(carrier, defender, final_att_mult, final_def_mult):
            
            # Structural Damage
            current_struct = state.home_structure["overall"] if def_side == 'home' else state.away_structure["overall"]
            damage = mechanics.calculate_damage(defender.current_stamina, current_struct, base_damage=env.base_damage)
            
            state.degrade_structure(def_side, damage)
            
            phase_msg = state.check_phase_shift(def_side, def_side)
            if phase_msg: log.append(narrator.announce(minute, 'PHASE', level=phase_msg, team=def_side.title()))

            log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(), damage=damage))
            
            # [STEP 3] Shot Frequency Dampener (Environment Realism)
            if random.random() > env.shot_density:
                home_has_ball = not home_has_ball
                continue

            # PHASE 3: The Finish
            state.stats[f'{att_side}_shots'] += 1
            
            # Striker selection remains weighted by finishing & selfishness trait
            candidates = [p for p in att_team if p.role != 'GK']
            weights = [p.finishing * (1.15 if p.traits['selfishness'] > 0.5 else 1.0) for p in candidates]
            striker = random.choices(candidates, weights=weights, k=1)[0]
            
            opp_structure = state.home_structure["overall"] if def_side == 'home' else state.away_structure["overall"]
            integrity_bonus = (100 - opp_structure) / 5.0 
            
            shot_mult = integ_att * att_profile.att_mult 
            result = mechanics.resolve_finish(striker, gk, shot_mult, integrity_bonus, minute)
            
            if result == 'GOAL':
                state.stats[f'{att_side}_score'] += 1
                state.stats[f'{att_side}_on_target'] += 1
                score_str = f"{state.stats['home_score']}-{state.stats['away_score']}"
                log.append(narrator.announce(minute, 'GOAL', player=striker.name, score=score_str))
                home_has_ball = not home_has_ball 
                
            elif result == 'SAVE':
                state.stats[f'{att_side}_on_target'] += 1
                state.stats[f'{att_side}_corners'] += 1
                log.append(narrator.announce(minute, 'SAVE', player=gk.name))
                if random.random() < 0.5: home_has_ball = not home_has_ball

            else: # MISS
                log.append(narrator.announce(minute, 'MISS', player=striker.name))
                if random.random() < 0.5: home_has_ball = not home_has_ball

        else:
            # Defensive Hold (Fouls or Blocks)
            if random.random() < 0.1:
                state.stats[f'{def_side}_fouls'] += 1
                log.append(narrator.announce(minute, 'FOUL', player=defender.name))
            else:
                log.append(narrator.announce(minute, 'BLOCK', player=defender.name))
                home_has_ball = not home_has_ball

    # --- POST MATCH POSTING ---
    total_turns = state.stats['home_possession_count'] + state.stats['away_possession_count']
    state.stats['home_possession_pct'] = int((state.stats['home_possession_count'] / total_turns) * 100) if total_turns > 0 else 50
    state.stats['away_possession_pct'] = 100 - state.stats['home_possession_pct']
    
    h_att = max(1, state.stats['home_passes_attempted'])
    state.stats['home_pass_pct'] = int((state.stats['home_passes_completed'] / h_att) * 100)
    a_att = max(1, state.stats['away_passes_attempted'])
    state.stats['away_pass_pct'] = int((state.stats['away_passes_completed'] / a_att) * 100)
    
    state.stats['home_integrity_final'] = int(state.home_structure["overall"])
    state.stats['away_integrity_final'] = int(state.away_structure["overall"])
    
    log.append("FULL TIME.")
    return log, state.stats