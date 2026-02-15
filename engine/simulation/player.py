import random

class SimPlayer:
    def __init__(self, db_player):
        self.name = db_player.name
        self.role = db_player.role
        
        # Stats (Safety Defaults)
        self.vision = getattr(db_player, 'vision', 60)
        self.finishing = getattr(db_player, 'finishing', 60)
        self.composure = getattr(db_player, 'composure', 60)
        self.def_awareness = getattr(db_player, 'def_awareness', 60)
        self.short_passing = getattr(db_player, 'short_passing', 60)
        self.interceptions = getattr(db_player, 'interceptions', 60)
        self.stamina = getattr(db_player, 'stamina', 70)
        
        # Dynamic State
        self.current_stamina = self.stamina

    def drain_stamina(self, amount=1):
        self.current_stamina = max(0, self.current_stamina - amount)

    def get_effective_stat(self, stat_name, structural_mult=1.0):
        base = getattr(self, stat_name, 60)
        
        # Fatigue Penalty: -30% stats if exhausted
        if self.current_stamina < 30: 
            base *= 0.7 
            
        # Structural Penalty: Team shape affects individual performance
        return int(base * structural_mult)