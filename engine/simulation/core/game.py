import random
from collections import defaultdict

from ..entities.player import SimPlayer
from .state import GameState
from ..systems.tactics import get_tactical_profile, get_tactical_mods, calc_width_advantage
from ..systems.environment import get_environment
from ..systems.matchups import select_duellists
from ..systems import fatigue
from ..systems import recovery
from ..systems import phases
from ..systems.movement import place_player, arrive, apply_velocity
from ..constants import FATIGUE_BREACH_STAMINA, STRUCT_BREACH_INTEGRITY
from .formation import get_formation_target


ZONE_MAP = {'L': 'Left', 'C': 'Center', 'R': 'Right'}
FLANK_PRESSURE_THRESHOLD = 3

# Positional effectiveness per phase: defenders defend, midfielders link,
# forwards attack. Playing someone out of their job costs real output, so
# roles are a mechanical choice rather than a label (audit Phase 4).
ROLE_PHASE_MODS = {
    #          poss_att, poss_def, break_att, break_def
    'GK':  (0.70, 0.80, 0.60, 0.80),
    'DEF': (0.95, 1.06, 0.90, 1.08),
    'MID': (1.05, 1.00, 1.02, 0.98),
    'FWD': (0.98, 0.88, 1.06, 0.85),
}


def _role_mods(player):
    return ROLE_PHASE_MODS.get(player.role, (1.0, 1.0, 1.0, 1.0))


def get_player_target(player, ball, side, field, tactical_style=None):
    """Get tactical target for player. Ball carrier moves to ball, others use formation."""
    if player.last_carried:
        return ball.x, ball.y
    return get_formation_target(player, ball, side, field, tactical_style)


def advance_carrier_position(carrier, zone_key, field, att_side, rng):
    """Move carrier into a realistic final-third location after a successful break."""
    depth_pct = rng.uniform(0.68, 0.88)
    if att_side == 'home':
        carrier.x = field.width * depth_pct
    else:
        carrier.x = field.width * (1.0 - depth_pct)

    zone_y = {
        'Center': field.height * rng.uniform(0.35, 0.65),
        'Left': field.height * rng.uniform(0.10, 0.35),
        'Right': field.height * rng.uniform(0.65, 0.90),
    }
    carrier.y = zone_y.get(zone_key, field.height * 0.5)


def scatter_defenders_to_positions(def_team, field, def_side, rng):
    """Place defenders in plausible recovery positions during break defense.

    The transform is computed side-agnostically as a distance from the
    defending goal, then mirrored, so home and away defenses recover
    identically.
    """
    for defender in def_team:
        if defender.role == 'GK':
            defender.x = field.width * (0.02 if def_side == 'home' else 0.98)
            defender.y = field.height * 0.5
            continue

        discipline = defender.traits.get('discipline', 0.5)
        depth_from_goal = rng.uniform(0.05, 0.35) * (1.0 - discipline * 0.3)

        if def_side == 'home':
            x_pct = depth_from_goal
        else:
            x_pct = 1.0 - depth_from_goal

        defender.x = max(0.0, min(float(field.width), field.width * x_pct))
        defender.y = field.height * rng.uniform(0.15, 0.85)


