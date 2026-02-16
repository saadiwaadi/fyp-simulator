from django.shortcuts import render
from .models import Team, Player
from .simulation.engine import play_match

def match_dashboard(request):
    # 1. SETUP DEFAULTS
    teams = Team.objects.all()
    active_tab = 'tab-stats' # Default tab
    
    # Try to keep the same team selected if we just reloaded the page
    active_team_id = request.POST.get('edit_team_id')
    
    # If no team is selected (first load), pick the first one from DB
    if not active_team_id and teams.exists():
        active_team_id = teams.first().id
    
    # Safety convert to int
    try:
        active_team_id = int(active_team_id)
    except (TypeError, ValueError):
        active_team_id = None

    log = []
    stats = {}
    
    # 2. HANDLE ACTIONS
    if request.method == 'POST':
        
        # --- SCENARIO A: SWITCHING TEAMS (Dropdown) ---
        # The form just submits 'edit_team_id', we just need to catch it (done above) and switch tabs
        if 'update_squad_view' in request.POST:
            active_tab = 'tab-squad'

        # --- SCENARIO B: SAVING THE SQUAD ---
        elif 'update_squad_save' in request.POST:
            active_tab = 'tab-squad'
            
            # Reset bench for this team
            Player.objects.filter(team_id=active_team_id).update(is_starting=False)
            
            # Set new starters
            selected_ids = request.POST.getlist('starting_players')
            Player.objects.filter(id__in=selected_ids).update(is_starting=True)
            
            # Save Zones
            # We fetch players again to ensure we iterate over the correct set
            team_players = Player.objects.filter(team_id=active_team_id)
            for p in team_players:
                new_zone = request.POST.get(f'zone_{p.id}')
                if new_zone:
                    p.preferred_zone = new_zone
                    p.save()

        # --- SCENARIO C: EXECUTING MATCH ---
        elif 'home_team' in request.POST:
            active_tab = 'tab-stats' # Go to results
            h_id = request.POST.get('home_team')
            a_id = request.POST.get('away_team')
            mode = request.POST.get('match_mode')
            
            # Run Engine
            try:
                h = Team.objects.get(id=h_id)
                a = Team.objects.get(id=a_id)
                log, stats = play_match(h.name, a.name, mode=mode)
            except Exception as e:
                log = [f">> ERROR: {str(e)}"]

    # 3. GET PLAYERS FOR THE ACTIVE TEAM
    current_players = Player.objects.filter(team_id=active_team_id) if active_team_id else []

    context = {
        'teams': teams,
        'players': current_players, # This populates the table
        'active_edit_team_id': active_team_id, # This tells the dropdown which team is selected
        'active_tab': active_tab, # This tells JS which tab to open
        'log': log,
        'stats': stats
    }
    
    return render(request, 'engine/dashboard.html', context)