import random

# ==========================================
# MECHANICS MODULE (v2.1 - Hybrid Tuned)
# ==========================================

def resolve_possession(carrier, defender, att_mult, def_mult):
    """
    PHASE 1: The Battle for Control.
    Uses "Press Resistance" trait to dampen high-pressure defenses.
    """
    # [v2.1] PRESS RESISTANCE LOGIC
    # If defender has a tactical boost (High Press > 1.0), 
    # a Press Resistant carrier dampens it.
    press_res = carrier.traits.get('press_resistance', 0.0)
    
    effective_def_mult = def_mult
    if def_mult > 1.0:
        # Reduces the enemy's boost by up to 50% based on resistance trait
        reduction = (def_mult - 1.0) * (press_res * 0.5)
        effective_def_mult = def_mult - reduction

    # 1. The Rolls (Preserved Additive Variance 0-20)
    pass_roll = carrier.get_effective_stat('short_passing', att_mult) + random.randint(0, 20)
    intercept_roll = defender.get_effective_stat('interceptions', effective_def_mult) + random.randint(0, 20)
    
    return pass_roll > intercept_roll


def resolve_tactical_break(carrier, defender, att_mult, def_mult):
    """
    PHASE 2: Breaking the Line.
    Uses "Discipline" trait to stabilize the defense.
    """
    # [v2.1] DISCIPLINE LOGIC
    # High discipline defenders get a flat bonus to their awareness check.
    discipline = defender.traits.get('discipline', 0.0)
    discipline_bonus = int(10 * discipline) # Up to +10 flat bonus

    tactical_val = carrier.get_effective_stat('vision', att_mult) + random.randint(0, 25)
    
    # Defender gets the Discipline Bonus added to their structural roll
    structural_val = defender.get_effective_stat('def_awareness', def_mult) + discipline_bonus + random.randint(0, 25)
    
    return tactical_val > structural_val


def calculate_damage(defender_stamina, structure_level, base_damage=3.0):
    """
    [v2.3 UPDATE] Environment-Aware Damage.
    Accepts 'base_damage' from the MatchEnvironment (4.0 for 5v5, 2.0 for 11v11).
    """
    # Start with the environment's base rule
    damage = base_damage

    # 1. Fatigue (The Primary Driver)
    if defender_stamina < 50:
        damage *= 1.25
    if defender_stamina < 30:
        damage *= 1.4  # Cumulative fatigue penalty

    # 2. Structure (The Soft Accelerator)
    if structure_level < 60:
        damage *= 1.1
    if structure_level < 40:
        damage *= 1.2

    return round(damage, 2)


def resolve_finish(striker, gk, att_mult, integrity_bonus, minute):
    """
    PHASE 3: THE FINISH (Merged v1.5 + v2.1)
    - Preserves your Asymmetric Stability & 25-min Dampener.
    - Adds "Chaos Thrives" trait.
    """
    
    # 1. Calculate Base Stats
    # [v2.1] CHAOS THRIVES: If the integrity bonus is high (>5), Chaos players get a boost.
    chaos_trait = striker.traits.get('chaos_thrives', 0.0)
    
    base_att_val = striker.finishing * att_mult
    
    if integrity_bonus > 5:
        base_att_val *= (1.0 + (chaos_trait * 0.15)) # The "Fox in the Box" bonus

    att_val = int(base_att_val)
    def_val = int(gk.composure)

    # 2. Apply Early Game Dampener (PRESERVED)
    final_bonus = integrity_bonus
    if minute < 25:
        final_bonus = int(integrity_bonus * 0.5)

    # 3. The Rolls (PRESERVED Asymmetric Stability)
    # Striker: ±18 variance
    # GK: -5 to +25 variance
    att_roll = att_val + final_bonus + random.randint(-18, 18)
    def_roll = def_val + random.randint(-5, 25)
    
    # 4. The Resolution (PRESERVED Thresholds)
    if att_roll > (def_roll + 10): 
        return 'GOAL'
    elif att_roll > def_roll: 
        return 'SAVE' 
    else:
        return 'MISS'