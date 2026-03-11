# engine/simulation/fatigue.py
# ============================================================
# FATIGUE MODULE
# Extracted from engine.py Phase C.
#
# Owns every stamina DRAIN operation that happens during a match.
# Recovery (halftime, micro-regen) lives in recovery.py instead.
#
# PUBLIC API
# ----------
# calc_burn_rates(stats, avg_h_stam, avg_a_stam)
#     -> (h_burn, a_burn)
#     Computes base burn rates for both teams this minute.
#     Applies smooth sustainability scaling so tired teams drain slower.
#
# apply_passive_drain(team_home, team_away, h_burn, a_burn)
#     Drains all players at 50% of their team's burn rate.
#     Passive = background exertion, not directly involved in duel.
#
# apply_active_drain(carrier, defender, att_burn, def_burn)
#     Drains the two duellists at higher rates.
#     Carrier (1.2x) works harder than defender (1.0x).
#
# apply_mirrored_drain(def_team, att_press_val)
#     High-press attacking teams passively tire out defenders too.
#     Formula: att_press * 0.04 per defender per minute.
#
# apply_width_cost(team, width_val)
#     Wide play (width >= 4) burns extra stamina for flank specialists.
#     Width 4: +0.3 per wide player. Width 5: +0.6.
# ============================================================


def calc_burn_rates(stats, avg_h_stam, avg_a_stam):
    """
    Compute per-minute burn rate for each team.

    SUSTAINABILITY SCALING (Phase C):
      burn *= 0.9 + (avg_stamina / 200)
      Fresh team (avg 100):  1.40x — explosive early drain
      Tired team (avg 60):   1.20x — naturally slowing down
      Exhausted team (avg 20): 1.00x — floor, tempo always costs something

    Parameters
    ----------
    stats        : state.stats dict (reads h_tempo, h_press, a_tempo, a_press)
    avg_h_stam   : current average stamina for home squad
    avg_a_stam   : current average stamina for away squad

    Returns
    -------
    (h_burn, a_burn) : float burn scalars for this minute
    """
    h_sustainability = 0.9 + (avg_h_stam / 200.0)
    a_sustainability = 0.9 + (avg_a_stam / 200.0)

    h_burn = ((stats['h_tempo'] + stats['h_press']) / 6.0) * h_sustainability
    a_burn = ((stats['a_tempo'] + stats['a_press']) / 6.0) * a_sustainability

    return h_burn, a_burn


def apply_passive_drain(team_home, team_away, h_burn, a_burn):
    """
    Drain all players at 50% of their team's burn rate.
    Represents constant background exertion — positioning, pressing shape,
    tracking runs — for players not directly in the minute's duel.

    Each player's drain_stamina() applies the intensity-dependent curve
    internally (Phase C), so high-stamina players still burn proportionally more.
    """
    passive_h = 0.5 * h_burn
    passive_a = 0.5 * a_burn
    for p in team_home:
        p.drain_stamina(passive_h)
    for p in team_away:
        p.drain_stamina(passive_a)


def apply_active_drain(carrier, defender, att_burn, def_burn):
    """
    Drain the two duellists at elevated rates.
    Carrier works harder (1.2x) — they're driving the attack.
    Defender responds (1.0x) — reactive but still costly.

    Parameters
    ----------
    carrier   : SimPlayer — the ball carrier this minute
    defender  : SimPlayer — the opposing duellist
    att_burn  : burn scalar for the attacking team
    def_burn  : burn scalar for the defending team
    """
    carrier.drain_stamina(1.2 * att_burn)
    defender.drain_stamina(1.0 * def_burn)


def apply_mirrored_drain(def_team, att_press_val):
    """
    Mirrored opponent drain (Phase C).
    A high-press attacking team forces defenders to work harder too —
    they're constantly retreating, marking, and holding shape under pressure.

    Formula: att_press * 0.04 per defender per minute
      press=1 → +0.04  (negligible, low intensity)
      press=3 → +0.12  (moderate)
      press=5 → +0.20  (full gegenpressing burns both teams)

    Parameters
    ----------
    def_team      : list of SimPlayer — the defending team
    att_press_val : int — attacker's press slider (1–5)
    """
    mirrored = att_press_val * 0.04
    for p in def_team:
        p.drain_stamina(mirrored)


def apply_width_cost(team, width_val):
    """
    Wide tactical shape costs extra stamina for flank specialists.
    Only fires when width >= 4. Only affects players whose preferred
    zone is Left or Right — center players don't cover the extra ground.

    Width 4 (Wide):    +0.3 per flank player per minute
    Width 5 (Stretch): +0.6 per flank player per minute

    Parameters
    ----------
    team      : list of SimPlayer — the attacking team
    width_val : int — attacker's width slider (1–5)
    """
    if width_val < 4:
        return
    extra = 0.3 if width_val == 4 else 0.6
    for p in team:
        pz_char = (p.preferred_zone[0].upper() if p.preferred_zone else 'C')
        if pz_char in ('L', 'R'):
            p.drain_stamina(extra)