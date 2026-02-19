import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
django.setup()

from engine.models import Team, Player

def create_elite_squads():
    # 1. Create Teams
    team_p, _ = Team.objects.get_or_create(name="Team P", defaults={'tactical_mode': 'Standard'})
    team_s, _ = Team.objects.get_or_create(name="Team S", defaults={'tactical_mode': 'Standard'})

    # 2. Define Player Data
    players_p = [
        ("Pedri", 77, 77, 73, 78, 73, "Center"),
        ("Donnarumma", 87, 52, 20, 90, 15, "Center"),
        ("Hakimi", 79, 92, 79, 82, 79, "Right"),
        ("Lamine Yamal", 53, 85, 81, 23, 81, "Left"),
        ("Harry Kane", 82, 64, 92, 48, 92, "Center"),
    ]

    players_s = [
        ("Vinícius Júnior", 69, 95, 84, 29, 84, "Left"),
        ("Thibaut Courtois", 88, 46, 20, 90, 15, "Center"),
        ("Vitinha", 70, 72, 80, 75, 80, "Center"),
        ("Rayan Cherki", 65, 75, 75, 21, 75, "Right"),
        ("Jamal Musiala", 65, 80, 82, 66, 82, "Center"),
    ]

    # 3. Inject Players
    def inject(team, player_list):
        for name, sta, spd, sho, df, fin, zone in player_list:
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
                    'is_starting': True
                }
            )

    inject(team_p, players_p)
    inject(team_s, players_s)
    print("✅ Elite Teams P and S successfully added to the database!")

if __name__ == "__main__":
    create_elite_squads()