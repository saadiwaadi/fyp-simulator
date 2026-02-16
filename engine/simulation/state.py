class MatchState:
    def __init__(self, home_team, away_team):
        # --- THE NEW 11v11 STRUCTURAL SLOTS ---
        # We preserve the 100.0 start and the Phases (4=Perfect, 0=Collapse)
        self.home_structure = {
            "overall": 100.0,
            "phase": 4,
            "def_line": 100.0, # Placeholder for 11v11
            "mid_line": 100.0, # Placeholder for 11v11
            "att_line": 100.0  # Placeholder for 11v11
        }
        self.away_structure = {
            "overall": 100.0,
            "phase": 4,
            "def_line": 100.0,
            "mid_line": 100.0,
            "att_line": 100.0
        }
        
        # The Data Sheet
        self.stats = {
            'home_score': 0, 'away_score': 0,
            'home_possession_count': 0, 'away_possession_count': 0, 
            'home_shots': 0, 'away_shots': 0,
            'home_on_target': 0, 'away_on_target': 0,
            'home_passes_attempted': 0, 'home_passes_completed': 0,
            'away_passes_attempted': 0, 'away_passes_completed': 0,
            'home_corners': 0, 'away_corners': 0,
            'home_fouls': 0, 'away_fouls': 0,
            'home_offsides': 0, 'away_offsides': 0,
            'home_integrity_final': 100, 'away_integrity_final': 100
        }

    def degrade_structure(self, team_side, raw_damage):
        """
        PRESERVED: SOFTENED NON-LINEAR DECAY
        Now targeting the 'overall' key in the structure dict.
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        current = struct["overall"]
        
        # YOUR CALIBRATED THRESHOLDS
        if current > 75:
            modifier = 0.6   # CONCRETE
        elif current > 50:
            modifier = 1.0   # WOOD
        elif current > 25:
            modifier = 1.3   # GLASS
        else:
            modifier = 1.6   # SAND
            
        final_damage = raw_damage * modifier
        struct["overall"] = max(0, struct["overall"] - final_damage)

    def get_structure_mult(self, team_side):
        """
        PRESERVED: 100% Structure = 1.0x stats. 0% = 0.6x stats.
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        val = struct["overall"]
        return 0.6 + (0.4 * (val / 100))

    def check_phase_shift(self, team_side, team_name):
        """
        PRESERVED: Narrative Alerts.
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        current_phase = struct["phase"]
        val = struct["overall"]
        
        new_phase = current_phase
        msg = None
        
        if val < 30 and current_phase > 0:
            new_phase = 0
            msg = f"☠️ [PHASE] {team_name.upper()}: STRUCTURAL COLLAPSE IMMINENT."
        elif val < 45 and current_phase > 1:
            new_phase = 1
            msg = f"🚨 [PHASE] {team_name}: Shape Unstable. Gaps everywhere."
        elif val < 60 and current_phase > 2:
            new_phase = 2
            msg = f"⚠️ [PHASE] {team_name}: Defensive line stretched."
        elif val < 75 and current_phase > 3:
            new_phase = 3
            msg = f"⚠️ [PHASE] {team_name}: Slight structural distortion."

        if new_phase != current_phase:
            struct["phase"] = new_phase
            return msg
        return None