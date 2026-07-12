import math
import random

from . import mechanics
from . import passing
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
        carrier.sap_confidence(0.04)
        defender.boost_confidence(0.04)
        state.regen_structure(def_side, 0.3, zone=zone_key)
        recovery.apply_micro_regen(defender)
        return 'TURNOVER'

    state.stats[f'{att_side}_passes_completed'] += 1
    return 'CONTINUE'


def _nearest_outfield_defender(carrier, def_team):
    best, best_d = None, float('inf')
    for d in def_team:
        if d.role == 'GK':
            continue
        dist = math.hypot(carrier.x - d.x, carrier.y - d.y)
        if dist < best_d:
            best, best_d = d, dist
    return best


def _in_crossing_position(carrier, field, att_side):
    """Wide channel, final quarter of the pitch: cross territory."""
    wide = carrier.y < field.height * 0.25 or carrier.y > field.height * 0.75
    if att_side == 'home':
        return wide and carrier.x > field.width * 0.70
    return wide and carrier.x < field.width * 0.30


def _cross_target(att_team, carrier, field, att_side):
    """The body attacking the box: nearest FWD (or advanced MID) to goal center."""
    goal_x = float(field.width) if att_side == 'home' else 0.0
    center_y = field.height / 2.0
    candidates = [p for p in att_team if p is not carrier and p.role == 'FWD']
    if not candidates:
        candidates = [p for p in att_team if p is not carrier and p.role == 'MID']
    if not candidates:
        return None
    return min(candidates, key=lambda p: math.hypot(goal_x - p.x, center_y - p.y))


def _attempt_cross(carrier, att_team, def_team, att_mult, def_mult, minute,
                   att_side, def_side, state, log, add_impact, rng):
    target = _cross_target(att_team, carrier, state.field, att_side)
    if target is None:
        return None

    lane = {
        'receiver': target,
        'length': math.hypot(target.x - carrier.x, target.y - carrier.y),
        'dy': abs(target.y - carrier.y),
        'blockers': [],
        'openness': 1.0,
    }
    # Rebuild shading against the real defensive bodies between the flank
    # and the box, so packed boxes clear more crosses.
    full = passing.compute_lanes(carrier, [target], def_team)
    if full:
        lane = full[0]

    # A cross is always contested at the far post: whoever marks the target
    # gets a clearance chance scaled by how tight the marking is, even when
    # nobody sits on the flight path itself.
    if not lane['blockers']:
        marker = _nearest_outfield_defender(target, def_team)
        if marker is not None:
            mark_dist = math.hypot(marker.x - target.x, marker.y - target.y)
            if mark_dist < 3.5:
                lane['blockers'] = [{'defender': marker,
                                     'closeness': 1.0 - mark_dist / 3.5,
                                     'along': 0.9}]
                lane['openness'] = max(0.0, 1.0 - (1.0 - mark_dist / 3.5) * 0.75)

    state.stats[f'{att_side}_crosses'] += 1
    result, interceptor = passing.resolve_pass(
        carrier, lane, 'cross', att_mult, def_mult, rng=rng, state=state)

    if result == 'COMPLETE':
        state.stats[f'{att_side}_crosses_completed'] += 1
        state.stats[f'{att_side}_passes_completed'] += 1
        carrier.boost_confidence(0.03)
        target.boost_confidence(0.02)
        carrier.last_carried = False
        target.last_carried = True
        state.ball.attach_to_owner(target, target.x, target.y)
        log.append(f"{minute}' [CROSS] {carrier.name} whips it in -- {target.name} attacks the ball!")
        return {'outcome': 'CROSS', 'carrier': target}

    defender = interceptor or _nearest_outfield_defender(target, def_team)
    if defender is not None:
        add_impact(defender.name, 'def_stops', 2)
        defender.boost_confidence(0.03)
        state.stats[f'{def_side}_interceptions_won'] += 1
        log.append(f"{minute}' [CLEARED] {defender.name} heads {carrier.name}'s cross away.")
    carrier.sap_confidence(0.02)
    add_impact(carrier.name, 'turnovers', -1)
    return {'outcome': 'TURNOVER'}


