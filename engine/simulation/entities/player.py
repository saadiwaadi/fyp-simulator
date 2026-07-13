import random

# System-fit magnitude: suited players get 1+FIT_BONUS on every duel in that
# system, misfits 1-FIT_BONUS. Module-level so the fit probe can sweep it
# (±5/10/15/20%) without editing this file; ±10% is the verified-safe value.
FIT_BONUS = 0.10


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
        # `shooting` becomes shot power: drives from range ride it, while
        # placed finishes stay on `finishing` (see mechanics.resolve_finish).
        raw_shooting = getattr(db_player, 'shooting', 0) or 0
        self.shooting = raw_shooting if raw_shooting > 30 else int((self.finishing + self.speed) / 2)

        # Specialist stats (league-level data). Zero/absent means the squad
        # predates them: derive a role-sensible stand-in so nothing breaks.
        raw_drb = getattr(db_player, 'dribbling', 0) or 0
        self.dribbling = raw_drb if raw_drb > 0 else int(
            self.short_passing * 0.45 + self.composure * 0.30 + self.speed * 0.25)
        raw_hed = getattr(db_player, 'heading', 0) or 0
        if raw_hed > 0:
            self.heading = raw_hed
        elif self.role == 'FWD':
            self.heading = int(self.finishing * 0.55 + self.composure * 0.20 + 20)
        elif self.role == 'DEF':
            self.heading = int(self.def_awareness * 0.50 + self.composure * 0.20 + 22)
        else:
            self.heading = int(self.finishing * 0.30 + self.def_awareness * 0.30 + 25)
        raw_mrk = getattr(db_player, 'marking', 0) or 0
        self.marking = raw_mrk if raw_mrk > 0 else int(
            self.def_awareness * 0.60 + self.interceptions * 0.30)

        # Goalkeeping triple: keepers without data fall back to composure,
        # which is exactly what saves used to run on.
        raw_ref = getattr(db_player, 'gk_reflexes', 0) or 0
        raw_han = getattr(db_player, 'gk_handling', 0) or 0
        raw_aer = getattr(db_player, 'gk_aerials', 0) or 0
        self.gk_reflexes = raw_ref if raw_ref > 0 else int(self.composure * 0.95 + 3)
        self.gk_handling = raw_han if raw_han > 0 else int(self.composure * 0.92)
        self.gk_aerials = raw_aer if raw_aer > 0 else int(self.composure * 0.90)

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
        # Range ~2.0 (40 pace) to ~3.0 (100 pace) units per sim-minute: fast
        # enough that a line genuinely steps up/drops inside one minute, so
        # the scenario shapes (attack/defend/counter) are visible on the
        # pitch instead of being eaten by slow convergence.
        self.move_speed = 1.4 + (max(40, min(100, self.speed)) / 100.0) * 1.6
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

        # Fit multipliers are deliberately mild (FIT_BONUS, ±10% by default):
        # they apply to every duel and compound across a match, so wider
        # ranges turn a stylistic mismatch into an auto-loss (verified by
        # the motion/fit probes).
        hi = 1.0 + FIT_BONUS
        lo = 1.0 - FIT_BONUS

        if self.stamina > 80 and self.interceptions > 75:
            fit['High Press'] = hi
        elif self.stamina < 65:
            fit['High Press'] = lo

        if self.short_passing > 85 and self.vision > 85:
            fit['Tiki Taka'] = hi
        elif self.short_passing < 70:
            fit['Tiki Taka'] = lo

        if self.def_awareness > 80:
            fit['Park the Bus'] = hi
        elif self.composure < 60:
            fit['Park the Bus'] = 1.0 - FIT_BONUS * 0.6

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
