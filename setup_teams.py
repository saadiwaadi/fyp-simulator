import os
import django
import random

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player
from engine.simulation.engine import play_match  # Import engine to run tests

def create_squad(team_obj, style):
    """
    Generates a full 11-man squad (1 GK + 10 Outfield)
    based on the team's tactical identity.
    """
    print(f"   -> Signing 11 players for {team_obj.name} ({style})...")
    
    # 1. Goalkeeper
    # FIX: Removed 'keeping' (doesn't exist). Used 'composure' instead.
    Player.objects.create(
        team=team_obj, 
        name=f"{team_obj.name} GK", 
        role="GK", 
        composure=random.randint(85, 95), # High composure = Good GK
        stamina=70
    )

    # 2. Outfield Players (4 Defenders, 4 Midfielders, 2 Forwards)
    roles = ['DEF', 'DEF', 'DEF', 'DEF', 'MID', 'MID', 'MID', 'MID', 'FWD', 'FWD']
    
    for i, role in enumerate(roles):
        # Define stats based on Team Identity
        if style == "POSSESSION": # The Technicians (High Skill, Low Physical)
            stats = {
                'short_passing': random.randint(85, 95),
                'vision': random.randint(85, 95),
                'stamina': random.randint(65, 75),
                'def_awareness': random.randint(50, 65),
                'finishing': 75 if role == 'FWD' else 50
            }
        else: # The Pressers (High Physical, Low Skill)
            stats = {
                'short_passing': random.randint(65, 75),
                'vision': random.randint(60, 70),
                'stamina': random.randint(88, 98), # Elite Engines
                'def_awareness': random.randint(80, 90),
                'finishing': 75 if role == 'FWD' else 50
            }

        Player.objects.create(
            team=team_obj,
            name=f"{team_obj.name} {role} {i+1}",
            role=role,
            interceptions=stats['def_awareness'], 
            composure=70,
            **stats
        )

def run():
    print("\n========== 🛠️ SETUP PHASE: RESET DATABASE ==========")
    print(">> Wiping old data...")
    Player.objects.all().delete()
    Team.objects.all().delete()

    # --- CREATE TEAMS ---
    techs = Team.objects.create(name="The Technicians", style=85, tactical_mode="TIKI_TAKA")
    press = Team.objects.create(name="The Pressers", style=30, tactical_mode="HIGH_PRESS")

    # --- CREATE SQUADS ---
    create_squad(techs, "POSSESSION")
    create_squad(press, "PHYSICAL")
    
    print(">> DATABASE POPULATED SUCCESSFULLY.")

    # --- VERIFICATION TEST ---
    print("\n========== 🧪 TESTING PHASE: PHYSICS CHECK ==========")
    
    # Test 1: 5v5 Mode (Should be destructive)
    print("1️⃣  Running 5v5 Mode (Chaos)...")
    log1, stats1 = play_match("The Technicians", "The Pressers", mode="5v5")
    dmg5 = 100 - stats1.get('away_integrity_final', 100)
    print(f"   -> 5v5 Damage Dealt: {dmg5}")

    # Test 2: 11v11 Mode (Should be controlled)
    print("2️⃣  Running 11v11 Mode (Control)...")
    log2, stats2 = play_match("The Technicians", "The Pressers", mode="11v11")
    dmg11 = 100 - stats2.get('away_integrity_final', 100)
    print(f"   -> 11v11 Damage Dealt: {dmg11}")

    # Comparison Verdict
    print("\n========== 🏁 VERDICT ==========")
    if dmg5 > (dmg11 + 5):
        print(f"✅ SUCCESS: Physics Shift Verified.")
        print(f"   5v5 was {dmg5 - dmg11} points more destructive.")
        print("   The Environment Layer is WORKING.")
    else:
        print(f"⚠️  WARNING: Physics look similar (Diff: {dmg5 - dmg11}).")
        print("   Check environment.py values.")

if __name__ == "__main__":
    run()