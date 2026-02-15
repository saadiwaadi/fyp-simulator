import os
import django
import random

# 1. Setup Django Environment
# OLD: os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'football_sim.settings')
# NEW (CORRECT):
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player

def run():
    print(">> Wiping old database...")
    # (Rest of the file remains the same...)
    Player.objects.all().delete()
    Team.objects.all().delete()

    # --- TEAM A: THE TECHNICIANS ---
    techs = Team.objects.create(name="The Technicians", style=85)
    print(f"Created Team: {techs.name} (Style: Possession)")

    Player.objects.create(name="Leo Drift", team=techs, role="OUT", vision=96, finishing=92, short_passing=95, def_awareness=40, stamina=75)
    Player.objects.create(name="Harry Kane-ish", team=techs, role="OUT", vision=85, finishing=94, short_passing=82, def_awareness=50, stamina=78)
    Player.objects.create(name="Luka Magic", team=techs, role="OUT", vision=94, finishing=75, short_passing=96, def_awareness=65, stamina=70)
    Player.objects.create(name="Virgil V", team=techs, role="OUT", vision=70, finishing=40, short_passing=85, def_awareness=92, interceptions=90, stamina=85)
    Player.objects.create(name="Ederson B", team=techs, role="GK", composure=90, short_passing=88)

    # --- TEAM B: THE PRESSERS ---
    press = Team.objects.create(name="The Pressers", style=30)
    print(f"Created Team: {press.name} (Style: Physical)")

    Player.objects.create(name="Roy Keane-ish", team=press, role="OUT", vision=78, finishing=70, short_passing=82, def_awareness=88, interceptions=89, stamina=95)
    Player.objects.create(name="Jamie Vardy-ish", team=press, role="OUT", vision=72, finishing=88, short_passing=70, def_awareness=45, stamina=92)
    Player.objects.create(name="The Rock", team=press, role="OUT", vision=60, finishing=50, short_passing=65, def_awareness=85, interceptions=85, stamina=90)
    Player.objects.create(name="Darwin N", team=press, role="OUT", vision=65, finishing=80, short_passing=68, def_awareness=60, stamina=99)
    Player.objects.create(name="Pickford J", team=press, role="GK", composure=84, short_passing=60)

    print(">> DATABASE POPULATED SUCCESSFULLY.")

if __name__ == "__main__":
    run()