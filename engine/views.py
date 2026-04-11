from django.shortcuts import render, redirect, get_object_or_404
from .models import Team, Player, Match
from .simulation.engine import play_match
from .simulation.analyst import generate_post_match_report

# --- PHASE 0: DASHBOARD ---
def dashboard(request):
    return render(request, 'engine/dashboard.html')

# --- PHASE 1: TACTICAL LAB (Configuration) ---
def tactical_lab(request):
    # OPTIMIZATION 1: Only fetch teams. We removed the massive "fetch all players" query.
    teams = Team.objects.all()
    
    # 1. INITIALIZE MEMORY BANK
    if 'team_tactics' not in request.session:
        request.session['team_tactics'] = {}

    # The team you were just looking at before clicking submit/switch
    submitted_team_id = request.session.get('last_active_team_id')
    
    # The team you want to look at NOW
    active_team_id = request.POST.get('edit_team_id') or submitted_team_id
    
    if not active_team_id and teams.exists():
        active_team_id = teams.first().id
        
    try: active_team_id = int(active_team_id)
    except: active_team_id = None

    if request.method == 'POST':
        
        # --- HELPER: CLAMP SLIDERS ---
        def clamp(val):
            try:
                return max(1, min(5, int(val)))
            except (ValueError, TypeError):
                return 3

        # 2. SAVE STATE FOR THE SUBMITTED TEAM
        if submitted_team_id:
            # Save Sliders
            tactics = request.session['team_tactics']
            tactics[str(submitted_team_id)] = {
                'tempo': clamp(request.POST.get('sys_tempo', 3)),
                'width': clamp(request.POST.get('sys_width', 3)),
                'depth': clamp(request.POST.get('sys_depth', 3)),
                'press': clamp(request.POST.get('sys_press', 3)),
                'risk':  clamp(request.POST.get('sys_risk', 3))
            }
            request.session.modified = True

            # OPTIMIZATION 2: BULK UPDATE PLAYERS
            current_mode = request.POST.get('match_mode', '5v5')
            started_ids = request.POST.getlist('starting_players')
            
            # Fetch players as a list so we can modify them in memory
            team_players = list(Player.objects.filter(team_id=submitted_team_id))
            
            for p in team_players:
                p.tactical_instruction = request.POST.get(f'instruction_{p.id}', p.tactical_instruction)
                p.set_piece_role = request.POST.get(f'set_piece_{p.id}', p.set_piece_role)
                if str(p.id) in started_ids:
                    p.is_starting = True
                    slot_id = request.POST.get(f'slot_{p.id}', "Center")
                    p.preferred_zone = str(slot_id) if slot_id else "Center"
                    if current_mode == '5v5': p.slot_5v5 = p.preferred_zone
                    else: p.slot_11v11 = p.preferred_zone
                else:
                    p.is_starting = False
                    if not getattr(p, 'preferred_zone', None): p.preferred_zone = "Bench"
                    
            # This hits the database EXACTLY ONCE instead of 25 times!
            Player.objects.bulk_update(team_players, [
                'tactical_instruction', 'set_piece_role', 'is_starting', 
                'preferred_zone', 'slot_5v5', 'slot_11v11'
            ])

        # 3. EXECUTE MATCH
        if 'execute_match' in request.POST:
            import uuid
            
            home_id = request.POST.get('home_team_id')
            away_id = request.POST.get('away_team_id')
            mode = request.POST.get('match_mode', '5v5')

            if not home_id or not away_id:
                home_id = Team.objects.first().id
                away_id = Team.objects.last().id

            request.session['match_config'] = {
                'home_id': home_id,
                'away_id': away_id,
                'mode': mode,
                'match_seed': str(uuid.uuid4())
            }
            return redirect('match_execution')

    # 4. PREPARE UI FOR THE ACTIVE TEAM
    request.session['last_active_team_id'] = active_team_id
    
    # OPTIMIZATION 3: Only fetch the players for the specific team we are viewing
    current_players = Player.objects.filter(team_id=active_team_id) if active_team_id else []
    
    current_tactics = request.session.get('team_tactics', {}).get(str(active_team_id), {
        'tempo': 3, 'width': 3, 'depth': 3, 'press': 3, 'risk': 3
    })

    context = {
        'teams': teams,
        'players': current_players,
        'active_edit_team_id': active_team_id,
        'current_tactics': current_tactics,
    }
    return render(request, 'engine/lab.html', context)


# --- PHASE 2: EXECUTION (The Engine Room) ---
def match_execution(request):
    config = request.session.get('match_config')
    if not config: return redirect('tactical_lab')

    h_team = Team.objects.get(id=config['home_id'])
    a_team = Team.objects.get(id=config['away_id'])
    mode = config['mode']

    team_tactics = request.session.get('team_tactics', {})
    h_team.sys_style = team_tactics.get(str(h_team.id), {'tempo':3, 'width':3, 'depth':3, 'press':3, 'risk':3})
    a_team.sys_style = team_tactics.get(str(a_team.id), {'tempo':3, 'width':3, 'depth':3, 'press':3, 'risk':3})

    h_players = list(Player.objects.filter(team=h_team, is_starting=True))
    a_players = list(Player.objects.filter(team=a_team, is_starting=True))

    if not h_players: h_players = list(Player.objects.filter(team=h_team))[:11]
    if not a_players: a_players = list(Player.objects.filter(team=a_team))[:11]

    current_seed = config.get('match_seed') 

    logs, stats = play_match(h_team, a_team, h_players, a_players, mode=mode, sys_style=h_team.sys_style, match_seed=current_seed)
    
    match = Match.objects.create(
        home_team=h_team, away_team=a_team, mode=mode,
        home_score=stats['home_score'], away_score=stats['away_score'],
        stats=stats, logs=logs
    )
    request.session['last_match_id'] = match.id

    return render(request, 'engine/match_live.html', {
        'match': match, 'logs': logs, 'stats': stats,
    })

# --- PHASE 3: DEEP SCAN (Analysis) ---
def match_analysis(request, match_id=None):
    if not match_id:
        match_id = request.session.get('last_match_id')
    
    if not match_id:
        return redirect('tactical_lab')

    match = get_object_or_404(Match, id=match_id)
    
    analysis = generate_post_match_report(match.stats, match.home_team.name, match.away_team.name)

    return render(request, 'engine/match_report.html', {
        'match_state': match, 
        'stats': match.stats, 
        'analysis': analysis  
    })