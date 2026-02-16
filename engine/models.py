from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    # [MANAGER MODE] Store the chosen tactic
    TACTIC_CHOICES = [
        ('Standard', 'Standard'),
        ('High Press', 'High Press'),
        ('Park the Bus', 'Park the Bus'),
        ('Tiki Taka', 'Tiki Taka'),
        ('Counter Attack', 'Counter Attack'),
    ]
    tactical_mode = models.CharField(max_length=50, choices=TACTIC_CHOICES, default='Standard')
    
    def __str__(self):
        return self.name

class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    # [MANAGER MODE] Selection & Roles
    ROLE_CHOICES = [('GK', 'GK'), ('DEF', 'DEF'), ('MID', 'MID'), ('FWD', 'FWD')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    ZONE_CHOICES = [('L', 'Left'), ('C', 'Center'), ('R', 'Right')]
    preferred_zone = models.CharField(max_length=1, choices=ZONE_CHOICES, default='C')
    
    is_starting = models.BooleanField(default=False) # The "Manager's Call"

    # Core Stats
    vision = models.IntegerField(default=60)
    finishing = models.IntegerField(default=60)
    composure = models.IntegerField(default=60)
    def_awareness = models.IntegerField(default=60)
    short_passing = models.IntegerField(default=60)
    interceptions = models.IntegerField(default=60)
    stamina = models.IntegerField(default=70)

    def __str__(self):
        return f"{self.name} ({self.role})"