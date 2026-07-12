"""Passing lanes, vision-gated perception, and pass resolution.

Lane geometry runs on the players' real pitch positions each sim-minute:

- A lane is the straight segment from the carrier to a teammate. Defenders
  standing near that segment shade it (openness drops); the best-placed of
  them becomes the potential interceptor.
- The carrier only PLAYS what he PERCEIVES: short lanes are obvious to
  everyone, but the further and more shaded a lane is, the more the vision
  attribute decides whether he sees it at all. Low-vision carriers play in
  a small bubble; visionaries find the switch to the far flank.
- Resolution is position-first: lane exposure (how shaded it is, how long
  it is) sets the stakes, then the passer's short/long passing duels the
  interceptor's interceptions/def_awareness through the same compressed
  curve and noise band as every other duel, so ratings tilt passes rather
  than decide them.

Switches of play (cross-field shifts) and crosses into the box use the
repurposed `long_passing` attribute (legacy `passing` DB field).
"""

import math
import random

from .mechanics import _duel_value, _record_attribution

# A defender within this many grid units of the lane segment shades it.
LANE_BLOCK_RADIUS = 2.0
# Lanes at or below this length are perceived by everyone.
SHORT_SIGHT = 4.0
# A lane must cover at least this fraction of pitch height to be a switch.
SWITCH_MIN_DY_FRAC = 0.40
SWITCH_MIN_LENGTH = 6.0


def _point_segment_distance(px, py, ax, ay, bx, by):
    """Distance from point P to segment AB, and the projection fraction t."""
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-9:
        return math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), t


def compute_lanes(carrier, att_team, def_team):
    """All geometric lanes from the carrier to his outfield teammates."""
    lanes = []
    for mate in att_team:
        if mate is carrier or mate.role == 'GK':
            continue
        length = math.hypot(mate.x - carrier.x, mate.y - carrier.y)
        if length < 0.5:
            continue

        blockers = []
        shade = 0.0
        for d in def_team:
            if d.role == 'GK':
                continue
            dist, t = _point_segment_distance(d.x, d.y, carrier.x, carrier.y, mate.x, mate.y)
            # Bodies right on top of either end belong to the pressure/tackle
            # game, not the lane; only mid-lane positioning shades a pass.
            if dist < LANE_BLOCK_RADIUS and 0.08 < t < 0.95:
                closeness = 1.0 - dist / LANE_BLOCK_RADIUS
                blockers.append({'defender': d, 'closeness': closeness, 'along': t})
                shade += closeness * 0.55

        lanes.append({
            'receiver': mate,
            'length': length,
            'dy': abs(mate.y - carrier.y),
            'blockers': blockers,
            'openness': max(0.0, 1.0 - shade),
        })
    return lanes


def perceive_lanes(carrier, lanes, rng=None):
    """Vision gates which lanes the carrier is actually aware of."""
    rng = rng or random
    vision = carrier.get_effective_stat('vision')
    seen = []
    for lane in lanes:
        if lane['length'] <= SHORT_SIGHT:
            seen.append(lane)
            continue
        # Long lanes: base chance grows with vision, shrinks with distance
        # and shade. At vision 60 a 12-unit shaded switch is a coin flip at
        # best; at vision 90 it is routine.
        reach = 1.0 - (lane['length'] - SHORT_SIGHT) / 22.0
        p = (0.15 + (vision / 100.0) * 0.85) * max(0.30, reach)
        p *= 0.65 + lane['openness'] * 0.35
        if rng.random() < p:
            seen.append(lane)
    return seen


def is_switch(lane, field):
    return lane['dy'] >= field.height * SWITCH_MIN_DY_FRAC and lane['length'] >= SWITCH_MIN_LENGTH


