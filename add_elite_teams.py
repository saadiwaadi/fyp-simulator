import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player

def update_elite_squads():
    # 1. Grab your existing teams
    team_p, _ = Team.objects.get_or_create(name="Team P", defaults={'tactical_mode': 'Standard'})
    team_s, _ = Team.objects.get_or_create(name="Team S", defaults={'tactical_mode': 'Standard'})

    # 2. Your original 10 players (These will remain your active Starters)
    starters_p = [
        ("Pedri", 77, 77, 73, 78, 73, "Center", "MID"),
        ("Donnarumma", 87, 52, 20, 90, 15, "Center", "GK"),
        ("Hakimi", 79, 92, 79, 82, 79, "Right", "DEF"),
        ("Lamine Yamal", 53, 85, 81, 23, 81, "Left", "FWD"),
        ("Harry Kane", 82, 64, 92, 48, 92, "Center", "FWD"),
    ]

    starters_s = [
        ("Vinícius Júnior", 69, 95, 84, 29, 84, "Left", "FWD"),
        ("Thibaut Courtois", 88, 46, 20, 90, 15, "Center", "GK"),
        ("Vitinha", 70, 72, 80, 75, 80, "Center", "MID"),
        ("Rayan Cherki", 65, 75, 75, 21, 75, "Right", "FWD"),
        ("Jamal Musiala", 65, 80, 82, 66, 82, "Center", "MID"),
    ]

    # 3. The Massive Elite Pool (Available on the Bench for both teams)
    bench_pool = [
        # --- STRIKERS ---
        ("Erling Haaland", 79, 88, 92, 45, 96, "Center", "FWD"),
        ("Kylian Mbappé", 84, 97, 90, 36, 92, "Center", "FWD"),
        ("Robert Lewandowski", 76, 75, 88, 44, 90, "Center", "FWD"),
        ("Viktor Gyökeres", 85, 90, 84, 42, 86, "Center", "FWD"),
        ("Alexander Isak", 77, 85, 82, 30, 84, "Center", "FWD"),
        ("Cristiano Ronaldo", 73, 77, 87, 34, 89, "Center", "FWD"),
        
        # --- WINGERS ---
        ("Rodrygo", 81, 88, 82, 33, 83, "Right", "FWD"),
        ("Phil Foden", 83, 85, 81, 47, 82, "Left", "FWD"),
        ("Mohamed Salah", 83, 89, 87, 45, 89, "Right", "FWD"),
        ("Leroy Sané", 78, 91, 81, 38, 80, "Left", "FWD"),
        ("Ousmane Dembélé", 73, 93, 77, 36, 75, "Right", "FWD"),
        ("Lionel Messi", 70, 79, 85, 24, 87, "Right", "FWD"),
        
        # --- MIDFIELDERS ---
        ("Luka Modrić", 70, 69, 75, 70, 73, "Center", "MID"),
        ("Kevin De Bruyne", 78, 67, 85, 65, 82, "Center", "MID"),
        ("Jude Bellingham", 88, 80, 82, 78, 84, "Center", "MID"),
        ("Dominik Szoboszlai", 82, 80, 81, 60, 79, "Center", "MID"),
        ("Bruno Fernandes", 90, 71, 83, 69, 81, "Center", "MID"),
        ("Sandro Tonali", 86, 81, 73, 80, 70, "Center", "MID"),
        ("Paul Scholes", 85, 73, 87, 60, 82, "Center", "MID"),
        ("Federico Valverde", 92, 88, 82, 80, 79, "Right", "MID"),
        ("Eduardo Camavinga", 85, 80, 70, 81, 65, "Center", "MID"),
        ("Antoine Griezmann", 86, 79, 85, 60, 88, "Center", "MID"),
        
        # --- DEFENDERS ---
        ("Virgil van Dijk", 74, 78, 60, 89, 50, "Center", "DEF"),
        ("Antonio Rüdiger", 77, 82, 55, 86, 45, "Center", "DEF"),
        ("Matthijs de Ligt", 72, 70, 59, 84, 48, "Center", "DEF"),
        ("Jules Koundé", 81, 84, 45, 85, 40, "Right", "DEF"),
        ("Harry Maguire", 68, 48, 52, 79, 45, "Center", "DEF"),
        ("Trent Alexander-Arnold", 89, 76, 72, 80, 64, "Right", "DEF"),
        ("Kyle Walker", 85, 90, 63, 80, 55, "Right", "DEF"),
        ("Nuno Mendes", 85, 90, 68, 78, 62, "Left", "DEF"),
        ("Alejandro Balde", 80, 91, 55, 75, 50, "Left", "DEF"),
        ("Joshua Kimmich", 86, 70, 73, 82, 68, "Center", "DEF"),
    ]

    # 4. The Injection Function
    def inject(team, player_list, is_starting):
        for name, sta, spd, sho, df, fin, zone, role in player_list:
            Player.objects.update_or_create(
                name=name,
                team=team,
                defaults={
                    'stamina': sta,
                    'speed': spd,
                    'shooting': sho,
                    'defense': df,
                    'finishing': fin,
                    'preferred_zone': zone,
                    'role': role,
                    'is_starting': is_starting 
                }
            )

    # Load Sandbox Pool onto the bench for both Team P and Team S
    inject(team_p, bench_pool, is_starting=False)
    inject(team_s, bench_pool, is_starting=False)

    # Load and lock the original starters for both teams
    inject(team_p, starters_p, is_starting=True)
    inject(team_s, starters_s, is_starting=True)

    print("✅ Successfully loaded the massive sandbox pool directly into Team P and Team S!")

if __name__ == "__main__":
    update_elite_squads()