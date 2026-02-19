from engine.models import Team, Player
from engine.simulation.engine import play_match

def run_tests():
    home = Team.objects.first()
    away = Team.objects.last()
    h_players = list(Player.objects.filter(team=home))[:11]
    a_players = list(Player.objects.filter(team=away))[:11]

    def run_batch(mode, h_style, a_style, runs=30):
        total_h_goals, total_a_goals = 0, 0
        fatigue_mins, struct_mins = [], []
        
        # Inject styles
        home.sys_style = h_style
        away.sys_style = a_style

        for _ in range(runs):
            logs, stats = play_match(home, away, h_players, a_players, mode=mode, sys_style=h_style)
            total_h_goals += stats.get('home_score', 0)
            total_a_goals += stats.get('away_score', 0)
            if stats.get('fatigue_breach_min'): fatigue_mins.append(stats['fatigue_breach_min'])
            if stats.get('struct_breach_min'): struct_mins.append(stats['struct_breach_min'])
            
        print(f"--- {mode} ({runs} Matches) ---")
        print(f"Avg Score: {total_h_goals/runs:.1f} - {total_a_goals/runs:.1f}")
        if fatigue_mins: print(f"Avg Fatigue Breach: {sum(fatigue_mins)/len(fatigue_mins):.0f}'")
        if struct_mins: print(f"Avg Struct Collapse: {sum(struct_mins)/len(struct_mins):.0f}'")
        print("-" * 30)

    # Run the batches
    print("\nStarting Engine Tests...\n")
    run_batch('5v5', {'tempo':3, 'press':3, 'risk':3, 'depth':3}, {'tempo':3, 'press':3, 'risk':3, 'depth':3})
    run_batch('11v11', {'tempo':4, 'press':3, 'risk':5, 'depth':4}, {'tempo':2, 'press':2, 'risk':1, 'depth':1})