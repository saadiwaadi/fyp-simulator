# Project TODO & Roadmap

**Last Updated**: After motion-personalization pass + player-profile audit  
**Status**: Attribute-driven motion complete and verified ✅

---

## Completed Work

### Phase 1: Structural Integrity & Core Fixes ✅
- ✅ Fixed regen_structure() floor lift bug (state.py:88-92)
- ✅ Fixed double-compressed integrity multiplier in game.py
- ✅ Fixed drain_stamina() fatigue direction (fitter players burn less)
- ✅ Fixed stamina effectiveness gradient (was cliff at 30, now gradual below 50)
- ✅ Fixed micro-regen gate (stamina < 50 threshold, not defender.last_carried)
- ✅ Fixed away-team spawn position (relative to field.width)
- ✅ Fixed reproducibility (per-match random.Random instances)

### Phase 2: Bias & Fairness ✅
- ✅ Fixed home-advantage bias in defender scatter
- ✅ Randomized kick-off possession (was always home first)
- ✅ Fixed finish roll symmetry (±18 noise, was GK-skewed)
- ✅ Fixed team OVR calculation (from speed/defense dead fields → actual playing stats)
- ✅ Verified: 800-match regression shows symmetry intact

### Phase 3: Role & Routing ✅
- ✅ Implemented role-phase multipliers (DEF/FWD ±6% per phase)
- ✅ Fixed finisher routing (was deterministic highest finishing → 35% keep + role-weighted lay-off)
- ✅ Fixed shot decision logic (continuous, not veto)
- ✅ Tuned GOAL_MARGIN = 8 (down from 21)
- ✅ Verified: goals ~1.8/match, scoring spread FWD>MID>DEF intact

### Phase 4: Attribute-Driven Motion ✅
- ✅ Implemented MotionSystem with sub-minute render ticks (8/min)
- ✅ Wired speed attribute → move_speed (0.7 + speed/100 * 0.8)
- ✅ Wired speed attribute → quickness → motion_inertia (quick players cut sharper)
- ✅ Implemented trait-based wander (discipline/risk_appetite/work_rate shape idle motion)
- ✅ Wired system_loyalty → formation compliance (25% weight)
- ✅ Wired press slider → ball attraction multiplier (0.14 per level above 3)
- ✅ Verified with tools/motion_probe.py:
  - Tactics visibly move players (depth, width, press all measurable)
  - Personality shapes motion (discipline/maverick roam and jitter differ)
  - Speed attribute = real pace (+15% at 90 vs 55)
  - System misfits genuinely cost games (High Press: 83W vs 4W for full misfit)

### Phase 5: Visualization ✅
- ✅ Pitch canvas with real-time player dots and ball
- ✅ Movement frames export to JSON
- ✅ Frame-by-frame replay with currentMinute sync
- ✅ Pitch markings (center, box, etc.)
- ✅ Legend with player colors (home blue, away red)

---

## Known Errors & Open Items

### Dead Model Fields ⚠️ — DECISION NEEDED

| Field | Status | Current | Fate Decision |
|-------|--------|---------|----------------|
| `shooting` | Removed from team OVR | Unused in any calculation | Repurpose for long-shot power (when shot types exist) OR drop from model + Lab UI |
| `defense` | Removed from team OVR | Unused in any calculation | Repurpose for tackling/defensive interception (when defending phase lands) OR drop from model + Lab UI |
| `passing` | Fully superseded by `short_passing` | Unused in any calculation | Repurpose for long passing (when passing lanes land) OR drop from model + Lab UI |

**Action**: Decide now or defer to next session after passing lanes implemented. If dropped, also remove from DB schema, Lab creation UI, and any player-creation defaults.

### Fit Multiplier Calibration ⚠️ — MONITORING

- Current: ±10% (softened from ±18%)
- Status: Verified safe in motion_probe.py; High Press effect is stamina-driven, not fit-dominated
- Action: Watch in real-team play (non-probe matches) to see if profile identity still reads strongly; re-tune via probe4 battery if personality fades

### Open Future Features (Not Blocking)

