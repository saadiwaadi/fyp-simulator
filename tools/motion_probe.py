"""Motion & influence probe: verifies that tactics visibly move players on the
pitch, that player personality shapes roaming, and that players who don't fit
the system comply less and cost their team.

Usage: python tools/motion_probe.py
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


def home_frame_stats(stats, indices=None):
    """Mean x, y-spread, and per-player roam radius for home outfielders."""
    frames = stats['movement_frames']
    n_home = 11
    idxs = indices if indices is not None else [i for i in range(1, n_home)]  # skip GK at 0
    xs, ys = [], []
    per_player = {i: [] for i in idxs}
    for f in frames:
        for i in idxs:
            x, y = f['p'][i]
            xs.append(x)
            ys.append(y)
            per_player[i].append((x, y))
    roam = {}
    for i, pts in per_player.items():
        mx = statistics.mean(p[0] for p in pts)
        my = statistics.mean(p[1] for p in pts)
        roam[i] = statistics.mean(((p[0] - mx) ** 2 + (p[1] - my) ** 2) ** 0.5 for p in pts)
    return statistics.mean(xs), statistics.pstdev(ys), roam


SEEDS = [f"motion-{i}" for i in range(12)]

print("=== 1. TACTICS -> MOTION (same squad, one slider changed) ===")
for label, style in [
    ('depth 1 (deep)',   {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 1, 'width': 3}),
    ('depth 5 (high)',   {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 5, 'width': 3}),
    ('width 1 (narrow)', {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': 1}),
    ('width 5 (wide)',   {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': 5}),
    ('press 1 (passive)', {'tempo': 3, 'press': 1, 'risk': 3, 'depth': 3, 'width': 3}),
    ('press 5 (swarm)',  {'tempo': 3, 'press': 5, 'risk': 3, 'depth': 3, 'width': 3}),
]:
    mean_x, y_spread, roam = [], [], []
    for s in SEEDS:
        P._id = 0
        _, st = run(T('H', style), T('A'), squad(), squad(), s)
        mx, ysp, rm = home_frame_stats(st)
        mean_x.append(mx)
        y_spread.append(ysp)
        roam.append(statistics.mean(rm.values()))
    print(f"  {label:18} mean line x={statistics.mean(mean_x):5.2f} | width spread y={statistics.mean(y_spread):4.2f} | roam radius={statistics.mean(roam):4.2f}")

print()
print("=== 2. PERSONALITY -> MOTION (one squad, contrasting players) ===")
# index 5 = first MID. Same stamina/speed both ways so work-rate and pace do
# not confound the comparison: only temperament (discipline/risk) differs.
robot = dict(def_awareness=92, composure=95)      # disciplined, calm
maverick = dict(def_awareness=48, composure=40)   # erratic, risky
for label, over in [('disciplined MID', robot), ('maverick MID', maverick)]:
    roams, jitters = [], []
    for s in SEEDS:
        P._id = 0
        sq = squad()
        for k, v in over.items():
            setattr(sq[5], k, v)
        _, st = run(T('H'), T('A'), sq, squad(), s)
        _, _, rm = home_frame_stats(st, indices=[5])
        roams.append(rm[5])
        # idle jitter: small-step oscillation only, excluding sprints and
        # recovery runs (disciplined players legitimately track back further,
        # which inflates raw roam radius)
        frames = st['movement_frames']
        steps = []
        for k2 in range(1, len(frames)):
            x0, y0 = frames[k2 - 1]['p'][5]
            x1, y1 = frames[k2]['p'][5]
            d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if d < 0.6:
                steps.append(d)
        jitters.append(statistics.mean(steps))
    print(f"  {label:16} roam radius = {statistics.mean(roams):4.2f} | idle jitter = {statistics.mean(jitters):5.3f}")

print()
print("=== 3. SPEED ATTRIBUTE -> PACE (fast vs slow squad, same elsewhere) ===")
for label, spd in [('speed 55 squad', 55), ('speed 90 squad', 90)]:
    dists = []
    for s in SEEDS[:6]:
        P._id = 0
        _, st = run(T('H'), T('A'), squad(speed=spd), squad(), s)
        frames = st['movement_frames']
        total = 0.0
        for k in range(1, len(frames)):
            for i in range(1, 11):
                x0, y0 = frames[k - 1]['p'][i]
                x1, y1 = frames[k]['p'][i]
                total += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        dists.append(total / (10 * len(frames)))
    print(f"  {label:15} avg distance covered per frame = {statistics.mean(dists):5.3f}")

print()
print("=== 4. SYSTEM FIT: misfit squad in High Press vs suited squad ===")
# High Press wants stamina>80 & interceptions>75. Misfits have neither.
suited = dict(stamina=88, interceptions=80)
fit_only_misfit = dict(stamina=62)  # crosses the fit threshold, stats near-baseline otherwise
misfit = dict(stamina=62, interceptions=60, short_passing=60, vision=60)  # low fit AND low loyalty
N = 120
for label, over in [('suited squad', suited), ('fit-only misfit', fit_only_misfit), ('misfit squad', misfit)]:
    w = l = d = 0
    gf = ga = 0
    for i in range(N):
        P._id = 0
        _, st = run(T('H', mode='High Press'), T('A'), squad(**over), squad(), f"fit-{i}")
        h, a = st['home_score'], st['away_score']
        gf += h
        ga += a
        if h > a:
            w += 1
        elif a > h:
            l += 1
        else:
            d += 1
    print(f"  {label:13} running High Press: W/L/D {w}/{l}/{d} | goals {gf}-{ga}")
