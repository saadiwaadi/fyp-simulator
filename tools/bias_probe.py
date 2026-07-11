"""Regression probe: run mirrored matches (identical squads both sides) and report
symmetry + collapse-reachability numbers. Run after any engine/balance change.

Usage:  python tools/bias_probe.py [N]   (default N=400 matches per mode)
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulation.engine import play_match


class ProbePlayer:
    _id = 0

    def __init__(self, role, zone='C'):
        ProbePlayer._id += 1
        self.id = ProbePlayer._id
        self.name = f"P{ProbePlayer._id}"
        self.role = role
        self.preferred_zone = zone
        self.speed = self.vision = self.finishing = self.composure = 70
        self.def_awareness = self.short_passing = self.interceptions = 70
        self.stamina = 75
        self.shooting = 70
        self.defense = 70
        self.x = 0
        self.y = 0


class ProbeTeam:
    def __init__(self, name):
        self.name = name
        self.tactical_mode = 'Standard'
        self.sys_style = {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3, 'width': 3}


def build_squad(mode):
    if mode == '5v5':
        return [ProbePlayer('GK'), ProbePlayer('DEF'), ProbePlayer('MID'),
                ProbePlayer('MID'), ProbePlayer('FWD')]
    return ([ProbePlayer('GK')]
            + [ProbePlayer('DEF') for _ in range(4)]
            + [ProbePlayer('MID', z) for z in 'LCCR']
            + [ProbePlayer('FWD'), ProbePlayer('FWD')])


def run_mode(mode, n):
    home_wins = away_wins = draws = 0
    home_goals = away_goals = 0
    possession_sum = 0
    min_zone_seen = 100.0

    for i in range(n):
        home, away = ProbeTeam('HOME'), ProbeTeam('AWAY')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _, stats = play_match(home, away, build_squad(mode), build_squad(mode),
                                  mode=mode, match_seed=f"probe-{mode}-{i}")

        h, a = stats['home_score'], stats['away_score']
        home_goals += h
        away_goals += a
        possession_sum += stats['home_possession_pct']
        if h > a:
            home_wins += 1
        elif a > h:
            away_wins += 1
        else:
            draws += 1

        match_min_zone = min(
            min(stats['home_zone_finals'].values()),
            min(stats['away_zone_finals'].values()),
        )
        min_zone_seen = min(min_zone_seen, match_min_zone)

    print(f"[{mode}] N={n}")
    print(f"  results: home {home_wins} ({home_wins / n:.0%}) | away {away_wins} ({away_wins / n:.0%}) | draws {draws} ({draws / n:.0%})")
    print(f"  goals:   home {home_goals} vs away {away_goals} (total {home_goals + away_goals}, {(home_goals + away_goals) / n:.2f}/match)")
    print(f"  avg home possession: {possession_sum / n:.1f}%")
    print(f"  lowest zone integrity observed anywhere: {min_zone_seen:.0f}")
    print()


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    for mode in ('5v5', '11v11'):
        run_mode(mode, n)
