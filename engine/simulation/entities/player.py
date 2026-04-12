import random


class SimPlayer:
    def __init__(self, db_player):
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

        self.current_stamina = self.stamina
        self.last_carried = False
        self.match_form = random.uniform(-0.05, 0.05)

        self.traits = {
            'selfishness': round(max(0, (self.finishing - self.short_passing) / 100), 2),
            'discipline': round((self.def_awareness * 0.6 + self.stamina * 0.4) / 100, 2),
            'system_loyalty': round((self.short_passing + self.vision) / 200, 2),
            'risk_appetite': round(1.0 - (self.composure / 100), 2),
            'press_resistance': round((self.composure * 0.7 + self.short_passing * 0.3) / 100, 2),
            'work_rate': round(self.stamina / 100, 2),
            'chaos_thrives': round(max(0, (self.finishing - 70) / 100), 2) if self.finishing > 80 else 0.0,
        }

        self.move_speed = 1.0 + (self.traits['work_rate'] * 0.5)

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

        if self.stamina > 80 and self.interceptions > 75:
            fit['High Press'] = 1.18
        elif self.stamina < 65:
            fit['High Press'] = 0.82

        if self.short_passing > 85 and self.vision > 85:
            fit['Tiki Taka'] = 1.18
        elif self.short_passing < 70:
            fit['Tiki Taka'] = 0.82

        if self.def_awareness > 80:
            fit['Park the Bus'] = 1.18
        elif self.composure < 60:
            fit['Park the Bus'] = 0.88

        return fit

    def get_tactical_fit(self, profile):
        return self.tactical_fits.get(profile.name, 1.0)

    def drain_stamina(self, base_burn=1.0):
        work_rate_mod = 0.7 + (0.3 * self.traits['work_rate'])
        intensity_factor = 1.0 + (self.current_stamina / 100.0)
        final_burn = base_burn * work_rate_mod * intensity_factor
        self.current_stamina = max(0.0, self.current_stamina - final_burn)

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

    def get_effective_stat(self, stat_name, structural_mult=1.0):
        base = getattr(self, stat_name, 60)
        base *= (1.0 + self.match_form)
        if self.current_stamina < 30:
            base *= 0.7
        return int(base * structural_mult)
