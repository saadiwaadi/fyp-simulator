from engine.simulation.core.game import Game


def play_match(home_team_name, away_team_name):
    from engine_5v5.models import Team as DBTeam

    try:
        home_db = DBTeam.objects.get(name=home_team_name)
        away_db = DBTeam.objects.get(name=away_team_name)
    except DBTeam.DoesNotExist:
        return ['ERROR: Teams not found.'], {}

    h_players = list(home_db.player_set.all())
    a_players = list(away_db.player_set.all())

    return Game(mode='5v5').play(home_db, away_db, h_players, a_players)
