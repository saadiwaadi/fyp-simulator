import random

class SimPlayer:
    def __init__(self, db_player):
        self.name = db_player.name
        self.role = db_player.role
        
        # --- CORE STATS ---
        self.vision = getattr(db_player, 'vision', 60)
        self.finishing = getattr(db_player, 'finishing', 60)
        self.composure = getattr(db_player, 'composure', 60)
        self.def_awareness = getattr(db_player, 'def_awareness', 60)
        self.short_passing = getattr(db_player, 'short_passing', 60)
        self.interceptions = getattr(db_player, 'interceptions', 60)
        self.stamina = getattr(db_player, 'stamina', 70)
        
        # Dynamic State
        self.current_stamina = self.stamina

        # --- MATCH VOLATILITY ---
        self.match_form = random.uniform(-0.05, 0.05)

        # --- PERSONALITY LAYER ---
        self.traits = {
            "selfishness": round(max(0, (self.finishing - self.short_passing) / 100), 2),
            "discipline": round((self.def_awareness * 0.6 + self.stamina * 0.4) / 100, 2),
            "system_loyalty": round((self.short_passing + self.vision) / 200, 2),
            "risk_appetite": round(1.0 - (self.composure / 100), 2),
            "press_resistance": round((self.composure * 0.7 + self.short_passing * 0.3) / 100, 2),
            "work_rate": round(self.stamina / 100, 2),
            "chaos_thrives": round(max(0, (self.finishing - 70)/100), 2) if self.finishing > 80 else 0.0
        }

        # --- [v2.6] SPATIAL DNA ---
        # This determines where the player naturally belongs on the pitch.
        self.preferred_zone = self.assign_preferred_zone()
        # Coverage map: how well they play in L, C, R.
        self.zone_coverage = self.assign_zone_coverage()

        # --- TACTICAL FIT (Optimized) ---
        self.tactical_fits = self.calculate_tactical_fits()

    # --- NEW SPATIAL METHODS ---

    def assign_preferred_zone(self):
        """Assigns a primary zone (Left, Center, Right) based on role and a bit of randomness."""
        if self.role == 'GK': return 'C'
        if self.role == 'DEF': return random.choice(['L', 'C', 'C', 'R']) # Bias toward Center
        if self.role == 'MID': return random.choice(['L', 'C', 'R'])
        if self.role == 'FWD': return random.choice(['L', 'C', 'R'])
        return 'C'

    def assign_zone_coverage(self):
        """
        Determines the efficiency multiplier when in a specific zone.
        Midfielders are versatile (0.9 out of position), GKs and Wingers are specialists (0.75).
        """
        zones = ['L', 'C', 'R']
        coverage = {}
        for z in zones:
            if z == self.preferred_zone:
                coverage[z] = 1.0 # Full Power
            else:
                if self.role == 'MID': coverage[z] = 0.90 # High versatility
                elif self.role in ['GK', 'FWD']: coverage[z] = 0.75 # Specialist penalty
                else: coverage[z] = 0.85 # Standard (DEF)
        return coverage

    # --- EXISTING METHODS (UNTOUCHED) ---

    def calculate_tactical_fits(self):
        fit = {
            'Standard': 1.0,
            'High Press': 1.0,
            'Park the Bus': 1.0,
            'Tiki Taka': 1.0,
            'Counter Attack': 1.0
        }
        if self.stamina > 80 and self.interceptions > 75:
            fit['High Press'] = 1.10
        elif self.stamina < 65:
            fit['High Press'] = 0.90
        if self.short_passing > 85 and self.vision > 85:
            fit['Tiki Taka'] = 1.10
        elif self.short_passing < 70:
            fit['Tiki Taka'] = 0.90
        if self.def_awareness > 80:
            fit['Park the Bus'] = 1.10
        elif self.composure < 60:
            fit['Park the Bus'] = 0.95
        return fit

    def get_tactical_fit(self, profile):
        return self.tactical_fits.get(profile.name, 1.0)

    def drain_stamina(self, base_burn=1):
        burn_modifier = 0.7 + (0.3 * self.traits['work_rate'])
        final_burn = base_burn * burn_modifier
        self.current_stamina = max(0, self.current_stamina - final_burn)

    def get_effective_stat(self, stat_name, structural_mult=1.0):
        base = getattr(self, stat_name, 60)
        base *= (1.0 + self.match_form)
        if self.current_stamina < 30: 
            base *= 0.7 
        return int(base * structural_mult)