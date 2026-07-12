"""Single source of truth for thresholds shared by the engine and the analyst.

Keeping these here prevents the engine flagging an event at one value while
the post-match report describes it at another.
"""

# Average squad stamina below this flags the fatigue breach minute.
FATIGUE_BREACH_STAMINA = 50

# Overall structural integrity below this flags the structural breach minute.
STRUCT_BREACH_INTEGRITY = 50

# A fatigue breach later than this fraction of the match is rated sustainable.
PRESS_SUSTAINABLE_FRACTION = 0.75

# Early-match finishing is damped until this fraction of the match has passed.
EARLY_FINISH_FRACTION = 0.25
