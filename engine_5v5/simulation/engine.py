import random
from engine.models import Player as DBPlayer, Team as DBTeam
from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator
from .tactics import get_tactical_mods  # <--- NEW IMPORT

# ==========================================
# THE ENGINE (v1.5 - Modular)
# ==========================================
def play_match(home_team_name, away_team_name):
    # --- SETUP PHASE ---
    try:
        home_db = DBTeam.objects.get(name=home_team_name)
        away_db = DBTeam.objects.get(name=away_team_name)
    except DBTeam.DoesNotExist:
        return [f"ERROR: Teams not found."], {}

    h_players = list(home_db.player_set.all())
    a_players = list(away_db.player_set.all())

    if len(h_players) < 5 or len(a_players) < 5:
        return [f"ERROR: Squads too small."], {}

    # Convert to SimPlayers
    team_home = [SimPlayer(p) for p in h_players]
    team_away = [SimPlayer(p) for p in a_players]

    # --- FETCH TACTICS (From the new module) ---
    h_mode = home_db.tactical_mode
    a_mode = away_db.tactical_mode
    
    h_mods = get_tactical_mods(h_mode)
    a_mods = get_tactical_mods(a_mode)

    state = MatchState(home_team_name, away_team_name)
    log = [] 
    log.append(f"MATCH STARTED: {home_team_name} ({h_mode}) vs {away_team_name} ({a_mode})")
    
    home_has_ball = True 

    # --- THE LOOP ---
    for minute in range(1, 91, 3): 
        # A. Possession Count
        if home_has_ball: state.stats['home_possession_count'] += 1
        else: state.stats['away_possession_count'] += 1
        
        # B. Define Actors
        att_team, def_team = (team_home, team_away) if home_has_ball else (team_away, team_home)
        att_side, def_side = ('home', 'away') if home_has_ball else ('away', 'home')
        att_mods = h_mods if home_has_ball else a_mods
        def_mods = a_mods if home_has_ball else h_mods
        
        carrier = random.choice([p for p in att_team if p.role != 'GK'])
        defender = random.choice([p for p in def_team if p.role != 'GK'])
        gk = [p for p in def_team if p.role == 'GK'][0]
        
        # C. Fatigue (Apply Tactical Burn Rate)
        carrier.drain_stamina(1 * att_mods['stam'])
        defender.drain_stamina(1 * def_mods['stam'])

        # D. Mechanics with GRANULAR MULTIPLIERS
        state.stats[f'{att_side}_passes_attempted'] += 1
        
        # 1. Calculate General Integrity Modifiers
        integ_att = state.get_integrity_mult(att_side)
        integ_def = state.get_integrity_mult(def_side)

        # 2. Apply Specific Tactical Multipliers
        final_att_mult = integ_att * att_mods['att']
        final_int_mult = integ_def * def_mods['int'] # Phase 1 Defense
        final_def_mult = integ_def * def_mods['def'] # Phase 2 Defense

        # PHASE 1: Possession (Uses Interception Multiplier)
        if mechanics.resolve_possession(carrier, defender, final_att_mult, final_int_mult):
            state.stats[f'{att_side}_passes_completed'] += 1
        else:
            log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name))
            home_has_ball = not home_has_ball
            continue 

        # PHASE 2: Tactical Break (Uses Def Awareness Multiplier)
        if mechanics.resolve_tactical_break(carrier, defender, final_att_mult, final_def_mult):
            damage = mechanics.calculate_damage(defender.current_stamina)
            state.degrade_integrity(def_side, damage)
            
            phase_msg = state.check_phase_shift(def_side, def_side)
            if phase_msg: log.append(narrator.announce(minute, 'PHASE', level=phase_msg, team=def_side.title()))

            log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(), damage=damage))
            
            # PHASE 3: The Shot
            state.stats[f'{att_side}_shots'] += 1
            striker = max(att_team, key=lambda p: p.finishing)
            
            opp_integrity = state.home_integrity if def_side == 'home' else state.away_integrity
            
            # Safety Valve: Max Bonus capped at +20
            integrity_bonus = (100 - opp_integrity) / 5.0 
            
            # Dampener: Harder to score early
            result = mechanics.resolve_finish(striker, gk, final_att_mult, integrity_bonus, minute)
            
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
            # DEFENSIVE HOLD
            if random.random() < 0.1:
                state.stats[f'{def_side}_fouls'] += 1
                log.append(narrator.announce(minute, 'FOUL', player=defender.name))
            else:
                log.append(narrator.announce(minute, 'BLOCK', player=defender.name))
                home_has_ball = not home_has_ball

    # --- POST MATCH ---
    total_turns = state.stats['home_possession_count'] + state.stats['away_possession_count']
    state.stats['home_possession_pct'] = int((state.stats['home_possession_count'] / total_turns) * 100) if total_turns > 0 else 50
    state.stats['away_possession_pct'] = 100 - state.stats['home_possession_pct']
    
    h_att = max(1, state.stats['home_passes_attempted'])
    state.stats['home_pass_pct'] = int((state.stats['home_passes_completed'] / h_att) * 100)
    a_att = max(1, state.stats['away_passes_attempted'])
    state.stats['away_pass_pct'] = int((state.stats['away_passes_completed'] / a_att) * 100)
    
    state.stats['home_integrity_final'] = int(state.home_integrity)
    state.stats['away_integrity_final'] = int(state.away_integrity)
    
    log.append("FULL TIME.")
    return log, state.stats