def predict_ball_position(ball, ticks=3, friction=0.9):
    return ball.predict_position(ticks=ticks, friction=friction)


def player_travel_time(player, target_position):
    speed = getattr(player, 'speed', None)
    if speed is None:
        speed = getattr(player, 'current_speed', None)
    if speed is None:
        speed = 1.0

    speed = max(float(speed), 0.1)

    player_x = getattr(player, 'x', None)
    player_y = getattr(player, 'y', None)
    if player_x is None or player_y is None:
        return float('inf')

    dx = player_x - target_position[0]
    dy = player_y - target_position[1]
    distance = (dx * dx + dy * dy) ** 0.5
    return distance / speed


def player_can_reach(player, target_position, ticks, ball=None, controllable_height=1.5):
    if ball is not None and getattr(ball, 'z', 0) > controllable_height:
        return False
    return player_travel_time(player, target_position) <= ticks


def find_earliest_intercept_point(player, ball, max_ticks=5, friction=0.9, controllable_height=1.5):
    for ticks in range(1, max_ticks + 1):
        future_position = predict_ball_position(ball, ticks=ticks, friction=friction)
        if player_can_reach(player, future_position, ticks, ball=ball, controllable_height=controllable_height):
            return future_position, ticks
    return None, None
