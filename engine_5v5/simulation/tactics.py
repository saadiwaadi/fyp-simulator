# engine/simulation/tactics.py

# ==========================================
# TACTICAL CONFIGURATION MATRIX (v1.5 Granular)
# ==========================================
# att:  Attack Multiplier (Vision / Passing)
# def:  Defense Multiplier (Defensive Awareness - Phase 2 Stability)
# int:  Interception Multiplier (Ball Winning - Phase 1 Chaos)
# stam: Stamina Burn Rate (1.0 = Normal)

TACTICAL_MODIFIERS = {
    'STANDARD':   {'att': 1.0,  'def': 1.0,  'int': 1.0,  'stam': 1.0},
    
    # AGGRESSIVE TACTICS
    'HIGH_PRESS': {
        'att': 1.0, 
        'def': 1.05, # Vulnerable if line is broken
        'int': 1.20, # ELITE at stealing the ball (Phase 1)
        'stam': 1.35 # Nerfed from 1.5 to 1.35
    }, 
    'ALL_OUT_ATT':{
        'att': 1.25, 
        'def': 0.7, 
        'int': 0.8,  # Risky
        'stam': 1.2
    },

    # DEFENSIVE TACTICS
    'PARK_BUS':   {
        'att': 0.85, 
        'def': 1.20, # Hard to break down (Phase 2)
        'int': 1.20, # Hard to pass through (Phase 1)
        'stam': 0.7
    },
    'COUNTER':    {
        'att': 1.0, 
        'def': 1.1, 
        'int': 1.05, 
        'stam': 0.9
    },
    
    # TECHNICAL TACTICS
    'TIKI_TAKA':  {
        'att': 1.15, 
        'def': 0.9, 
        'int': 0.9,  # Soft defensively
        'stam': 1.1
    },
}

def get_tactical_mods(mode):
    """Safely fetch modifiers, defaulting to STANDARD if mode is missing."""
    return TACTICAL_MODIFIERS.get(mode, TACTICAL_MODIFIERS['STANDARD'])