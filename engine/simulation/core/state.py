from .field import Field
from ..entities.ball import Ball


class GameState:
    def __init__(self, home_team, away_team, field_config=None):
        self.home_team = home_team
        self.away_team = away_team
        self.field = Field(field_config or {})
        self.ball = Ball(self.field.width / 2.0, self.field.height / 2.0)
        self.home_structure = self._init_structure()
        self.away_structure = self._init_structure()

        zone_names = self.field.zone_names

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
            'home_integrity_final': 100,
            'away_integrity_final': 100,
            'home_zone_finals': {zone: 100 for zone in zone_names},
            'away_zone_finals': {zone: 100 for zone in zone_names},
        }

    def _init_structure(self):
        zone_names = self.field.zone_names
        return {
            'zones': {zone: 100.0 for zone in zone_names},
            'overall': 100.0,
            'phase': 4,
            'def_line': 100.0,
            'mid_line': 100.0,
            'att_line': 100.0,
        }

    def _update_overall(self, struct):
        z = struct['zones']
        struct['overall'] = round(
            (z['Center'] * 0.50) + (z['Left'] * 0.25) + (z['Right'] * 0.25),
            2,
        )

    def degrade_structure(self, team_side, raw_damage, zone='Center'):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        zones = struct['zones']
        zone_names = self.field.zone_names

        if zone not in zones:
            zone = 'Center'

        adjacent_map = {
            'Left': ['Center'],
            'Center': ['Left', 'Right'],
            'Right': ['Center'],
        }
        adjacent_map = {k: [adj for adj in v if adj in zone_names] for k, v in adjacent_map.items() if k in zone_names}

        def _apply_to_zone(z_name, dmg):
            current = zones[z_name]
            if current > 75:
                modifier = 0.6
            elif current > 50:
                modifier = 1.0
            elif current > 25:
                modifier = 1.3
            else:
                modifier = 1.6
            zones[z_name] = max(0.0, round(current - (dmg * modifier), 2))

        _apply_to_zone(zone, raw_damage * 0.70)
        for adj in adjacent_map.get(zone, []):
            _apply_to_zone(adj, raw_damage * 0.15)

        self._update_overall(struct)

    def regen_structure(self, team_side, amount, zone=None, floor=40):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        zones = struct['zones']

        if zone and zone in zones:
            zones[zone] = max(floor, min(100.0, zones[zone] + amount))
        else:
            spread = amount / 3.0
            for z in zones:
                zones[z] = max(floor, min(100.0, zones[z] + spread))

        self._update_overall(struct)

    def get_structure_mult(self, team_side, zone=None):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        if zone and zone in struct['zones']:
            val = struct['zones'][zone]
        else:
            val = struct['overall']
        return 0.6 + (0.4 * (val / 100.0))

    # Compatibility for legacy callers from old 5v5 implementation.
    def degrade_integrity(self, team_side, raw_damage):
        self.degrade_structure(team_side, raw_damage, zone='Center')

    def get_integrity_mult(self, team_side):
        return self.get_structure_mult(team_side)

    @property
    def home_integrity(self):
        return self.home_structure['overall']

    @home_integrity.setter
    def home_integrity(self, value):
        for z in self.home_structure['zones']:
            self.home_structure['zones'][z] = float(value)
        self._update_overall(self.home_structure)

    @property
    def away_integrity(self):
        return self.away_structure['overall']

    @away_integrity.setter
    def away_integrity(self, value):
        for z in self.away_structure['zones']:
            self.away_structure['zones'][z] = float(value)
        self._update_overall(self.away_structure)

    @property
    def home_phase(self):
        return self.home_structure['phase']

    @home_phase.setter
    def home_phase(self, value):
        self.home_structure['phase'] = int(value)

    @property
    def away_phase(self):
        return self.away_structure['phase']

    @away_phase.setter
    def away_phase(self, value):
        self.away_structure['phase'] = int(value)

    def check_phase_shift(self, team_side, team_name):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        current_phase = struct['phase']
        val = struct['overall']

        new_phase = current_phase
        msg = None

        if val < 30 and current_phase > 0:
            new_phase = 0
            msg = f"☠️  [PHASE] {team_name.upper()}: STRUCTURAL COLLAPSE IMMINENT."
        elif val < 45 and current_phase > 1:
            new_phase = 1
            msg = f"🚨 [PHASE] {team_name}: Shape Unstable. Gaps everywhere."
        elif val < 60 and current_phase > 2:
            new_phase = 2
            msg = f"⚠️  [PHASE] {team_name}: Defensive line stretched."
        elif val < 75 and current_phase > 3:
            new_phase = 3
            msg = f"⚠️  [PHASE] {team_name}: Slight structural distortion."

        if new_phase != current_phase:
            struct['phase'] = new_phase
            return msg
        return None

    def get_zone_snapshot(self, team_side):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        return {z: int(v) for z, v in struct['zones'].items()}

    def get_weakest_zone(self, team_side):
        struct = self.home_structure if team_side == 'home' else self.away_structure
        return min(struct['zones'], key=lambda z: struct['zones'][z])

    def reset_ball(self, owner=None):
        self.ball.x = self.field.width / 2.0
        self.ball.y = self.field.height / 2.0
        self.ball.z = 0
        self.ball.vx = 0
        self.ball.vy = 0
        self.ball.vz = 0
        self.ball.owner = owner

    def update_ball(self):
        self.ball.update()


MatchState = GameState
