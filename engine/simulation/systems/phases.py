import random

from . import mechanics
from . import recovery
from ..commentary import narrator


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
    shot_chance = 0.62
    shot_chance += att_risk_val * 0.03
    shot_chance += att_tempo_val * 0.02
    shot_chance -= def_depth_val * 0.02
    if zone_health < 60:
        shot_chance += 0.10
    if defender.current_stamina < 45:
        shot_chance += 0.08
    shot_chance = max(0.30, min(0.85, shot_chance))

    if random.random() > shot_chance:
        log.append(f"{minute}' [RECOVERY] {defender.name} tracks back to snuff out the danger!")
        zone = 'Center'
        if defender.preferred_zone:
            if defender.preferred_zone.startswith('L'):
                zone = 'Left'
            elif defender.preferred_zone.startswith('R'):
                zone = 'Right'
        state.regen_structure(def_side, 1.0, zone=zone)
        return {'flip': True}

    striker = max([p for p in att_team if p.role != 'GK'], key=lambda p: p.finishing + random.randint(0, 15))

    precision_penalty = 0
    if striker.current_stamina < 60:
        precision_penalty = (60 - striker.current_stamina) / 100.0

    bonus = ((100 - zone_health) / 20.0) + (stat_adv / 15.0) - precision_penalty
    result = mechanics.resolve_finish(striker, gk, break_att, bonus, minute)

    if result == 'GOAL':
        state.stats[f'{att_side}_score'] += 1
        add_impact(striker.name, 'goals', 15)
        log.append(narrator.announce(minute, 'GOAL', player=striker.name, score=f"{state.stats['home_score']}-{state.stats['away_score']}"))
        avg_def_stam = sum(p.current_stamina for p in def_team) / len(def_team)
        regen_amount = 15.0 * (max(avg_def_stam, 10.0) / 100.0)
        state.regen_structure(def_side, regen_amount, zone=None)
        return {'flip': True}

    if result == 'SAVE':
        log.append(narrator.announce(minute, 'SAVE', player=gk.name))
        add_impact(gk.name, 'saves', 8)
        return {'flip': random.random() < 0.5}

    log.append(narrator.announce(minute, 'MISS', player=striker.name))
    return {'flip': random.random() < 0.5}
