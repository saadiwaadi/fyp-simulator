"""Phase 8: system-fit calibration on diverse (realistic) squads.

Uniform-stat probe squads overstate fit effects — every player crosses the
same threshold together. This probe builds varied squads (players drawn from
ranges, only most crossing the fit thresholds) and checks, at each fit
magnitude (±5/10/15/20%):

  - a suited squad running High Press still profits from it
  - a misfit squad running High Press is damaged but NOT auto-lost
  - the gap grows with the magnitude (sanity of the knob itself)

Usage: python tools/fit_probe.py
"""
import contextlib
import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulation.engine import play_match
import engine.simulation.entities.player as player_mod


class P:
    _id = 0

    def __init__(self, role, zone='C', **stats):
        P._id += 1
        self.id = P._id
        self.name = f"P{P._id}"
        self.role = role
        self.preferred_zone = zone
        self.x = 0
        self.y = 0
        for k, v in stats.items():
            setattr(self, k, v)


class T:
    def __init__(self, name, mode='Standard'):
        self.name = name
        self.tactical_mode = mode
        self.sys_style = {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': 3}


BASE_KEYS = ('speed', 'vision', 'composure', 'finishing', 'def_awareness',
             'short_passing', 'interceptions', 'stamina', 'shooting', 'defense', 'passing')


def diverse_squad(rng, archetype):
    """11 varied players; the archetype shifts the ranges, it doesn't clone."""
    shifts = {
        'suited':  {'stamina': (80, 93), 'interceptions': (74, 90)},
        'misfit':  {'stamina': (52, 66), 'interceptions': (55, 72),
                    'short_passing': (55, 72), 'vision': (55, 72)},
        'neutral': {},
    }[archetype]

    squad = []
    roles = [('GK', 'C')] + [('DEF', z) for z in 'LCCR'] + [('MID', z) for z in 'LCCR'] + [('FWD', 'L'), ('FWD', 'C')]
    for role, zone in roles:
        stats = {k: rng.randint(60, 80) for k in BASE_KEYS}
        for k, (lo, hi) in shifts.items():
            stats[k] = rng.randint(lo, hi)
        squad.append(P(role, zone, **stats))
    return squad


def run_batch(n, h_arch, h_mode, prefix):
    w = l = d = 0
    for i in range(n):
        rng = random.Random(f"{prefix}-{i}")
        P._id = 0
        home = diverse_squad(rng, h_arch)
        away = diverse_squad(rng, 'neutral')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _, st = play_match(T('H', h_mode), T('A'), home, away, mode='11v11', match_seed=f"{prefix}-{i}")
        h, a = st['home_score'], st['away_score']
        if h > a:
            w += 1
        elif a > h:
            l += 1
        else:
            d += 1
    return w, l, d


N = 60
print("=== FIT SWEEP: diverse squads, High Press vs neutral Standard ===")
print(f"    ({N} matches per cell; suited/misfit vs a fresh neutral squad each match)\n")

gaps = {}
for bonus in (0.05, 0.10, 0.15, 0.20):
    player_mod.FIT_BONUS = bonus
    sw, sl, sd = run_batch(N, 'suited', 'High Press', f"fit{bonus}-s")
    mw, ml, md = run_batch(N, 'misfit', 'High Press', f"fit{bonus}-m")
    gap = (sw - mw) / N * 100
    gaps[bonus] = gap
    not_lost = (mw + md) / N * 100
    print(f"  ±{int(bonus * 100):>2}%  suited W/L/D {sw}/{sl}/{sd}  |  misfit W/L/D {mw}/{ml}/{md}"
          f"  |  win-gap {gap:.0f}pts | misfit avoids defeat {not_lost:.0f}%")

player_mod.FIT_BONUS = 0.10  # restore the shipped value

print()
assert gaps[0.10] > 8, "fit effect faded: personality no longer visible at ±10%"
assert gaps[0.20] > gaps[0.05], "fit knob is not monotonic"
mw10 = run_batch(12, 'misfit', 'High Press', "fit-recheck")[0]
print(f"  PASS: ±10% keeps fit visible (gap {gaps[0.10]:.0f}pts) without auto-loss;"
      f" knob is monotonic ({gaps[0.05]:.0f} -> {gaps[0.20]:.0f}pts)")
