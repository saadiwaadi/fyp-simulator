# Fix Log — Engine Overhaul (from `docs/system-audit-v1.md`)

Every change below was validated with the probe suite (`tools/bias_probe.py`,
funnel traces, and the influence A/B battery). "Before" numbers come from the
audit; "after" numbers from the same probes on the fixed engine.

## Headline before → after (mirrored teams, identical squads)

| Metric (11v11) | Before | After |
| --- | --- | --- |
| Draws | 96% (nearly all 0-0) | ~40% |
| Goals per match | 0.04 | ~1.8 (equal teams; more in mismatches) |
| Home vs away goals | 15 vs 2 (p≈0.0004) | 735 vs 697 over N=800 (statistically even; funnel identical at every stage) |
| Deterministic replay from seed | No (global RNG) | Yes |
| Structural collapse reachable | Never (min zone 78+) | Yes (mismatch/fatigue games reach broken/collapsed states) |
| Roles affect outcomes | No (relabel test: no change) | Yes (FWD-less side scores less & loses more; FWD > MID > DEF scoring: 392/233/11) |
| Scoring distribution | One striker monopoly (design), then flat | Strikers lead, spread across squad |
| +3 OVR favorite | (untested; +10 was 100% blowout at 1972-1 goals) | 71% of decisive results, 40% draws; +10 still dominant by design (no rubber-banding) |

## Phase 1 — Correctness

| Audit ID | Fix | File |
| --- | --- | --- |
| A1 | Regen clamps to 100 instead of lifting collapsed zones back to 40 | `core/state.py` |
| A2 | Integrity multiplier applied once (real range 0.6–1.0, was 0.84–1.0) | `core/game.py` |
| A3 | Micro-regen gate rewritten: only defenders below 50 stamina recover | `systems/recovery.py` |
| A4 | Shared constants module; breach thresholds identical in engine & analyst; minute logic scales with `max_minutes` | `constants.py`, `core/game.py`, `analyst.py` |
| A5 | Shots, on-target, passes, corners now actually counted | `systems/phases.py` |
| A6 | Kick-off placement relative to pitch size (away no longer spawns off a 14-wide 5v5 pitch) | `core/game.py` |
| A7 | Per-match `random.Random(match_seed)` threaded through all systems — reproducible replays, no cross-match RNG interference | all simulation modules |
| A8 | Blanket `except Exception` around duellist selection removed | `core/game.py` |
| A9 | Minute-1 debug `print` removed | `core/game.py` |
| — | Structure phase can recover upward silently (was one-way ratchet) | `core/state.py` |
| — | Views default lineup builds a proper XI by role — the `[:11]` slice fielded **11 goalkeepers** (players stored grouped by role) | `views.py` |

## Phase 2 — Symmetry (home-bias removal)

| Audit ID | Fix |
| --- | --- |
| B1 | Defender scatter computed as distance-from-own-goal then mirrored (was multiplicative for home, additive for away — the dominant measured bias) |
| B2 | Kick-off possession randomized per match; ball reset to center after goals |
| B3 | Quality gap applied once on the attacking side only (defender no longer got a conditional boost that double-punished weaker teams) |
| B4 | Home-only `sys_style` parameter deprecated; both teams read from their own team object |
| B6 | Center-zone anti-repetition applied to zone weights **before** duellist selection (stats no longer mislabeled) |

Validation: N=800 mirrored matches — goals 735/697, possession 49.7%, and the
instrumented funnel (turnovers/blocks/breaks/build-ups/lane-blocks/shots/goals)
is statistically identical per side.

## Phase 3 — Calibration (goal funnel & scorer distribution)

