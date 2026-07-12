# System Audit — Simulation Engine Flags, Bias & Roadmap

**Scope:** `engine/simulation/*` (core loop, phases, mechanics, fatigue, matchups, movement/formation, analyst) plus the views that drive it.
**Method:** Full code read + empirical probes: 400 mirrored matches per mode with *identical* squads, a 300-match instrumented funnel trace, a 400-match scorer-concentration test, a 300-match tactics A/B test, and a 300-match role-relabel test.

---

## Headline empirical results

**Mirrored teams (identical squads both sides):**

| Metric | 5v5 (N=400) | 11v11 (N=400) |
| --- | --- | --- |
| Draws | 390 (97.5%) | 385 (96%) |
| Total goals | 11 (0.03/match) | 17 (0.04/match) |
| Home goals vs Away goals | 8 vs 3 | 15 vs 2 |
| Matches where any zone ended below 38 integrity | 0 / 400 | 0 / 400 |

**Funnel trace (11v11, N=300, per attacking side):**

| Stage | Home | Away |
| --- | --- | --- |
| Successful tactical breaks | 4,677 | 4,755 |
| "Recycles — no clear opening" (declined shot) | 4,468 (95.5%) | 4,576 (96.2%) |
| Shot attempts | 209 | 179 |
| Blocked shooting lane | 113 (54%) | 114 (64%) |
| Shots taken | 96 | 65 |
| Goals | 7 | 2 |

**Influence A/B tests (N=300 each):**

| Test | Result |
| --- | --- |
| Maxed tempo/press/risk home vs neutral | 22W/15L (vs 8W/5L baseline), goals 39 vs 17 → **sliders do matter** |
| Away FWDs relabeled MID (same stats) | 7W/8L/285D — indistinguishable from baseline → **roles are near-cosmetic** |

Systemic conclusions:

1. **Goal drought:** ~96% of matches end 0-0. The collapse model never pays off — no zone dropped below 38 integrity in 800 matches, so the spec's "Glass/Sand" phases are unreachable.
2. **Home bias:** with mirrored inputs, home takes ~48% more shots and scored 23 of 28 total goals across both modes (binomial p ≈ 0.0004).
3. **Roles don't influence outcomes**; tactics sliders influence outcomes moderately (mostly via mismatch scaling and stamina burn), but through a very narrow channel.
4. A large amount of built simulation machinery (spatial AI, tactical modifiers, per-mode tuning) is **defined but never wired into the match loop** (section F).

---

## A. Bugs that break core mechanics

### A1. `regen_structure` floor teleports collapsed zones back to 40
`engine/simulation/core/state.py:88` / `:92` — `zones[zone] = max(floor, min(100.0, zones[zone] + amount))` with `floor=40`. `max(40, …)` doesn't *prevent dropping below* 40, it *lifts* any zone already below 40 straight back to 40 the moment any regen fires. Regen fires on every turnover (+0.5), block (+1.0), and blocked lane (+1.0) — many times per match. This is why no zone ever collapses, why "Sand/Glass" phases never occur, and it is also the source of the **drastic, random-looking integrity jumps** in match progression: a zone ground down to 12 over twenty minutes snaps back to 40 from a single 0.5-point regen event.
**Fix:** clamp instead of lift: `zones[zone] = min(100.0, zones[zone] + amount)`; if a floor is desired, apply it to degradation only.

### A2. Structure multiplier is double-compressed, so integrity barely matters
`state.get_structure_mult` already maps integrity to `[0.6, 1.0]` (`state.py:96-102`). `game.py:325-328` wraps it *again*: `struct_att = 0.6 + (raw * 0.4)` → final range `[0.84, 1.0]`. A fully collapsed team fights at 84% strength instead of the intended 60%. Combined with A1, structural collapse — the engine's core resource — has almost no effect on possession/break phases.
**Fix:** apply the mapping once (use `raw_att_struct` directly in `game.py`).