def select_lane(carrier, lanes, att_side, field, width_pref=3, rng=None):
    """Pick a lane the way a player would: mostly the open, progressive one.

    Wide setups (width slider 4-5) actively look for the cross-field shift
    when the near side is congested.
    """
    rng = rng or random
    if not lanes:
        return None

    goal_x = float(field.width) if att_side == 'home' else 0.0
    weights = []
    for lane in lanes:
        recv = lane['receiver']
        progress = (goal_x - recv.x) - (goal_x - carrier.x)
        progress = -progress / max(field.width, 1)  # + = toward goal, roughly -1..1
        w = 0.35 + lane['openness'] * 1.1 + max(-0.25, min(0.6, progress * 0.9))
        w *= {'FWD': 1.15, 'MID': 1.0, 'DEF': 0.75}.get(recv.role, 0.9)
        if is_switch(lane, field):
            # Switching is deliberate: attractive when instructed to play
            # wide, or when everything short is shaded.
            local_shade = 1.0 - lane['openness']
            switch_appeal = 0.55 + (width_pref - 3) * 0.28
            w *= max(0.35, switch_appeal - local_shade * 0.2)
        weights.append(max(0.05, w))

    return rng.choices(lanes, weights=weights, k=1)[0]


def pick_interceptor(lane):
    """The defender best placed AND best wired to read this pass."""
    best, best_score = None, 0.0
    for b in lane['blockers']:
        d = b['defender']
        read = (d.interceptions * 0.6 + d.def_awareness * 0.4) / 100.0
        score = b['closeness'] * (0.55 + read * 0.45)
        if score > best_score:
            best, best_score = b['defender'], score
    return best


def _lane_point(carrier, lane, t):
    """Point on the lane segment at fraction t (0=carrier, 1=receiver)."""
    recv = lane['receiver']
    return (carrier.x + (recv.x - carrier.x) * t,
            carrier.y + (recv.y - carrier.y) * t)


def resolve_pass(carrier, lane, kind, att_mult, def_mult, rng=None, state=None):
    """Play the pass.

    Returns (result, interceptor, point):
      ('COMPLETE',    None,     None)
      ('INTERCEPTED', defender, (x, y))  — cut out ON the lane; the defender
                                           steps to the interception point
      ('INTERCEPTED', None,     (x, y))  — loose ball that dies mid-lane

    kind: 'short' | 'switch' | 'cross' — switches and crosses ride the
    repurposed long_passing attribute and carry more inherent risk.
    """
    rng = rng or random
    stat_name = 'short_passing' if kind == 'short' else 'long_passing'
    passer_val = _duel_value(carrier.get_effective_stat(stat_name, att_mult))

    interceptor = pick_interceptor(lane)

    # Unshaded lanes can still go astray on a bad touch, more so over distance.
    if interceptor is None:
        stray = 0.015 + max(0.0, lane['length'] - SHORT_SIGHT) * 0.004
        if kind != 'short':
            stray += 0.02
        stray *= 1.0 - (passer_val - 60.0) / 200.0  # better passers stray less
        if rng.random() < max(0.005, stray):
            # Overhit: the ball dies somewhere in the second half of the lane.
            return 'INTERCEPTED', None, _lane_point(carrier, lane, rng.uniform(0.55, 1.1))
        return 'COMPLETE', None, None

    # Contested lane: exposure (positioning) sets the baseline, then the
    # passer's technique duels the interceptor's reading of the play.
    exposure = 1.0 - lane['openness']
    read_val = _duel_value(
        interceptor.get_effective_stat('interceptions', def_mult) * 0.6
        + interceptor.get_effective_stat('def_awareness', def_mult) * 0.4
    )
    # Crosses are the hardest ball in the game: even a good delivery is a
    # 50/50 against a set marker, which is what keeps them a choice rather
    # than a cheat code past the break duel.
    risk_bonus = {'short': 0.0, 'switch': 6.0, 'cross': 20.0}.get(kind, 0.0)

    def_base = read_val * (0.55 + exposure * 0.48) + risk_bonus
    att_noise = rng.randint(0, 30)
    def_noise = rng.randint(0, 30)
    att_roll = passer_val + att_noise
    def_roll = def_base + def_noise

    _record_attribution(state, passer_val - def_base, att_noise - def_noise)
    if def_roll > att_roll:
        # The ball is cut out where the defender's body meets the lane:
        # he steps IN to the line rather than the ball warping to him.
        along = next((b['along'] for b in lane['blockers']
                      if b['defender'] is interceptor), 0.5)
        ix, iy = _lane_point(carrier, lane, along)
        interceptor.x, interceptor.y = ix, iy
        return 'INTERCEPTED', interceptor, (ix, iy)
    return 'COMPLETE', None, None
