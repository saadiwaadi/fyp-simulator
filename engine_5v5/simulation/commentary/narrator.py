import random

# THE SCRIPT DATABASE
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
        "CAN YOU BEIEVE IT!! WHat a save",
        "Saving this team time and time an immvable wall"
    ],
    'MISS': [
        "fires wide.",
        "rushes the finish and misses.",
        "can't keep the shot down.",
        "scuffs the shot.",
        "Quite frankly an opportunity squandered"
    ],
    'TACTIC': [
        "breaks the defensive line.",
        "finds space in the pocket.",
        "exposes the gap in the structure.",
        "splits the defense with a pass."
    ],
    'TURNOVER': [
        "loses possession.",
        "is dispossessed in midfield.",
        "misplaces the pass.",
        "runs into a wall of defenders.",
        "stray pass caught"
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

def announce(minute, event_type, **kwargs):
    """
    Generates a formatted log line.
    Usage: announce(12, 'GOAL', player='Messi', score='1-0')
    """
    player = kwargs.get('player', 'Unknown')
    team = kwargs.get('team', 'Unknown')
    target = kwargs.get('target', 'Unknown') # e.g., Defender or Integrity amount
    
    # 1. Handle Phase Shifts (Special Case)
    if event_type == 'PHASE':
        phase_level = kwargs.get('level')
        return f"{minute}' {PHASE_ALERTS.get(phase_level, '').format(team=team)}"

    # 2. Select Random Phrase
    phrase = random.choice(PHRASES.get(event_type, ["Event occurred."]))
    
    # 3. Format the String
    text = f"{player} {phrase}"
    
    # 4. Add Tags based on type
    if event_type == 'GOAL':
        score = kwargs.get('score', '0-0')
        return f"{minute}' [GOAL] {text} ({score})"
    
    elif event_type == 'TACTIC':
        damage = kwargs.get('damage', 0)
        return f"{minute}' [TACTIC] {text} {team} Integrity -{damage}%"
    
    elif event_type == 'SAVE':
        return f"{minute}' [SAVE] {player} {phrase} Corner."
    
    elif event_type == 'MISS':
        return f"{minute}' [MISS] {text}"

    elif event_type == 'TURNOVER':
        return f"{minute}' [TURNOVER] {text}"
        
    elif event_type == 'BLOCK':
        return f"{minute}' [BLOCK] {text}"

    elif event_type == 'FOUL':
        return f"{minute}' [FOUL] {text}"
        
    return f"{minute}' {text}"