def run_passing_chain(att_team, def_team, carrier, att_mult, def_mult, minute,
                      att_side, def_side, state, log, add_impact, att_style, rng=None):
    """Move the ball through real space before committing to the break.

    Each link: pressure may trigger a tackle, wide-and-deep may trigger a
    cross, otherwise the carrier plays the best lane he can actually see.
    Returns the chain outcome and whoever ends up on the ball.
    """
    rng = rng or random
    tempo = int(att_style.get('tempo', 3))
    width_pref = int(att_style.get('width', 3))
    field = state.field

    # Direct teams (high tempo) commit forward after fewer passes; patient
    # teams keep the ball moving and probe longer.
    max_passes = max(1, 3 - (tempo - 3)) + (1 if rng.random() < 0.4 else 0)
    switched = False
    completed = 0

    for _ in range(max_passes):
        # 1) Ball-winning: a defender close enough may dive in. Positioning
        # opens the door; the tackle duel decides it.
        pressure = defensive_pressure(carrier, def_team)
        if pressure > 0.6:
            tackler = _nearest_outfield_defender(carrier, def_team)
            if tackler is not None and rng.random() < (pressure - 0.6) * 0.8:
                state.stats[f'{def_side}_tackle_attempts'] += 1
                if mechanics.resolve_tackle(carrier, tackler, att_mult, def_mult,
                                            pressure, rng=rng, state=state):
                    state.stats[f'{def_side}_tackles_won'] += 1
                    add_impact(tackler.name, 'def_stops', 3)
                    add_impact(carrier.name, 'turnovers', -1)
                    tackler.boost_confidence(0.05)
                    carrier.sap_confidence(0.04)
                    state.ball.attach_to_owner(tackler, tackler.x, tackler.y)
                    log.append(f"{minute}' [TACKLE] {tackler.name} times the challenge and strips {carrier.name}!")
                    return {'outcome': 'TURNOVER'}
                # Rode the challenge: the carrier grows, the lunging defender pays.
                carrier.boost_confidence(0.02)
                tackler.sap_confidence(0.02)

        # 2) Wide and deep: look for the cross.
        if _in_crossing_position(carrier, field, att_side) and rng.random() < 0.55:
            cross = _attempt_cross(carrier, att_team, def_team, att_mult, def_mult,
                                   minute, att_side, def_side, state, log, add_impact, rng)
            if cross is not None:
                cross['switched'] = switched
                cross['completed'] = completed
                return cross

        # 3) Ordinary link: perceive lanes, pick one, play it.
        lanes = passing.compute_lanes(carrier, att_team, def_team)
        seen = passing.perceive_lanes(carrier, lanes, rng=rng)
        if not seen:
            break  # nothing on: carrier holds and the move goes direct

        lane = passing.select_lane(carrier, seen, att_side, field, width_pref, rng=rng)
        kind = 'switch' if passing.is_switch(lane, field) else 'short'
        state.stats[f'{att_side}_passes_attempted'] += 1

        result, interceptor = passing.resolve_pass(
            carrier, lane, kind, att_mult, def_mult, rng=rng, state=state)

        if result == 'INTERCEPTED':
            carrier.sap_confidence(0.04)
            add_impact(carrier.name, 'turnovers', -1)
            if interceptor is not None:
                state.stats[f'{def_side}_interceptions_won'] += 1
                add_impact(interceptor.name, 'def_stops', 3)
                interceptor.boost_confidence(0.05)
                state.ball.attach_to_owner(interceptor, interceptor.x, interceptor.y)
                log.append(f"{minute}' [INTERCEPTED] {interceptor.name} reads the "
                           f"{'switch' if kind == 'switch' else 'pass'} and steps in.")
            else:
                log.append(f"{minute}' [LOOSE] {carrier.name}'s ball runs away from everyone.")
            return {'outcome': 'TURNOVER'}

        receiver = lane['receiver']
        state.stats[f'{att_side}_passes_completed'] += 1
        completed += 1
        carrier.boost_confidence(0.015)
        receiver.boost_confidence(0.01)
        carrier.last_carried = False
        receiver.last_carried = True
        state.ball.attach_to_owner(receiver, receiver.x, receiver.y)

        if kind == 'switch':
            switched = True
            state.stats[f'{att_side}_switches'] += 1
            log.append(f"{minute}' [SWITCH] {carrier.name} shifts play across to {receiver.name}.")

        carrier = receiver

        # A completed forward ball often IS the trigger to commit.
        if rng.random() < 0.25:
            break

    return {'outcome': 'CONTINUE', 'carrier': carrier, 'switched': switched, 'completed': completed}


