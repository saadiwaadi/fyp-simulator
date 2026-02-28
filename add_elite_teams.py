"""
TACTICAL LAB — FULL PLAYER DATABASE
=====================================
Run this script once to wipe the old DB and populate the new squad pool.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player

def inject(team, player_list, is_starting):
    for (name, sta, spd, sho, df, fin,
         vis, comp, def_aw, passing, intercept,
         zone, role) in player_list:
        Player.objects.create(
            name=name,
            team=team,
            stamina=sta,
            speed=spd,
            shooting=sho,
            defense=df,
            finishing=fin,
            vision=vis,
            composure=comp,
            def_awareness=def_aw,
            short_passing=passing,
            interceptions=intercept,
            preferred_zone=zone,
            role=role,
            is_starting=is_starting,
        )

# ==============================================================
# GOALKEEPERS
# ==============================================================
GOALKEEPERS = [
    ("Alisson Becker",      88, 62, 15, 90, 10,  68, 90, 92, 78, 58, "Center", "GK"),
    ("Ederson",             85, 68, 20, 88, 12,  72, 88, 90, 86, 55, "Center", "GK"),
    ("Thibaut Courtois",    88, 58, 15, 92, 10,  65, 88, 92, 72, 52, "Center", "GK"),
    ("Manuel Neuer",        80, 72, 18, 88, 12,  70, 86, 90, 80, 60, "Center", "GK"),
    ("Marc-André ter Stegen",82, 65, 16, 87, 11, 68, 87, 88, 84, 56, "Center", "GK"),
    ("Gianluigi Donnarumma",87, 60, 14, 90, 10,  62, 87, 91, 72, 54, "Center", "GK"),
    ("Mike Maignan",        84, 70, 14, 87, 10,  66, 85, 88, 74, 58, "Center", "GK"),
    ("David Raya",          82, 65, 14, 85, 10,  64, 84, 86, 82, 52, "Center", "GK"),
    ("Gregor Kobel",        83, 63, 13, 86, 10,  62, 85, 87, 70, 50, "Center", "GK"),
    ("Yann Sommer",         80, 60, 12, 84, 10,  65, 86, 86, 74, 50, "Center", "GK"),
    ("Diogo Costa",         84, 72, 14, 85, 11,  68, 82, 84, 76, 52, "Center", "GK"),
    ("Jordan Pickford",     80, 65, 14, 82, 10,  60, 80, 83, 68, 48, "Center", "GK"),
    ("Unai Simón",          82, 68, 13, 84, 10,  64, 83, 85, 74, 50, "Center", "GK"),
    ("Kepa Arrizabalaga",   79, 63, 13, 82, 10,  62, 80, 82, 72, 48, "Center", "GK"),
    ("Emiliano Martínez",   84, 62, 14, 87, 10,  64, 85, 88, 68, 52, "Center", "GK"),
]

# ==============================================================
# DEFENDERS
# ==============================================================
DEFENDERS = [
    ("Virgil van Dijk",     82, 78, 55, 92, 48,  68, 85, 92, 72, 82, "Center", "DEF"),
    ("Antonio Rüdiger",     85, 84, 52, 90, 42,  58, 78, 90, 62, 80, "Center", "DEF"),
    ("William Saliba",      84, 80, 50, 89, 40,  65, 82, 91, 68, 82, "Center", "DEF"),
    ("Matthijs de Ligt",    80, 72, 55, 87, 45,  62, 80, 88, 65, 78, "Center", "DEF"),
    ("Éder Militão",        80, 82, 48, 87, 40,  60, 78, 88, 62, 78, "Center", "DEF"),
    ("Josko Gvardiol",      84, 82, 58, 86, 50,  64, 80, 86, 70, 78, "Left",   "DEF"),
    ("Dayot Upamecano",     82, 82, 50, 86, 42,  60, 76, 86, 64, 76, "Center", "DEF"),
    ("Ibrahima Konaté",     80, 84, 48, 86, 40,  58, 74, 86, 60, 76, "Center", "DEF"),
    ("Jules Koundé",        82, 86, 48, 86, 42,  66, 80, 84, 70, 78, "Right",  "DEF"),
    ("Harry Maguire",       75, 60, 50, 82, 42,  60, 72, 84, 62, 72, "Center", "DEF"),
    ("Trent Alexander-Arnold", 82, 80, 72, 76, 62, 88, 80, 74, 88, 72, "Right",  "DEF"),
    ("Kyle Walker",         85, 92, 58, 82, 52,  62, 76, 80, 68, 72, "Right",  "DEF"),
    ("Achraf Hakimi",       82, 94, 72, 80, 72,  72, 72, 76, 74, 72, "Right",  "DEF"),
    ("Nuno Mendes",         84, 90, 62, 80, 58,  68, 72, 78, 72, 70, "Left",   "DEF"),
    ("Alejandro Balde",     78, 90, 52, 76, 48,  64, 70, 76, 72, 66, "Left",   "DEF"),
    ("Theo Hernández",      82, 88, 65, 78, 60,  66, 72, 74, 70, 66, "Left",   "DEF"),
    ("Andrew Robertson",    85, 84, 60, 78, 52,  70, 74, 76, 76, 68, "Left",   "DEF"),
    ("Joshua Kimmich",      88, 74, 72, 80, 65,  88, 84, 80, 86, 80, "Center", "DEF"),
    ("Benjamin Pavard",     80, 78, 55, 82, 48,  64, 76, 82, 68, 74, "Right",  "DEF"),
    ("Raphaël Varane",      76, 78, 48, 84, 38,  64, 78, 86, 64, 76, "Center", "DEF"),
]

# ==============================================================
# MIDFIELDERS
# ==============================================================
MIDFIELDERS = [
    ("Kevin De Bruyne",     80, 76, 82, 62, 78,  96, 88, 64, 92, 72, "Center", "MID"),
    ("Martin Ødegaard",     78, 76, 74, 64, 72,  92, 88, 66, 90, 68, "Center", "MID"),
    ("Luka Modrić",         78, 72, 68, 68, 65,  94, 92, 70, 92, 78, "Center", "MID"),
    ("Pedri",               80, 78, 68, 72, 68,  90, 86, 72, 92, 76, "Center", "MID"),
    ("Florian Wirtz",       78, 80, 78, 62, 76,  90, 84, 62, 88, 66, "Center", "MID"),
    ("Gavi",                84, 78, 62, 70, 62,  86, 80, 72, 88, 78, "Center", "MID"),
    ("Jude Bellingham",     88, 84, 80, 76, 80,  86, 84, 76, 80, 78, "Center", "MID"),
    ("Vitinha",             78, 74, 70, 72, 68,  84, 82, 72, 84, 76, "Center", "MID"),
    ("Jamal Musiala",       72, 82, 76, 64, 78,  86, 82, 64, 82, 66, "Center", "MID"),
    ("Rayan Cherki",        68, 78, 72, 58, 72,  84, 76, 58, 80, 60, "Right",  "MID"),
    ("Dominik Szoboszlai",  84, 84, 80, 64, 76,  82, 78, 64, 80, 66, "Center", "MID"),
    ("Bruno Fernandes",     85, 74, 80, 64, 78,  90, 78, 62, 84, 64, "Center", "MID"),
    ("Rodri",               84, 68, 70, 84, 58,  88, 90, 88, 88, 88, "Center", "MID"),
    ("Declan Rice",         88, 74, 70, 84, 60,  80, 82, 84, 78, 86, "Center", "MID"),
    ("Sandro Tonali",       88, 78, 70, 80, 66,  82, 76, 80, 78, 82, "Center", "MID"),
    ("Eduardo Camavinga",   86, 82, 66, 78, 58,  80, 72, 74, 72, 80, "Center", "MID"),
    ("Frenkie de Jong",     84, 76, 64, 74, 60,  86, 84, 76, 88, 80, "Center", "MID"),
    ("Antoine Griezmann",   86, 80, 82, 64, 84,  88, 88, 64, 84, 68, "Center", "MID"),
    ("Federico Valverde",   90, 88, 82, 80, 76,  80, 78, 76, 76, 78, "Right",  "MID"),
    ("Granit Xhaka",        82, 68, 66, 78, 58,  80, 80, 78, 82, 78, "Center", "MID"),
]

# ==============================================================
# FORWARDS
# ==============================================================
FORWARDS = [
    ("Erling Haaland",      82, 82, 90, 42, 96,  72, 88, 44, 68, 42, "Center", "FWD"),
    ("Harry Kane",          80, 66, 90, 48, 92,  86, 92, 50, 82, 48, "Center", "FWD"),
    ("Robert Lewandowski",  78, 74, 86, 46, 90,  82, 90, 48, 78, 46, "Center", "FWD"),
    ("Viktor Gyökeres",     86, 88, 84, 44, 86,  74, 80, 44, 68, 42, "Center", "FWD"),
    ("Alexander Isak",      78, 86, 80, 34, 84,  76, 78, 36, 70, 38, "Center", "FWD"),
    ("Lautaro Martínez",    80, 80, 82, 50, 88,  78, 86, 52, 72, 52, "Center", "FWD"),
    ("Dusan Vlahovic",      78, 76, 84, 42, 86,  68, 78, 44, 62, 40, "Center", "FWD"),
    ("Rasmus Højlund",      78, 86, 76, 40, 80,  70, 72, 40, 64, 38, "Center", "FWD"),
    ("Vinícius Júnior",     72, 96, 82, 32, 84,  80, 70, 34, 76, 36, "Left",   "FWD"),
    ("Leroy Sané",          80, 92, 78, 40, 80,  78, 72, 40, 76, 38, "Left",   "FWD"),
    ("Phil Foden",          82, 84, 80, 50, 82,  86, 84, 52, 84, 52, "Left",   "FWD"),
    ("Lamine Yamal",        58, 86, 78, 26, 80,  82, 68, 30, 78, 36, "Left",   "FWD"),
    ("Gabriel Martinelli",  80, 88, 74, 44, 74,  72, 68, 46, 70, 48, "Left",   "FWD"),
    ("Khvicha Kvaratskhelia",78, 88, 78, 38, 80, 84, 72, 40, 80, 44, "Left",   "FWD"),
    ("Kylian Mbappé",       84, 97, 88, 38, 92,  84, 80, 40, 76, 40, "Left",   "FWD"),
    ("Mohamed Salah",       84, 88, 85, 46, 88,  82, 82, 48, 76, 48, "Right",  "FWD"),
    ("Rodrygo",             80, 88, 78, 36, 82,  78, 76, 38, 76, 42, "Right",  "FWD"),
    ("Ousmane Dembélé",     72, 94, 74, 34, 76,  74, 64, 36, 70, 38, "Right",  "FWD"),
    ("Bukayo Saka",         82, 84, 78, 52, 80,  82, 82, 52, 82, 54, "Right",  "FWD"),
    ("Raphinha",            80, 84, 78, 44, 78,  78, 74, 46, 74, 46, "Right",  "FWD"),
    ("Bernardo Silva",      84, 80, 74, 60, 74,  88, 86, 60, 88, 60, "Right",  "FWD"),
    ("Federico Chiesa",     80, 88, 76, 46, 78,  74, 70, 48, 70, 48, "Right",  "FWD"),
    ("Lionel Messi",        62, 72, 82, 30, 88,  96, 90, 34, 94, 44, "Right",  "FWD"),
    ("Cristiano Ronaldo",   72, 76, 85, 36, 90,  72, 82, 38, 66, 36, "Center", "FWD"),
    ("Marcus Rashford",     78, 90, 76, 42, 76,  72, 66, 44, 68, 42, "Left",   "FWD"),
]

# ==============================================================
# STARTER SQUADS
# ==============================================================
STARTERS_NEON = [
    ("Pedri",               80, 78, 68, 72, 68,  90, 86, 72, 92, 76, "Center", "MID"),
    ("Gianluigi Donnarumma",87, 60, 14, 90, 10,  62, 87, 91, 72, 54, "Center", "GK"),
    ("Achraf Hakimi",       82, 94, 72, 80, 72,  72, 72, 76, 74, 72, "Right",  "DEF"),
    ("Lamine Yamal",        58, 86, 78, 26, 80,  82, 68, 30, 78, 36, "Left",   "FWD"),
    ("Harry Kane",          80, 66, 90, 48, 92,  86, 92, 50, 82, 48, "Center", "FWD"),
]

STARTERS_CATALYST = [
    ("Vinícius Júnior",     72, 96, 82, 32, 84,  80, 70, 34, 76, 36, "Left",   "FWD"),
    ("Thibaut Courtois",    88, 58, 15, 92, 10,  65, 88, 92, 72, 52, "Center", "GK"),
    ("Vitinha",             78, 74, 70, 72, 68,  84, 82, 72, 84, 76, "Center", "MID"),
    ("Rayan Cherki",        68, 78, 72, 58, 72,  84, 76, 58, 80, 60, "Right",  "MID"),
    ("Jamal Musiala",       72, 82, 76, 64, 78,  86, 82, 64, 82, 66, "Center", "MID"),
]

def build_database():
    print("🔥 Wiping the old database clean...")
    Player.objects.all().delete()
    Team.objects.all().delete()
    
    print("✨ Creating new teams...")
    team_neon = Team.objects.create(name="Neon FC", tactical_mode='Standard')
    team_catalyst = Team.objects.create(name="Catalyst United", tactical_mode='Standard')

    full_bench = GOALKEEPERS + DEFENDERS + MIDFIELDERS + FORWARDS

    print(f"Loading {len(full_bench)} bench players into Neon FC...")
    inject(team_neon, full_bench, is_starting=False)

    print(f"Loading {len(full_bench)} bench players into Catalyst United...")
    inject(team_catalyst, full_bench, is_starting=False)

    print("Loading starting lineups...")
    inject(team_neon, STARTERS_NEON, is_starting=True)
    inject(team_catalyst, STARTERS_CATALYST, is_starting=True)

    total = len(full_bench)
    print(f"\n✅ Done. {total} players loaded per team.")
    print(f"   GKs: {len(GOALKEEPERS)} | DEFs: {len(DEFENDERS)} | MIDs: {len(MIDFIELDERS)} | FWDs: {len(FORWARDS)}")
    print(f"   Starters: Neon={len(STARTERS_NEON)} Catalyst={len(STARTERS_CATALYST)}")

if __name__ == "__main__":
    build_database()