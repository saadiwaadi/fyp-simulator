from django.shortcuts import render
from .models import Team
from .simulation.engine import play_match

def match_dashboard(request):
    # 1. Fetch all teams for the Dropdown Menu
    teams = Team.objects.all()
    context = {'teams': teams}
    
    if request.method == 'POST':
        # 2. Try to get User Selection
        home_id = request.POST.get('home_team')
        away_id = request.POST.get('away_team')
        
        h_team = None
        a_team = None

        # 3. LOGIC CHECK: Did the user pick teams?
        if home_id and away_id:
            try:
                h_team = Team.objects.get(id=home_id)
                a_team = Team.objects.get(id=away_id)
            except Team.DoesNotExist:
                pass # Fallback to auto-select if IDs are weird

        # 4. SAFETY NET: If no selection (or error), pick first 2 teams automatically
        if not h_team or not a_team:
            if teams.count() >= 2:
                h_team = teams[0]
                a_team = teams[1]
            else:
                # CRITICAL ERROR: Database is empty
                context['log'] = ["ERROR: You need at least 2 Teams in the Database to play."]
                return render(request, 'engine/dashboard.html', context)

        # 5. Run the Match
        log, stats = play_match(h_team.name, a_team.name)
        
        context['log'] = log
        context['stats'] = stats
            
    return render(request, 'engine/dashboard.html', context)