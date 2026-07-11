import random

from . import mechanics
from . import recovery
from ..commentary import narrator
from ..ai.decision import should_attempt_shot, position_danger, defensive_pressure


def run_possession_phase(carrier, defender, poss_att, poss_def, minute, raw_zone, zone_key,
                         att_side, def_side, state, log, add_impact, rng=None):
    rng = rng or random
    state.stats[f'{att_side}_passes_attempted'] += 1

    if not mechanics.resolve_possession(carrier, defender, poss_att, poss_def, rng=rng, state=state):
        log.append(narrator.announce(minute, 'TURNOVER', player=carrier.name, zone=raw_zone, rng=rng))
        add_impact(defender.name, 'def_stops', 3)
        add_impact(carrier.name, 'turnovers', -2)
        state.regen_structure(def_side, 0.3, zone=zone_key)
        recovery.apply_micro_regen(defender)
        return 'TURNOVER'

    state.stats[f'{att_side}_passes_completed'] += 1
    return 'CONTINUE'


def run_break_phase(carrier, defender, break_att, break_def, minute, raw_zone, zone_key,
                    def_side, state, log, add_impact, base_damage, rng=None):
    rng = rng or random
    if not mechanics.resolve_tactical_break(carrier, defender, break_att, break_def, rng=rng, state=state):
        log.append(narrator.announce(minute, 'BLOCK', player=defender.name, rng=rng))
        add_impact(defender.name, 'def_stops', 2)
        state.regen_structure(def_side, 0.6, zone=zone_key)
        return {'outcome': 'BLOCKED'}

    state.stats['break_timestamps'].append(minute)
    def_struct_dict = state.home_structure if def_side == 'home' else state.away_structure
    zone_health = def_struct_dict['zones'][zone_key]

    damage = mechanics.calculate_damage(defender.current_stamina, zone_health, base_damage=base_damage) * 1.2
    damage = min(damage, base_damage * 2.0)

    state.degrade_structure(def_side, damage, zone=zone_key)
    log.append(narrator.announce(minute, 'TACTIC', player=carrier.name, team=def_side.title(),
                                 damage=round(damage, 1), zone=raw_zone, rng=rng))
    add_impact(carrier.name, 'breaks', 4)
    add_impact(carrier.name, 'damage', int(damage))

    return {'outcome': 'SUCCESS', 'zone_health': zone_health}


_FINISH_ROLE_WEIGHT = {'FWD': 3.5, 'MID': 1.0, 'DEF': 0.15, 'GK': 0.0}


def _select_finisher(att_team, carrier, rng):
    """Route the chance to a finisher. A selfish or striker carrier keeps it;
    otherwise the move ends with a role-weighted lay-off -- this is what makes
    FWD a real finishing role instead of a cosmetic label (audit Phase 4)."""
    keep_chance = 0.35 + carrier.traits.get('selfishness', 0.0) * 0.4
    if carrier.role == 'FWD':
        keep_chance += 0.35
    if rng.random() < keep_chance:
        return carrier

    candidates = [p for p in att_team if p is not carrier and p.role != 'GK']
    if not candidates:
        return carrier

    weights = [
        _FINISH_ROLE_WEIGHT.get(p.role, 0.5) * (0.5 + p.finishing / 100.0)
        for p in candidates
    ]
    if sum(weights) <= 0:
        return carrier
    return rng.choices(candidates, weights=weights, k=1)[0]


def run_shot_phase(att_team, def_team, gk, defender, zone_health, break_att, stat_adv,
                   att_side, def_side, att_risk_val, att_tempo_val, def_depth_val,
                   minute, state, log, add_impact, rng=None):
    rng = rng or random

    carrier = next((p for p in att_team if p.last_carried), None)
    if carrier is None:
        outfield = [p for p in att_team if p.role != 'GK'] or att_team
        carrier = rng.choice(outfield)

    finisher = _select_finisher(att_team, carrier, rng)
    if finisher is not carrier:
        # The finisher receives in the space the break created.
        finisher.x, finisher.y = carrier.x, carrier.y
        carrier = finisher

    game_context = {
        'score_diff': (state.stats['home_score'] - state.stats['away_score'])
        if att_side == 'home'
        else (state.stats['away_score'] - state.stats['home_score']),
        'minute': minute,
        'max_minutes': state.stats.get('max_minutes', 90),
        'shot_freq': state.stats.get('_shot_freq', 1.0),
    }

    if not should_attempt_shot(carrier, def_team, state.field, att_side, game_context, rng=rng):
        log.append(f"{minute}' [BUILD-UP] {carrier.name} recycles -- no clear opening.")
        return {'flip': False}

    danger = position_danger(carrier, state.field, att_side)
    pressure = defensive_pressure(carrier, def_team)

    shot_chance = 0.55 + (danger * 0.35) - (pressure * 0.25)
    shot_chance = max(0.25, min(0.9, shot_chance))

    if rng.random() > shot_chance:
        log.append(f"{minute}' [RECOVERY] {defender.name} blocks the shooting lane!")
        add_impact(defender.name, 'def_stops', 2)
        state.regen_structure(def_side, 0.6, zone='Center')
        return {'flip': True}

    precision_penalty = 0
    if carrier.current_stamina < 60:
        precision_penalty = (60 - carrier.current_stamina) / 100.0

    state.stats[f'{att_side}_shots'] += 1

    minute_frac = minute / max(state.stats.get('max_minutes', 90), 1)
    bonus = ((100 - zone_health) / 12.0) + (stat_adv / 15.0) - precision_penalty
    result = mechanics.resolve_finish(carrier, gk, break_att, bonus, minute_frac, rng=rng)

    if result == 'GOAL':
        state.stats[f'{att_side}_on_target'] += 1
        state.stats[f'{att_side}_score'] += 1
        add_impact(carrier.name, 'goals', 15)
        log.append(narrator.announce(minute, 'GOAL', player=carrier.name,
                                     score=f"{state.stats['home_score']}-{state.stats['away_score']}",
                                     rng=rng))
        avg_def_stam = sum(p.current_stamina for p in def_team) / len(def_team)
        regen_amount = 15.0 * (max(avg_def_stam, 10.0) / 100.0)
        state.regen_structure(def_side, regen_amount, zone=None)
        return {'flip': True, 'goal': True}

    if result == 'SAVE':
        state.stats[f'{att_side}_on_target'] += 1
        state.stats[f'{att_side}_corners'] += 1
        log.append(narrator.announce(minute, 'SAVE', player=gk.name, rng=rng))
        add_impact(gk.name, 'saves', 8)
        return {'flip': rng.random() < 0.5}

    log.append(narrator.announce(minute, 'MISS', player=carrier.name, rng=rng))
    add_impact(carrier.name, 'misses', -1)
    return {'flip': rng.random() < 0.5}
