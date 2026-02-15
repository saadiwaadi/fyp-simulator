from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=50)
    style = models.IntegerField(default=50)  # Old style number (keep for now)
    
    # NEW: The Tactical Instruction Slot
    tactical_mode = models.CharField(max_length=20, default='STANDARD')

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=50)
    # The Link: If a Team is deleted, the player becomes a Free Agent (SET_NULL)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    
    ROLE_CHOICES = [('GK', 'Goalkeeper'), ('OUT', 'Outfielder')]
    role = models.CharField(max_length=3, choices=ROLE_CHOICES)
    
    # Stats
    vision = models.IntegerField(default=60)
    finishing = models.IntegerField(default=60)
    composure = models.IntegerField(default=60)
    def_awareness = models.IntegerField(default=60)
    short_passing = models.IntegerField(default=60)
    interceptions = models.IntegerField(default=60)
    stamina = models.IntegerField(default=70)

    def __str__(self):
        return f"{self.name} ({self.team})"