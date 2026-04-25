import random


def resolve_possession(carrier, defender, att_mult, def_mult):
    press_res = carrier.traits.get('press_resistance', 0.0)

    effective_def_mult = def_mult
    if def_mult > 1.0:
        reduction = (def_mult - 1.0) * (press_res * 0.5)
        effective_def_mult = def_mult - reduction

    pass_roll = carrier.get_effective_stat('short_passing', att_mult) + random.randint(0, 20)
    intercept_roll = defender.get_effective_stat('interceptions', effective_def_mult) + random.randint(0, 20)

    return pass_roll > intercept_roll


def resolve_tactical_break(carrier, defender, att_mult, def_mult):
    discipline = defender.traits.get('discipline', 0.0)
    discipline_bonus = int(10 * discipline)

    tactical_val = carrier.get_effective_stat('vision', att_mult) + random.randint(0, 25)
    structural_val = defender.get_effective_stat('def_awareness', def_mult) + discipline_bonus + random.randint(0, 25)

    return tactical_val > structural_val


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


def resolve_finish(striker, gk, att_mult, integrity_bonus, minute):
    chaos_trait = striker.traits.get('chaos_thrives', 0.0)
    base_att_val = striker.finishing * att_mult

    if integrity_bonus > 5:
        base_att_val *= 1.0 + (chaos_trait * 0.15)

    att_val = int(base_att_val)
    def_val = int(gk.composure * 1.1)

    final_bonus = integrity_bonus * 0.5
    if minute < 25:
        final_bonus = int(final_bonus * 0.5)

    att_roll = att_val + final_bonus + random.randint(-20, 15)
    def_roll = def_val + random.randint(-10, 20)

    if att_roll > (def_roll + 12):
        return 'GOAL'
    if att_roll > (def_roll - 5):
        return 'SAVE'
    return 'MISS'
