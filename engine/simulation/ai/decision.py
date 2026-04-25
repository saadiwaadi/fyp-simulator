import math
import random


def position_danger(carrier, field, att_side):
    if att_side == 'home':
        depth_pct = carrier.x / field.width
    else:
        depth_pct = 1.0 - (carrier.x / field.width)

    if depth_pct < 0.66:
        return 0.0

    center_y = field.height / 2.0
    width_penalty = abs(carrier.y - center_y) / (field.height / 2.0)

    danger = (depth_pct - 0.66) / 0.34
    danger *= (1.0 - width_penalty * 0.5)

    return round(danger, 3)


def defensive_pressure(carrier, def_team, pressure_radius=3.0):
    pressure = 0.0
    for defender in def_team:
        if defender.role == 'GK':
            continue
        dist = math.sqrt((carrier.x - defender.x) ** 2 + (carrier.y - defender.y) ** 2)
        if dist < pressure_radius:
            pressure += (pressure_radius - dist) / pressure_radius
    return min(pressure, 1.0)


def should_attempt_shot(carrier, def_team, field, att_side, game_context):
    danger = position_danger(carrier, field, att_side)

    if danger < 0.15:
        return False

    pressure = defensive_pressure(carrier, def_team)

    role_inclination = {
        'FWD': 0.7,
        'MID': 0.3,
        'DEF': 0.05,
        'GK': 0.0,
    }.get(carrier.role, 0.2)

    selfishness = carrier.traits.get('selfishness', 0.0)
    composure = carrier.composure / 100.0

    shot_score = (
        danger * 0.5
        + role_inclination * 0.2
        + selfishness * 0.15
        - pressure * 0.35
        + composure * 0.1
    )

    score_diff = game_context.get('score_diff', 0)
    if score_diff < 0:
        shot_score += 0.1
    elif score_diff > 0:
        shot_score -= 0.08

    minute = game_context.get('minute', 45)
    max_minutes = game_context.get('max_minutes', 90)
    if minute > max_minutes * 0.8 and score_diff <= 0:
        shot_score += 0.12

    return random.random() < shot_score