### A3. `apply_micro_regen` gate is always true
`systems/recovery.py:23` — `if not defender.last_carried or defender.current_stamina > 20:`. The defender is never the carrier, so the condition never gates anything; every turnover grants 1.5 stamina unconditionally. Dead flag logic.
**Fix:** write the intended rule explicitly (likely `and`, or a stamina-threshold-only condition).

### A4. Breach flags disagree with the analyst's narrative and ignore mode length
`game.py:209` flags `struct_breach_min` at overall structure < **65**, but `analyst.py:47-50` reports it as "dropped below **40%** … critical failure". `fatigue_breach_min` (avg stamina < 50) is rated against hard-coded minute **70** (`analyst.py:37`) — unreachable in a 40-minute 5v5 match, so every 5v5 breach reads "Overextended" and every non-breach "Optimal".
**Fix:** one constants module for thresholds; scale minute-based logic by `max_minutes`.

### A5. Dead stats rendered in the UI
`GameState.__init__` seeds `home_shots`, `on_target`, passes, corners, fouls, offsides (`state.py:19-25`) but nothing increments them, and `analysis.html:72` renders `stats.home_shots` — reports show 0 shots even in matches with goals.
**Fix:** increment shots/on-target in `run_shot_phase`, passes in the possession phase — or remove until implemented.

### A6. Away team spawns off the pitch in 5v5
`game.py:92-93` hard-codes kick-off placement at `x=3.0` / `x=17.0`, but the 5v5 pitch is 14 wide (`environment.py:33`). Away players start out of bounds.
**Fix:** place relative to `field.width` (e.g. `0.15w` / `0.85w`).

### A7. Global `random.seed()` per match
`game.py:71-74` seeds the *process-global* RNG. Under Django, concurrent matches interleave draws — stored match seeds don't reproduce replays, and one match perturbs another.
**Fix:** `self.rng = random.Random(match_seed)` threaded through mechanics/matchups/phases. Prerequisite for all later calibration work.

### A8. Silent exception swallowing flips possession
`game.py:254-256` — `except Exception:` around `select_duellists` hides any real bug as a phantom turnover. This is a prime suspect for "match progression fails randomly": a genuine error mid-match becomes an invisible, unexplained possession flip.
**Fix:** remove the blanket catch (or catch a specific expected case and log loudly).

### A9. Leftover debug `print` in the match loop
`game.py:194` prints player positions to stdout on minute 1 of every match.
**Fix:** delete or move behind a logger.

---

## B. Sources of bias (home/away asymmetries)

### B1. Defender scatter math is not mirrored — the main home-shot bias
`scatter_defenders_to_positions` (`game.py:52-57`): home defenders get discipline applied **multiplicatively** (`base_x *= 1 - d*0.3`), away defenders **additively** (`base_x += d*0.1*width`). With typical discipline ≈ 0.72, the recovering home defense sits a mean 0.063·width from the away carrier while the away defense sits 0.081·width from the home carrier. Home carriers see less `defensive_pressure`, pass the lane-block check more often (54% vs 64% blocked), and take ~48% more shots. Dominant measured bias.
**Fix:** identical mirrored transform: `off = uniform(0.05, 0.35) * (1 - d*0.3)`; `x = off*w` (home) / `(1-off)*w` (away).

### B2. Home always takes first possession; no kick-off reset after goals
`game.py:145` — `home_has_ball = True` every match; after a goal the ball is merely released, never reset to center.
**Fix:** randomize/alternate opening possession with the match RNG; `state.reset_ball()` after goals.

### B3. Stat advantage double-counted only when the weaker team attacks
`game.py:352-359` — the attacker's `stat_multiplier` applies both directions, but the defender additionally gets `1 + |stat_adv|/75` **only when the attacker is weaker**. The weaker team is penalized twice on its own possessions; the stronger team's possessions penalize the defense zero times. Super-linear amplification of quality gaps — this is a big contributor to "player-biased rather than tactics-biased" outcomes.
**Fix:** single representation of the quality gap (attacker-side only, or symmetric halves); remove the conditional defender boost.

