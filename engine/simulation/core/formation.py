import math

# Formation anchors as percentages of field dimensions
# x = depth (0 = own goal, 1 = opponent goal)
# y = width (0 = bottom, 1 = top)

# ── Scenario shape: the whole block moves with the game state ─────────
# Depth push per role in grid units on a reference 20-unit pitch (scaled
# to the actual field), + width multiplier and ball-attraction multiplier.
#   attack  — in possession: lines step up, pitch gets big, players hold
#             structure instead of crowding the carrier
#   defend  — out of possession: block drops and narrows, hunts the ball
#   counter — just won it: midfield and forwards spring forward at once
#   recover — just lost it: everyone sprints back into the narrow block
PHASE_SHAPE = {
    'attack':  {'push': {'GK': 0.4, 'DEF': 2.2, 'MID': 2.6, 'FWD': 2.2},
                'width': 1.15, 'attraction': 0.55},
    'defend':  {'push': {'GK': 0.0, 'DEF': -1.6, 'MID': -2.2, 'FWD': -1.2},
                'width': 0.78, 'attraction': 1.30},
    'counter': {'push': {'GK': 0.0, 'DEF': 0.6, 'MID': 2.4, 'FWD': 4.2},
                'width': 1.05, 'attraction': 0.75},
    'recover': {'push': {'GK': 0.0, 'DEF': -2.4, 'MID': -1.8, 'FWD': -0.4},
                'width': 0.72, 'attraction': 1.15},
}
PHASE_REFERENCE_WIDTH = 20.0  # 11v11 pitch; smaller modes scale down

# ── Formation templates ───────────────────────────────────────────────
# Slots as (role, x_pct, y_pct) for the HOME side attacking left→right;
# away mirrors x. Players are matched to slots by role first, so a 3-5-2
# with only four listed midfielders still fields sensibly.
FORMATIONS = {
    '11v11': {
        '4-4-2': [
            ('GK', 0.05, 0.50),
            ('DEF', 0.22, 0.14), ('DEF', 0.19, 0.38), ('DEF', 0.19, 0.62), ('DEF', 0.22, 0.86),
            ('MID', 0.48, 0.12), ('MID', 0.44, 0.38), ('MID', 0.44, 0.62), ('MID', 0.48, 0.88),
            ('FWD', 0.76, 0.40), ('FWD', 0.76, 0.60),
        ],
        '4-3-3': [
            ('GK', 0.05, 0.50),
            ('DEF', 0.22, 0.14), ('DEF', 0.19, 0.38), ('DEF', 0.19, 0.62), ('DEF', 0.22, 0.86),
            ('MID', 0.42, 0.50), ('MID', 0.50, 0.28), ('MID', 0.50, 0.72),
            ('FWD', 0.72, 0.15), ('FWD', 0.80, 0.50), ('FWD', 0.72, 0.85),
        ],
        '4-2-3-1': [
            ('GK', 0.05, 0.50),
            ('DEF', 0.22, 0.14), ('DEF', 0.19, 0.38), ('DEF', 0.19, 0.62), ('DEF', 0.22, 0.86),
            ('MID', 0.40, 0.35), ('MID', 0.40, 0.65),
            ('MID', 0.58, 0.18), ('MID', 0.60, 0.50), ('MID', 0.58, 0.82),
            ('FWD', 0.80, 0.50),
        ],
        '3-5-2': [
            ('GK', 0.05, 0.50),
            ('DEF', 0.20, 0.25), ('DEF', 0.18, 0.50), ('DEF', 0.20, 0.75),
            ('MID', 0.46, 0.07), ('MID', 0.44, 0.30), ('MID', 0.42, 0.50), ('MID', 0.44, 0.70), ('MID', 0.46, 0.93),
            ('FWD', 0.76, 0.40), ('FWD', 0.76, 0.60),
        ],
        '5-3-2': [
            ('GK', 0.05, 0.50),
            ('DEF', 0.26, 0.08), ('DEF', 0.19, 0.30), ('DEF', 0.17, 0.50), ('DEF', 0.19, 0.70), ('DEF', 0.26, 0.92),
            ('MID', 0.46, 0.30), ('MID', 0.44, 0.50), ('MID', 0.46, 0.70),
            ('FWD', 0.74, 0.40), ('FWD', 0.74, 0.60),
        ],
    },
    '5v5': {
        '1-2-1 Diamond': [
            ('GK', 0.08, 0.50),
            ('DEF', 0.28, 0.50),
            ('MID', 0.52, 0.22), ('MID', 0.52, 0.78),
            ('FWD', 0.78, 0.50),
        ],
        '2-1-1 Box': [
            ('GK', 0.08, 0.50),
            ('DEF', 0.26, 0.30), ('DEF', 0.26, 0.70),
            ('MID', 0.55, 0.50),
            ('FWD', 0.80, 0.50),
        ],
        '1-1-2 Y': [
            ('GK', 0.08, 0.50),
            ('DEF', 0.28, 0.50),
            ('MID', 0.50, 0.50),
            ('FWD', 0.75, 0.28), ('FWD', 0.75, 0.72),
        ],
        '2-2 Square': [
            ('GK', 0.08, 0.50),
            ('DEF', 0.26, 0.30), ('DEF', 0.26, 0.70),
            ('FWD', 0.68, 0.30), ('FWD', 0.68, 0.70),
        ],
    },
}
DEFAULT_FORMATION = {'11v11': '4-4-2', '5v5': '1-2-1 Diamond'}


