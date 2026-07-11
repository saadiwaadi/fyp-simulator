"""Human-like motion layer.

The tactical engine decides WHERE players should be (logic positions x/y,
updated once per sim-minute, including instant repositioning after breaks).
This module makes them LOOK like footballers getting there: render positions
(rx/ry) chase the logic positions through sub-minute ticks with inertia,
per-player idle oscillation, teammate separation, and stamina-scaled pace.

It runs on its OWN deterministic RNG stream (seeded from the match seed), so
adding or tuning motion never changes a single duel roll — match outcomes for
a given seed are identical with or without this layer.
"""

import math

import random

TICKS_PER_MINUTE = 8
FRAME_STRIDE = 2          # record every Nth tick -> 4 frames per sim-minute
SEPARATION_RADIUS = 0.9   # grid units
SEPARATION_PUSH = 0.35
CATCHUP_DISTANCE = 2.5    # beyond this, the player breaks into a sprint
SPRINT_MULT = 5.0
INERTIA = 0.72            # fraction of previous velocity kept each tick

TAU = math.pi * 2.0


class MotionSystem:
    def __init__(self, team_home, team_away, field, match_seed=None):
        self.rng = random.Random(f"{match_seed}:motion" if match_seed else None)
        self.field = field
        self.home = team_home
        self.away = team_away
        self.all_players = list(team_home) + list(team_away)
        self.t = 0.0
        self.frames = []

        role_amplitude = {'GK': 0.35, 'DEF': 0.8, 'MID': 1.15, 'FWD': 1.25}

        for p in self.all_players:
            p.rx = float(p.x)
            p.ry = float(p.y)
            p.rvx = 0.0
            p.rvy = 0.0

            # Personal movement signature, mapped from the player's profile:
            #  - discipline shrinks the roaming radius, risk appetite grows it
            #  - work rate sets how busily he fidgets (oscillation frequency)
            #  - quickness (speed attr) sharpens turns via lower inertia
            #  - role sets the baseline: keepers barely stray, forwards prowl
            discipline = p.traits.get('discipline', 0.5)
            risk = p.traits.get('risk_appetite', 0.3)
            work_rate = p.traits.get('work_rate', 0.7)

            amplitude = role_amplitude.get(p.role, 1.0)
            amplitude *= (0.5 + risk * 0.9) * (1.4 - discipline * 0.8)
            busy = 0.7 + work_rate * 0.6
            p.motion_inertia = 0.80 - 0.12 * getattr(p, 'quickness', 0.5)

            # Slow drift (fractions of a cycle per minute): players wander over
            # 10-20 second arcs they can actually run, rather than twitching
            # against the speed cap, so amplitude differences stay visible.
            p.wander = {
                'ax': self.rng.uniform(0.35, 0.85) * amplitude,
                'ay': self.rng.uniform(0.40, 0.95) * amplitude,
                'fx': self.rng.uniform(0.18, 0.45) * busy,
                'fy': self.rng.uniform(0.18, 0.45) * busy,
                'px': self.rng.uniform(0.0, TAU),
                'py': self.rng.uniform(0.0, TAU),
            }

    def roster(self):
        """Fixed-order roster matching the per-frame position arrays."""
        out = []
        for side, team in (('home', self.home), ('away', self.away)):
            for p in team:
                out.append({'id': p.id, 'name': p.name, 'role': p.role, 'side': side})
        return out

    def tick_minute(self, minute, ball):
        for i in range(TICKS_PER_MINUTE):
            self.t += 1.0 / TICKS_PER_MINUTE
            self._step()
            if i % FRAME_STRIDE == 0:
                self._record(minute, ball)

    def _step(self):
        dt = 1.0 / TICKS_PER_MINUTE

        for p in self.all_players:
            w = p.wander
            target_x = p.x + w['ax'] * math.sin(self.t * w['fx'] * TAU + w['px'])
            target_y = p.y + w['ay'] * math.sin(self.t * w['fy'] * TAU + w['py'])

            dx = target_x - p.rx
            dy = target_y - p.ry
            dist = math.hypot(dx, dy)

            stamina_pace = 0.6 + 0.4 * (p.current_stamina / 100.0)
            max_speed = p.move_speed * stamina_pace * 2.0  # units per minute
            if dist > CATCHUP_DISTANCE:
                max_speed *= SPRINT_MULT

            if dist > 0.02:
                desired = min(max_speed, dist / dt)
                des_vx = (dx / dist) * desired
                des_vy = (dy / dist) * desired
            else:
                des_vx = des_vy = 0.0

            # Inertia: velocity eases toward the desired vector, so paths curve
            # and players decelerate into position instead of beelining.
            # Quick players (high speed attribute) carry less inertia and cut
            # sharper; slower players take longer, rounder paths.
            inertia = getattr(p, 'motion_inertia', INERTIA)
            p.rvx = p.rvx * inertia + des_vx * (1.0 - inertia)
            p.rvy = p.rvy * inertia + des_vy * (1.0 - inertia)

            p.rx += p.rvx * dt
            p.ry += p.rvy * dt

        self._separate()

        w_max = float(self.field.width)
        h_max = float(self.field.height)
        for p in self.all_players:
            p.rx = min(max(p.rx, 0.0), w_max)
            p.ry = min(max(p.ry, 0.0), h_max)

    def _separate(self):
        """Gently push apart players who crowd the same spot."""
        players = self.all_players
        for i in range(len(players)):
            a = players[i]
            for j in range(i + 1, len(players)):
                b = players[j]
                dx = b.rx - a.rx
                dy = b.ry - a.ry
                dist = math.hypot(dx, dy)
                if dist >= SEPARATION_RADIUS or dist < 1e-6:
                    continue
                push = SEPARATION_PUSH * (1.0 - dist / SEPARATION_RADIUS)
                nx, ny = dx / dist, dy / dist
                a.rx -= nx * push * 0.5
                a.ry -= ny * push * 0.5
                b.rx += nx * push * 0.5
                b.ry += ny * push * 0.5

    def _record(self, minute, ball):
        owner = getattr(ball, 'owner', None)
        if owner is not None and hasattr(owner, 'rx'):
            bx, by = owner.rx, owner.ry
        else:
            bx, by = ball.x, ball.y

        self.frames.append({
            'm': minute,
            'p': [[round(p.rx, 2), round(p.ry, 2)] for p in self.all_players],
            'b': [round(float(bx), 2), round(float(by), 2)],
        })
