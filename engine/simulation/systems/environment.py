GAME_MODES = {
    '11v11': {
        'squad_size': 11,
        'base_damage': 3.5,
        'fatigue_scale': 0.8,
        'shot_density': 0.8,
        'stamina_drain': 0.8,
        'stamina_recovery': 0.3,
        'shot_frequency_modifier': 1.0,
        'match_duration': 5400,
        'pitch_size': (20, 13),
        'max_minutes': 90,
        'half_time_min': 45,
        'mismatch_scale': 0.04,
        'trailing_escalation_boost': 1.05,
        'width_zone_weights': {
            1: [0.55, 0.225, 0.225],
            2: [0.50, 0.25, 0.25],
            3: [0.40, 0.30, 0.30],
            4: [0.28, 0.36, 0.36],
            5: [0.18, 0.41, 0.41],
        },
    },
    '5v5': {
        'squad_size': 5,
        'base_damage': 6.0,
        'fatigue_scale': 1.2,
        'shot_density': 1.2,
        'stamina_drain': 1.4,
        'stamina_recovery': 0.8,
        'shot_frequency_modifier': 1.8,
        'match_duration': 2700,
        'pitch_size': (14, 9),
        'max_minutes': 40,
        'half_time_min': 20,
        'mismatch_scale': 0.07,
        'trailing_escalation_boost': 1.10,
        'width_zone_weights': {
            1: [0.65, 0.175, 0.175],
            2: [0.60, 0.20, 0.20],
            3: [0.50, 0.25, 0.25],
            4: [0.30, 0.35, 0.35],
            5: [0.20, 0.40, 0.40],
        },
    },
}


class MatchEnvironment:
    def __init__(self, name, config):
        self.name = name
        self.config = dict(config)
        self.squad_size = self.config['squad_size']
        self.base_damage = self.config['base_damage']
        self.fatigue_scale = self.config['fatigue_scale']
        self.shot_density = self.config['shot_density']
        self.stamina_drain = self.config['stamina_drain']
        self.stamina_recovery = self.config['stamina_recovery']
        self.shot_frequency_modifier = self.config['shot_frequency_modifier']
        self.match_duration = self.config['match_duration']
        self.pitch_size = self.config['pitch_size']
        self.max_minutes = self.config['max_minutes']
        self.half_time_min = self.config['half_time_min']
        self.mismatch_scale = self.config['mismatch_scale']
        self.trailing_escalation_boost = self.config['trailing_escalation_boost']
        self.width_zone_weights = self.config['width_zone_weights']


def get_environment(mode_name):
    mode_key = mode_name if mode_name in GAME_MODES else '5v5'
    return MatchEnvironment(mode_key, GAME_MODES[mode_key])


FIVE_V_FIVE = get_environment('5v5')
ELEVEN_V_ELEVEN = get_environment('11v11')
