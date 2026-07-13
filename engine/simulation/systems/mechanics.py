import random

from ..constants import EARLY_FINISH_FRACTION


def _record_attribution(state, stat_component, rand_component):
    """Accumulate how much of a contested roll's margin came from stats vs dice.

    Feeds the analyst's system-vs-variance attribution with a real measurement
    instead of the old fixed-increment placeholder (audit B7).
    """
    if state is None:
        return
    denominator = abs(stat_component) + abs(rand_component)
    if denominator == 0:
        return
    state.stats['system_influence'] += abs(stat_component) / denominator
    state.stats['random_influence'] += abs(rand_component) / denominator


def _duel_value(stat):
    """Compress raw ratings into duel values with diminishing returns, so a
    +10 rating edge tilts duels instead of deciding them. This is the lever
    that lets tactics/structure compete with raw player quality (audit C)."""
    return 60.0 + (stat - 60.0) * 0.40


def resolve_possession(carrier, defender, att_mult, def_mult, rng=None, state=None):
    rng = rng or random
    press_res = carrier.traits.get('press_resistance', 0.0)

    effective_def_mult = def_mult
    if def_mult > 1.0:
        reduction = (def_mult - 1.0) * (press_res * 0.5)
        effective_def_mult = def_mult - reduction

    att_stat = _duel_value(carrier.get_effective_stat('short_passing', att_mult))
    # Blend the defensive read: pure interceptions let one attribute swing
    # team pass completion by ~18 points (probe section 2), which made the
    # first duel excessively stats-driven. Awareness carries part of it now,
    # and the positional lane/tackle mechanics carry the rest of the press.
    def_read = (defender.get_effective_stat('interceptions', effective_def_mult) * 0.6
                + defender.get_effective_stat('def_awareness', effective_def_mult) * 0.4)
    def_stat = _duel_value(def_read)
    att_noise = rng.randint(0, 28)
    def_noise = rng.randint(0, 28)

    _record_attribution(state, att_stat - def_stat, att_noise - def_noise)
    return (att_stat + att_noise) > (def_stat + def_noise)


def resolve_tactical_break(carrier, defender, att_mult, def_mult, rng=None, state=None):
    rng = rng or random
    discipline = defender.traits.get('discipline', 0.0)
    discipline_bonus = int(10 * discipline)

    att_stat = _duel_value(carrier.get_effective_stat('vision', att_mult))
    def_stat = _duel_value(defender.get_effective_stat('def_awareness', def_mult)) + discipline_bonus
    att_noise = rng.randint(0, 32)
    def_noise = rng.randint(0, 32)

    _record_attribution(state, att_stat - def_stat, att_noise - def_noise)
    return (att_stat + att_noise) > (def_stat + def_noise)


def calculate_damage(defender_stamina, zone_health, base_damage=3.0):
    damage = base_damage

    if defender_stamina < 50:
        damage *= 1.25
    if defender_stamina < 30:
        damage *= 1.40

    if zone_health < 60:
        damage *= 1.10
    if zone_health < 40:
        damage *= 1.20

    return round(damage, 2)


# Margin the attacker's roll must clear over the keeper's for a goal; anything
# within GOAL_MARGIN..-SAVE_WINDOW of the keeper is a save, below is a miss.
GOAL_MARGIN = 8
SAVE_WINDOW = 8