### B4. `sys_style` fallback only reaches the home team
`game.py:95-96` — `h_style = getattr(home_team, 'sys_style', sys_style or {})` vs `a_style = getattr(away_team, 'sys_style', {})`. Any caller relying on the `sys_style` parameter (the signature invites it; `views.py:139` passes it) hands a style to home only.
**Fix:** drop the parameter or accept explicit `(h_style, a_style)`.

### B5. Analyst tie-breaks award everything to the away team
`analyst.py:73` gives zone dominance ties to away; `analyst.py:29-33` grades "system resilience" on the away team whenever the match is a draw (currently ~96% of matches).
**Fix:** explicit "Contested" handling; grade both teams or the winner.

### B6. Forced center→flank rewrite corrupts zone accounting
`game.py:262-267` — after two consecutive Center possessions the zone label is overwritten to a random flank *after* carrier/defender were selected with Center weighting. Zone stats, width advantage, and flank-pressure tracking then operate on a zone the duel wasn't built for — another source of erratic progression.
**Fix:** apply anti-repetition to the zone *weights before* `select_duellists`.

### B7. "System vs variance" attribution is structurally rigged
`game.py:361-362` — `system_influence += abs(break_att - break_def)` vs a flat `random_influence += 0.1`. The ratio is a foregone conclusion of multiplier scales, not a measurement, yet `analyst.py:147` uses it to declare "Systemic Victory".
**Fix:** measure the actual share of each contested roll's margin contributed by the random component vs the stat component.

---

## C. Calibration problems (goal drought + scorer monopoly)

1. **`should_attempt_shot` is a near-absolute veto** (`ai/decision.py:34-71`): the `danger < 0.15` hard gate plus `- pressure*0.35` rejects ~95% of *successful* breaks. A break that just "carved the defense open" should rarely yield zero chance of a shot.
2. **Finish math is stacked toward the GK** (`mechanics.py:44-65`): attacker noise `randint(-20, 15)` skews negative, GK noise `randint(-10, 20)` skews positive, goals require beating `def_roll + 12`, GK composure gets ×1.1. A 70-rated finisher vs a 70-rated GK converts ~5-7%.
3. **This threshold shape is why "one striker scores every goal."** Goal probability is a steep step function of `finishing`: below ~75 finishing a player essentially cannot clear `def_roll + 12`, and the `chaos_thrives` trait (extra bonus) only exists above a hard 80-finishing cliff (`player.py:38`, `mechanics.py:45-49`). On top of that, if no carrier is flagged, `run_shot_phase` deterministically hands the shot to the *single highest-finishing* player (`phases.py:44`). Result: the top finisher takes a monopoly on the few goals that exist. Softening the threshold into a smooth curve (and removing the 80-cliff) redistributes scoring realistically.
4. **Integrity bonus capped near zero** by A1: `bonus = (100 - zone_health)/20` with `zone_health = max(40, …)` (`phases.py:28`) caps the collapse payoff at +3; the spec intends collapse to be the primary goal driver (up to ~+33).
5. **Hard-coded minute constants ignore mode**: `resolve_finish` halves the bonus for `minute < 25` — 62% of a 5v5 match.
6. **Fatigue direction is inverted twice**: `drain_stamina`'s `intensity_factor = 1 + current_stamina/100` (`player.py:92`) and `calc_burn_rates`' `0.9 + avg_stam/200` (`fatigue.py:2-3`) make fitter players/teams burn *more*, and `work_rate` (derived from stamina) adds a third burn increase. High base stamina is largely self-cancelling — contradicts spec §5.
7. **`influence_penalty` punishes small squads**: threshold `max_minutes/4` carries (`game.py:298`) is crossed routinely by every 5v5 player — a blanket late-game attack nerf, not a star-player balancer. This is also why player-influence tracking feels wrong: involvement is possession-weighted randomness, then crudely penalized.
8. **Player impact scores are arbitrary constants** (`+3` def stop, `+4` break, `+15` goal, `+8` save; `phases.py`), with no negative events (misses, turnovers conceded, being dribbled past) and no normalization — the leaderboard measures touch count more than contribution.
9. **Trailing-team escalation boost** (`game.py:304-313`) is explicit rubber-banding; spec §5 promises none. Either the spec or the mechanic must change.

