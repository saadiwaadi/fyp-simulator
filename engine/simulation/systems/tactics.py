class TacticalProfile:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"TacticalProfile({self.name!r})"


_PROFILES = {
    'Standard': TacticalProfile('Standard'),
    'High Press': TacticalProfile('High Press'),
    'Park the Bus': TacticalProfile('Park the Bus'),
    'Tiki Taka': TacticalProfile('Tiki Taka'),
    'Counter Attack': TacticalProfile('Counter Attack'),
}
_DEFAULT_PROFILE = _PROFILES['Standard']


def get_tactical_profile(mode_string):
    return _PROFILES.get(mode_string, _DEFAULT_PROFILE)


TACTICAL_MODIFIERS = {
    'STANDARD': {'att': 1.0, 'def': 1.0, 'int': 1.0, 'stam': 1.0},
    'HIGH_PRESS': {'att': 1.0, 'def': 1.05, 'int': 1.20, 'stam': 1.35},
    'ALL_OUT_ATT': {'att': 1.25, 'def': 0.7, 'int': 0.8, 'stam': 1.2},
    'PARK_BUS': {'att': 0.85, 'def': 1.20, 'int': 1.20, 'stam': 0.7},
    'COUNTER': {'att': 1.0, 'def': 1.1, 'int': 1.05, 'stam': 0.9},
    'TIKI_TAKA': {'att': 1.15, 'def': 0.9, 'int': 0.9, 'stam': 1.1},
}


_PROFILE_TO_MODIFIER_KEY = {
    'Standard': 'STANDARD',
    'High Press': 'HIGH_PRESS',
    'Park the Bus': 'PARK_BUS',
    'Tiki Taka': 'TIKI_TAKA',
    'Counter Attack': 'COUNTER',
}


def get_tactical_mods(mode):
    key = _PROFILE_TO_MODIFIER_KEY.get(mode, mode)
    return TACTICAL_MODIFIERS.get(key, TACTICAL_MODIFIERS['STANDARD'])


def calc_width_advantage(att_side, zone_key, stats):
    if zone_key == 'Center':
        return 1.0

    att_width = stats['h_width'] if att_side == 'home' else stats['a_width']
    def_depth = stats['a_depth'] if att_side == 'home' else stats['h_depth']
    def_width = stats['a_width'] if att_side == 'home' else stats['h_width']

    advantage = 1.0

    if att_width >= 4 and def_depth <= 2:
        advantage += 0.12
    elif att_width >= 4 and def_depth == 3:
        advantage += 0.06
    elif att_width >= 4 and def_depth >= 4:
        advantage -= 0.05

    if att_width >= 4 and def_width <= 2:
        advantage += 0.08
    elif att_width >= 4 and def_width >= 4:
        advantage -= 0.03

    return max(0.88, min(1.20, advantage))
