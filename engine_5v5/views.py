from django.shortcuts import render
from .models import Team
from .simulation.engine import play_match

def match_dashboard(request):
    teams = Team.objects.all()
    context = {'teams': teams}
    
    if request.method == 'POST':
        # CHECK: Is this a TACTICAL UPDATE?
        if 'update_tactic' in request.POST:
            target_team_id = request.POST.get('target_team')
            new_mode = request.POST.get('tactic_value')
            
            if target_team_id and new_mode:
                team = Team.objects.get(id=target_team_id)
                team.tactical_mode = new_mode
                team.save()
                
                # Add a "System Message" to the log so you know it worked
                context['log'] = [f">> INSTRUCTION RECEIVED: {team.name} switched to {new_mode}"]
        
        # CHECK: Is this a MATCH SIMULATION?
        elif 'home_team' in request.POST:
            # (Your existing match logic here)
            home_id = request.POST.get('home_team')
            away_id = request.POST.get('away_team')
            
            # ... (Rest of your existing match code) ...
            # JUST ENSURE YOU COPY YOUR EXISTING LOGIC BACK HERE
            if home_id and away_id:
                try:
                    h_team = Team.objects.get(id=home_id)
                    a_team = Team.objects.get(id=away_id)
                    # Run match
                    from .simulation.engine import play_match
                    log, stats = play_match(h_team.name, a_team.name)
                    context['log'] = log
                    context['stats'] = stats
                except:
                    pass

    return render(request, 'engine/dashboard.html', context)