---

## D. Built but never wired (dead subsystems)

These exist in the codebase, look like features, and have **zero effect** on any match:

| Subsystem | Location | Status |
| --- | --- | --- |
| `TACTICAL_MODIFIERS` / `get_tactical_mods` (att/def/int/stam multipliers per style) | `systems/tactics.py:23-34` | Exported, never called — tactical *profiles* only act via player "fit"; the actual style modifiers do nothing |
| `InfluenceMap` | `ai/influence_map.py` | Never instantiated |
| Ball tracking / interception AI | `ai/ball_tracking.py`, `Ball.predict_position` | Never called from the loop |
| `seek()` steering | `systems/movement.py:4` | Never used (only `arrive`) |
| Field node grid (`Node`, `get_node`, `get_neighbors`, `iter_nodes`, `danger`, `occupied`) | `core/field.py` | Built every match, never read |
| `zone_coverage` per player | `entities/player.py:45-59` | Computed, never read |
| Env tuning fields: `fatigue_scale`, `shot_density`, `stamina_drain`, `stamina_recovery`, `shot_frequency_modifier`, `match_duration` | `systems/environment.py` | Loaded into `MatchEnvironment`, never read — per-mode balance knobs are inert |
| `tactical_instruction`, `set_piece_role` | models + lab UI | Saved to DB from the Tactical Lab, never read by the engine — the UI promises influence it doesn't have |

This is the concrete answer to "some logic are made and not wired up": the spatial/AI layer and the per-style modifier layer are both dormant. Wiring them is Phase 4/5 below.

---

## E. Phase-wise execution roadmap

Target vision: outcomes driven by **tactics, positioning, space, and play style** — where any system can win with suitable players — not by raw player ratings or by side of the pitch. Each phase below is independently shippable, and each ends with the same measurement loop (see "Iteration protocol").

### Phase 1 — Foundation & determinism (fix what's broken)
**Focus:** correctness only; no balance opinions. Small surgical diffs.
- A1 regen floor, A2 double-compressed multiplier, A3 micro-regen gate, A6 spawn bounds, A8 exception swallowing, A9 debug print, A4 threshold constants, A5 wire (or remove) dead stats.
- A7 per-match `random.Random` — mandatory first, since every later phase needs reproducible A/B runs.
**Exit criteria:** zones reach < 25 integrity in some mirrored matches; identical seed ⇒ identical match; stress framework reproducible.

### Phase 2 — Symmetry & fairness (kill the home bias)
**Focus:** the engine must be provably side-blind before any balancing, or every later tune bakes the bias in.
- B1 mirrored defender scatter (largest measured effect), B2 kick-off randomization + post-goal ball reset, B3 single-count stat advantage, B4 style parameter cleanup, B6 zone anti-repetition before selection.
**Exit criteria:** 1,000 mirrored matches → |home−away| shot share < 2%; goal split passes a binomial test (p > 0.05); win counts within noise.

### Phase 3 — Goal funnel & scorer distribution (make matches decisive)
**Focus:** calibration of the four-phase gauntlet so realistic scorelines emerge and scoring isn't a one-man monopoly.
- C1 turn the shot veto into a continuous modifier; C2 symmetric finish noise and tuned goal margin; C3 let integrity bonus scale once A1 lands; C4 mode-scaled minute constants; C5 smooth finishing curve + remove the 80-finishing `chaos_thrives` cliff (fixes "only one striker scores"); C7 squad-size-aware influence threshold.
- Tune against explicit targets with `stress_framework.py`: 11v11 ≈ 2.5-3.0 goals/match, ~25% draws, +10 OVR favorite wins ~55-65%; 5v5 higher-scoring. Add a scorer-Gini/HHI check: the top scorer should take a plurality, not a monopoly.
**Exit criteria:** distribution targets met over 1,000+ seeded matches per mode; goals spread across ≥3 players per team in aggregate with FWD > MID > DEF ordering.

