_HALFTIME_RECOVERY = {
    'GK': 18.0,
    'DEF': 12.0,
    'MID': 8.0,
    'FWD': 6.0,
}


def apply_halftime_recovery(team, press_val, team_label, log):
    press_penalty = 1.0 - ((press_val - 1) / 4.0) * 0.30

    for p in team:
        base = _HALFTIME_RECOVERY.get(p.role, 8.0)
        p.recover_stamina(base * press_penalty)

    log.append(
        f"--- HALF TIME --- {team_label}: Players recover "
        f"(press penalty: {round((1 - press_penalty) * 100)}%)"
    )


def apply_micro_regen(defender):
    # A defender who just won the ball gets a breather, but only if tired --
    # fresh players gain nothing from a broken-up attack.
    if defender.current_stamina < 50:
        defender.recover_stamina(1.5)
