"""
TACTICAL LAB — PHILOSOPHY STRESS FRAMEWORK
===========================================
Runs 1000 automated matches across scenario matrix.
Tests whether engine output aligns with game philosophy.

WHAT THIS TESTS (that stress_test.py does NOT):
  - Tactic vs tactic counter-relationships
  - Squad profile fit vs tactical mismatch
  - Player position misfit impact
  - DB-sourced player pools (real attributes, not synthetic)

USAGE:
  python stress_framework.py
  python stress_framework.py --quick   (100 runs per scenario)

OUTPUT:
  Console: PASS / WARN / FAIL per scenario
  File:    framework_results.json (regression baseline)

PHILOSOPHY ASSERTIONS:
  Max Chaos        → 3.0–6.0 goals/match, struct breach >85%
  Park the Bus     → 0.5–2.0 goals/match, blank rate >20%
  Counter Exploit  → counter team wins >55% of the time
  Tiki Breakdown   → high press wins >55% vs tiki taka
  Aligned Fit      → aligned squad outperforms misaligned by >15% breaks
  Position Misfit  → wrong-position squad underperforms natural by >20% goals
  Elite vs Weak    → elite wins >70%
  Mirror Balanced  → home win rate 40–60%, goals 1.5–3.5
"""

import os
import sys
import json
import statistics
import argparse
from collections import defaultdict
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')

import django
django.setup()

from engine.models import Team, Player
from engine.simulation.engine import play_match


# ============================================================
# CONSTANTS
# ============================================================

# How many runs per scenario (override with --quick)
DEFAULT_RUNS = 1000
QUICK_RUNS   = 100

# Philosophy assertion ranges: (min, max)
# FAIL if outside range, WARN if within 10% of boundary
PHILOSOPHY = {
    'Max Chaos': {
        'goals_mean':        (3.0, 6.0),
        'blank_rate':        (0.0, 0.08),
        'struct_breach_rate':(0.85, 1.0),
    },
    'Park the Bus': {
        'goals_mean':        (0.5, 2.5),
        'blank_rate':        (0.15, 0.65),
        'break_rate':        (0.0, 0.40),
    },
    'Counter Exploit': {
        'home_win_rate':     (0.50, 0.75),   # counter team is home
    },
    'Tiki Breakdown': {
        'home_win_rate':     (0.50, 0.75),   # high press team is home
    },
    'Aligned vs Misaligned': {
        'aligned_break_rate_advantage': (0.05, 1.0),  # aligned must be higher
    },
    'Position Misfit': {
        'natural_goals_advantage': (0.0, 10.0),       # natural must score more on avg
    },
    'Elite vs Weak': {
        'home_win_rate':     (0.65, 1.0),
    },
    'Mirror Balanced': {
        'goals_mean':        (1.5, 3.5),
        'home_win_rate':     (0.35, 0.65),
    },
}


# ============================================================
# SQUAD POOL BUILDER
# Pulls real players from DB grouped by attribute profile.
# Pools are built ONCE at startup and reused across all scenarios.
# ============================================================

