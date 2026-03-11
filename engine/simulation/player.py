# engine/simulation/player.py
# ============================================================
# PHASE C — STAMINA RHYTHM
#
# WHAT CHANGED FROM PHASE B:
#
# 1. FATIGUE CURVE — Intensity-Dependent Exponential Decay
#    Old: flat drain per minute
#    New: drain = base_drain * tempo_multiplier * (1 + current_stamina / 100)
#
#    This means:
#      High stamina player under high tempo → burns FAST (explosive early)
#      Low stamina player → self-limits naturally (crawl late)
#      Tempo input always matters — never neutralised completely
#
# 2. RECOVERY METHOD — recover_stamina(amount)
#    Hard ceiling: player can never recover past (base_stamina * 0.75)
#    Tired legs stay tired — no magical full resets.
#
#    Depth-scaled recovery:
#      effective_recovery = amount * (current_stamina / base_stamina + 0.3)
#    A player at 10/80 stamina recovers LESS efficiently than one at 50/80.
#    Deeply exhausted players get diminishing halftime returns.
#
# 3. LAST CARRIER TRACKING
#    self.last_carried added to SimPlayer.
#    Used by engine to prevent exploit loops in micro-regen:
#    Only regen if player was NOT the previous carrier.
# ============================================================

import random


class SimPlayer:
    def __init__(self, db_player):
        self.id   = db_player.id
        self.name = db_player.name
        self.role = db_player.role

        # --- SPATIAL DNA ---
        self.preferred_zone  = getattr(db_player, 'preferred_zone', 'C')
        self.zone_coverage   = self.assign_zone_coverage()

        # --- CORE STATS ---
        self.vision        = getattr(db_player, 'vision',        60)
        self.finishing     = getattr(db_player, 'finishing',     60)
        self.composure     = getattr(db_player, 'composure',     60)
        self.def_awareness = getattr(db_player, 'def_awareness', 60)
        self.short_passing = getattr(db_player, 'short_passing', 60)
        self.interceptions = getattr(db_player, 'interceptions', 60)
        self.stamina       = getattr(db_player, 'stamina',       70)

        # --- DYNAMIC STATE ---
        self.current_stamina = self.stamina
        # PHASE C: Track whether this player was the last carrier this minute.
        # Used by engine's micro-regen guard to prevent exploit loops.
        self.last_carried    = False

        # --- MATCH VOLATILITY ---
        self.match_form = random.uniform(-0.05, 0.05)

        # --- PERSONALITY LAYER ---
        self.traits = {
            "selfishness":     round(max(0, (self.finishing - self.short_passing) / 100), 2),
            "discipline":      round((self.def_awareness * 0.6 + self.stamina * 0.4) / 100, 2),
            "system_loyalty":  round((self.short_passing + self.vision) / 200, 2),
            "risk_appetite":   round(1.0 - (self.composure / 100), 2),
            "press_resistance":round((self.composure * 0.7 + self.short_passing * 0.3) / 100, 2),
            "work_rate":       round(self.stamina / 100, 2),
            "chaos_thrives":   round(max(0, (self.finishing - 70) / 100), 2) if self.finishing > 80 else 0.0
        }

        # --- TACTICAL FIT (pre-calculated for speed) ---
        self.tactical_fits = self.calculate_tactical_fits()

    # ============================================================
    # SPATIAL LOGIC
    # ============================================================

    def assign_zone_coverage(self):
        """
        Efficiency multiplier when playing in a given zone.
        MIDs are versatile (0.90 out of zone).
        GKs and FWDs are specialists (0.75 out of zone).
        DEFs are standard (0.85 out of zone).
        """
        zones    = ['L', 'C', 'R']
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

    # ============================================================
    # TACTICAL METHODS
    # ============================================================

    def calculate_tactical_fits(self):
        """Pre-calculates fit percentages for different manager tactics."""
        fit = {
            'Standard':       1.0,
            'High Press':     1.0,
            'Park the Bus':   1.0,
            'Tiki Taka':      1.0,
            'Counter Attack': 1.0,
        }

        # High Press: Needs stamina + interceptions
        if self.stamina > 80 and self.interceptions > 75:
            fit['High Press'] = 1.18
        elif self.stamina < 65:
            fit['High Press'] = 0.82

        # Tiki Taka: Needs vision + passing
        if self.short_passing > 85 and self.vision > 85:
            fit['Tiki Taka'] = 1.18
        elif self.short_passing < 70:
            fit['Tiki Taka'] = 0.82

        # Park the Bus: Needs defensive awareness
        if self.def_awareness > 80:
            fit['Park the Bus'] = 1.18
        elif self.composure < 60:
            fit['Park the Bus'] = 0.88

        return fit

    def get_tactical_fit(self, profile):
        return self.tactical_fits.get(profile.name, 1.0)

    # ============================================================
    # PHASE C: STAMINA DRAIN — Intensity-Dependent Curve
    # ============================================================

    def drain_stamina(self, base_burn=1.0):
        """
        PHASE C: Intensity-dependent exponential decay.

        Formula:
          drain = base_burn * work_rate_modifier * (1 + current_stamina / 100)

        Why this formula works:
          - High stamina (100) → multiplier of 2.0 — fast drain when fresh
          - Low stamina  (20)  → multiplier of 1.2 — self-limiting when tired
          - base_burn already encodes tempo/press intensity from engine
          - work_rate trait still modulates individual differences

        Effect in practice:
          - First 15 minutes of high tempo: explosive, fast depletion
          - After stamina drops below 40: curve flattens, game slows naturally
          - Tempo slider never becomes completely irrelevant (always in base_burn)
        """
        work_rate_mod = 0.7 + (0.3 * self.traits['work_rate'])

        # PHASE C: Intensity-dependent multiplier
        # (1 + current_stamina / 100) means high stamina = faster drain
        intensity_factor = 1.0 + (self.current_stamina / 100.0)

        final_burn = base_burn * work_rate_mod * intensity_factor
        self.current_stamina = max(0.0, self.current_stamina - final_burn)

    # ============================================================
    # PHASE C: STAMINA RECOVERY — Depth-Scaled with Hard Ceiling
    # ============================================================

    def recover_stamina(self, base_amount):
        """
        PHASE C: Halftime and micro-regen recovery.

        Two guardrails:

        1. CEILING: Player can never recover past (base_stamina * 0.75)
           A 90-stamina player's recovery ceiling is 67.5.
           Tired legs stay tired. No magical full resets.

        2. DEPTH-SCALED EFFICIENCY:
           effective_recovery = base_amount * (current_stamina / base_stamina + 0.3)
           A player at 10/80 stamina (12.5% left) gets:
             10/80 + 0.3 = 0.425 → they recover 42.5% of base_amount
           A player at 50/80 stamina (62.5% left) gets:
             50/80 + 0.3 = 0.925 → they recover 92.5% of base_amount

           Deeply exhausted players get diminishing halftime returns.
           This is the "tired legs stay tired" guarantee.
        """
        recovery_ceiling = self.stamina * 0.75

        # Don't bother if already above ceiling
        if self.current_stamina >= recovery_ceiling:
            return

        # Depth-scaled efficiency (exhausted = less efficient recovery)
        depth_factor     = (self.current_stamina / max(self.stamina, 1)) + 0.3
        depth_factor     = max(0.1, min(1.0, depth_factor))  # Clamp [0.1, 1.0]
        effective_amount = base_amount * depth_factor

        self.current_stamina = min(
            recovery_ceiling,
            self.current_stamina + effective_amount
        )

    # ============================================================
    # PERFORMANCE LOGIC
    # ============================================================

    def get_effective_stat(self, stat_name, structural_mult=1.0):
        """Applies match form and fatigue penalty to a raw stat."""
        base = getattr(self, stat_name, 60)
        base *= (1.0 + self.match_form)

        # Significant drop-off when exhausted
        if self.current_stamina < 30:
            base *= 0.7

        return int(base * structural_mult)