- **Passing lanes & chains** (agreed next phase): pass chains between real positions, vision gating, short_passing execution, interceptors reading lanes
- **Shot types** (post-passing): drive, finesse, header, free kick — will unlock `shooting` field repurposing
- **Defending phase** (post-shot): actual tackling, clearances, goalkeeper distribution — will unlock `defense` field repurposing
- **Responsive UI** (deferred): mobile pitch layout, better mobile touch support

---

## Remaining Work (Priority Order)

### 🔴 PHASE 6: Ball Possession & Passing Lanes (NEXT SESSION)

**Scope**: Implement passing-phase duel where vision and short_passing drive chain success  
**Deliverables**:
1. Compute passing lanes between all live players (carrier → teammates)
2. Vision-gated lane perception (carrier can't see lanes to low-vision players)
3. Short_passing duel success (success % vs nearby defenders)
4. Interceptor reading (defenders with high interceptions + def_awareness read lanes)
5. Passing probe tool: verify lanes are computed, vision gates them, interceptions block them
6. Integration into funnel: possession → passing chain → break/breakdown → shot

**Files to touch**:
- `engine/simulation/systems/mechanics.py`: add `passing_duel()` alongside existing duel types
- `engine/simulation/core/formation.py`: compute lane positions and visibility
- `tools/passing_probe.py`: new verification tool (lane count, vision effect, interception blocking)
- `docs/passing-audit.md`: document lane geometry and trait effect matrix

**Estimated LOC**: ~200 (lane math) + ~150 (duel logic) + ~100 (probe)

---

### 🟡 PHASE 7: Dead Fields Decision & Cleanup

**Scope**: Resolve fate of `passing`, `shooting`, `defense` fields  
**Options**:
- **Option A (Repurpose)**: Keep fields in model, redefine them for long passing / shot power / tackling when those phases land
- **Option B (Drop)**: Remove from SimPlayer, remove from DB schema, remove from Lab UI

**Action Items**:
1. Decide which option in next sync
2. If Option A: update field names/comments to clarify future repurposing
3. If Option B:
   - Remove from `engine/simulation/entities/player.py` (attrs)
   - Remove from `engine/simulation/core/game.py` (team OVR calculation)
   - Remove from DB Player model (if using one)
   - Remove from Lab UI player-creation form
   - Remove from tools/motion_probe.py test squad defaults

**Estimated LOC**: ~50 (if Drop) / ~20 (if Repurpose)

---

### 🟡 PHASE 8: Fit Multiplier Real-Team Testing

**Scope**: Verify ±10% fit multipliers still make profile personality visible in non-probe matches  
**Acceptance**:
- Run 50 real-seed matches with diverse squads (High Press suit + misfit + neutral)
- Measure win% distribution — should still show fit effect without being auto-loss
- If personality fades, run probe4 to calibrate new multipliers

**Files**:
- `tools/probe4.py`: add fit-sweep sub-battery (±5%, ±10%, ±15%, ±20%)

**Estimated LOC**: ~80

---

### 🟢 PHASE 9: Passing Lanes Integration & Funnel Validation (Post Phase 6)

**Scope**: Wire passing duel into full funnel, re-validate end-to-end  
**Acceptance**:
- Possessions can now pass (not just break directly)
- Break rate should drop (because passing chains absorb time)
- Goal funnel: possession → pass → break → shot → goal (4 gates vs 3 before)

**Files**:
- `engine/simulation/core/game.py`: update possession phase to allow passes
- `tools/funnel_probe.py`: measure pass rate, break rate, goal rate per 1000 possessions

**Estimated LOC**: ~100

---

### 🟢 PHASE 10: Defending Phase (Post Passing, Further Future)

**Scope**: When passing lands, add defending phase (tackles, clearances, GK distribution)  
**Unlocks**: `defense` field repurposing (tackling power)  
**Estimated LOC**: ~300

---

## Known Limitations & Caveats

1. **Passing will change funnel balance**: Once passing lands, possession success % will drop (chains add duration), meaning break rates will drop and goal rates will change. All calibrations will need re-tuning.

2. **Fit multipliers are blunt**: ±10% is uniform across all duels. Could refine to per-phase multipliers later (e.g., High Press penalties only in possession, not shot).

3. **Motion inertia is global per player**: All turns use same quickness value. Could refine to stamina-scaled inertia (tired players move wider paths) later.

4. **Dead fields can't be recovered**: If you choose to drop `passing/shooting/defense`, old data won't auto-repopulate when those phases land. Plan accordingly.

5. **Pitch visualization is frame-based**: Uses recorded motion frames, not live simulation. If match runs 90 frames and replay logic advances by 1 frame per key, replay won't catch up on fast playback.

---

## Quick Reference: What Drives What

### Attributes → Effects (Complete Map)

| Attr | Drives | Status |
|------|--------|--------|
| `speed` | move_speed, quickness, team OVR | ✅ Wired |
| `stamina` | energy pool, work_rate, discipline (40%), recovery | ✅ Wired |
| `short_passing` | possession duels, selfishness (−), system_loyalty, press_resistance (30%) | ✅ Wired |
| `vision` | break duels, system_loyalty, Tiki Taka fit | ✅ Wired, **next**: lane gating |
| `interceptions` | possession-defense duels, High Press fit | ✅ Wired, **next**: lane reading |
| `def_awareness` | break-defense duels, discipline (60%), Park Bus fit | ✅ Wired |
| `finishing` | finish rolls, finisher routing, selfishness (+), chaos_thrives | ✅ Wired |
| `composure` | GK saves, risk_appetite (inv), shot decision, Park Bus fit | ✅ Wired |
| `shooting` | **DEAD** — repurpose or drop | ⚠️ Decision pending |
| `defense` | **DEAD** — repurpose or drop | ⚠️ Decision pending |
| `passing` | **DEAD** — repurpose or drop | ⚠️ Decision pending |

### Traits → Formula → Effect (Complete Map)

| Trait | Formula | Drives | Status |
|-------|---------|--------|--------|
| `discipline` | def_aw·0.6 + stamina·0.4 | duel bonus (defend), leash, scatter depth, idle amplitude | ✅ Wired |
| `risk_appetite` | 1 − composure | forward drift, idle amplitude | ✅ Wired |
| `work_rate` | stamina | ball attraction, burn efficiency, fidget freq | ✅ Wired |
| `system_loyalty` | (short_passing + vision)/2 | **25% of formation compliance** — low-loyalty players drift off script | ✅ Wired (this pass) |
| `selfishness` | finishing − short_passing | shoot-vs-recycle, FWD drift | ✅ Wired |
| `press_resistance` | composure·0.7 + passing·0.3 | shrug off possession pressure | ✅ Wired |
| `chaos_thrives` | smooth from 65 finishing | finish bonus vs collapsed defenses | ✅ Wired |
| `quickness` | (speed − 40)/50 | motion inertia — sharp vs curved paths | ✅ Wired (this pass) |

---

## Testing & Verification Tooling

| Tool | Purpose | Status |
|------|---------|--------|
| `tools/bias_probe.py` | Regression: symmetry, mirrored outcome, collapse reachability | ✅ Passing |
| `tools/motion_probe.py` | 4-part motion verification: tactics, personality, speed, fit | ✅ Passing |
| `tools/probe4.py` | Per-phase sanity (goals/duel/pace targets, no NaN) | ✅ Passing |
| `tools/passing_probe.py` | *Future*: lane geometry, vision gating, interception blocking | 🔜 Phase 6 |
| `tools/funnel_probe.py` | *Future*: possession/break/shot/goal rates per match volume | 🔜 Phase 9 |

---

## Summary for Next Session

**Pick up here**: Implement ball passing and passing lanes  
**Before that**: Review dead-fields decision (repurpose vs drop)  
**Blocker**: None — all motion & attribute work is complete  

**Expected output from Phase 6**:
- Passing duels working in funnel
- Lanes gated by vision, blocked by interceptions
- Passing probe showing lane counts, vision effect, interception rate
- Funnel balance shift documented (pass rate, break rate, goal rate)
