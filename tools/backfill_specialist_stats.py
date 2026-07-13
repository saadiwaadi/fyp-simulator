"""Backfill specialist stats (dribbling / heading / marking / GK triple)
with league-level ratings for the real-world squad.

Values are informed by public league-level ratings (EA FC / FM style
consensus) for each player's real profile. Anyone not in the table gets
a role-sensible derivation from his existing stats, so custom squads
never sit at zero.

Run:  python tools/backfill_specialist_stats.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_perfect.settings')
import django

django.setup()

from engine.models import Player

# name: (dribbling, heading, marking)  — outfield
OUTFIELD = {
    # ── DEF ──────────────────────────────────────────────────────────
    'Virgil van Dijk':        (72, 91, 90),
    'Antonio Rüdiger':        (68, 88, 88),
    'William Saliba':         (70, 85, 89),
    'Matthijs de Ligt':       (66, 86, 86),
    'Éder Militão':           (71, 84, 86),
    'Josko Gvardiol':         (78, 82, 85),
    'Dayot Upamecano':        (68, 84, 84),
    'Ibrahima Konaté':        (65, 86, 85),
    'Jules Koundé':           (76, 78, 86),
    'Harry Maguire':          (60, 89, 82),
    'Trent Alexander-Arnold': (80, 72, 76),
    'Kyle Walker':            (76, 74, 82),
    'Achraf Hakimi':          (84, 70, 78),
    'Nuno Mendes':            (84, 72, 80),
    'Alejandro Balde':        (85, 64, 76),
    'Theo Hernández':         (84, 76, 79),
    'Andrew Robertson':       (78, 74, 81),
    'Joshua Kimmich':         (81, 70, 83),
    'Benjamin Pavard':        (70, 82, 83),
    'Raphaël Varane':         (66, 85, 85),
    # ── MID ──────────────────────────────────────────────────────────
    'Kevin De Bruyne':        (85, 68, 62),
    'Martin Ødegaard':        (87, 58, 64),
    'Luka Modrić':            (86, 60, 68),
    'Pedri':                  (89, 54, 66),
    'Florian Wirtz':          (90, 58, 58),
    'Gavi':                   (84, 62, 70),
    'Jude Bellingham':        (86, 80, 72),
    'Vitinha':                (87, 56, 66),
    'Jamal Musiala':          (92, 54, 56),
    'Rayan Cherki':           (91, 50, 48),
    'Dominik Szoboszlai':     (84, 66, 66),
    'Bruno Fernandes':        (82, 70, 62),
    'Rodri':                  (80, 76, 84),
    'Declan Rice':            (76, 78, 84),
    'Sandro Tonali':          (80, 70, 80),
    'Eduardo Camavinga':      (84, 64, 80),
    'Frenkie de Jong':        (88, 62, 74),
    'Antoine Griezmann':      (85, 74, 62),
    'Federico Valverde':      (84, 74, 76),
    'Granit Xhaka':           (74, 72, 80),
    # ── FWD ──────────────────────────────────────────────────────────
    'Erling Haaland':         (80, 92, 48),
    'Harry Kane':             (82, 88, 54),
    'Robert Lewandowski':     (84, 90, 50),
    'Viktor Gyökeres':        (82, 84, 46),
    'Alexander Isak':         (87, 76, 42),
    'Lautaro Martínez':       (84, 82, 50),
    'Dusan Vlahovic':         (78, 86, 44),
    'Rasmus Højlund':         (78, 80, 40),
    'Vinícius Júnior':        (92, 62, 38),
    'Leroy Sané':             (88, 58, 40),
    'Phil Foden':             (90, 62, 50),
    'Lamine Yamal':           (93, 54, 42),
    'Gabriel Martinelli':     (88, 62, 46),
    'Khvicha Kvaratskhelia':  (91, 58, 42),
    'Kylian Mbappé':          (93, 72, 38),
    'Mohamed Salah':          (89, 64, 45),
    'Rodrygo':                (90, 60, 44),
    'Ousmane Dembélé':        (92, 56, 40),
    'Bukayo Saka':            (88, 62, 52),
    'Raphinha':               (88, 64, 50),
    'Bernardo Silva':         (91, 54, 58),
    'Federico Chiesa':        (86, 60, 44),
    'Lionel Messi':           (94, 70, 32),
    'Cristiano Ronaldo':      (82, 90, 34),
    'Marcus Rashford':        (85, 68, 40),
}

# name: (reflexes, handling, aerials) — keepers
KEEPERS = {
    'Alisson Becker':          (89, 86, 87),
    'Ederson':                 (84, 82, 84),
    'Thibaut Courtois':        (89, 87, 88),
    'Manuel Neuer':            (87, 85, 86),
    'Marc-André ter Stegen':   (88, 87, 84),
    'Gianluigi Donnarumma':    (91, 84, 87),
    'Mike Maignan':            (88, 84, 85),
    'David Raya':              (85, 84, 83),
    'Gregor Kobel':            (87, 85, 84),
    'Yann Sommer':             (87, 86, 79),
    'Diogo Costa':             (86, 83, 84),
    'Jordan Pickford':         (86, 82, 80),
    'Unai Simón':              (85, 82, 84),
    'Kepa Arrizabalaga':       (84, 79, 78),
    'Emiliano Martínez':       (86, 83, 85),
}

# Ederson/Neuer famously have outfield feet — give keepers a dribbling
# figure too so sweeper-keeper play has data behind it later.
KEEPER_DRIBBLING = {'Ederson': 62, 'Manuel Neuer': 58, 'Alisson Becker': 52}


def derive_outfield(p):
    """Role-sensible fallback for players not in the table."""
    drb = int(p.short_passing * 0.45 + p.composure * 0.30 + p.speed * 0.25)
    if p.role == 'FWD':
        hed = int(p.finishing * 0.55 + p.composure * 0.20 + 20)
        mrk = int(p.def_awareness * 0.55 + 10)
    elif p.role == 'DEF':
        hed = int(p.def_awareness * 0.50 + p.composure * 0.20 + 22)
        mrk = int(p.def_awareness * 0.65 + p.interceptions * 0.30)
    else:
        hed = int(p.finishing * 0.30 + p.def_awareness * 0.30 + 25)
        mrk = int(p.def_awareness * 0.55 + p.interceptions * 0.25)
    return min(drb, 95), min(hed, 95), min(mrk, 95)


def derive_keeper(p):
    base = p.composure
    return min(int(base * 0.95 + 3), 95), min(int(base * 0.92), 95), min(int(base * 0.90), 95)


def main():
    updated_named = updated_derived = 0
    for p in Player.objects.all():
        if p.role == 'GK':
            trip = KEEPERS.get(p.name)
            if trip:
                p.gk_reflexes, p.gk_handling, p.gk_aerials = trip
                updated_named += 1
            else:
                p.gk_reflexes, p.gk_handling, p.gk_aerials = derive_keeper(p)
                updated_derived += 1
            p.dribbling = KEEPER_DRIBBLING.get(p.name, 35)
            p.heading = 25
            p.marking = 30
        else:
            trio = OUTFIELD.get(p.name)
            if trio:
                p.dribbling, p.heading, p.marking = trio
                updated_named += 1
            else:
                p.dribbling, p.heading, p.marking = derive_outfield(p)
                updated_derived += 1
        p.save(update_fields=['dribbling', 'heading', 'marking',
                              'gk_reflexes', 'gk_handling', 'gk_aerials'])
    print(f'named ratings applied: {updated_named}; derived fallbacks: {updated_derived}')


if __name__ == '__main__':
    main()
