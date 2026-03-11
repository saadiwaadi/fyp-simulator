# engine/simulation/recovery.py
# ============================================================
# RECOVERY MODULE
# Extracted from engine.py Phase C.
#
# Owns every stamina RECOVERY operation that happens during a match.
# Drain logic lives in fatigue.py instead.
#
# PUBLIC API
# ----------
# apply_halftime_recovery(team, press_val, team_label, log)
#     Role-weighted stamina recovery at halftime.
#     Press slider reduces recovery — high-press teams recover less.
#     Appends the HALF TIME line to the match log.
#
# apply_micro_regen(defender)
#     +1.5 stamina for the player who wins the ball back on a turnover.
#     Exploit guard: only fires if defender wasn't the previous carrier
#     OR their stamina is above 20 (prevents cycling possession to self-heal).
# ============================================================


# Role-based halftime recovery amounts.
# GKs barely moved all half → recover most.
# FWDs were pressing and sprinting → recover least.
_HALFTIME_RECOVERY = {
    'GK':  18.0,
    'DEF': 12.0,
    'MID':  8.0,
    'FWD':  6.0,
}


def apply_halftime_recovery(team, press_val, team_label, log):
    """
    Role-weighted halftime stamina recovery (Phase C).

    Press penalty scales from 0% (press=1) to 30% (press=5).
    A gegenpressing team that spent 20 minutes sprinting recovers
    significantly less than a low-block team that stood their shape.

    After the press penalty, each player's recover_stamina() applies
    the depth-scaled efficiency ceiling internally:
      - Hard ceiling at base_stamina * 0.75 (tired legs stay tired)
      - Exhausted players recover less efficiently than fresh ones

    Parameters
    ----------
    team        : list of SimPlayer — the squad to recover
    press_val   : int — team's press slider (1–5)
    team_label  : str — team name for the log line
    log         : list — match log to append the HALF TIME event to
    """
    # press=1 → 0% penalty (full recovery)
    # press=5 → 30% penalty (high-press fatigue carries over)
    press_penalty = 1.0 - ((press_val - 1) / 4.0) * 0.30

    for p in team:
        base = _HALFTIME_RECOVERY.get(p.role, 8.0)
        p.recover_stamina(base * press_penalty)

    log.append(
        f"--- HALF TIME --- {team_label}: Players recover "
        f"(press penalty: {round((1 - press_penalty) * 100)}%)"
    )


def apply_micro_regen(defender):
    """
    Micro-regen on turnover (Phase C).

    When a defender wins the ball back, they get a small stamina reward (+1.5).
    This models the brief mental reset of regaining possession.

    EXPLOIT GUARD — regen only fires if:
      - defender.last_carried is False (they weren't the previous carrier)
      OR
      - defender.current_stamina > 20 (not cycling possession at near-zero
        stamina to game the recovery system)

    Parameters
    ----------
    defender : SimPlayer — the player who won possession back
    """
    if not defender.last_carried or defender.current_stamina > 20:
        defender.recover_stamina(1.5)