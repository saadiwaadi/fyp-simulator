import random
from engine.models import Player as DBPlayer
from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator

import random
from engine.models import Player as DBPlayer
from .player import SimPlayer
from .state import MatchState
from . import mechanics
from .commentary import narrator

from engine.models import Player as DBPlayer, Team as DBTeam # <--- New Import

def play_match(home_team_name, away_team_name):
    # 1. SETUP: Fetch Teams from Database
    try:
        home_db = DBTeam.objects.get(name=home_team_name)
        away_db = DBTeam.objects.get(name=away_team_name)
    except DBTeam.DoesNotExist:
        return [f"ERROR: Teams '{home_team_name}' or '{away_team_name}' not found in DB."], {}

    # Fetch Players specifically belonging to these teams
    # We use 'player_set' which is the reverse link from Team to Player
    h_players = list(home_db.player_set.all())
    a_players = list(away_db.player_set.all())

    # Validation: Do they have enough players?
    # (Simplified validation for now, assumes you added GKs correctly)
    if len(h_players) < 5 or len(a_players) < 5:
        return [f"ERROR: Squads too small. Add players to {home_team_name} and {away_team_name}."], {}

    # Convert to SimPlayers
    team_home = [SimPlayer(p) for p in h_players]
    team_away = [SimPlayer(p) for p in a_players]
        
    # 2. INITIALIZE STATE
    state = MatchState(home_team_name, away_team_name)
    log = [] 
    
    log.append(f"MATCH STARTED: {home_team_name} vs {away_team_name}")
    log.append(f"ANALYSIS: Structural Integrity at 100%. Simulation Engine v1.4 Loaded.")
    
    home_has_ball = True 

    # 3. THE LOOP (90 Minutes)
    for minute in range(1, 91, 3): 
        # A. Possession Count
        if home_has_ball: state.stats['home_possession_count'] += 1
        else: state.stats['away_possession_count'] += 1
        
        # B. Define Actors
        att_team, def_team = (team_home, team_away) if home_has_ball else (team_away, team_home)
        att_side, def_side = ('home', 'away') if home_has_ball else ('away', 'home')
        def_name = away_team_name if home_has_ball else home_team_name
        
        carrier = random.choice([p for p in att_team if p.role != 'GK'])
        defender = random.choice([p for p in def_team if p.role != 'GK'])
        gk = [p for p in def_team if p.role == 'GK'][0]
        
        # C. Fatigue
        carrier.drain_stamina(1)
        defender.drain_stamina(1)

        # D. Mechanics & Stats
        state.stats[f'{att_side}_passes_attempted'] += 1
        att_mult = state.get_integrity_mult(att_side)
        def_mult = state.get_integrity_mult(def_side)

        # PHASE 1: Possession Check
        if mechanics.resolve_possession(carrier, defender, att_mult, def_mult):
            state.stats[f'{att_side}_passes_completed'] += 1
        else:
            log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name))
            home_has_ball = not home_has_ball
            continue 

        # PHASE 2: Tactical Break Check
        if mechanics.resolve_tactical_break(carrier, defender, att_mult, def_mult):
            # --- CORRECTED LINE: Using Stamina for Damage ---
            damage = mechanics.calculate_damage(defender.current_stamina)
            state.degrade_integrity(def_side, damage)
            
            # Phase Shift Check
            phase_msg = state.check_phase_shift(def_side, def_name)
            if phase_msg: 
                log.append(narrator.announce(minute, 'PHASE', level=state.home_phase if def_side=='home' else state.away_phase, team=def_name))

            log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(), damage=damage))
            
            # --- PHASE 3: The Shot (Correctly Nested) ---
            state.stats[f'{att_side}_shots'] += 1
            striker = max(att_team, key=lambda p: p.finishing)
                
            opp_integrity = state.home_integrity if def_side == 'home' else state.away_integrity
            integrity_bonus = (100 - opp_integrity) / 3.0 
                
            if mechanics.resolve_finish(striker, gk, att_mult, integrity_bonus):
                # GOAL
                state.stats[f'{att_side}_score'] += 1
                state.stats[f'{att_side}_on_target'] += 1
                score_str = f"{state.stats['home_score']}-{state.stats['away_score']}"
                log.append(narrator.announce(minute, 'GOAL', player=striker.name, score=score_str))
                home_has_ball = not home_has_ball 
            else:
                # SAVE / MISS
                if random.random() < 0.6:
                    state.stats[f'{att_side}_on_target'] += 1
                    state.stats[f'{att_side}_corners'] += 1
                    log.append(narrator.announce(minute, 'SAVE', player=gk.name))
                else:
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

    # --- 4. FINALIZE STATS (Outside Loop) ---
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