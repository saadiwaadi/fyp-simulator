"""Passing, tackling, crossing & confidence probe.

Verifies the natural ball-progression mechanics end to end:
  1. Lane geometry & vision gating (unit-level, real SimPlayers)
  2. Interception reading: high-interceptions defenses pick off more passes
  3. Tackling: the repurposed `defense` (tackling) stat tilts ball-winning
     without deciding it
  4. Confidence: event-driven swings, decay toward neutral, bounded stat effect
  5. Tactics: wide setups switch play and cross more than narrow ones
  6. Funnel sanity: completion %, tackle win %, cross completion %, goals

Usage: python tools/passing_probe.py
"""
import contextlib
import io
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulation.engine import play_match
from engine.simulation.entities.player import SimPlayer
from engine.simulation.systems import passing


class P:
    _id = 0

    def __init__(self, role, zone='C', **over):
        P._id += 1
        self.id = P._id
        self.name = f"P{P._id}"
        self.role = role
        self.preferred_zone = zone
        self.speed = 70
        self.vision = 70
        self.composure = 70
        self.finishing = 70
        self.def_awareness = 70
        self.short_passing = 70
        self.interceptions = 70
        self.stamina = 75
        self.shooting = 70
        self.defense = 70
        self.passing = 70
        self.x = 0
        self.y = 0
        for k, v in over.items():
            setattr(self, k, v)


