import os
import django
import statistics

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player
from engine.simulation.engine import play_match

def build_lineup(team, gk_count, def_count, mid_count, fwd_count):
    gks = list(Player.objects.filter(team=team, role="GK").order_by('-defense')[:gk_count])
    defs = list(Player.objects.filter(team=team, role="DEF").order_by('-defense')[:def_count])
    mids = list(Player.objects.filter(team=team, role="MID").order_by('-passing')[:mid_count])
    fwds = list(Player.objects.filter(team=team, role="FWD").order_by('-finishing')[:fwd_count])
    return gks + defs + mids + fwds

def run_tests():
    home = Team.objects.first()
    away = Team.objects.last()

    def run_batch(test_name, h_lineup, a_lineup, h_style, a_style, runs=20):
        if len(h_lineup) == 0 or len(a_lineup) == 0:
            print(f"⚠️ Skipping {test_name}: Not enough players.")
            return

        home.sys_style = h_style
        away.sys_style = a_style

        total_h_goals, total_a_goals = 0, 0
        match_totals = []
        high_scoring_matches = 0

        for _ in range(runs):
            logs, stats = play_match(home, away, h_lineup, a_lineup, mode='5v5', sys_style=h_style)
            
            h_score = stats.get('home_score', 0)
            a_score = stats.get('away_score', 0)
            total_goals = h_score + a_score
            
            total_h_goals += h_score
            total_a_goals += a_score
            match_totals.append(total_goals)
            
            if total_goals >= 5:
                high_scoring_matches += 1

        # Statistical Calculations
        avg_h = total_h_goals / runs
        avg_a = total_a_goals / runs
        avg_total = sum(match_totals) / runs
        max_score = max(match_totals)
        min_score = min(match_totals)
        
        # Need at least 2 runs for variance/stdev
        goal_variance = statistics.variance(match_totals) if runs > 1 else 0
        std_dev = statistics.stdev(match_totals) if runs > 1 else 0
        high_score_pct = (high_scoring_matches / runs) * 100

        print(f"🧪 {test_name} ({runs} Matches)")
        print(f"   ⚽ Avg Goals per Team: Home {avg_h:.1f} | Away {avg_a:.1f}")
        print(f"   📊 Avg Total Goals: {avg_total:.1f}")
        print(f"   📈 Goal Variance: {goal_variance:.2f}")
        print(f"   📉 Std Deviation: {std_dev:.2f}")
        print(f"   🔥 5+ Goal Matches: {high_score_pct:.0f}%")
        print(f"   🥅 Max Total Score: {max_score} | Min Total Score: {min_score}")
        
        # Volatility Alerts
        if avg_total > 7:
            print("   ⚠️ ALERT: Engine is too volatile (Avg Total > 7)")
        if std_dev < 1.0 and avg_total > 5:
            print("   ⚠️ ALERT: Randomness weight too low. Every match is identical and high-scoring.")
        print("-" * 50)

    print("\n🚀 BOOTING ADVANCED STATISTICAL MONTE CARLO...\n")

    # TEST A: Balanced vs Balanced (2-1-1)
    run_batch(
        test_name="Scenario A — Balanced vs Balanced", 
        h_lineup=build_lineup(home, 1, 2, 1, 1), 
        a_lineup=build_lineup(away, 1, 2, 1, 1), 
        h_style={'tempo':3, 'press':3, 'risk':3, 'depth':3}, 
        a_style={'tempo':3, 'press':3, 'risk':3, 'depth':3},
    )

    # TEST B: High Press vs Low Block
    run_batch(
        test_name="Scenario B — High Press vs Low Block", 
        h_lineup=build_lineup(home, 1, 2, 1, 1), 
        a_lineup=build_lineup(away, 1, 2, 1, 1), 
        h_style={'tempo':4, 'press':5, 'risk':4, 'depth':4}, # High Press
        a_style={'tempo':2, 'press':1, 'risk':2, 'depth':5}, # Low Block / Deep Def
    )

    # TEST C: Counter vs High Line
    run_batch(
        test_name="Scenario C — Counter vs High Line", 
        h_lineup=build_lineup(home, 1, 2, 1, 1), 
        a_lineup=build_lineup(away, 1, 2, 1, 1), 
        h_style={'tempo':5, 'press':2, 'risk':4, 'depth':2}, # Fast Counter
        a_style={'tempo':3, 'press':4, 'risk':4, 'depth':1}, # High Line (Low depth value)
    )

    # TEST D: All-Out Attack vs All-Out Attack
    run_batch(
        test_name="Scenario D — All-Out Attack vs All-Out Attack", 
        h_lineup=build_lineup(home, 1, 1, 1, 2), # 1-1-2
        a_lineup=build_lineup(away, 1, 1, 1, 2), # 1-1-2
        h_style={'tempo':5, 'press':4, 'risk':5, 'depth':2}, 
        a_style={'tempo':5, 'press':4, 'risk':5, 'depth':2},
    )

    # TEST E: Strong Defense vs Strong Attack
    run_batch(
        test_name="Scenario E — Strong Defense vs Strong Attack", 
        h_lineup=build_lineup(home, 1, 3, 0, 1), # 3-0-1 Park the Bus
        a_lineup=build_lineup(away, 1, 1, 1, 2), # 1-1-2 Glass Cannon
        h_style={'tempo':2, 'press':2, 'risk':1, 'depth':5}, 
        a_style={'tempo':4, 'press':4, 'risk':5, 'depth':3},
    )

if __name__ == "__main__":
    run_tests()