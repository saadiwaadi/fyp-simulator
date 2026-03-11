# engine/simulation/tactics.py
# ============================================================
# TACTICS MODULE
#
# Owns two concerns:
#   1. Tactical profile lookup — maps team's tactical_mode string
#      to a TacticalProfile object used for player fit calculations.
#   2. Width advantage calculator — determines the spatial multiplier
#      a team gets when attacking down the flanks based on slider matchups.
#
# PUBLIC API
# ----------
# get_tactical_profile(mode_string)  -> TacticalProfile
#     Returns a TacticalProfile for the given mode name.
#     Falls back to Standard if name is unrecognised.
#
# calc_width_advantage(att_side, zone_key, stats)  -> float
#     Returns a multiplier [0.88, 1.20] for break_att.
#     Only applies to flank zones (Left/Right). Center always returns 1.0.
#     Driven by attacker's width slider vs defender's depth and width sliders.
# ============================================================


# ============================================================
# TACTICAL PROFILES
# ============================================================

class TacticalProfile:
    """
    Lightweight container for a tactical mode.
    The .name attribute is matched against SimPlayer.tactical_fits keys.

    Valid names (must match player.py calculate_tactical_fits keys):
      'Standard', 'High Press', 'Park the Bus', 'Tiki Taka', 'Counter Attack'
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"TacticalProfile({self.name!r})"


# Pre-built profile objects — avoid creating new objects every match minute
_PROFILES = {
    'Standard':       TacticalProfile('Standard'),
    'High Press':     TacticalProfile('High Press'),
    'Park the Bus':   TacticalProfile('Park the Bus'),
    'Tiki Taka':      TacticalProfile('Tiki Taka'),
    'Counter Attack': TacticalProfile('Counter Attack'),
}

_DEFAULT_PROFILE = _PROFILES['Standard']


def get_tactical_profile(mode_string):
    """
    Returns the TacticalProfile for a given tactical mode name.

    Parameters
    ----------
    mode_string : str — value of team.tactical_mode (e.g. 'High Press')

    Returns
    -------
    TacticalProfile — always returns something, falls back to Standard
    """
    return _PROFILES.get(mode_string, _DEFAULT_PROFILE)


# ============================================================
# WIDTH ADVANTAGE CALCULATOR
# Extracted from engine.py nested closure — now pure and testable.
# ============================================================

def calc_width_advantage(att_side, zone_key, stats):
    """
    Width-based spatial multiplier for break_att (Phase B).

    Only applies to flank zones. Central attacks gain no width advantage
    since width is a lateral stretch mechanic, not a central one.

    ADVANTAGE RULES:
      att_width >= 4 vs def_depth <= 2  → +0.12  (wide team exploits high line)
      att_width >= 4 vs def_depth == 3  → +0.06  (moderate exposure)
      att_width >= 4 vs def_depth >= 4  → -0.05  (deep block neutralises width)
      att_width >= 4 vs def_width <= 2  → +0.08  (narrow defence leaves flanks open)
      att_width >= 4 vs def_width >= 4  → -0.03  (defender mirrors the width)

    Result clamped to [0.88, 1.20].

    Parameters
    ----------
    att_side : str — 'home' or 'away'
    zone_key : str — 'Left', 'Center', or 'Right'
    stats    : dict — state.stats (reads h/a width, depth sliders)

    Returns
    -------
    float — multiplier to apply to break_att
    """
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