# 📄 TACTICAL ENGINE v1.5 — TECHNICAL SPECIFICATION
**Status:** SUPERSEDED — see `docs/fix-log.md` for the v2.0 engine behaviour (several numbers below no longer match the shipped math)
**Date:** February 15, 2026
**Architecture:** Django (Backend) / JavaScript (Ticker) / SQLite (Data)

### 1. SYSTEM ARCHITECTURE
The engine operates as a **deterministic structural simulation** with controlled variance. It is not a random number generator; it is a resource management system where "Integrity" acts as a team's collective health bar.

* **Core Loop:** 90 Minutes / 3-minute increments (30 turns).
* **State Management:** Stateless processing (inputs → math → outputs). No persistent session data between matches.
* **Visual Layer:** "Live Broadcast" terminal simulation via delayed DOM manipulation (0.4s – 0.8s ticker speed).

### 2. SIMULATION PHYSICS (The Causality Chain)
The engine resolves matches through a strictly ordered four-phase logic gate.

1.  **Possession Phase:**
    * **Input:** Attacker `Short Passing` vs Defender `Interceptions`.
    * **Variance:** Low (`±10`).
    * **Outcome:** Success grants a roll at Phase 2; Failure results in `[TURNOVER]`.
2.  **Tactical Phase:**
    * **Input:** Attacker `Vision` vs Defender `Defensive Awareness`.
    * **Variance:** Medium (`±15`).
    * **Outcome:** Success triggers **Structural Damage** (Phase 3); Failure results in `[BLOCK]` or `[FOUL]`.
3.  **Structural Phase (The Collapse Model):**
    * **Concept:** Successful attacks degrade the opponent's organization (`Integrity`).
    * **Base Damage:** `3–6` points.
    * **Fatigue Multiplier:** Damage increases non-linearly as defender stamina drops below `45` and `25`.
4.  **Finishing Phase:**
    * **Input:** Attacker `Finishing` vs GK `Composure`.
    * **Modifier:** Attacker gains a massive bonus based on opponent's missing integrity (`(100 - Integrity) / 3`).
    * **Variance:** High (`±25`).
    * **Outcome:** `[GOAL]`, `[SAVE]`, or `[MISS]`.

### 3. INTEGRITY DECAY MODEL
Integrity does not scale linearly; it utilizes "Material Phases" to simulate psychological collapse.

| Phase | Integrity % | Resistance Modifier | Description |
| :--- | :--- | :--- | :--- |
| **Concrete** | 100–76% | 0.6x Damage | Organized. Hard to break down. |
| **Wood** | 75–51% | 1.0x Damage | Standard play. Breaks occur normally. |
| **Glass** | 50–26% | 1.3x Damage | Fragile. One break leads to another. |
| **Sand** | 25–0% | 1.6x Damage | Terminal collapse. Goals flow freely. |

### 4. ATTRIBUTE MAP
Only these 7 attributes influence the simulation. All others are cosmetic.

| Attribute | Function | Impact Phase |
| :--- | :--- | :--- |
| **Short Passing** | Ball Retention | Phase 1 (Possession) |
| **Interceptions** | Ball Recovery | Phase 1 (Possession) |
| **Vision** | Creating Chances | Phase 2 (Tactical) |
| **Def. Awareness** | Preventing Chances | Phase 2 (Tactical) |
| **Stamina** | Damage Mitigation | Phase 3 (Structural) |
| **Finishing** | Scoring Probability | Phase 4 (Finishing) |
| **Composure** | Save Probability | Phase 4 (Finishing) |

### 5. DESIGN PHILOSOPHY
* **The "Roy Keane" Factor:** High `Interception` stats can neutralize superior teams by killing moves in Phase 1, preventing Phase 2 damage entirely.
* **The Late Game:** Matches are decided in the final 20 minutes. A team with 90+ Stamina will retain "Concrete" or "Wood" integrity longer than a skilled team with 70 Stamina.
* **No "Rubber Banding":** There is no artificial logic to keep games close. If a team hits "Sand" phase in the 60th minute, they will lose 5-0.