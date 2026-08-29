from django.contrib import admin
from .models import GamingProfile, Tournament

@admin.register(GamingProfile)
class GamingProfileAdmin(admin.ModelAdmin):
    list_display = ('in_game_name', 'uid', 'user', 'br_rank', 'level', 'score', 'kd_ratio', 'total_booyahs', 'is_verified')
    list_filter = ('game_type', 'br_rank', 'is_verified')
    search_fields = ('in_game_name', 'uid', 'user__username', 'user__first_name')
    ordering = ('-score',)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('title', 'game_type', 'match_type', 'status', 'start_time', 'created_by')
    list_filter = ('game_type', 'match_type', 'status')
    search_fields = ('title', 'room_id')
