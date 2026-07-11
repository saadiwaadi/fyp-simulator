import random

# THE SCRIPT DATABASE (v2.6 Spatial Edition)
PHRASES = {
    'GOAL': [
        "smashes it home!",
        "finds the bottom corner!",
        "capitalizes on the chaos!",
        "fires it past the keeper!",
        "finishes clinically!",
        "On the money"
    ],
    'SAVE': [
        "dives to the rescue.",
        "pulls off a miracle save.",
        "denies the effort with a fingertip.",
        "blocks the shot point-blank.",
        "CAN YOU BELIEVE IT!! What a save",
        "An immovable wall, saving this team time and again"
    ],
    'MISS': [
        "fires wide.",
        "rushes the finish and misses.",
        "can't keep the shot down.",
        "scuffs the shot.",
        "Quite frankly an opportunity squandered"
    ],
    'TACTIC': [
        # Combined with {zone} later in the formatter
        "breaks the defensive line through the",
        "finds space in the pocket in the",
        "exposes the gap in the structure via the",
        "splits the defense with a pass down the"
    ],
    'TURNOVER': [
        "loses possession in the",
        "is dispossessed in the",
        "misplaces a pass in the",
        "runs into a wall of defenders in the",
        "has a stray pass caught in the"
    ],
    'BLOCK': [
        "reads the play perfectly.",
        "steps in to intercept.",
        "clears the danger.",
        "holds the defensive line.",
        "Reads them like a book"
    ],
    'FOUL': [
        "commits a tactical foul.",
        "brings down the attacker.",
        "stops the play illegally.",
        "Quite a bit of foul temper there"
    ]
}

PHASE_ALERTS = {
    0: "☠️ [PHASE] {team}: They’re hanging by a thread. One more push could break them.",
    1: "🚨 [PHASE] {team}: The back line is wobbling. Too many gaps opening up.",
    2: "⚠️ [PHASE] {team}: They’re getting stretched now. Midfield losing control.",
    3: "⚠️ [PHASE] {team}: Slight cracks in the shape. Pressure building."
}

def announce(minute, event_type, rng=None, **kwargs):
    rng = rng or random
    player = kwargs.get('player', 'Unknown')
    team = kwargs.get('team', 'Unknown')
    
    # [v2.6] Zone Mapping
    zone_raw = kwargs.get('zone', 'C')
    zone_map = {'L': 'Left Wing', 'C': 'Center', 'R': 'Right Wing'}
    zone_name = zone_map.get(zone_raw, 'Center')

    # 1. Handle Phase Shifts
    if event_type == 'PHASE':
        phase_level = kwargs.get('level')
        return f"{minute}' {PHASE_ALERTS.get(phase_level, '').format(team=team)}"

    # 2. Select Random Phrase
    phrase = rng.choice(PHRASES.get(event_type, ["Event occurred."]))
    
    # 3. Format based on type
    if event_type == 'GOAL':
        score = kwargs.get('score', '0-0')
        return f"{minute}' [GOAL] {player} {phrase} ({score})"
    
    elif event_type == 'TACTIC':
        damage = kwargs.get('damage', 0)
        # Result: "12' [TACTIC] Messi finds space in the pocket in the Left Wing! Home Integrity -5%"
        return f"{minute}' [TACTIC] {player} {phrase} {zone_name}! {team} Integrity -{damage}%"
    
    elif event_type == 'TURNOVER':
        # Result: "24' [TURNOVER] Kroos misplaces a pass in the Center"
        return f"{minute}' [TURNOVER] {player} {phrase} {zone_name}"

    elif event_type == 'SAVE':
        return f"{minute}' [SAVE] {player} {phrase} Corner."

    # Standard Fallback for MISS, BLOCK, FOUL
    text = f"{player} {phrase}"
    return f"{minute}' [{event_type}] {text}"