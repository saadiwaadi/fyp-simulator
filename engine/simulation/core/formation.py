import math

# Formation anchors as percentages of field dimensions
# x = depth (0 = own goal, 1 = opponent goal)
# y = width (0 = bottom, 1 = top)

ROLE_ANCHORS = {
    'home': {
        'GK':  (0.05, 0.5),
        'DEF': (0.25, 0.5),
        'MID': (0.50, 0.5),
        'FWD': (0.78, 0.5),
    },
    'away': {
        'GK':  (0.95, 0.5),
        'DEF': (0.75, 0.5),
        'MID': (0.50, 0.5),
        'FWD': (0.22, 0.5),
    }
}

# How much each role drifts toward ball position
BALL_ATTRACTION = {
    'GK':  0.05,
    'DEF': 0.15,
    'MID': 0.35,
    'FWD': 0.45,
}


# How much each role's leash expands per press point above neutral (3)
PRESS_LEASH_SENSITIVITY = {
    'GK':  0.1,
    'DEF': 0.4,
    'MID': 0.7,
    'FWD': 0.5,
}

# Base leash size per role (grid units from anchor)
BASE_LEASH = {
    'GK':  1.0,
    'DEF': 2.0,
    'MID': 3.5,
    'FWD': 3.0,
}


def get_role_players(players, role):
    return [p for p in players if p.role == role]


def assign_width_spread(role_players, field_height):
    role_players = sorted(role_players, key=lambda p: p.id)
    n = len(role_players)
    lane_map = {}

    if n == 0:
        return lane_map

    if n == 1:
        lone_y = field_height / 2.0
        role_players[0].target_y = lone_y
        lane_map[role_players[0].id] = lone_y
        return lane_map

    spacing = field_height / float(n + 1)
    for i, role_player in enumerate(role_players):
        spread_y = spacing * (i + 1)
        role_player.target_y = spread_y
        lane_map[role_player.id] = spread_y

    return lane_map


def get_formation_target(player, ball, side, field, tactical_style=None):
    style = tactical_style or {}
    press = style.get('press', 3)
    depth = style.get('depth', 3)
    width = style.get('width', 3)
    tactical_profile = style.get('profile', 'Standard')
    team_players = style.get('team_players', [])

    # Layer 1: base role anchor
    anchor_pct = ROLE_ANCHORS[side].get(player.role, (0.5, 0.5))
    anchor_x = anchor_pct[0] * field.width
    anchor_y = anchor_pct[1] * field.height

    # Layer 2: manager instructions shift the anchor
    depth_shift = (depth - 3) * 1.2
    if side == 'home':
        anchor_x = min(anchor_x + depth_shift, field.width * 0.95)
    else:
        anchor_x = max(anchor_x - depth_shift, field.width * 0.05)

    width_multiplier = 0.5 + (width / 5.0) * 0.8

    # Assign deterministic width lanes by role once per formation update.
    lane_map = style.get('_lane_map')
    if lane_map is None:
        lane_map = {}
        for role_name in ('GK', 'DEF', 'MID', 'FWD'):
            role_lane_map = assign_width_spread(get_role_players(team_players, role_name), float(field.height))
            lane_map.update(role_lane_map)
        style['_lane_map'] = lane_map

    spread_y = lane_map.get(player.id, anchor_y)
    anchor_y = (field.height * 0.5) + (spread_y - field.height * 0.5) * width_multiplier

    press_expansion = (press - 3) * PRESS_LEASH_SENSITIVITY.get(player.role, 0.5)
    max_wander = BASE_LEASH.get(player.role, 2.5) + press_expansion
    max_wander = max(0.5, max_wander)

    # Layer 3: player resistance to instructions
    tactical_fit = player.tactical_fits.get(tactical_profile, 1.0)
    normalized_fit = (tactical_fit - 0.82) / (1.18 - 0.82)
    normalized_fit = max(0.0, min(1.0, normalized_fit))

    compliance = 0.5 + (normalized_fit * 0.5)

    discipline_tighten = player.traits['discipline'] * 1.5
    effective_wander = max_wander * compliance - discipline_tighten * (1.0 - compliance)
    effective_wander = max(0.5, effective_wander)

    raw_risk_push = player.traits['risk_appetite'] * 2.0
    risk_push = raw_risk_push * (1.0 - player.traits['discipline'] * 0.5)
    if side == 'home':
        anchor_x = min(anchor_x + risk_push, field.width * 0.95)
    else:
        anchor_x = max(anchor_x - risk_push, field.width * 0.05)

    if player.role == 'FWD' and player.traits['selfishness'] > 0.3:
        goal_x = float(field.width) if side == 'home' else 0.0
        selfish_pull = player.traits['selfishness'] * 0.3 * compliance
        anchor_x += (goal_x - anchor_x) * selfish_pull

    # Ball attraction within leash
    base_attraction = BALL_ATTRACTION.get(player.role, 0.2)
    attraction = base_attraction * (0.7 + player.traits['work_rate'] * 0.6)
    attraction *= (1.0 - player.traits['discipline'] * 0.3)

    raw_target_x = anchor_x + (ball.x - anchor_x) * attraction
    raw_target_y = anchor_y + (ball.y - anchor_y) * attraction * 0.5

    dx = raw_target_x - anchor_x
    dy = raw_target_y - anchor_y
    dist = math.sqrt(dx**2 + dy**2)

    if dist > effective_wander:
        raw_target_x = anchor_x + (dx / dist) * effective_wander
        raw_target_y = anchor_y + (dy / dist) * effective_wander

    target_x = max(0.0, min(float(field.width), raw_target_x))
    target_y = max(0.0, min(float(field.height), raw_target_y))

    return target_x, target_y
