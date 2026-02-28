# engine/simulation/state.py
# ============================================================
# PHASE A — ZONAL STRUCTURE MODEL
#
# KEY ARCHITECTURAL DECISION:
#   structure["overall"] is now a COMPUTED value, never written directly.
#   All structural changes go through degrade_structure() or regen_structure().
#   This is the single source of truth rule — no direct struct writes anywhere else.
#
# ZONE WEIGHT PHILOSOPHY:
#   Center = 50%, Left = 25%, Right = 25%
#   Reflects football's compactness bias — the spine matters most.
#
# BLEED MODEL:
#   An attack on Center bleeds both flanks (15% each).
#   An attack on a flank bleeds Center only (15%).
#   This creates spatial imbalance WITHOUT destroying the whole structure.
# ============================================================


class MatchState:
    def __init__(self, home_team, away_team):
        # --- ZONAL STRUCTURE BLOCKS ---
        self.home_structure = self._init_structure()
        self.away_structure = self._init_structure()

        # --- STATS SHEET ---
        # Everything the analyst and template will read.
        self.stats = {
            'home_score': 0, 'away_score': 0,
            'home_possession_count': 0, 'away_possession_count': 0,
            'home_shots': 0, 'away_shots': 0,
            'home_on_target': 0, 'away_on_target': 0,
            'home_passes_attempted': 0, 'home_passes_completed': 0,
            'away_passes_attempted': 0, 'away_passes_completed': 0,
            'home_corners': 0, 'away_corners': 0,
            'home_fouls': 0, 'away_fouls': 0,
            'home_offsides': 0, 'away_offsides': 0,

            # Overall integrity finals (backwards compat for template)
            'home_integrity_final': 100,
            'away_integrity_final': 100,

            # PHASE A: Zonal integrity finals for Deep Scan zone breakdown
            'home_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},
            'away_zone_finals': {'Left': 100, 'Center': 100, 'Right': 100},
        }

    # ============================================================
    # STRUCTURE FACTORY
    # ============================================================

    def _init_structure(self):
        """
        Creates a fresh zonal structure block at full integrity.
        All zones start at 100. Overall is the weighted average.
        Phase is narrative (4=Solid, 0=Collapse), driven by overall.
        Line slots (def_line, mid_line, att_line) preserved for future
        11v11 vertical structure layer — not yet wired into math.
        """
        return {
            # THE THREE COMBAT ZONES — these drive all math
            "zones": {
                "Left":   100.0,
                "Center": 100.0,
                "Right":  100.0,
            },
            # COMPUTED WEIGHTED AVERAGE — do NOT write to this directly.
            # Always call _update_overall() after any zone modification.
            "overall": 100.0,
            # Narrative phase tracker (0=Collapse, 4=Solid)
            "phase": 4,
            # Future 11v11 vertical layers — preserved for V6
            "def_line": 100.0,
            "mid_line": 100.0,
            "att_line": 100.0,
        }

    # ============================================================
    # INTERNAL UTILITY — OVERALL SYNC
    # ============================================================

    def _update_overall(self, struct):
        """
        Recomputes and writes overall from current zone values.
        CENTER weighted 50% (spine of defense).
        LEFT and RIGHT weighted 25% each.

        RULE: Call this at the end of EVERY method that touches zones.
        Missing this call = overall desyncs = analytics lies.
        """
        z = struct["zones"]
        struct["overall"] = round(
            (z["Center"] * 0.50) + (z["Left"] * 0.25) + (z["Right"] * 0.25),
            2
        )

    # ============================================================
    # STRUCTURAL DAMAGE — ZONE-AWARE
    # ============================================================

    def degrade_structure(self, team_side, raw_damage, zone="Center"):
        """
        PHASE A: Applies zone-specific structural damage with spatial bleed.

        DAMAGE SPLIT:
          Primary zone:    70% of raw_damage
          Adjacent zones:  15% of raw_damage each

        Adjacency map:
          Center → bleeds Left AND Right
          Left   → bleeds Center only
          Right  → bleeds Center only

        Why bleed? Because in football, an attack down the right
        doesn't just hurt Right — it pulls defenders, which weakens
        the center. That's the imbalance philosophy made mathematical.

        NON-LINEAR DECAY THRESHOLDS (preserved from V4):
          >75 = CONCRETE (0.6x)   — hard to break through
          >50 = WOOD    (1.0x)    — normal resistance
          >25 = GLASS   (1.3x)    — crumbling shape
           ≤25 = SAND    (1.6x)   — defensive panic
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        zones = struct["zones"]

        # Validate zone key — default to Center if something went wrong
        if zone not in zones:
            zone = "Center"

        # Adjacency: what zones bleed when this zone is attacked
        adjacent_map = {
            "Left":   ["Center"],
            "Center": ["Left", "Right"],
            "Right":  ["Center"],
        }

        def _apply_to_zone(z_name, dmg):
            """Apply non-linear decay modifier to a specific zone."""
            current = zones[z_name]
            if current > 75:   modifier = 0.6   # CONCRETE
            elif current > 50: modifier = 1.0   # WOOD
            elif current > 25: modifier = 1.3   # GLASS
            else:              modifier = 1.6   # SAND
            zones[z_name] = max(0.0, round(current - (dmg * modifier), 2))

        # Primary hit: 70% of raw damage
        _apply_to_zone(zone, raw_damage * 0.70)

        # Bleed: 15% per adjacent zone
        for adj in adjacent_map.get(zone, []):
            _apply_to_zone(adj, raw_damage * 0.15)

        # Sync overall from new zone values
        self._update_overall(struct)

    # ============================================================
    # STRUCTURAL REGENERATION — ZONE-AWARE
    # ============================================================

    def regen_structure(self, team_side, amount, zone=None, floor=40):
        """
        PHASE A: Zone-specific or spread regeneration.

        zone=None  → spread heal across all zones (e.g. halftime, goal reset)
        zone="Left" → targeted heal on that zone (e.g. defender wins ball in Left)

        FLOOR: No zone can drop below this value through regen.
        The floor prevents regen from accidentally bringing a zone UP
        past where it should be (regen only heals, the floor is a minimum).

        Note: The 40 floor is the 'never fully collapses' guarantee from V4.
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        zones = struct["zones"]

        if zone and zone in zones:
            # Targeted zone recovery
            zones[zone] = max(floor, min(100.0, zones[zone] + amount))
        else:
            # Spread recovery — divide evenly across all three zones
            spread = amount / 3.0
            for z in zones:
                zones[z] = max(floor, min(100.0, zones[z] + spread))

        # Sync overall
        self._update_overall(struct)

    # ============================================================
    # STRUCTURE MULTIPLIER — ZONE-AWARE
    # ============================================================

    def get_structure_mult(self, team_side, zone=None):
        """
        Returns the effectiveness multiplier for structural math.

        zone provided → use that zone's specific health (precise, for combat)
        zone=None     → use overall (for analytics reads, backwards compat)

        SCALE: 100% integrity = 1.0x | 0% integrity = 0.6x
        Even a fully collapsed defense still has 60% effectiveness.
        (Players don't vanish — they just fall apart.)
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure

        if zone and zone in struct["zones"]:
            val = struct["zones"][zone]
        else:
            val = struct["overall"]

        return 0.6 + (0.4 * (val / 100.0))

    # ============================================================
    # PHASE SHIFT — NARRATIVE ALERTS (uses overall)
    # ============================================================

    def check_phase_shift(self, team_side, team_name):
        """
        Narrative phase alerts still use OVERALL for clean storytelling.
        Zonal data drives the math. Overall drives the story.
        These are the dramatic broadcast moments in the match log.
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        current_phase = struct["phase"]
        val = struct["overall"]

        new_phase = current_phase
        msg = None

        if val < 30 and current_phase > 0:
            new_phase = 0
            msg = f"☠️  [PHASE] {team_name.upper()}: STRUCTURAL COLLAPSE IMMINENT."
        elif val < 45 and current_phase > 1:
            new_phase = 1
            msg = f"🚨 [PHASE] {team_name}: Shape Unstable. Gaps everywhere."
        elif val < 60 and current_phase > 2:
            new_phase = 2
            msg = f"⚠️  [PHASE] {team_name}: Defensive line stretched."
        elif val < 75 and current_phase > 3:
            new_phase = 3
            msg = f"⚠️  [PHASE] {team_name}: Slight structural distortion."

        if new_phase != current_phase:
            struct["phase"] = new_phase
            return msg
        return None

    # ============================================================
    # SNAPSHOT UTILITY — FOR TIMELINE & DEEP SCAN
    # ============================================================

    def get_zone_snapshot(self, team_side):
        """
        Returns a clean {zone: int_value} dict of current zone health.
        Used for:
          - Timeline logging (every N minutes)
          - Finalize step (zone_finals in stats)
          - Debug prints during development
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        return {z: int(v) for z, v in struct["zones"].items()}

    def get_weakest_zone(self, team_side):
        """
        Returns the name of the most damaged zone.
        Useful for: AI targeting, commentary, analyst decisions.
        e.g. "Away's Left zone is at 32 — attack there."
        """
        struct = self.home_structure if team_side == 'home' else self.away_structure
        return min(struct["zones"], key=lambda z: struct["zones"][z])