class Game:
    def __init__(self, mode='5v5'):
        self.mode = mode
        self.env = get_environment(mode)
        self.max_minutes = self.env.max_minutes
        self.half_time_min = self.env.half_time_min

    def play(self, home_team, away_team, h_players, a_players, sys_style=None, match_seed=None):
        # Per-match RNG: reproducible from match_seed and isolated from other
        # concurrently running matches (never touches the global random state).
        rng = random.Random(match_seed) if match_seed else random.Random()

        team_home = [SimPlayer(p, rng=rng) for p in h_players]
        team_away = [SimPlayer(p, rng=rng) for p in a_players]

        if len(team_home) < self.env.squad_size or len(team_away) < self.env.squad_size:
            return ['ERROR: Squads too small.'], {}

        h_profile = get_tactical_profile(getattr(home_team, 'tactical_mode', 'Standard'))
        a_profile = get_tactical_profile(getattr(away_team, 'tactical_mode', 'Standard'))
        h_mods = get_tactical_mods(h_profile.name)
        a_mods = get_tactical_mods(a_profile.name)

        state = GameState(home_team.name, away_team.name, field_config=self.env.config)
        state.reset_ball()

        # Place players at kick-off positions relative to the actual pitch size.
        for i, p in enumerate(team_home):
            place_player(p, x=state.field.width * 0.15, y=state.field.height * (i + 1) / (len(team_home) + 1))

        for i, p in enumerate(team_away):
            place_player(p, x=state.field.width * 0.85, y=state.field.height * (i + 1) / (len(team_away) + 1))

        # Tactical styles come from the team objects; the legacy sys_style
        # parameter is ignored (it only ever reached the home team - see audit B4).
        h_style = getattr(home_team, 'sys_style', {}) or {}
        a_style = getattr(away_team, 'sys_style', {}) or {}

        h_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0 for p in h_players]) / max(len(h_players), 1)
        a_ovr = sum([(p.speed + p.shooting + p.defense + p.stamina) / 4.0 for p in a_players]) / max(len(a_players), 1)

        state.stats.update({
            'home_score': 0,
            'away_score': 0,
            'home_possession_count': 0,
            'away_possession_count': 0,
            'h_tempo': h_style.get('tempo', 3),
            'h_press': h_style.get('press', 3),
            'h_risk': h_style.get('risk', 3),
            'h_depth': h_style.get('depth', 3),
            'h_width': h_style.get('width', 3),
            'a_tempo': a_style.get('tempo', 3),
            'a_press': a_style.get('press', 3),
            'a_risk': a_style.get('risk', 3),
            'a_depth': a_style.get('depth', 3),
            'a_width': a_style.get('width', 3),
            'timeline': [],
            'fatigue_breach_min': None,
            'struct_breach_min': None,
            'break_timestamps': [],
            'zone_control': {
                'Center': {'home': 0, 'away': 0},
                'Left': {'home': 0, 'away': 0},
                'Right': {'home': 0, 'away': 0},
            },
            'system_influence': 0.0,
            'random_influence': 0.0,
            'impact_detail': defaultdict(lambda: {
                'total': 0,
                'breaks': 0,
                'damage': 0,
                'saves': 0,
                'goals': 0,
                'def_stops': 0,
                'misses': 0,
                'turnovers': 0,
            }),
            'home_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},
            'away_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},
            '_zone_pressure': {
                'home': {'Left': 0, 'Center': 0, 'Right': 0},
                'away': {'Left': 0, 'Center': 0, 'Right': 0},
            },
            'max_minutes': self.max_minutes,
            '_shot_freq': self.env.shot_frequency_modifier,
        })

        log = [f"MATCH STARTED: {home_team.name} vs {away_team.name} ({self.mode})"]
        home_has_ball = rng.random() < 0.5
        log.append(f"KICK-OFF: {home_team.name if home_has_ball else away_team.name} get us underway.")

        def add_impact(name, category, points):
            state.stats['impact_detail'][name]['total'] += points
            state.stats['impact_detail'][name][category] += 1

        consecutive_center = {'home': 0, 'away': 0}
        consecutive_flank = {
            'home': {'zone': None, 'count': 0},
            'away': {'zone': None, 'count': 0},
        }
        player_influence = defaultdict(int)
        # A player can dominate roughly this many possessions before defenses
        # key on him. Scales with squad size so 5v5 players are not blanket-nerfed.
        influence_threshold = (self.max_minutes * 2.5) / self.env.squad_size

        for minute in range(1, self.max_minutes + 1):
            state.update_ball()

            h_tactical = {
                'press': state.stats['h_press'],
                'depth': state.stats['h_depth'],
                'width': state.stats['h_width'],
                'profile': h_profile.name,
                'team_players': team_home,
            }
            a_tactical = {
                'press': state.stats['a_press'],
                'depth': state.stats['a_depth'],
                'width': state.stats['a_width'],
                'profile': a_profile.name,
                'team_players': team_away,
            }

            # Update player positions
            for p in team_home:
                target_x, target_y = get_player_target(p, state.ball, 'home', state.field, h_tactical)
                arrive(p, target_x, target_y)
                apply_velocity(p)

            for p in team_away:
                target_x, target_y = get_player_target(p, state.ball, 'away', state.field, a_tactical)
                arrive(p, target_x, target_y)
                apply_velocity(p)

            if minute == self.half_time_min:
                recovery.apply_halftime_recovery(team_home, state.stats['h_press'], home_team.name, log)
                recovery.apply_halftime_recovery(team_away, state.stats['a_press'], away_team.name, log)

            for p in team_home + team_away:
                p.last_carried = False

            avg_h_stam = sum(p.current_stamina for p in team_home) / len(team_home)
            avg_a_stam = sum(p.current_stamina for p in team_away) / len(team_away)

            if (avg_h_stam < FATIGUE_BREACH_STAMINA or avg_a_stam < FATIGUE_BREACH_STAMINA) \
                    and state.stats['fatigue_breach_min'] is None:
                state.stats['fatigue_breach_min'] = minute

            if (state.home_structure['overall'] < STRUCT_BREACH_INTEGRITY
                    or state.away_structure['overall'] < STRUCT_BREACH_INTEGRITY) \
                    and state.stats['struct_breach_min'] is None:
                state.stats['struct_breach_min'] = minute

            for side, name in [('home', home_team.name), ('away', away_team.name)]:
                phase_msg = state.check_phase_shift(side, name)
                if phase_msg:
                    log.append(phase_msg)

            if minute % 15 == 1 or minute == self.max_minutes - 2:
                state.stats['timeline'].append({
                    'min': minute,
                    'h_struct': int(state.home_structure['overall']),
                    'a_struct': int(state.away_structure['overall']),
                    'h_zones': state.get_zone_snapshot('home'),
                    'a_zones': state.get_zone_snapshot('away'),
                    'h_avg_sta': int(avg_h_stam),
                    'a_avg_sta': int(avg_a_stam),
                })

            if home_has_ball:
                state.stats['home_possession_count'] += 1
            else:
                state.stats['away_possession_count'] += 1

            att_team = team_home if home_has_ball else team_away
            def_team = team_away if home_has_ball else team_home
            att_side = 'home' if home_has_ball else 'away'
            def_side = 'away' if home_has_ball else 'home'
            att_profile = h_profile if att_side == 'home' else a_profile
            att_mods = h_mods if att_side == 'home' else a_mods
            def_mods = a_mods if att_side == 'home' else h_mods
            att_sty = h_style if att_side == 'home' else a_style
            def_sty = a_style if att_side == 'home' else h_style

            duellists = select_duellists(
                att_team,
                def_team,
                self.mode,
                att_style=att_sty,
                def_style=def_sty,
                mode_config=self.env.config,
                rng=rng,
                discourage_center=consecutive_center[att_side] >= 2,
            )
            if not duellists:
                home_has_ball = not home_has_ball
                continue
            carrier, defender, gk, raw_zone = duellists

            carrier.last_carried = True
            state.ball.attach_to_owner(carrier)
            zone_key = ZONE_MAP.get(raw_zone, 'Center')

            if zone_key == 'Center':
                consecutive_center[att_side] += 1
            else:
                consecutive_center[att_side] = 0

            state.stats['zone_control'][zone_key][att_side] += 1
            state.stats['_zone_pressure'][att_side][zone_key] += 1

            flank_data = consecutive_flank[att_side]
            if zone_key in ('Left', 'Right'):
                if flank_data['zone'] == zone_key:
                    flank_data['count'] += 1
                else:
                    flank_data['zone'] = zone_key
                    flank_data['count'] = 1
                if flank_data['count'] >= FLANK_PRESSURE_THRESHOLD:
                    def_struct_dict = state.home_structure if def_side == 'home' else state.away_structure
                    center_health = def_struct_dict['zones']['Center']
                    if center_health > 50:
                        bleed = 1.5
                        state.degrade_structure(def_side, bleed, zone='Center')
                        log.append(
                            f"{minute}' [DENSITY] {att_side.upper()} overloading {zone_key} -- "
                            f"{def_side.upper()} center corridor opening. (-{bleed}% central integrity)"
                        )
                        flank_data['count'] = 0
            else:
                flank_data['zone'] = None
                flank_data['count'] = 0

            player_influence[carrier.name] += 1
            influence_penalty = 1.0
            if player_influence[carrier.name] > influence_threshold:
                influence_penalty = 0.75
                carrier.drain_stamina(2.0)

            h_burn, a_burn = fatigue.calc_burn_rates(state.stats, avg_h_stam, avg_a_stam)
            h_burn *= h_mods['stam'] * self.env.fatigue_scale
            a_burn *= a_mods['stam'] * self.env.fatigue_scale

            score_diff = state.stats['home_score'] - state.stats['away_score']
            escalation_boost = 1.0
            if score_diff != 0:
                trailing = 'home' if score_diff < 0 else 'away'
                if att_side == trailing:
                    escalation_boost = self.env.trailing_escalation_boost
                    if att_side == 'home':
                        h_burn *= 1.15
                    else:
                        a_burn *= 1.15

            att_burn = h_burn if att_side == 'home' else a_burn
            def_burn = a_burn if att_side == 'home' else h_burn

            fatigue.apply_passive_drain(team_home, team_away, h_burn, a_burn)
            fatigue.apply_active_drain(carrier, defender, att_burn, def_burn)

            att_press_val = state.stats['h_press'] if att_side == 'home' else state.stats['a_press']
            fatigue.apply_mirrored_drain(def_team, att_press_val)
            fatigue.apply_width_cost(att_team, int(att_sty.get('width', 3)))

            # get_structure_mult already maps integrity into [0.6, 1.0]; use it
            # directly (previously double-compressed into [0.84, 1.0] - audit A2).
            struct_att = state.get_structure_mult(att_side, zone=zone_key)
            struct_def = state.get_structure_mult(def_side, zone=zone_key)

            mismatch_scale = self.env.mismatch_scale
            att_tempo = state.stats['h_tempo'] if att_side == 'home' else state.stats['a_tempo']
            def_press = state.stats['h_press'] if def_side == 'home' else state.stats['a_press']
            att_risk = state.stats['h_risk'] if att_side == 'home' else state.stats['a_risk']
            def_depth = state.stats['h_depth'] if def_side == 'home' else state.stats['a_depth']

            m_poss_att, m_poss_def = 1.0, 1.0
            m_break_att, m_break_def = 1.0, 1.0

            if def_press > att_tempo:
                m_poss_def += (def_press - att_tempo) * mismatch_scale
            elif att_tempo > def_press:
                m_poss_att += (att_tempo - def_press) * mismatch_scale

            if att_risk > def_depth:
                m_break_att += (att_risk - def_depth) * mismatch_scale
            elif def_depth > att_risk:
                m_break_def += (def_depth - att_risk) * mismatch_scale

            att_fit = carrier.get_tactical_fit(att_profile) * influence_penalty
            def_fit = defender.get_tactical_fit(h_profile if def_side == 'home' else a_profile)

            # Zone familiarity: playing/defending outside your preferred zone
            # costs a fraction of your effectiveness (dormant zone_coverage,
            # wired per audit Phase 4).
            att_zone_cov = carrier.zone_coverage.get(raw_zone, 1.0)
            def_zone_cov = defender.zone_coverage.get(raw_zone, 1.0)

            # Quality gap: applied once, on the attacking side only (audit B3),
            # and heavily damped -- raw ratings already enter every duel roll,
            # so this multiplier only nudges. Tactics/structure carry the rest.
            stat_adv = (h_ovr - a_ovr) if att_side == 'home' else (a_ovr - h_ovr)
            stat_multiplier = max(0.92, min(1.08, 1.0 + (stat_adv / 200.0)))
            base_att_adv = 0.13
            width_adv = calc_width_advantage(att_side, zone_key, state.stats)

            carrier_poss, _, carrier_break, _ = _role_mods(carrier)
            _, defender_poss, _, defender_break = _role_mods(defender)

            poss_att = min((struct_att * att_fit * att_zone_cov * att_mods['att'] * carrier_poss * escalation_boost * m_poss_att * stat_multiplier) + base_att_adv, 3.5)
            poss_def = min(struct_def * def_fit * def_zone_cov * def_mods['def'] * defender_poss * m_poss_def, 3.5)
            break_att = min((struct_att * att_fit * att_zone_cov * att_mods['att'] * carrier_break * escalation_boost * m_break_att * stat_multiplier * width_adv) + base_att_adv, 3.5)
            break_def = min(struct_def * def_fit * def_zone_cov * def_mods['def'] * defender_break * m_break_def, 3.5)

            poss_result = phases.run_possession_phase(
                carrier, defender, poss_att, poss_def, minute, raw_zone, zone_key,
                att_side, def_side, state, log, add_impact, rng,
            )
            if poss_result == 'TURNOVER':
                state.ball.release()
                home_has_ball = not home_has_ball
                continue

            break_result = phases.run_break_phase(
                carrier,
                defender,
                break_att,
                break_def,
                minute,
                raw_zone,
                zone_key,
                def_side,
                state,
                log,
                add_impact,
                self.env.base_damage / max(def_mods['int'], 0.1),
                rng,
            )

            if break_result['outcome'] == 'BLOCKED':
                state.ball.release()
                home_has_ball = not home_has_ball
                continue

            if break_result['outcome'] == 'SUCCESS':
                advance_carrier_position(carrier, zone_key, state.field, att_side, rng)
                scatter_defenders_to_positions(def_team, state.field, def_side, rng)

            zone_health = break_result['zone_health']

            att_risk_val = state.stats['h_risk'] if att_side == 'home' else state.stats['a_risk']
            att_tempo_val = state.stats['h_tempo'] if att_side == 'home' else state.stats['a_tempo']
            def_depth_val = state.stats['h_depth'] if def_side == 'home' else state.stats['a_depth']

            shot_result = phases.run_shot_phase(
                att_team,
                def_team,
                gk,
                defender,
                zone_health,
                break_att,
                stat_adv,
                att_side,
                def_side,
                att_risk_val,
                att_tempo_val,
                def_depth_val,
                minute,
                state,
                log,
                add_impact,
                rng,
            )

            if shot_result.get('goal'):
                state.reset_ball()

            if shot_result['flip']:
                state.ball.release()
                home_has_ball = not home_has_ball

        total = max(state.stats['home_possession_count'] + state.stats['away_possession_count'], 1)
        state.stats['home_possession_pct'] = int((state.stats['home_possession_count'] / total) * 100)
        state.stats['home_integrity_final'] = int(state.home_structure['overall'])
        state.stats['away_integrity_final'] = int(state.away_structure['overall'])
        state.stats['home_zone_finals'] = state.get_zone_snapshot('home')
        state.stats['away_zone_finals'] = state.get_zone_snapshot('away')

        log.append('FULL TIME.')
        return log, state.stats


def play_match(home_team, away_team, h_players, a_players, mode='5v5', sys_style=None, match_seed=None):
    return Game(mode=mode).play(home_team, away_team, h_players, a_players, sys_style=sys_style, match_seed=match_seed)
