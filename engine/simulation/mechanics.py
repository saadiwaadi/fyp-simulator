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

def resolve_finish(striker, gk, att_mult, integrity_bonus):
    """
    NERFED: The bonus is now capped and smaller.
    """
    # Reduced multiplier for the bonus (e.g., / 3.0 instead of / 1.5)
    finish_roll = striker.get_effective_stat('finishing', att_mult) + (integrity_bonus / 2.0) + random.randint(0, 25)
    save_roll = gk.get_effective_stat('composure') + random.randint(10, 50)
    return finish_roll > save_roll