def calc_burn_rates(stats, avg_h_stam, avg_a_stam):
    # Tired squads pay MORE per action (previously inverted: fresher squads
    # burned faster, cancelling fitness advantages - audit C6). Kept mild
    # (0.9x fresh .. 1.15x exhausted) to avoid a runaway death spiral.
    h_sustainability = 1.15 - (avg_h_stam / 400.0)
    a_sustainability = 1.15 - (avg_a_stam / 400.0)

    h_burn = ((stats['h_tempo'] + stats['h_press']) / 7.0) * h_sustainability
    a_burn = ((stats['a_tempo'] + stats['a_press']) / 7.0) * a_sustainability

    return h_burn, a_burn


def apply_passive_drain(team_home, team_away, h_burn, a_burn):
    passive_h = 0.5 * h_burn
    passive_a = 0.5 * a_burn
    for p in team_home:
        p.drain_stamina(passive_h)
    for p in team_away:
        p.drain_stamina(passive_a)


def apply_active_drain(carrier, defender, att_burn, def_burn):
    carrier.drain_stamina(1.2 * att_burn)
    defender.drain_stamina(1.0 * def_burn)


def apply_mirrored_drain(def_team, att_press_val):
    mirrored = att_press_val * 0.04
    for p in def_team:
        p.drain_stamina(mirrored)


def apply_width_cost(team, width_val):
    if width_val < 4:
        return
    extra = 0.3 if width_val == 4 else 0.6
    for p in team:
        pz_char = p.preferred_zone[0].upper() if p.preferred_zone else 'C'
        if pz_char in ('L', 'R'):
            p.drain_stamina(extra)
