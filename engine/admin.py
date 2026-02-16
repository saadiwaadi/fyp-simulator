from django.contrib import admin
from .models import Team, Player

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    # CHANGE THIS:
    # list_display = ('name', 'style') 
    
    # TO THIS:
    list_display = ('name', 'tactical_mode')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'role', 'is_starting', 'stamina')
    list_filter = ('team', 'role', 'is_starting')