def run_break_phase(carrier, defender, break_att, break_def, minute, raw_zone, zone_key,
                    def_side, state, log, add_impact, base_damage, rng=None):
    rng = rng or random
    if not mechanics.resolve_tactical_break(carrier, defender, break_att, break_def, rng=rng, state=state):
        log.append(narrator.announce(minute, 'BLOCK', player=defender.name, rng=rng))
        add_impact(defender.name, 'def_stops', 2)
        defender.boost_confidence(0.03)
        carrier.sap_confidence(0.02)
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
    carrier.boost_confidence(0.03)

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
                   minute, state, log, add_impact, rng=None, from_cross=False):
    rng = rng or random

    carrier = next((p for p in att_team if p.last_carried), None)
    if carrier is None:
        outfield = [p for p in att_team if p.role != 'GK'] or att_team
        carrier = rng.choice(outfield)

    if from_cross:
        # The delivery already beat the marker; whoever attacked the ball
        # must play it first time. No lay-off, no recycling out of it —
        # but plenty of good deliveries are still claimed or scrambled
        # behind before the attacker truly connects.
        if rng.random() > 0.50:
            log.append(f"{minute}' [CLAIMED] {gk.name} rises above the pack and gathers.")
            add_impact(gk.name, 'def_stops', 2)
            gk.boost_confidence(0.02)
            return {'flip': True}
        shot_type = 'header'
    else:
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
            defender.boost_confidence(0.02)
            state.regen_structure(def_side, 0.6, zone='Center')
            return {'flip': True}

        # Shot type from the situation: from range you hit it (drive, shot
        # power), in close you place it (finesse) -- composed players trust
        # placement a little longer.
        if danger < 0.30:
            shot_type = 'drive'
        else:
            finesse_pref = 0.62 + (carrier.composure - 70) / 150.0
            shot_type = 'finesse' if rng.random() < finesse_pref else 'drive'

    precision_penalty = 0
    if carrier.current_stamina < 60:
        precision_penalty = (60 - carrier.current_stamina) / 100.0

    state.stats[f'{att_side}_shots'] += 1
    state.stats[f'{att_side}_shots_{shot_type}'] += 1

    minute_frac = minute / max(state.stats.get('max_minutes', 90), 1)
    bonus = ((100 - zone_health) / 12.0) + (stat_adv / 15.0) - precision_penalty
    result = mechanics.resolve_finish(carrier, gk, break_att, bonus, minute_frac, rng=rng,
                                      state=state, shot_type=shot_type)

    if result == 'GOAL':
        state.stats[f'{att_side}_on_target'] += 1
        state.stats[f'{att_side}_score'] += 1
        add_impact(carrier.name, 'goals', 15)
        # Goals swing the whole pitch's belief: scorer soars, teammates lift,
        # the keeper and back line drop.
        carrier.boost_confidence(0.12)
        gk.sap_confidence(0.05)
        for p in att_team:
            if p is not carrier:
                p.boost_confidence(0.02)
        for p in def_team:
            if p is not gk:
                p.sap_confidence(0.02)
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
        gk.boost_confidence(0.06)
        carrier.sap_confidence(0.02)
        return {'flip': rng.random() < 0.5}

    log.append(narrator.announce(minute, 'MISS', player=carrier.name, rng=rng))
    add_impact(carrier.name, 'misses', -1)
    carrier.sap_confidence(0.04)
    return {'flip': rng.random() < 0.5}
