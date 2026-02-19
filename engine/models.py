from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)
    # Tactical Profile (0-100)
    attack_strength = models.IntegerField(default=50)
    defense_strength = models.IntegerField(default=50)
    # New Field for Tactical Identity
    tactical_mode = models.CharField(max_length=20, default='STANDARD') 

    def __str__(self):
        return self.name

class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10) # GK, DEF, MID, FWD
    
    # [v2.6] SPATIAL DNA
    # 'L' = Left, 'C' = Center, 'R' = Right
    preferred_zone = models.CharField(max_length=50, null=True, blank=True, default="Center")

    # Core Stats (0-100)
    stamina = models.IntegerField(default=70)
    speed = models.IntegerField(default=60)
    shooting = models.IntegerField(default=50)
    passing = models.IntegerField(default=50)
    defense = models.IntegerField(default=50)
    
    # Advanced Stats
    vision = models.IntegerField(default=50)
    finishing = models.IntegerField(default=50)
    composure = models.IntegerField(default=50)
    def_awareness = models.IntegerField(default=50)
    short_passing = models.IntegerField(default=50)
    interceptions = models.IntegerField(default=50)

    # --- TACTICAL MEMORY (The Missing Fields) ---
    is_starting = models.BooleanField(default=False)
    
    # Stores "Stay Back", "False 9", etc.
    tactical_instruction = models.CharField(max_length=50, default="Standard", blank=True)
    
    # Stores "CAP", "PEN", etc.
    set_piece_role = models.CharField(max_length=10, default="", blank=True)

    # Position Slots (Where they stand on the pitch)
    slot_5v5 = models.CharField(max_length=20, blank=True, null=True)
    slot_11v11 = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

# [NEW] THE BLACK BOX RECORDER
class Match(models.Model):
    date_played = models.DateTimeField(auto_now_add=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    mode = models.CharField(max_length=10) # '5v5' or '11v11'
    
    # Results
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    
    # Telemetry Data (JSON)
    # This stores the entire match log and stat sheet
    stats = models.JSONField(default=dict)
    logs = models.JSONField(default=list)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} [{self.date_played.strftime('%Y-%m-%d')}]"