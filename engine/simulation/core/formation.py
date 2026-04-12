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


def get_formation_target(player, ball, side, field):
    """Compute formation-based target for player based on role and ball position."""
    anchor_pct = ROLE_ANCHORS[side].get(player.role, (0.5, 0.5))
    
    # Convert percentage anchor to grid coordinates
    anchor_x = anchor_pct[0] * field.width
    anchor_y = anchor_pct[1] * field.height

    # Pull anchor toward ball based on role
    attraction = BALL_ATTRACTION.get(player.role, 0.2)
    
    target_x = anchor_x + (ball.x - anchor_x) * attraction
    target_y = anchor_y + (ball.y - anchor_y) * attraction * 0.5

    # Clamp to field
    target_x = max(0.0, min(float(field.width), target_x))
    target_y = max(0.0, min(float(field.height), target_y))

    return target_x, target_y
