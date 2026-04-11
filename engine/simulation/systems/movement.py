import math


def seek(player, target_x, target_y):
    """Move player toward target at full move_speed."""
    dx = target_x - player.x
    dy = target_y - player.y
    dist = math.sqrt(dx**2 + dy**2)
    if dist < 0.01:
        return
    player.vx = (dx / dist) * player.move_speed
    player.vy = (dy / dist) * player.move_speed


def arrive(player, target_x, target_y, slowdown_radius=2.0, stop_radius=0.1):
    """Move toward target with smooth deceleration near target."""
    dx = target_x - player.x
    dy = target_y - player.y
    dist = math.sqrt(dx**2 + dy**2)
    
    # Close enough — stop completely
    if dist < stop_radius:
        player.vx = 0.0
        player.vy = 0.0
        return
    
    # Inside slowdown zone — scale speed down
    speed = player.move_speed * min(dist / slowdown_radius, 1.0)
    
    player.vx = (dx / dist) * speed
    player.vy = (dy / dist) * speed


def apply_velocity(player):
    """Update player position based on velocity."""
    player.x += player.vx
    player.y += player.vy


def place_player(player, x, y):
    """Place player at exact position with zero velocity."""
    player.x = float(x)
    player.y = float(y)
    player.vx = 0.0
    player.vy = 0.0