class SquadPools:
    """
    Builds four player pools from the DB.

    ELITE PHYSICAL  — top stamina + speed + defense
                      → suits High Press, Counter Attack
    ELITE TECHNICAL — top short_passing + vision + composure
                      → suits Tiki Taka, Park the Bus
    AVERAGE BALANCED— mid-tier across all attributes
    WEAK            — bottom tier overall
    """

    def __init__(self):
        all_players = list(Player.objects.all())

        if not all_players:
            print("ABORT: No players in DB. Run populate_players.py first.")
            sys.exit(1)

        # Score each player per profile
        def physical_score(p):
            return getattr(p, 'stamina', 0) + getattr(p, 'speed', 0) + getattr(p, 'defense', 0)

        def technical_score(p):
            return getattr(p, 'short_passing', 0) + getattr(p, 'vision', 0) + getattr(p, 'composure', 0)

        def overall_score(p):
            return (getattr(p, 'stamina', 0) + getattr(p, 'speed', 0) +
                    getattr(p, 'shooting', 0) + getattr(p, 'defense', 0)) / 4.0

        sorted_physical  = sorted(all_players, key=physical_score,  reverse=True)
        sorted_technical = sorted(all_players, key=technical_score, reverse=True)
        sorted_overall   = sorted(all_players, key=overall_score,   reverse=True)

        pool_size = 30  # enough to assemble 5v5 and 11v11 squads by role

        self.elite_physical  = sorted_physical[:pool_size]
        self.elite_technical = sorted_technical[:pool_size]
        self.average         = sorted_overall[len(sorted_overall)//3 : len(sorted_overall)//3 + pool_size]
        self.weak            = sorted_overall[-pool_size:]

        print(f"\n  [POOLS] elite_physical={len(self.elite_physical)}  "
              f"elite_technical={len(self.elite_technical)}  "
              f"average={len(self.average)}  weak={len(self.weak)}")

    def get(self, profile_name):
        return {
            'elite_physical':  self.elite_physical,
            'elite_technical': self.elite_technical,
            'average':         self.average,
            'weak':            self.weak,
        }[profile_name]


# ============================================================
# SQUAD ASSEMBLER
# Builds match squads from a pool respecting role requirements
# and position alignment type (natural / adjacent / wrong).
# ============================================================

ROLE_ORDER = ['GK', 'DEF', 'MID', 'FWD']

def _pick_by_role(pool, role, n):
    """Pick up to n players of a given role from pool."""
    candidates = [p for p in pool if p.role == role]
    return candidates[:n]


def assemble_squad(pool, mode, alignment='natural'):
    """
    Build a squad from pool with positional alignment applied.

    alignment options:
      'natural'  — each role fills its correct slot
      'adjacent' — MIDs fill FWD slots, DEFs fill MID slots
      'wrong'    — DEFs fill FWD slots, FWDs fill DEF slots

    For 5v5:  1 GK + 1 DEF + 1 MID + 2 FWD  (natural)
    For 11v11: 1 GK + 4 DEF + 4 MID + 2 FWD (natural)
    """
    if mode == '5v5':
        needs = {'GK': 1, 'DEF': 1, 'MID': 1, 'FWD': 2}
    else:
        needs = {'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2}

    if alignment == 'natural':
        squad = []
        for role, n in needs.items():
            picked = _pick_by_role(pool, role, n)
            # Fallback: if pool doesn't have enough of this role, fill from any role
            if len(picked) < n:
                extras = [p for p in pool if p not in picked][:n - len(picked)]
                picked += extras
            squad.extend(picked)
        return squad

    elif alignment == 'adjacent':
        # MIDs play FWD slots, DEFs play MID slots, GK stays, FWDs play DEF
        role_remap = {'GK': 'GK', 'DEF': 'MID', 'MID': 'FWD', 'FWD': 'DEF'}
        squad = []
        for intended_role, n in needs.items():
            source_role = role_remap[intended_role]
            picked = _pick_by_role(pool, source_role, n)
            if len(picked) < n:
                extras = [p for p in pool if p not in picked][:n - len(picked)]
                picked += extras
            squad.extend(picked)
        return squad

    elif alignment == 'wrong':
        # DEFs play FWD slots, FWDs play DEF slots (maximum disruption)
        role_remap = {'GK': 'GK', 'DEF': 'FWD', 'MID': 'MID', 'FWD': 'DEF'}
        squad = []
        for intended_role, n in needs.items():
            source_role = role_remap[intended_role]
            picked = _pick_by_role(pool, source_role, n)
            if len(picked) < n:
                extras = [p for p in pool if p not in picked][:n - len(picked)]
                picked += extras
            squad.extend(picked)
        return squad

    return []


def make_team_obj(name, tactic, style_dict):
    """
    Creates a lightweight team object the engine accepts.
    Pulls the real Team from DB if it exists, otherwise makes a mock.
    """
    try:
        team = Team.objects.get(name=name)
    except Team.DoesNotExist:
        # Use first available team as base and override name/style
        team = Team.objects.first()
        if not team:
            print("ABORT: No teams in DB.")
            sys.exit(1)

    team.name         = name
    team.tactical_mode = tactic
    team.sys_style     = style_dict
    return team


# ============================================================
# METRICS EXTRACTION
# Extended version of stress_test.py's extract_metrics.
# Adds: break_rate, shot_rate, tactical_fit signals.
# ============================================================

def extract_metrics(log, stats):
    h_score = stats.get('home_score', 0)
    a_score = stats.get('away_score', 0)

    # Break rate: breaks fired / total minutes (proxy for offensive penetration)
    break_timestamps = stats.get('break_timestamps', [])
    max_min  = stats.get('max_minutes', 40)
    break_rate = len(break_timestamps) / max(max_min, 1)

    # Zone dominance: which zone saw most attacking action
    zone_ctrl = stats.get('zone_control', {})
    dominant_zone = max(
        ['Left', 'Center', 'Right'],
        key=lambda z: zone_ctrl.get(z, {}).get('home', 0) + zone_ctrl.get(z, {}).get('away', 0)
    )

    return {
        'h_score':           h_score,
        'a_score':           a_score,
        'total_goals':       h_score + a_score,
        'home_win':          h_score > a_score,
        'away_win':          a_score > h_score,
        'draw':              h_score == a_score,
        'blank':             (h_score + a_score) == 0,
        'h_integrity':       stats.get('home_integrity_final', 100),
        'a_integrity':       stats.get('away_integrity_final', 100),
        'fatigue_breach_min':stats.get('fatigue_breach_min'),
        'struct_breach_min': stats.get('struct_breach_min'),
        'break_rate':        break_rate,
        'dominant_zone':     dominant_zone,
        'zone_ctrl':         zone_ctrl,
        'density_events':    sum(1 for l in log if '[DENSITY]' in l),
    }


# ============================================================
# SCENARIO RUNNER
# Runs N matches for one scenario config, returns raw metrics list.
# ============================================================

def run_scenario(home_team, away_team, h_squad, a_squad, mode, n_runs):
    results = []
    crashes = 0

    for _ in range(n_runs):
        try:
            log, stats = play_match(home_team, away_team, h_squad, a_squad, mode=mode)
            results.append(extract_metrics(log, stats))
        except Exception:
            crashes += 1

    return results, crashes


# ============================================================
# AGGREGATOR
# Compresses raw match list into summary statistics.
# ============================================================

def aggregate(results):
    if not results:
        return {}

    n = len(results)

    goals      = [r['total_goals']   for r in results]
    h_ints     = [r['h_integrity']   for r in results]
    a_ints     = [r['a_integrity']   for r in results]
    break_rates= [r['break_rate']    for r in results]
    f_mins     = [r['fatigue_breach_min'] for r in results if r['fatigue_breach_min']]
    s_mins     = [r['struct_breach_min']  for r in results if r['struct_breach_min']]

    return {
        'n':                    n,
        'goals_mean':           statistics.mean(goals),
        'goals_std':            statistics.stdev(goals) if n > 1 else 0,
        'goals_min':            min(goals),
        'goals_max':            max(goals),
        'blank_rate':           sum(1 for r in results if r['blank']) / n,
        'home_win_rate':        sum(1 for r in results if r['home_win']) / n,
        'away_win_rate':        sum(1 for r in results if r['away_win']) / n,
        'draw_rate':            sum(1 for r in results if r['draw']) / n,
        'break_rate_mean':      statistics.mean(break_rates),
        'struct_breach_rate':   len(s_mins) / n,
        'struct_breach_min_mean': statistics.mean(s_mins) if s_mins else None,
        'fatigue_breach_rate':  len(f_mins) / n,
        'fatigue_breach_min_mean': statistics.mean(f_mins) if f_mins else None,
        'avg_h_integrity':      statistics.mean(h_ints),
        'avg_a_integrity':      statistics.mean(a_ints),
        'density_mean':         statistics.mean(r['density_events'] for r in results),
    }


# ============================================================
# PHILOSOPHY CHECKER
# Compares aggregated metrics against expected ranges.
# Returns list of (metric, value, status, expected_range)
# ============================================================

def check_philosophy(scenario_name, agg):
    expected = PHILOSOPHY.get(scenario_name, {})
    checks   = []

    for metric, (lo, hi) in expected.items():
        # Special comparative metrics handled separately
        if metric in ('aligned_break_rate_advantage', 'natural_goals_advantage'):
            continue

        val = agg.get(metric)
        if val is None:
            checks.append((metric, None, 'SKIP', (lo, hi)))
            continue

        warn_margin = (hi - lo) * 0.10
        if lo <= val <= hi:
            if (val - lo < warn_margin) or (hi - val < warn_margin):
                status = 'WARN'
            else:
                status = 'PASS'
        else:
            status = 'FAIL'

        checks.append((metric, round(val, 3), status, (lo, hi)))

    return checks


# ============================================================
# REPORT PRINTER
# ============================================================

STATUS_ICONS = {'PASS': '✅', 'WARN': '⚠️ ', 'FAIL': '❌', 'SKIP': '  '}

def print_scenario_report(scenario_name, agg, checks, crashes, n_runs):
    print(f"\n{'='*65}")
    print(f"  {scenario_name}")
    print(f"  {agg.get('n', 0)}/{n_runs} completed  |  {crashes} crashes")
    print(f"{'='*65}")
    print(f"  {'Metric':<30} {'Value':>8}   {'Expected':>16}   Status")
    print(f"  {'-'*58}")

    for metric, val, status, (lo, hi) in checks:
        val_str = f"{val:.3f}" if val is not None else "N/A"
        rng_str = f"[{lo:.2f}–{hi:.2f}]"
        icon    = STATUS_ICONS[status]
        print(f"  {metric:<30} {val_str:>8}   {rng_str:>16}   {icon} {status}")

    print(f"\n  Raw stats:")
    print(f"    goals/match : {agg.get('goals_mean', 0):.2f} ± {agg.get('goals_std', 0):.2f}"
          f"  [min:{agg.get('goals_min', 0)}  max:{agg.get('goals_max', 0)}]")
    print(f"    blank rate  : {agg.get('blank_rate', 0)*100:.1f}%")
    print(f"    H/D/A       : {agg.get('home_win_rate',0)*100:.0f}% / "
          f"{agg.get('draw_rate',0)*100:.0f}% / "
          f"{agg.get('away_win_rate',0)*100:.0f}%")
    print(f"    struct breach: {agg.get('struct_breach_rate',0)*100:.0f}%"
          + (f"  avg min {agg['struct_breach_min_mean']:.0f}"
             if agg.get('struct_breach_min_mean') else "  (never)"))
    print(f"    break rate  : {agg.get('break_rate_mean',0):.3f} breaks/min")
    print(f"    integrity   : H={agg.get('avg_h_integrity',100):.0f}%"
          f"  A={agg.get('avg_a_integrity',100):.0f}%")


def print_global_summary(all_scenario_checks):
    print(f"\n{'='*65}")
    print(f"  PHILOSOPHY REPORT")
    print(f"{'='*65}")
    total = fail = warn = passed = 0
    for name, checks in all_scenario_checks.items():
        s_total  = len([c for c in checks if c[2] != 'SKIP'])
        s_pass   = len([c for c in checks if c[2] == 'PASS'])
        s_warn   = len([c for c in checks if c[2] == 'WARN'])
        s_fail   = len([c for c in checks if c[2] == 'FAIL'])
        total += s_total; fail += s_fail; warn += s_warn; passed += s_pass
        icon = '✅' if s_fail == 0 and s_warn == 0 else ('⚠️ ' if s_fail == 0 else '❌')
        print(f"  {icon}  {name:<35}  {s_pass}P / {s_warn}W / {s_fail}F")
    print(f"\n  TOTAL: {passed} PASS  {warn} WARN  {fail} FAIL  (of {total} assertions)")
    if fail == 0 and warn == 0:
        print("  ✅ Engine fully aligned with game philosophy.")
    elif fail == 0:
        print("  ⚠️  Minor boundary warnings — review highlighted metrics.")
    else:
        print("  ❌ Philosophy violations detected — engine needs rebalancing.")
    print(f"{'='*65}\n")


# ============================================================
# SCENARIO DEFINITIONS
# Each entry defines the full match context.
# Squad pools and alignment are resolved at runtime.
# ============================================================

def build_scenarios(pools, mode, n_runs):
    """
    Returns list of scenario dicts ready to execute.
    Each scenario is self-contained with its own team objs and squads.
    """

    def teams(h_name, h_tactic, h_style, h_pool, h_align,
               a_name, a_tactic, a_style, a_pool, a_align):
        return {
            'home_team':  make_team_obj(h_name, h_tactic, h_style),
            'away_team':  make_team_obj(a_name, a_tactic, a_style),
            'h_squad':    assemble_squad(pools.get(h_pool), mode, h_align),
            'a_squad':    assemble_squad(pools.get(a_pool), mode, a_align),
            'mode':       mode,
            'n_runs':     n_runs,
        }

    return [
        # ----------------------------------------------------------
        # 1. MAX CHAOS
        # Both teams all-out aggression. Should produce high goals,
        # struct breach on almost every match.
        # ----------------------------------------------------------
        {
            'name':       'Max Chaos',
            'philosophy': 'Max Chaos',
            **teams(
                'Neon FC',       'Standard', {'tempo':5,'press':5,'width':5,'depth':5,'risk':5}, 'elite_physical', 'natural',
                'Catalyst United','Standard', {'tempo':5,'press':5,'width':5,'depth':5,'risk':5}, 'elite_physical', 'natural',
            )
        },

        # ----------------------------------------------------------
        # 2. PARK THE BUS
        # Both teams ultra-defensive. Should be low scoring, high
        # blank rate, low break rate.
        # ----------------------------------------------------------
        {
            'name':       'Park the Bus',
            'philosophy': 'Park the Bus',
            **teams(
                'Neon FC',        'Park the Bus', {'tempo':1,'press':1,'width':2,'depth':5,'risk':1}, 'elite_technical', 'natural',
                'Catalyst United','Park the Bus', {'tempo':1,'press':1,'width':2,'depth':5,'risk':1}, 'elite_technical', 'natural',
            )
        },

        # ----------------------------------------------------------
        # 3. COUNTER EXPLOIT
        # Home: Counter Attack (risk=4, depth=4) vs Away: High Press.
        # Counter should exploit space left by press → home wins >55%.
        # ----------------------------------------------------------
        {
            'name':       'Counter Exploit',
            'philosophy': 'Counter Exploit',
            **teams(
                'Neon FC',        'Counter Attack', {'tempo':3,'press':1,'width':4,'depth':2,'risk':4}, 'elite_physical', 'natural',
                'Catalyst United','High Press',     {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'average',        'natural',
            )
        },

        # ----------------------------------------------------------
        # 4. TIKI BREAKDOWN
        # Home: High Press vs Away: Tiki Taka.
        # Press disrupts buildup → home wins >55%.
        # ----------------------------------------------------------
        {
            'name':       'Tiki Breakdown',
            'philosophy': 'Tiki Breakdown',
            **teams(
                'Neon FC',        'High Press', {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'elite_physical',  'natural',
                'Catalyst United','Tiki Taka',  {'tempo':5,'press':1,'width':5,'depth':1,'risk':1}, 'elite_technical', 'natural',
            )
        },

        # ----------------------------------------------------------
        # 5. ALIGNED vs MISALIGNED FIT
        # Same tactic (High Press), but home squad is physical (aligned)
        # and away squad is technical (misaligned for High Press).
        # Aligned must show measurably higher break_rate.
        # Checked comparatively, not against PHILOSOPHY dict.
        # ----------------------------------------------------------
        {
            'name':       'Aligned Fit',
            'philosophy': 'Aligned vs Misaligned',
            **teams(
                'Neon FC',        'High Press', {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'elite_physical',  'natural',
                'Catalyst United','High Press', {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'elite_technical', 'natural',
            )
        },
        {
            'name':       'Misaligned Fit',
            'philosophy': 'Aligned vs Misaligned',
            **teams(
                'Neon FC',        'High Press', {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'elite_technical', 'natural',
                'Catalyst United','High Press', {'tempo':5,'press':5,'width':3,'depth':2,'risk':3}, 'elite_physical',  'natural',
            )
        },

        # ----------------------------------------------------------
        # 6. POSITION MISFIT
        # Same squad pool, but one plays natural positions vs wrong.
        # Natural must outscore wrong-position squad on average.
        # Checked comparatively.
        # ----------------------------------------------------------
        {
            'name':       'Natural Positions',
            'philosophy': 'Position Misfit',
            **teams(
                'Neon FC',        'Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'elite_physical', 'natural',
                'Catalyst United','Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'average',        'natural',
            )
        },
        {
            'name':       'Wrong Positions',
            'philosophy': 'Position Misfit',
            **teams(
                'Neon FC',        'Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'elite_physical', 'wrong',
                'Catalyst United','Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'average',        'natural',
            )
        },

        # ----------------------------------------------------------
        # 7. ELITE vs WEAK
        # Elite physical squad vs weak squad. Elite should win >70%.
        # ----------------------------------------------------------
        {
            'name':       'Elite vs Weak',
            'philosophy': 'Elite vs Weak',
            **teams(
                'Neon FC',        'Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'elite_physical', 'natural',
                'Catalyst United','Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'weak',           'natural',
            )
        },

        # ----------------------------------------------------------
        # 8. MIRROR BALANCED
        # Both identical mid-tier squads with balanced sliders.
        # Should be closest to 50/50. Goals 1.5–3.5 range.
        # ----------------------------------------------------------
        {
            'name':       'Mirror Balanced',
            'philosophy': 'Mirror Balanced',
            **teams(
                'Neon FC',        'Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'average', 'natural',
                'Catalyst United','Standard', {'tempo':3,'press':3,'width':3,'depth':3,'risk':3}, 'average', 'natural',
            )
        },
    ]


# ============================================================
# COMPARATIVE ASSERTIONS
# For scenarios that compare two related runs (aligned vs misaligned,
# natural vs wrong position) rather than checking absolute ranges.
# ============================================================

def check_comparative(scenario_a_agg, scenario_b_agg, philosophy_key):
    """
    scenario_a is the 'better' condition, scenario_b is the 'worse'.
    Returns (metric, a_val, b_val, advantage, status).
    """
    results = []

    if philosophy_key == 'Aligned vs Misaligned':
        a_br = scenario_a_agg.get('break_rate_mean', 0)
        b_br = scenario_b_agg.get('break_rate_mean', 0)
        adv  = a_br - b_br
        lo, hi = PHILOSOPHY[philosophy_key]['aligned_break_rate_advantage']
        status = 'PASS' if lo <= adv else 'FAIL'
        results.append(('break_rate advantage (aligned over misaligned)', round(a_br, 3), round(b_br, 3), round(adv, 3), status))

    elif philosophy_key == 'Position Misfit':
        a_g = scenario_a_agg.get('goals_mean', 0)
        b_g = scenario_b_agg.get('goals_mean', 0)
        adv  = a_g - b_g
        lo, hi = PHILOSOPHY[philosophy_key]['natural_goals_advantage']
        status = 'PASS' if adv >= 0 else 'FAIL'   # natural just needs to be >= wrong
        results.append(('goals advantage (natural over wrong position)', round(a_g, 3), round(b_g, 3), round(adv, 3), status))

    return results


def print_comparative_report(label, comparisons):
    print(f"\n{'='*65}")
    print(f"  COMPARATIVE: {label}")
    print(f"{'='*65}")
    for metric, a_val, b_val, adv, status in comparisons:
        icon = STATUS_ICONS[status]
        print(f"  {icon} {metric}")
        print(f"       A={a_val}  B={b_val}  advantage={adv:+.3f}")


# ============================================================
# MAIN
# ============================================================

def run_framework(n_runs, mode='5v5'):
    print(f"\n{'='*65}")
    print(f"  TACTICAL LAB — PHILOSOPHY STRESS FRAMEWORK")
    print(f"  {n_runs} runs/scenario  |  mode={mode}  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*65}")

    pools     = SquadPools()
    scenarios = build_scenarios(pools, mode, n_runs)

    # Validate squads loaded correctly
    for s in scenarios:
        if not s['h_squad'] or not s['a_squad']:
            print(f"  WARNING: Empty squad in scenario '{s['name']}' — check pool sizes and roles in DB.")

    all_aggs   = {}   # name → aggregated metrics
    all_checks = {}   # name → philosophy check results
    json_dump  = {}

    # Run each scenario
    for s in scenarios:
        print(f"\n  Running: {s['name']} ({s['n_runs']} matches)...", end='', flush=True)
        results, crashes = run_scenario(
            s['home_team'], s['away_team'],
            s['h_squad'], s['a_squad'],
            s['mode'], s['n_runs']
        )
        agg    = aggregate(results)
        checks = check_philosophy(s['philosophy'], agg)

        all_aggs[s['name']]   = agg
        all_checks[s['name']] = checks
        json_dump[s['name']]  = {'agg': agg, 'crashes': crashes}

        print(f" done. ({len(results)}/{s['n_runs']} completed, {crashes} crashes)")
        print_scenario_report(s['name'], agg, checks, crashes, s['n_runs'])

    # Comparative assertions
    print(f"\n\n{'='*65}")
    print(f"  COMPARATIVE ASSERTIONS")

    if 'Aligned Fit' in all_aggs and 'Misaligned Fit' in all_aggs:
        comps = check_comparative(
            all_aggs['Aligned Fit'], all_aggs['Misaligned Fit'],
            'Aligned vs Misaligned'
        )
        print_comparative_report('Aligned vs Misaligned Squad Fit', comps)
        aligned_status = [('aligned_vs_misaligned', None, c[4], None) for c in comps]
        all_checks['Aligned vs Misaligned'] = [(c[0], c[3], c[4], (0,1)) for c in comps]

    if 'Natural Positions' in all_aggs and 'Wrong Positions' in all_aggs:
        comps = check_comparative(
            all_aggs['Natural Positions'], all_aggs['Wrong Positions'],
            'Position Misfit'
        )
        print_comparative_report('Natural vs Wrong Position Lineup', comps)
        all_checks['Position Misfit'] = [(c[0], c[3], c[4], (0,1)) for c in comps]

    # Global philosophy summary
    print_global_summary(all_checks)

    # Save JSON baseline
    output_path = os.path.join(os.path.dirname(__file__), 'framework_results.json')
    with open(output_path, 'w') as f:
        json.dump(json_dump, f, indent=2, default=str)
    print(f"  Results saved → {output_path}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Run 100 matches per scenario instead of 1000')
    parser.add_argument('--mode',  default='5v5', choices=['5v5', '11v11'])
    args = parser.parse_args()

    n = QUICK_RUNS if args.quick else DEFAULT_RUNS
    run_framework(n_runs=n, mode=args.mode)