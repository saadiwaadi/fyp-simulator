# engine/simulation/tactics.py

class TacticalProfile:
    def __init__(self, name, att, def_aw, inter, stam, compactness=1.0, intensity=1.0, tempo=1.0):
        self.name = name
        
        # --- PHASE MODIFIERS (The v1.5 Numbers we are keeping) ---
        self.att_mult = att       # Replaces old 'att'
        self.def_mult = def_aw    # Replaces old 'def'
        self.int_mult = inter     # Replaces old 'int'
        self.stam_burn = stam     # Replaces old 'stam'
        
        # --- STRUCTURAL MODIFIERS (The 11v11 Future) ---
        self.line_compactness = compactness  
        self.press_intensity = intensity    
        self.transition_speed = tempo       

# ==========================================
# PRE-DEFINED PROFILES (Merged v1.5 Data)
# ==========================================
PROFILES = {
    'STANDARD': TacticalProfile(
        name='Standard', att=1.0, def_aw=1.0, inter=1.0, stam=1.0
    ),
    
    'HIGH_PRESS': TacticalProfile(
        name='High Press', 
        att=1.0, 
        def_aw=1.05, 
        inter=1.20, # Keeping your v1.5 Interception buff
        stam=1.35,  # Keeping your nerfed burn rate
        compactness=0.8, intensity=1.5, tempo=1.3
    ),
    
    'PARK_BUS': TacticalProfile(
        name='Park the Bus', 
        att=0.85, 
        def_aw=1.20, 
        inter=1.20, 
        stam=0.70,
        compactness=1.5, intensity=0.4, tempo=0.6
    ),
    
    'TIKI_TAKA': TacticalProfile(
        name='Tiki Taka', 
        att=1.15, 
        def_aw=0.90, 
        inter=0.90, 
        stam=1.10,
        compactness=1.2, intensity=1.0, tempo=0.8
    ),

    'ALL_OUT_ATT': TacticalProfile(
        name='All Out Attack',
        att=1.25,
        def_aw=0.70,
        inter=0.80,
        stam=1.20,
        compactness=0.6, intensity=1.6, tempo=1.5
    ),
    
    'COUNTER': TacticalProfile(
        name='Counter Attack', 
        att=1.10, 
        def_aw=1.10, 
        inter=1.05, 
        stam=0.90,
        compactness=1.1, intensity=0.7, tempo=1.6
    )
}

def get_tactical_profile(mode_name):
    """Safely fetch the profile object, defaulting to STANDARD."""
    return PROFILES.get(mode_name, PROFILES['STANDARD'])