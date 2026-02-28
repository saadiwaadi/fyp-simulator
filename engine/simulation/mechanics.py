# engine/simulation/mechanics.py
# ============================================================
# PHASE A CHANGES:
#   calculate_damage() — parameter renamed structure_level → zone_health
#   Semantically clearer: we now always pass the ZONE'S health, not global.
#   All other functions unchanged from V4.
# ============================================================

import random


def resolve_possession(carrier, defender, att_mult, def_mult):
    """
    PHASE 1: The Battle for Control.
    Uses press_resistance trait to dampen high-pressure defenses.

    Press resistance reduces the opponent's tactical boost by up to 50%.
    High composure + passing = harder to press off the ball.
    """
    press_res = carrier.traits.get('press_resistance', 0.0)

    effective_def_mult = def_mult
    if def_mult > 1.0:
        # Dampen the defensive boost proportional to carrier's press resistance
        reduction = (def_mult - 1.0) * (press_res * 0.5)
        effective_def_mult = def_mult - reduction

    # Rolls: passing stat + att multiplier + variance (0–20)
    pass_roll      = carrier.get_effective_stat('short_passing', att_mult) + random.randint(0, 20)
    intercept_roll = defender.get_effective_stat('interceptions', effective_def_mult) + random.randint(0, 20)

    return pass_roll > intercept_roll


def resolve_tactical_break(carrier, defender, att_mult, def_mult):
    """
    PHASE 2: Breaking the Line.
    Uses discipline trait to stabilize the defense.

    High discipline defenders get a flat bonus to their awareness check.
    Discipline = (def_awareness * 0.6 + stamina * 0.4) / 100
    Max discipline bonus = +10 flat.
    """
    discipline       = defender.traits.get('discipline', 0.0)
    discipline_bonus = int(10 * discipline)  # Up to +10 flat

    tactical_val  = carrier.get_effective_stat('vision', att_mult) + random.randint(0, 25)
    structural_val = defender.get_effective_stat('def_awareness', def_mult) + discipline_bonus + random.randint(0, 25)

    return tactical_val > structural_val


def calculate_damage(defender_stamina, zone_health, base_damage=3.0):
    """
    PHASE A UPDATE: Parameter renamed structure_level → zone_health.
    Now receives the SPECIFIC ZONE's health value, not the global overall.

    This means damage is calculated against how healthy that particular
    zone is — a tired Left flank is more exploitable than a fresh one.

    Environment-aware: base_damage comes from MatchEnvironment
      5v5  → 4.0 (fragile, explosive)
      11v11 → 2.0 (layered, resilient)

    FATIGUE IS THE PRIMARY DRIVER:
      Below 50 stamina: 1.25x damage
      Below 30 stamina: cumulative 1.4x on top
    ZONE HEALTH IS THE SOFT ACCELERATOR:
      Below 60: 1.1x
      Below 40: 1.2x cumulative
    """
    damage = base_damage

    # 1. Fatigue multipliers (primary)
    if defender_stamina < 50:
        damage *= 1.25
    if defender_stamina < 30:
        damage *= 1.40  # Cumulative — exhausted defenders fall apart

    # 2. Zone health multipliers (secondary)
    if zone_health < 60:
        damage *= 1.10
    if zone_health < 40:
        damage *= 1.20  # Cumulative — zone is already crumbling

    return round(damage, 2)


def resolve_finish(striker, gk, att_mult, integrity_bonus, minute):
    """
    PHASE 3: THE FINISH (V4 preserved, no changes in Phase A)

    Asymmetric variance design:
      Striker: ±18 (explosive, unpredictable)
      GK:      -5 to +25 (safe hands bias, rare blunders)

    Chaos Thrives trait: High-finishing players get a bonus
    when the defense is broken (integrity_bonus > 5).

    Early game dampener: Integrity bonus halved before minute 25.
    Prevents first-minute capitulations.

    RESOLUTION THRESHOLDS:
      att_roll > def_roll + 10 → GOAL   (clean finish)
      att_roll > def_roll      → SAVE   (keeper works)
      att_roll ≤ def_roll      → MISS   (off target)
    """
    chaos_trait  = striker.traits.get('chaos_thrives', 0.0)
    base_att_val = striker.finishing * att_mult

    # Chaos Thrives: fox-in-the-box bonus when defense is broken
    if integrity_bonus > 5:
        base_att_val *= (1.0 + (chaos_trait * 0.15))

    att_val = int(base_att_val)
    def_val = int(gk.composure)

    # Early game dampener (minute < 25)
    final_bonus = integrity_bonus
    if minute < 25:
        final_bonus = int(integrity_bonus * 0.5)

    # Asymmetric rolls (striker explosive, GK reliable)
    att_roll = att_val + final_bonus + random.randint(-18, 18)
    def_roll = def_val + random.randint(-5, 25)

    if att_roll > (def_roll + 10):
        return 'GOAL'
    elif att_roll > def_roll:
        return 'SAVE'
    else:
        return 'MISS'