| Audit ID | Fix |
| --- | --- |
| C1 | `should_attempt_shot` is a continuous probability (position, role, temperament, pressure) — the old `danger < 0.15` veto killed ~95% of successful breaks |
| C2 | Finish roll: symmetric ±18 noise both sides (was skewed pro-GK), tuned `GOAL_MARGIN = 8` / `SAVE_WINDOW = 8` |
| C3 | Integrity bonus scales from true zone health (floor removed); collapse now feeds finishing as the spec intended |
| C4 | Early-finish damping uses `EARLY_FINISH_FRACTION` of `max_minutes` (was hard-coded minute 25 — 62% of a 5v5 match) |
| C5 | `chaos_thrives` is a smooth curve from 65 finishing (was a hard cliff at 80 that gave one striker a scoring monopoly) |
| C6 | Fatigue direction corrected in both places: fitter players/teams now burn *less* per action, tired squads pay more (mild, no death spiral); effective-stat decay is a gradient below 50 stamina instead of a cliff at 30 |
| C7 | Influence penalty threshold scales with squad size (`max_minutes*2.5/squad_size`) — 5v5 players are no longer blanket-nerfed |
| — | Duel-value compression (`60 + (stat-60)*0.40`): ratings tilt duels instead of deciding them, so tactics/structure/positioning carry real weight — the "good tactics + decent players beats mismatched stars" lever |

## Phase 4 — Dormant features wired

| Feature | Now does |
| --- | --- |
| `TACTICAL_MODIFIERS` (High Press / Tiki Taka / Park the Bus / Counter) | `att` multiplies possession & break attack; `def` multiplies defense; `int` divides structural damage taken; `stam` multiplies burn rate |
| `zone_coverage` | Playing or defending outside your preferred zone costs the coverage fraction in duel resolution |
| Role-phase modifiers | DEF defend better/attack worse, FWD attack better/defend worse, MID balanced, GK poor outfield — roles are a real mechanical choice |
| Finisher routing | Successful breaks route the chance to a finisher (role-weighted, selfishness-aware lay-off) — strikers finish what midfielders create |
| Midfield battles | Defended by MID/DEF (was MID/FWD, which made forwards a pure defensive liability and strikerless squads optimal) |
| Env knobs | `fatigue_scale` and `shot_frequency_modifier` wired into burn rates and shot decisions |

Still intentionally dormant (documented for the future spatial phase):
`InfluenceMap`, `ball_tracking`, `seek()`, the Field node grid,
`tactical_instruction`, `set_piece_role`, `shot_density`, `stamina_drain`,
`stamina_recovery`, `match_duration`.

## Phase 5 — Attribution & reporting

- System-vs-variance attribution measured from per-duel roll margins
  (`mechanics._record_attribution`) instead of fixed increments that always
  declared "Systemic Victory".
- Analyst tie handling: zone dominance ties are "Contested"; draws grade the
  better-held structure instead of always grading the away team.
- Player impact includes negative events (misses, turnovers) so the
  leaderboard reflects contribution, not touch count.
- Analyst narrative reads the same constants the engine flags with.

## Current calibration values (for future tuning)

| Knob | Value | Where |
| --- | --- | --- |
| `GOAL_MARGIN` / `SAVE_WINDOW` | 8 / 8 | `systems/mechanics.py` |
| Duel compression slope | 0.40 | `systems/mechanics.py` |
| Duel noise | poss ±0–28, break ±0–32, finish ±18 | `systems/mechanics.py` |
| Stat multiplier | 1 ± adv/200, clamp [0.92, 1.08] | `core/game.py` |
| Base damage | 3.5 (11v11) / 6.0 (5v5) | `systems/environment.py` |
| Regen | turnover 0.3, block 0.6, lane-block 0.6, goal ≤15 spread | `systems/phases.py` |
| Shot decision base | 0.34 + danger·0.40 + role·0.25 − pressure·0.30 | `ai/decision.py` |
| Breach thresholds | stamina < 50, integrity < 50 | `constants.py` |

## How to re-validate after any change

```
python tools/bias_probe.py 400        # symmetry + collapse reachability
```
plus the influence battery (tactics on/off, role relabel, quality gradient)
— every change should move only the outcome it targets.
