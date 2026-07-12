# Passing, Ball-Winning & Confidence — Mechanics Audit

**Status**: Implemented & verified via `tools/passing_probe.py`

## Lane geometry

- A lane is the segment carrier → outfield teammate, computed each sim-minute
  from **real player positions** (`passing.compute_lanes`).
- Defenders within 2.0 grid units of the segment (projection fraction
  0.08–0.95, so bodies on top of either end don't count) *shade* the lane:
  openness drops by 0.55 × closeness per blocker.
- The best-placed, best-wired blocker (`interceptions·0.6 + def_awareness·0.4`
  scaled by closeness) becomes the potential interceptor.

## Vision gating

- Lanes ≤ 4.0 units are perceived by everyone.
- Longer lanes are perceived with probability
  `(0.15 + vision/100·0.85) · reach · (0.65 + openness·0.35)` where reach
  decays with length. Verified: vision 50 sees 40% of long lanes, vision 90
  sees 69%.

## Pass resolution (position-first, stats-damped)

- Passer plays `short_passing` (short) or the repurposed **`long_passing`**
  (= legacy `passing` DB field) for switches & crosses.
- Unshaded lanes: only a small stray-ball chance (grows with distance).
- Contested lanes: exposure (1 − openness) sets the interceptor's baseline;
  both sides roll through the compressed duel curve + 0–30 noise so ratings
  tilt, never decide. Extra inherent risk: switch +6, cross +20.

## Tackling / ball-winning (`mechanics.resolve_tackle`)

- Trigger is **positional**: defensive pressure (bodies within 3.0 units)
  must exceed 0.6, and the attempt chance scales with how tight it is.
- Duel: carrier shield (`short_passing·0.6 + composure·0.4`, +5 shield edge)
  vs tackler (`tackling·0.7 + def_awareness·0.3`, + pressure×8 positioning
  bonus). `tackling` = repurposed legacy `defense` DB field.
- Verified: equal squads ≈ 45% tackle win; tackling 55 → 31%, tackling 90 →
  62%. Stats tilt without deciding.

## Crossing & switches of play

- **Switch**: any completed lane covering ≥ 40% of pitch height and ≥ 6
  units. Wide setups actively seek it: width 1 → 0.1 switches/match,
  width 5 → 5.2/match. A switch buys the subsequent break +6% space.
- **Cross**: from the wide final quarter (during the chain) or after a
  successful flank break (45% look). Delivery = `long_passing` vs the
  target's marker (nearest defender within 3.5 of the target contests even
  when off the flight path). Completion ≈ 54% overall; a completed cross
  bypasses the break duel — the ball is already in the box.

## Confidence (attacker & defender momentum)

- Every player carries `confidence` (0.05–0.95, starts ~0.5 ± match form).
- Rises: completed pass +0.015, riding a tackle +0.02, break +0.03,
  interception/tackle won +0.05, save +0.06, goal +0.12 (teammates +0.02).
- Falls: shaky touch/miss −0.04, turnover −0.04, beaten defender −0.02,
  conceding side −0.02, keeper beaten −0.05.
- Eases 2%/minute toward neutral, so spells fade naturally.
- Effect: ±6% on effective stats at the extremes (verified swing 11.9%
  floor-to-peak) — momentum colours duels, never decides them.

## Funnel after integration (baseline 11v11, verified bands)

| Metric | Value | Band |
|---|---|---|
| Goals/match | 1.67–1.88 | 1.2–2.8 |
| Pass completion | ~82% | 72–92% |
| Tackle win rate | ~45% | 30–62% |
| Cross completion | ~54% | ≤60% |
| Home/away symmetry | 49.4–49.7% possession | — |

## Dead-fields resolution (roadmap Phase 7)

- `passing` → **repurposed** as `long_passing` (switches, crosses).
- `defense` → **repurposed** as `tackling` (ball-winning duels).
- `shooting` → still reserved for shot types (drive/finesse/header).
- Squads with unpopulated legacy fields fall back to blends of modern stats.

## Doc correction

- `press_resistance` = `composure·0.7 + short_passing·0.3` (the roadmap
  table previously said `passing`; the code has always used `short_passing`).