def resolve_tackle(carrier, defender, att_mult, def_mult, pressure, rng=None, state=None):
    """Defender dives in to win the ball off the carrier's feet.

    Deliberately position-first: the defender's proximity (pressure 0..1)
    is worth as much as his ratings, so a well-placed average tackler beats
    a misplaced great one. Stats enter through the compressed duel curve
    (tackling vs the carrier's close control) and stay damped so the duel
    never becomes a pure ratings printout.
    """
    rng = rng or random

    # Carrier shields with close control first, nerve and touch behind it.
    control = (carrier.get_effective_stat('dribbling', att_mult) * 0.5
               + carrier.get_effective_stat('composure', att_mult) * 0.3
               + carrier.get_effective_stat('short_passing', att_mult) * 0.2)
    tackle = (defender.get_effective_stat('tackling', def_mult) * 0.7
              + defender.get_effective_stat('def_awareness', def_mult) * 0.3)

    # Press resistance is the anti-tackle trait: it widens the shield AND
    # blunts the value of the defender's proximity, so pressing a
    # press-resistant carrier is a losing game unless the tackler is
    # genuinely better positioned and better rated.
    press_res = carrier.traits.get('press_resistance', 0.0)

    # The carrier holds a small shield-edge (body between man and ball), the
    # defender buys it back with positioning. Even duels land near 40-45% for
    # the tackler, so diving in stays a real choice rather than a free win.
    att_stat = _duel_value(control) + 3.0 + press_res * 10.0
    def_stat = _duel_value(tackle) + pressure * 11.0 * (1.0 - press_res * 0.5)
    att_noise = rng.randint(0, 30)
    def_noise = rng.randint(0, 30)

    _record_attribution(state, att_stat - def_stat, att_noise - def_noise)
    return (def_stat + def_noise) > (att_stat + att_noise)


# Shot types: which attributes carry the strike, and how much harder it is
# to score than a clean placed finish. Drives ride the repurposed `shooting`
# (shot power) field; headers ride the real `heading` stat and remain the
# toughest chance in the game.
SHOT_TYPES = {
    #            finishing, shooting, composure, difficulty
    'finesse': (0.80, 0.00, 0.20, 0.0),
    'drive':   (0.30, 0.70, 0.00, 3.0),
    'header':  (0.35, 0.10, 0.00, 6.0),   # + heading 0.55, see below
}
HEADER_HEADING_WEIGHT = 0.55

# How the keeper meets each shot: reflexes stop placed finishes, handling
# holds the drilled ones, aerial command owns everything in the air.
GK_SHOT_BLEND = {
    'finesse': (('gk_reflexes', 0.60), ('composure', 0.25), ('gk_handling', 0.15)),
    'drive':   (('gk_handling', 0.45), ('gk_reflexes', 0.40), ('composure', 0.15)),
    'header':  (('gk_aerials', 0.50), ('gk_reflexes', 0.35), ('composure', 0.15)),
}


def resolve_finish(striker, gk, att_mult, integrity_bonus, minute_frac, rng=None, state=None,
                   shot_type='finesse'):
    rng = rng or random
    chaos_trait = striker.traits.get('chaos_thrives', 0.0)
    fin_w, sho_w, com_w, difficulty = SHOT_TYPES.get(shot_type, SHOT_TYPES['finesse'])
    # Effective stat keeps the finish consistent with every other duel:
    # match form, confidence, and fatigue all reach the shooter and keeper
    # (previously raw ratings - audit follow-up).
    base_att_val = (striker.get_effective_stat('finishing', att_mult) * fin_w
                    + striker.get_effective_stat('shooting', att_mult) * sho_w
                    + striker.get_effective_stat('composure', att_mult) * com_w)
    if shot_type == 'header':
        base_att_val += striker.get_effective_stat('heading', att_mult) * HEADER_HEADING_WEIGHT
    base_att_val -= difficulty

    if integrity_bonus > 5:
        base_att_val *= 1.0 + (chaos_trait * 0.15)

    att_val = _duel_value(base_att_val)
    gk_blend = GK_SHOT_BLEND.get(shot_type, GK_SHOT_BLEND['finesse'])
    gk_read = sum(gk.get_effective_stat(stat) * w for stat, w in gk_blend)
    def_val = _duel_value(float(gk_read)) * 1.05

    final_bonus = integrity_bonus
    if minute_frac < EARLY_FINISH_FRACTION:
        final_bonus *= 0.6

    att_noise = rng.randint(-18, 18)
    def_noise = rng.randint(-18, 18)
    _record_attribution(state, (att_val + final_bonus) - def_val, att_noise - def_noise)

    att_roll = att_val + final_bonus + att_noise
    def_roll = def_val + def_noise

    if att_roll > (def_roll + GOAL_MARGIN):
        return 'GOAL'
    if att_roll > (def_roll - SAVE_WINDOW):
        return 'SAVE'
    return 'MISS'
