import random

def resolve_possession(carrier, defender, att_mult, def_mult):
    """
    STRUCTURAL SHIFT: Defending team's integrity mult (def_mult) 
    now heavily impacts their ability to intercept.
    """
    pass_roll = carrier.get_effective_stat('short_passing', att_mult) + random.randint(0, 20)
    # If def_mult is low (0.6), the defender is practically invisible
    intercept_roll = defender.get_effective_stat('interceptions', def_mult) + random.randint(0, 20)
    return pass_roll > intercept_roll

def resolve_tactical_break(carrier, defender, att_mult, def_mult):
    """
    STRUCTURAL SHIFT: Lower integrity makes the defender 'slow to react.'
    """
    tactical_val = carrier.get_effective_stat('vision', att_mult) + random.randint(0, 25)
    # Integrity now punishes reaction (def_awareness)
    structural_val = defender.get_effective_stat('def_awareness', def_mult) + random.randint(0, 25)
    return tactical_val > structural_val
# engine/simulation/mechanics.py

def calculate_damage(defender_stamina):
    """
    Damage scales based on defender exhaustion.
    Fresh defenders (Stamina 70+) = 3-5% damage.
    Exhausted defenders (Stamina < 20) = 8-12% damage.
    """
    base_damage = random.randint(3, 6)
    
    if defender_stamina < 25:
        return base_damage + random.randint(4, 7) # Massive collapse
    elif defender_stamina < 45:
        return base_damage + random.randint(1, 3) # Noticeable strain
        
    return base_damage

def resolve_finish(striker, gk, att_mult, integrity_bonus, minute): # <--- Added 'minute'
    """
    PHASE 4: THE FINISH (Rebalanced v1.5)
    - Reduced Variance: Less random blowouts.
    - GK Stability: Keepers are more consistent than Strikers.
    - Early Game Dampener: Harder to score big early.
    """
    
    # 1. Calculate Base Stats
    # Attacker gets the tactical multiplier
    att_val = int(striker.finishing * att_mult)
    def_val = int(gk.composure) # GKs usually don't get tactical buffs, they rely on skill
    
    # 2. Apply Early Game Dampener
    # If match is young (< 25 mins), structure is fresh. Bonus is halved.
    final_bonus = integrity_bonus
    if minute < 25:
        final_bonus = int(integrity_bonus * 0.5)

    # 3. The Rolls (Asymmetric Stability)
    # Strikers have variance (Form/Luck): ±18
    # GKs have stability (Positioning): -5 to +25 (They rarely fumble, often save)
    att_roll = att_val + final_bonus + random.randint(-18, 18)
    def_roll = def_val + random.randint(-5, 25)
    
    # 4. The Resolution
    if att_roll > (def_roll + 10): # Dominant finish
        return 'GOAL'
    elif att_roll > def_roll: # Narrow advantage (Saved but corner, or scraped by)
        return 'SAVE' 
    else:
        return 'MISS'