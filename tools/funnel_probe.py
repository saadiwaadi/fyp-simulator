"""Phase 9: full-funnel validation after passing integration.

Measures how possessions convert down the funnel now that the ball travels
through passing chains: possession -> first press -> chain (passes, switches,
crosses, tackles, interceptions) -> break -> shot (by type) -> goal.

Usage: python tools/funnel_probe.py
"""
import contextlib
import io
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulation.engine import play_match


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


N = 150
SUM_KEYS = (
    'home_possession_count', 'away_possession_count',
    'home_passes_attempted', 'home_passes_completed',
    'away_passes_attempted', 'away_passes_completed',
    'home_switches', 'away_switches',
    'home_crosses', 'away_crosses', 'home_crosses_completed', 'away_crosses_completed',
    'home_tackles_won', 'away_tackles_won', 'home_interceptions_won', 'away_interceptions_won',
    'home_shots', 'away_shots',
    'home_shots_finesse', 'away_shots_finesse',
    'home_shots_drive', 'away_shots_drive',
    'home_shots_header', 'away_shots_header',
    'home_score', 'away_score',
)

acc = {k: 0 for k in SUM_KEYS}
breaks = 0
goals_pm = []
for i in range(N):
    P._id = 0
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _, st = play_match(T('H'), T('A'), squad(), squad(), mode='11v11', match_seed=f"funnel-{i}")
    for k in SUM_KEYS:
        acc[k] += st[k]
    breaks += len(st['break_timestamps'])
    goals_pm.append(st['home_score'] + st['away_score'])

poss = acc['home_possession_count'] + acc['away_possession_count']
passes_att = acc['home_passes_attempted'] + acc['away_passes_attempted']
passes_cmp = acc['home_passes_completed'] + acc['away_passes_completed']
switches = acc['home_switches'] + acc['away_switches']
crosses = acc['home_crosses'] + acc['away_crosses']
crosses_cmp = acc['home_crosses_completed'] + acc['away_crosses_completed']
tackles = acc['home_tackles_won'] + acc['away_tackles_won']
intercepts = acc['home_interceptions_won'] + acc['away_interceptions_won']
shots = acc['home_shots'] + acc['away_shots']
finesse = acc['home_shots_finesse'] + acc['away_shots_finesse']
drive = acc['home_shots_drive'] + acc['away_shots_drive']
header = acc['home_shots_header'] + acc['away_shots_header']
goals = acc['home_score'] + acc['away_score']

per_k = 1000.0 / max(poss, 1)
print(f"=== FUNNEL ({N} matches, 11v11, baseline squads) ===\n")
print(f"  possessions/match: {poss / N:.1f}")
print(f"  per 1000 possessions:")
print(f"    passes attempted {passes_att * per_k:7.1f} | completed {passes_cmp * per_k:7.1f} "
      f"({100 * passes_cmp / max(passes_att, 1):.1f}%)")
print(f"    switches        {switches * per_k:7.1f} | crosses {crosses * per_k:5.1f} "
      f"(completed {crosses_cmp * per_k:.1f})")
print(f"    ball won by:    tackles {tackles * per_k:5.1f} | lane interceptions {intercepts * per_k:5.1f}")
print(f"    breaks          {breaks * per_k:7.1f}")
print(f"    shots           {shots * per_k:7.1f}  (finesse {100 * finesse / max(shots, 1):.0f}% / "
      f"drive {100 * drive / max(shots, 1):.0f}% / header {100 * header / max(shots, 1):.0f}%)")
print(f"    goals           {goals * per_k:7.1f}")
print(f"\n  goals/match {statistics.mean(goals_pm):.2f} | shot conversion {100 * goals / max(shots, 1):.1f}%")

assert 1.2 < statistics.mean(goals_pm) < 2.8, "goal rate out of band"
assert breaks * per_k > 20, "breaks collapsed: chains absorb too much"
assert shots > goals, "conversion impossible"
assert 0 < header, "headers never happen"
assert 0 < drive, "drives never happen"
conv = 100 * goals / max(shots, 1)
assert 15 <= conv <= 45, f"shot conversion {conv:.1f}% unnatural"
print("  PASS: funnel gates all live and within bands")