def resolve_formation(mode, name):
    """Valid formation for the mode, falling back to the mode default."""
    table = FORMATIONS.get(mode, FORMATIONS['5v5'])
    if name in table:
        return name, table[name]
    default = DEFAULT_FORMATION.get(mode, next(iter(table)))
    return default, table[default]


def assign_slots(team_players, slots):
    """Match players to formation slots, same-role first, leftovers after.

    Returns {player_id: (x_pct, y_pct)}. Out-of-position fills are legal —
    the role/zone effectiveness costs already price them in the duels.
    """
    unfilled = list(range(len(slots)))
    unplaced = list(team_players)
    mapping = {}

    for role_pass in (True, False):
        for si in list(unfilled):
            role, sx, sy = slots[si]
            pick = None
            for p in unplaced:
                if (p.role == role) if role_pass else True:
                    pick = p
                    break
            if pick is not None:
                mapping[pick.id] = (sx, sy)
                unplaced.remove(pick)
                unfilled.remove(si)
    return mapping

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

    # Layer 1: formation slot anchor (falls back to the role line when no
    # formation is configured). Slots give every player his own station —
    # a left-back holds the left channel instead of sharing one flat line.
    slot_map = style.get('_slot_map')
    if slot_map is None and style.get('formation') and team_players:
        _, slots = resolve_formation(style.get('mode', '5v5'), style.get('formation'))
        slot_map = assign_slots(team_players, slots)
        style['_slot_map'] = slot_map

    slot = (slot_map or {}).get(player.id)
    if slot is not None:
        sx, sy = slot
        if side == 'away':
            sx = 1.0 - sx
        anchor_x = sx * field.width
        anchor_y = sy * field.height
    else:
        anchor_pct = ROLE_ANCHORS[side].get(player.role, (0.5, 0.5))
        anchor_x = anchor_pct[0] * field.width
        anchor_y = anchor_pct[1] * field.height

    # Layer 2: manager instructions shift the anchor
    depth_shift = (depth - 3) * 1.6

    # Layer 2b: game scenario moves the whole block. In possession the
    # lines step up and stretch; without it they drop and compact; on a
    # turnover the shape springs (counter) or scrambles back (recover).
    phase = style.get('phase', 'defend')
    shape = PHASE_SHAPE.get(phase, PHASE_SHAPE['defend'])
    scale = field.width / PHASE_REFERENCE_WIDTH
    depth_shift += shape['push'].get(player.role, 0.0) * scale

    if side == 'home':
        anchor_x = min(anchor_x + depth_shift, field.width * 0.95)
    else:
        anchor_x = max(anchor_x - depth_shift, field.width * 0.05)

    width_multiplier = (0.42 + (width / 5.0) * 0.95) * shape['width']

    if slot is not None:
        # Formation slots already carry their own width geometry; the
        # width slider and phase shape stretch/squeeze it around center.
        anchor_y = (field.height * 0.5) + (anchor_y - field.height * 0.5) * width_multiplier
    else:
        # Legacy role lines: assign deterministic width lanes by role.
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

    # Layer 3: player resistance to instructions.
    # Compliance blends how well the player suits the tactical profile with
    # his system_loyalty trait (passing+vision temperament) -- players who
    # don't believe in the system drift off its script (audit: system_loyalty
    # was computed but never read).
    tactical_fit = player.tactical_fits.get(tactical_profile, 1.0)
    normalized_fit = (tactical_fit - 0.90) / (1.10 - 0.90)
    normalized_fit = max(0.0, min(1.0, normalized_fit))
    loyalty = player.traits.get('system_loyalty', 0.5)

    compliance = 0.35 + (normalized_fit * 0.40) + (loyalty * 0.25)

    # Discipline reins the leash in directly (not only via low compliance),
    # so a disciplined player in a compliant side still holds his post while
    # a maverick roams — this is what keeps temperament visible on the pitch.
    discipline_tighten = player.traits['discipline'] * 2.2
    effective_wander = max_wander * compliance - discipline_tighten * (0.4 + (1.0 - compliance) * 0.6)
    effective_wander = max(0.5, effective_wander)

    raw_risk_push = player.traits['risk_appetite'] * 2.4
    risk_push = raw_risk_push * (1.0 - player.traits['discipline'] * 0.5)
    if side == 'home':
        anchor_x = min(anchor_x + risk_push, field.width * 0.95)
    else:
        anchor_x = max(anchor_x - risk_push, field.width * 0.05)

    if player.role == 'FWD' and player.traits['selfishness'] > 0.3:
        goal_x = float(field.width) if side == 'home' else 0.0
        selfish_pull = player.traits['selfishness'] * 0.3 * compliance
        anchor_x += (goal_x - anchor_x) * selfish_pull

    # Ball attraction within leash. The press slider directly drives how
    # hard the team hunts the ball, so pressing is visible on the pitch.
    base_attraction = BALL_ATTRACTION.get(player.role, 0.2)
    attraction = base_attraction * (0.7 + player.traits['work_rate'] * 0.6)
    attraction *= (1.0 - player.traits['discipline'] * 0.3)
    attraction *= 1.0 + (press - 3) * 0.18
    # In possession, players hold their structure and offer lanes instead
    # of collapsing onto the carrier; off the ball they hunt it.
    attraction *= shape['attraction']

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
