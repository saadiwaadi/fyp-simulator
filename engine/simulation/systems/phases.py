import random

from . import mechanics
from . import recovery
from ..commentary import narrator
from ..ai.decision import should_attempt_shot, position_danger, defensive_pressure


def run_possession_phase(carrier, defender, poss_att, poss_def, minute, raw_zone, zone_key, def_side, state, log, add_impact):
    if not mechanics.resolve_possession(carrier, defender, poss_att, poss_def):
        log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name, zone=raw_zone))
        add_impact(defender.name, 'def_stops', 3)
        state.regen_structure(def_side, 0.5, zone=zone_key)
        recovery.apply_micro_regen(defender)
        return 'TURNOVER'
    return 'CONTINUE'


def run_break_phase(carrier, defender, break_att, break_def, minute, raw_zone, zone_key, def_side, state, log, add_impact, base_damage):
    if not mechanics.resolve_tactical_break(carrier, defender, break_att, break_def):
        log.append(narrator.announce(minute, 'BLOCK', player=defender.name))
        add_impact(defender.name, 'def_stops', 2)
        state.regen_structure(def_side, 1.0, zone=zone_key)
        return {'outcome': 'BLOCKED'}

    state.stats['break_timestamps'].append(minute)
    def_struct_dict = state.home_structure if def_side == 'home' else state.away_structure
    zone_health = max(40.0, def_struct_dict['zones'][zone_key])

    damage = mechanics.calculate_damage(defender.current_stamina, zone_health, base_damage=base_damage) * 1.2
    damage = min(damage, 4.0)

    state.degrade_structure(def_side, damage, zone=zone_key)
    log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(), damage=round(damage, 1), zone=raw_zone))
    add_impact(carrier.name, 'breaks', 4)
    add_impact(carrier.name, 'damage', int(damage))

    return {'outcome': 'SUCCESS', 'zone_health': zone_health}


def run_shot_phase(att_team, def_team, gk, defender, zone_health, break_att, stat_adv, att_side, def_side, att_risk_val, att_tempo_val, def_depth_val, minute, state, log, add_impact):
    carrier = next((p for p in att_team if p.last_carried), None)
    if carrier is None:
        carrier = max([p for p in att_team if p.role != 'GK'], key=lambda p: p.finishing)

    game_context = {
        'score_diff': (state.stats['home_score'] - state.stats['away_score'])
        if att_side == 'home'
        else (state.stats['away_score'] - state.stats['home_score']),
        'minute': minute,
        'max_minutes': state.stats.get('max_minutes', 90),
    }

    if not should_attempt_shot(carrier, def_team, state.field, att_side, game_context):
        log.append(f"{minute}' [BUILD-UP] {carrier.name} recycles -- no clear opening.")
        return {'flip': False}

    danger = position_danger(carrier, state.field, att_side)
    pressure = defensive_pressure(carrier, def_team)

    shot_chance = 0.4 + (danger * 0.4) - (pressure * 0.25)
    shot_chance = max(0.15, min(0.85, shot_chance))

    if random.random() > shot_chance:
        log.append(f"{minute}' [RECOVERY] {defender.name} blocks the shooting lane!")
        state.regen_structure(def_side, 1.0, zone='Center')
        return {'flip': True}

    precision_penalty = 0
    if carrier.current_stamina < 60:
        precision_penalty = (60 - carrier.current_stamina) / 100.0

    bonus = ((100 - zone_health) / 20.0) + (stat_adv / 15.0) - precision_penalty
    result = mechanics.resolve_finish(carrier, gk, break_att, bonus, minute)

    if result == 'GOAL':
        state.stats[f'{att_side}_score'] += 1
        add_impact(carrier.name, 'goals', 15)
        log.append(narrator.announce(minute, 'GOAL', player=carrier.name, score=f"{state.stats['home_score']}-{state.stats['away_score']}"))
        avg_def_stam = sum(p.current_stamina for p in def_team) / len(def_team)
        regen_amount = 15.0 * (max(avg_def_stam, 10.0) / 100.0)
        state.regen_structure(def_side, regen_amount, zone=None)
        return {'flip': True}

    if result == 'SAVE':
        log.append(narrator.announce(minute, 'SAVE', player=gk.name))
        add_impact(gk.name, 'saves', 8)
        return {'flip': random.random() < 0.5}

    log.append(narrator.announce(minute, 'MISS', player=carrier.name))
    return {'flip': random.random() < 0.5}
