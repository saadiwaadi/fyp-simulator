# engine/simulation/environment.py

class MatchEnvironment:
    """
    Defines the 'Physics' of the match.
    Allows the same engine to run 5v5 (Volatile) and 11v11 (Stable).
    """
    def __init__(self, name, squad_size, base_damage, fatigue_scale, shot_density):
        self.name = name
        self.squad_size = squad_size
        
        # Structure: How much damage a break deals (5v5 is fragile, 11v11 is robust)
        self.base_damage = base_damage
        
        # Stamina: How fast players tire (5v5 is sprinting, 11v11 is pacing)
        self.fatigue_scale = fatigue_scale
        
        # Shooting: Modifier for shot frequency (5v5 is a shootout, 11v11 is tactical)
        self.shot_density = shot_density

# --- PRESETS ---

FIVE_V_FIVE = MatchEnvironment(
    name="5v5",
    squad_size=5,
    base_damage=4.0,   # Breaks deal massive damage
    fatigue_scale=1.2, # Players tire fast
    shot_density=1.2   # Lots of shots
)

ELEVEN_V_ELEVEN = MatchEnvironment(
    name="11v11",
    squad_size=11,
    base_damage=2.0,   # Breaks deal minimal damage (more cover)
    fatigue_scale=0.8, # Players tire slower
    shot_density=0.8   # Fewer clear cut chances
)

def get_environment(mode_name):
    """
    Factory function to fetch the correct physics package.
    """
    if mode_name == "11v11":
        return ELEVEN_V_ELEVEN
    return FIVE_V_FIVE # Default to 5v5