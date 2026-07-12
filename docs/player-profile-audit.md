# Player Profile Audit — attributes, traits, and what they actually affect

Status after the motion-personalization pass (see `tools/motion_probe.py` for
the verification suite). ✅ = wired and verified, 🔧 = fixed in this pass,
⚠️ = known inconsistency left open.

## Attribute → effect map (current, shipped)

| Attribute | Drives | Notes |
| --- | --- | --- |
| `speed` | 🔧 movement pace (`move_speed`), turn sharpness (`quickness` → motion inertia), team OVR | **Was completely unused for motion** — pace derived from stamina. Verified: speed-90 squad covers ~15% more ground per frame than speed-55. |
| `stamina` | energy pool, `work_rate` (ball-hunting, fidget frequency, burn efficiency), `discipline` (40%), High Press fit, recovery ceiling | Deliberate super-stat; no longer drives pace. |
| `short_passing` | possession duels, `selfishness` (−), `system_loyalty`, `press_resistance` (30%), Tiki Taka fit | |
| `vision` | break-attack duels, `system_loyalty`, Tiki Taka fit | Will drive passing-lane perception in the passing phase (next). |
| `interceptions` | possession-defense duels, High Press fit | |
| `def_awareness` | break-defense duels, `discipline` (60%), Park the Bus fit | |
| `finishing` | finish rolls, finisher-routing weight, `selfishness` (+), `chaos_thrives` | |
| `composure` | GK save rolls, `risk_appetite` (inverse), shot decision, Park Bus fit | Double-duty (GK stat + outfield temperament) — acceptable, documented. |
| `shooting`, `defense` | 🔧 removed from team OVR | ⚠️ Now fully dead model fields. Either repurpose (e.g. `shooting` = long-shot power once shot types exist) or drop from the model + UI. |
| `passing` | nothing | ⚠️ Fully dead (superseded by `short_passing`). Same choice: repurpose as long passing when passing lanes land, or remove. |

## Trait → effect map

| Trait (derived) | Formula | Drives |
| --- | --- | --- |
| `discipline` | def_aw·0.6 + stamina·0.4 | duel bonus when defending breaks, positional tightness (leash), scatter track-back depth, 🔧 smaller idle-wander amplitude |
| `risk_appetite` | 1 − composure | forward drift off-anchor, 🔧 larger idle-wander amplitude |
| `work_rate` | stamina | ball attraction, burn efficiency, 🔧 fidget frequency |
| `system_loyalty` | (short_passing + vision)/2 | 🔧 **was computed but never read** — now 25% of formation compliance: low-loyalty players drift off the tactical script |
| `selfishness` | finishing − short_passing | shoot-vs-recycle decision, keeping the finish instead of laying off, FWD goal-hanging drift |
| `press_resistance` | composure·0.7 + passing·0.3 | shrugging off possession pressure |
| `chaos_thrives` | smooth from 65 finishing | finishing bonus vs collapsed defenses |
| `quickness` 🔧 new | (speed − 40)/50 | motion inertia — quick players cut sharper, slow players carve wider arcs |

## Verified this pass (`tools/motion_probe.py`)

1. **Tactics visibly move players**: depth 1→5 pushes the mean line 5.97→8.12;
   width 1→5 spreads the block 1.99→2.68; press 1→5 squeezes the line up
   (6.95→7.32) via press-scaled ball attraction (new coupling).
2. **Personality shapes motion**: maverick (low composure/def_aw) idles with
   ~2.5× wander amplitude and higher measured jitter; the disciplined player's
   larger *total* roam is his deeper defensive track-backs — both intended.
3. **Speed attribute = real pace** (+15% ground covered at 90 vs 55).
4. **System misfits genuinely suffer**: a low-stamina squad forced to run High
   Press loses ~84/120 vs a neutral opponent (fit multipliers softened to ±10%
   so this is dominated by the real stamina cost, not a hidden fit blowout).
5. Full regression green: mirrored symmetry intact, goals ~1.8/match, +3 OVR
   favorite at 74% of decisive results, FWD>MID>DEF scoring spread unchanged.

## Open items / next session

- **Passing & lanes** (agreed next): pass chains between real positions,
  `vision` gating which lanes a carrier perceives, `short_passing` execution,
  interceptors reading lanes with `interceptions` + `def_awareness`.
- Decide fate of dead fields `passing`, `shooting`, `defense` (repurpose for
  long balls / shot power / tackling when the passing phase lands, or remove
  from model + Lab UI).
- Fit multipliers now ±10%: watch whether profile identity still reads
  strongly enough in real-team play; tune via `probe4` battery if not.
