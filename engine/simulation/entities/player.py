import random


class SimPlayer:
    def __init__(self, db_player, rng=None):
        rng = rng or random
        self.id = db_player.id
        self.name = db_player.name
        self.role = db_player.role

        self.preferred_zone = getattr(db_player, 'preferred_zone', 'C')
        self.zone_coverage = self.assign_zone_coverage()

        self.x = float(getattr(db_player, 'x', 0) or 0)
        self.y = float(getattr(db_player, 'y', 0) or 0)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = getattr(db_player, 'speed', 60)

        self.vision = getattr(db_player, 'vision', 60)
        self.finishing = getattr(db_player, 'finishing', 60)
        self.composure = getattr(db_player, 'composure', 60)
        self.def_awareness = getattr(db_player, 'def_awareness', 60)
        self.short_passing = getattr(db_player, 'short_passing', 60)
        self.interceptions = getattr(db_player, 'interceptions', 60)
        self.stamina = getattr(db_player, 'stamina', 70)

        # Repurposed legacy fields (roadmap Phase 7, Option A):
        #  - `passing` becomes long passing: switches of play and crosses.
        #  - `defense` becomes tackling: winning the ball in the duel itself.
        # Teams created before these were populated fall back to a blend of
        # the modern stats so old squads keep playing sensibly.
        raw_long = getattr(db_player, 'passing', 0) or 0
        self.long_passing = raw_long if raw_long > 30 else int((self.short_passing + self.vision) / 2)
        raw_tackle = getattr(db_player, 'defense', 0) or 0
        self.tackling = raw_tackle if raw_tackle > 30 else int((self.def_awareness + self.interceptions) / 2)

        self.current_stamina = self.stamina
        self.last_carried = False
        self.match_form = rng.uniform(-0.05, 0.05)

        # Confidence: a live, event-driven morale value. Starts near neutral
        # (shaded by match form), rises with completed passes/tackles/goals,
        # falls with turnovers/misses/being beaten, and always eases back
        # toward neutral. Its stat effect is deliberately small (±6% at the
        # extremes) so momentum colours duels without deciding them.
        self.confidence = 0.5 + self.match_form

        self.traits = {
            'selfishness': round(max(0, (self.finishing - self.short_passing) / 100), 2),
            'discipline': round((self.def_awareness * 0.6 + self.stamina * 0.4) / 100, 2),
            'system_loyalty': round((self.short_passing + self.vision) / 200, 2),
            'risk_appetite': round(1.0 - (self.composure / 100), 2),
            'press_resistance': round((self.composure * 0.7 + self.short_passing * 0.3) / 100, 2),
            'work_rate': round(self.stamina / 100, 2),
            # Smooth curve from 65 finishing upward; the old hard cliff at 80
            # made scoring a monopoly of the single best finisher (audit C5).
            'chaos_thrives': round(max(0.0, (self.finishing - 65) / 150), 2),
        }

        # Pace comes from the SPEED attribute (audit: it previously derived
        # from stamina, leaving the speed rating with zero effect on motion).
        # Range ~1.0 (40 pace) to ~1.5 (100 pace) keeps leash dynamics intact.
        self.move_speed = 0.7 + (max(40, min(100, self.speed)) / 100.0) * 0.8
        # Quickness 0..1: how sharply a player accelerates and turns.
        self.quickness = max(0.0, min(1.0, (self.speed - 40) / 50.0))

        self.tactical_fits = self.calculate_tactical_fits()

    def assign_zone_coverage(self):
        zones = ['L', 'C', 'R']
        coverage = {}
        for z in zones:
            pz_char = self.preferred_zone[0].upper() if self.preferred_zone else 'C'
            if z == pz_char:
                coverage[z] = 1.0
            else:
                if self.role == 'MID':
                    coverage[z] = 0.90
                elif self.role in ['GK', 'FWD']:
                    coverage[z] = 0.75
                else:
                    coverage[z] = 0.85
        return coverage

    def calculate_tactical_fits(self):
        fit = {
            'Standard': 1.0,
            'High Press': 1.0,
            'Park the Bus': 1.0,
            'Tiki Taka': 1.0,
            'Counter Attack': 1.0,
        }

        # Fit multipliers are deliberately mild (±10%): they apply to every
        # duel and compound across a match, so wider ranges turn a stylistic
        # mismatch into an auto-loss (verified by the motion/fit probe).
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
            fit['Park the Bus'] = 0.94

        return fit

    def get_tactical_fit(self, profile):
        return self.tactical_fits.get(profile.name, 1.0)

    def drain_stamina(self, base_burn=1.0):
        # Fitter players burn slightly LESS per action (the previous factors
        # made high-stamina players burn more, cancelling their advantage -
        # audit C6). Range: 1.1x at work_rate 0 down to 0.9x at work_rate 1.
        efficiency = 1.1 - (0.2 * self.traits['work_rate'])
        self.current_stamina = max(0.0, self.current_stamina - base_burn * efficiency)

    def recover_stamina(self, base_amount):
        recovery_ceiling = self.stamina * 0.75
        if self.current_stamina >= recovery_ceiling:
            return

        depth_factor = (self.current_stamina / max(self.stamina, 1)) + 0.3
        depth_factor = max(0.1, min(1.0, depth_factor))
        effective_amount = base_amount * depth_factor

        self.current_stamina = min(
            recovery_ceiling,
            self.current_stamina + effective_amount,
        )

    def boost_confidence(self, amount):
        self.confidence = min(0.95, self.confidence + amount)

    def sap_confidence(self, amount):
        self.confidence = max(0.05, self.confidence - amount)

    def settle_confidence(self, rate=0.02):
        """Ease confidence back toward neutral between events."""
        self.confidence += (0.5 - self.confidence) * rate

    def get_effective_stat(self, stat_name, structural_mult=1.0):
        base = getattr(self, stat_name, 60)
        base *= (1.0 + self.match_form)
        # Confidence shades output by at most ±6% at the extremes.
        base *= 0.94 + self.confidence * 0.12
        # Gradual decay below 50 stamina instead of a cliff at 30.
        if self.current_stamina < 50:
            base *= 0.7 + 0.3 * (self.current_stamina / 50.0)
        return int(base * structural_mult)
