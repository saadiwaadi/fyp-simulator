from engine.models import Team, Player
from engine.simulation.engine import play_match
import copy

def run_stress_test():
    # 1. Fetch real teams
    home = Team.objects.first()
    away = Team.objects.last()
    
    # 2. Define Tactical Profiles
    # Optimal: Balanced, sustainable, solid structure
    TAC_OPTIMAL = {'tempo': 3, 'press': 3, 'risk': 3, 'depth': 3}
    # Shit (Suicide): Max sprint, max press, exposed high line. Will collapse by minute 35.
    TAC_SHIT = {'tempo': 5, 'press': 5, 'risk': 5, 'depth': 5}
    
    def run_scenario(scenario_name, h_rating, a_rating, h_tac, a_tac, runs=10):
        # Fetch fresh players to avoid contamination
        h_players = list(Player.objects.filter(team=home))[:11]
        a_players = list(Player.objects.filter(team=away))[:11]
        
        # Override stats IN MEMORY only (Does not save to DB)
        for p in h_players:
            p.stamina, p.speed, p.shooting, p.defense = h_rating, h_rating, h_rating, h_rating
        for p in a_players:
            p.stamina, p.speed, p.shooting, p.defense = a_rating, a_rating, a_rating, a_rating

        home.sys_style = h_tac
        away.sys_style = a_tac

        total_h, total_a = 0, 0
        fatigue_h, struct_a = [], [] # Tracking Home fatigue and Away structure collapse
        
        for _ in range(runs):
            logs, stats = play_match(home, away, h_players, a_players, mode='11v11')
            total_h += stats.get('home_score', 0)
            total_a += stats.get('away_score', 0)
            
            if stats.get('fatigue_breach_min'): fatigue_h.append(stats['fatigue_breach_min'])
            if stats.get('struct_breach_min'): struct_a.append(stats['struct_breach_min'])

        print(f"\n[{scenario_name}]")
        print(f"Matchup: Home ({h_rating} OVR) vs Away ({a_rating} OVR)")
        print(f"Tactics: Home {list(h_tac.values())} vs Away {list(a_tac.values())}")
        print(f"--> AVG SCORE: {total_h/runs:.1f} - {total_a/runs:.1f}")
        
        avg_fatigue = sum(fatigue_h)/len(fatigue_h) if fatigue_h else 90
        avg_struct = sum(struct_a)/len(struct_a) if struct_a else 90
        print(f"--> Avg Match Collapse: Fatigue @ {avg_fatigue:.0f}' | Structure Break @ {avg_struct:.0f}'")

    print("="*50)
    print("INITIATING V3.5 STRESS MATRIX (10 Matches Each)")
    print("="*50)

    # Change the 95s to 85s, and the 50s to 70s
    run_scenario("1. THE BASELINE", 70, 70, TAC_OPTIMAL, TAC_OPTIMAL)
    run_scenario("2. THE MISMATCH (Title Contender vs Relegation)", 85, 70, TAC_OPTIMAL, TAC_OPTIMAL)
    run_scenario("3. TACTICAL DISASTER (Contender commits suicide)", 85, 70, TAC_SHIT, TAC_OPTIMAL)
    run_scenario("4. THE BLOODBATH (Relegation commits suicide)", 85, 70, TAC_OPTIMAL, TAC_SHIT)    
    print("\n" + "="*50)
    print("TEST COMPLETE.")