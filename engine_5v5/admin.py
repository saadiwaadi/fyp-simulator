from django.contrib import admin
from .models import Player, Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):  # <--- FIXED (Removed .site)
    list_display = ('name', 'style')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin): # <--- FIXED (Removed .site)
    list_display = ('name', 'team', 'role', 'vision', 'finishing', 'stamina')
    list_filter = ('team', 'role')
    search_fields = ('name',)