class T:
    def __init__(self, name, style=None, mode='Standard'):
        self.name = name
        self.tactical_mode = mode
        self.sys_style = style or {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': 3}


def squad(**over):
    return ([P('GK', **over)] + [P('DEF', **over) for _ in range(4)]
            + [P('MID', z, **over) for z in 'LCCR']
            + [P('FWD', 'L', **over), P('FWD', 'C', **over)])


def run(h_team, a_team, h_squad, a_squad, seed):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return play_match(h_team, a_team, h_squad, a_squad, mode='11v11', match_seed=seed)


def batch(n, h_team, a_team, h_over=None, a_over=None, prefix='pp'):
    keys = None
    acc = {}
    goals = []
    for i in range(n):
        P._id = 0
        _, st = run(h_team, a_team, squad(**(h_over or {})), squad(**(a_over or {})), f"{prefix}-{i}")
        goals.append(st['home_score'] + st['away_score'])
        if keys is None:
            keys = [k for k in st if isinstance(st[k], (int, float))]
        for k in keys:
            acc[k] = acc.get(k, 0) + st[k]
    return {k: v / n for k, v in acc.items()}, statistics.mean(goals)


print("=== 1. LANE GEOMETRY & VISION GATING (unit level) ===")
rng = random.Random("lanes")
placed_rng = random.Random("placement")


def sim_players(n, side_x, **over):
    out = []
    for i in range(n):
        p = SimPlayer(P('MID' if i else 'GK', **over), rng=rng)
        p.x = side_x + placed_rng.uniform(-6, 6)
        p.y = placed_rng.uniform(0, 13)
        out.append(p)
    return out


seen_frac = {}
for label, vis in [('vision 50', 50), ('vision 90', 90)]:
    total_long, seen_long = 0, 0
    lane_counts = []
    for trial in range(300):
        atts = sim_players(8, 10, vision=vis)
        defs = sim_players(8, 10)
        carrier = atts[1]
        lanes = passing.compute_lanes(carrier, atts, defs)
        lane_counts.append(len(lanes))
        seen = passing.perceive_lanes(carrier, lanes, rng=rng)
        seen_ids = {id(l) for l in seen}
        for lane in lanes:
            if lane['length'] > passing.SHORT_SIGHT:
                total_long += 1
                if id(lane) in seen_ids:
                    seen_long += 1
    frac = seen_long / max(total_long, 1)
    seen_frac[vis] = frac
    print(f"  {label}: lanes computed avg {statistics.mean(lane_counts):.1f} | long lanes perceived {frac * 100:.0f}%")
assert seen_frac[90] > seen_frac[50] + 0.10, "vision must gate long-lane perception"
print("  PASS: higher vision sees meaningfully more long lanes")

print()
print("=== 2. INTERCEPTION READING (high vs low interceptions defense) ===")
N = 80
for label, itc in [('interceptions 55', dict(interceptions=55)), ('interceptions 90', dict(interceptions=90))]:
    avg, _ = batch(N, T('H'), T('A'), a_over=itc, prefix=f"itc-{list(itc.values())[0]}")
    print(f"  away {label}: picks off {avg['away_interceptions_won']:.1f} passes/match "
          f"(home completion {100 * avg['home_passes_completed'] / max(avg['home_passes_attempted'], 1):.1f}%)")

print()
print("=== 3. TACKLING (repurposed `defense` stat) ===")
for label, tck in [('tackling 55', dict(defense=55)), ('tackling 90', dict(defense=90))]:
    avg, _ = batch(N, T('H'), T('A'), a_over=tck, prefix=f"tck-{list(tck.values())[0]}")
    win = 100 * avg['away_tackles_won'] / max(avg['away_tackle_attempts'], 1)
    print(f"  away {label}: {avg['away_tackle_attempts']:.1f} attempts, wins {win:.1f}%")

print()
print("=== 4. CONFIDENCE DYNAMICS (unit level) ===")
sp = SimPlayer(P('FWD'), rng=random.Random("conf"))
base = sp.confidence
lo = sp.get_effective_stat('finishing')
sp.confidence = 0.05
floor_val = sp.get_effective_stat('finishing')
sp.confidence = 0.95
peak_val = sp.get_effective_stat('finishing')
swing = (peak_val - floor_val) / max(floor_val, 1)
print(f"  baseline {base:.2f} | effective finishing: floor {floor_val}, peak {peak_val} (swing {swing * 100:.1f}%)")
assert swing < 0.16, "confidence effect must stay modest"
sp.confidence = 0.9
for _ in range(30):
    sp.settle_confidence()
print(f"  after 30 quiet minutes from 0.90 -> {sp.confidence:.2f} (decays toward neutral)")
assert 0.5 < sp.confidence < 0.75
sp.confidence = 0.5
sp.boost_confidence(0.12)
c_up = sp.confidence
sp.sap_confidence(0.04)
print(f"  goal (+0.12) -> {c_up:.2f}; then miss (-0.04) -> {sp.confidence:.2f}")
print("  PASS: bounded, event-driven, mean-reverting")

print()
print("=== 5. TACTICS -> SWITCHES & CROSSES (width slider) ===")
for label, w in [('width 1 (narrow)', 1), ('width 5 (wide)', 5)]:
    style = {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': w}
    avg, _ = batch(N, T('H', style), T('A'), prefix=f"wid-{w}")
    print(f"  home {label}: switches {avg['home_switches']:.1f}/match | crosses {avg['home_crosses']:.1f}/match "
          f"(completed {avg['home_crosses_completed']:.1f})")

print()
print("=== 6. FUNNEL SANITY (baseline vs baseline) ===")
avg, goals = batch(120, T('H'), T('A'), prefix='funnel')
completion = 100 * avg['home_passes_completed'] / max(avg['home_passes_attempted'], 1)
tackle_win = 100 * avg['away_tackles_won'] / max(avg['away_tackle_attempts'], 1)
cross_comp = 100 * avg['home_crosses_completed'] / max(avg['home_crosses'], 1)
print(f"  goals/match {goals:.2f} | pass completion {completion:.1f}% | tackle win {tackle_win:.1f}% | cross completion {cross_comp:.1f}%")
print(f"  per match: passes {avg['home_passes_attempted']:.0f}, switches {avg['home_switches']:.1f}, "
      f"crosses {avg['home_crosses']:.1f}, tackles won {avg['away_tackles_won']:.1f}, "
      f"interceptions {avg['away_interceptions_won']:.1f}")
assert 1.2 < goals < 2.8, "goal rate drifted out of band"
assert 72 <= completion <= 92, "pass completion out of natural band"
assert 30 <= tackle_win <= 62, "tackle win rate out of natural band"
assert cross_comp <= 60, "crosses complete too easily"
print("  PASS: funnel within natural bands")
