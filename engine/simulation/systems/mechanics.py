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
    def_stat = _duel_value(defender.get_effective_stat('interceptions', effective_def_mult))
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

    # Carrier shields with a blend of close passing control and composure.
    control = (carrier.get_effective_stat('short_passing', att_mult) * 0.6
               + carrier.get_effective_stat('composure', att_mult) * 0.4)
    tackle = (defender.get_effective_stat('tackling', def_mult) * 0.7
              + defender.get_effective_stat('def_awareness', def_mult) * 0.3)

    # The carrier holds a small shield-edge (body between man and ball), the
    # defender buys it back with positioning. Even duels land near 45% for
    # the tackler, so diving in stays a real choice rather than a free win.
    att_stat = _duel_value(control) + 5.0
    def_stat = _duel_value(tackle) + pressure * 8.0
    att_noise = rng.randint(0, 30)
    def_noise = rng.randint(0, 30)

    _record_attribution(state, att_stat - def_stat, att_noise - def_noise)
    return (def_stat + def_noise) > (att_stat + att_noise)


def resolve_finish(striker, gk, att_mult, integrity_bonus, minute_frac, rng=None, state=None):
    rng = rng or random
    chaos_trait = striker.traits.get('chaos_thrives', 0.0)
    # Effective stat keeps the finish consistent with every other duel:
    # match form, confidence, and fatigue all reach the shooter and keeper
    # (previously raw ratings - audit follow-up).
    base_att_val = float(striker.get_effective_stat('finishing', att_mult))

    if integrity_bonus > 5:
        base_att_val *= 1.0 + (chaos_trait * 0.15)

    att_val = _duel_value(base_att_val)
    def_val = _duel_value(float(gk.get_effective_stat('composure'))) * 1.05

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
