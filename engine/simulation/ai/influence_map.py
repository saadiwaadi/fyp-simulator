class InfluenceMap:
    """Initial scaffold for AI influence modeling based on shared GameState."""

    def __init__(self, zones=('Left', 'Center', 'Right')):
        self.zones = tuple(zones)

    def build(self, state):
        """
        Build a minimal influence snapshot from the single GameState source of truth.

        Returns a dict keyed by side with per-zone influence values.
        """
        field = getattr(state, 'field', None)
        zones = getattr(field, 'zone_names', self.zones)
        snapshot = {
            'home': state.get_zone_snapshot('home'),
            'away': state.get_zone_snapshot('away'),
        }
        influence = {'home': {}, 'away': {}}

        for zone in zones:
            h_val = snapshot['home'].get(zone, 0)
            a_val = snapshot['away'].get(zone, 0)
            influence['home'][zone] = max(0, h_val - a_val)
            influence['away'][zone] = max(0, a_val - h_val)

        return influence