### Phase 4 — Wire tactics, roles, and positions for real (the vision phase)
**Focus:** make managerial decisions and player placement the primary outcome drivers.
- Wire `TACTICAL_MODIFIERS` into the phase multipliers so choosing High Press / Tiki Taka / Park the Bus changes attack/defense/integrity/stamina math directly (today only player "fit" reacts).
- Make roles mechanically distinct (currently relabeling FWD→MID changes nothing measurable): role-specific contributions per phase — DEF interception weight, MID progression weight, FWD finishing access — instead of just candidate-pool filters.
- Use `preferred_zone` + the dormant `zone_coverage` in duel *resolution* (not just selection weighting): a defender defending outside his zone defends at his coverage fraction; an attacker in his zone gets his full break value.
- Wire `tactical_instruction` and `set_piece_role` into the engine, or remove them from the Lab UI until they work — a control that does nothing is worse than no control.
- Wire the inert environment knobs (`shot_density`, `stamina_drain`, `stamina_recovery`, …) into the systems they name, so 5v5 vs 11v11 balance is data-driven.
- Re-express the quality gap so tactics can beat ratings: cap `stat_multiplier`'s reach and route more probability mass through structure, zones, and mismatch terms. Acceptance test: a well-matched tactic with average players should beat a mismatched tactic with +5 OVR players a majority of the time.
**Exit criteria:** role-relabel A/B and tactics A/B probes show large, directionally-correct, statistically significant effects; instruction toggles measurably shift outcomes.

### Phase 5 — Spatial, real-time match progression
**Focus:** replace "per-minute dice with teleports" with continuous simulation, using the machinery that already exists.
- Drive possession as **pass chains** through the movement layer: carrier decisions each tick (pass/dribble/shoot) using `InfluenceMap`, `ball_tracking`, and the Field node grid — replacing `advance_carrier_position` / `scatter_defenders_to_positions` teleports, which are the root of both the geometry bias (B1) and the "not a proper match progression" feel.
- Ball becomes a physical object between owners (its physics code already exists in `entities/ball.py` — currently the ball only ever teleports with its owner).
- Real-time delivery: the engine already runs minute-steps; emit events incrementally (generator or stored event stream consumed by the existing JS ticker) so "live" mode reflects genuine engine state rather than a replayed log. A tick-based loop (e.g. 1 tick = 5-10 sim-seconds) slots into the existing `Game.play` structure.
- Keep the structural-integrity layer as the strategic resource on top of the spatial layer — they compose, not compete.
**Exit criteria:** goals traceable to a spatial sequence (positions + pass chain in the event stream); shot locations correlate with zone collapse; live view runs from the event stream.

### Phase 6 — Attribution, analytics & honest reporting
**Focus:** trustworthy post-match analysis.
- Rebuild player impact from logged events with signed contributions (misses, turnovers, dribbled-past count against you) normalized per involvement — fixes "player influence not mapped accurately".
- B5 analyst tie handling; B7 real system-vs-variance measurement; A4 narrative text driven by the same constants as the engine.
- Update `docs/specs_v1.5.md` to match shipped math — several spec numbers (variance ranges, damage bonus formula, thresholds) already diverge from code.
**Exit criteria:** impact leaderboard reproducible from the event log alone; spec and code agree.

### Iteration protocol (run at the end of every phase)
1. `tools/bias_probe.py` (mirrored teams, N≥400/mode): symmetry + collapse-reachability regression.
2. Funnel trace: possession→break→shot-decision→shot→goal conversion per side, compared against the previous phase's numbers.
3. Influence A/B battery: tactics on/off, role relabel, zone shuffle, star-player swap — each must move outcomes in the intended direction and *only* the intended direction.
4. `stress_framework.py` distribution targets (scorelines, draw rate, favorite win rate).
5. Freeze the numbers in the phase's exit report before starting the next phase, so drift is always attributable.

Fix order matters: **1 → 2 → 3** are strictly sequential (can't calibrate a biased engine; can't de-bias a broken one). **4 and 6** can be developed in parallel after 3. **5** is the largest and should start only once 4's semantics are settled, since spatial play must respect the same tactical modifiers.
