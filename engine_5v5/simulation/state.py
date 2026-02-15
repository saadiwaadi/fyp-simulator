class MatchState:
    def __init__(self, home_team, away_team):
        self.home_integrity = 100.0
        self.away_integrity = 100.0
        
        # Story Phase (4=Perfect, 0=Collapse)
        self.home_phase = 4
        self.away_phase = 4
        
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

    def degrade_integrity(self, team_side, raw_damage):
        """
        SOFTENED NON-LINEAR DECAY:
        Fragility exists, but we've removed the 'Instant Implosion' at <25%.
        """
        current = self.home_integrity if team_side == 'home' else self.away_integrity
        
        # SOFTENED THRESHOLDS
        if current > 75:
            modifier = 0.6   # CONCRETE
        elif current > 50:
            modifier = 1.0   # WOOD
        elif current > 25:
            modifier = 1.3   # GLASS (Softened from 1.4)
        else:
            modifier = 1.6   # SAND (Softened from 2.0)
            
        final_damage = raw_damage * modifier
        
        if team_side == 'home': 
            self.home_integrity = max(0, self.home_integrity - final_damage)
        else: 
            self.away_integrity = max(0, self.away_integrity - final_damage)
    def get_integrity_mult(self, team_side):
        # 100% Integrity = 1.0x stats. 0% Integrity = 0.6x stats.
        integrity = self.home_integrity if team_side == 'home' else self.away_integrity
        return 0.6 + (0.4 * (integrity / 100))

    def check_phase_shift(self, team_side, team_name):
        """Checks thresholds and returns a narrative alert if a phase changes."""
        integrity = self.home_integrity if team_side == 'home' else self.away_integrity
        current_phase = self.home_phase if team_side == 'home' else self.away_phase
        
        new_phase = current_phase
        msg = None
        
        if integrity < 30 and current_phase > 0:
            new_phase = 0
            msg = f"☠️ [PHASE] {team_name.upper()}: STRUCTURAL COLLAPSE IMMINENT."
        elif integrity < 45 and current_phase > 1:
            new_phase = 1
            msg = f"🚨 [PHASE] {team_name}: Shape Unstable. Gaps everywhere."
        elif integrity < 60 and current_phase > 2:
            new_phase = 2
            msg = f"⚠️ [PHASE] {team_name}: Defensive line stretched."
        elif integrity < 75 and current_phase > 3:
            new_phase = 3
            msg = f"⚠️ [PHASE] {team_name}: Slight structural distortion."

        if new_phase != current_phase:
            if team_side == 'home': self.home_phase = new_phase
            else: self.away_phase = new_phase
            return msg
        return None