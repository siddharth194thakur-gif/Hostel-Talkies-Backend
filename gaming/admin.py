from django.contrib import admin
from .models import Competition, CompetitionParticipant, CompetitionResult

class CompetitionParticipantInline(admin.TabularInline):
    model = CompetitionParticipant
    extra = 0
    readonly_fields = ['joined_at']

class CompetitionResultInline(admin.TabularInline):
    model = CompetitionResult
    extra = 0
    readonly_fields = ['submitted_at', 'updated_at']

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'game',
        'competition_type',
        'creator',
        'start_datetime',
        'status',
        'participants_count',
        'max_participants',
        'is_registration_closed_by_organizer',
        'is_active',
    ]
    list_filter = ['game', 'competition_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'custom_game_name', 'description', 'rules', 'creator__email', 'creator__username']
    inlines = [CompetitionParticipantInline, CompetitionResultInline]

@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'competition', 'user', 'in_game_name', 'game_uid', 'team_name', 'slot_number', 'status', 'joined_at']
    list_filter = ['status', 'competition__game', 'joined_at']
    search_fields = ['in_game_name', 'game_uid', 'team_name', 'user__email', 'competition__name']

@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'competition', 'participant', 'position', 'kills', 'points', 'score', 'verification_status', 'verified_by', 'submitted_at']
    list_filter = ['verification_status', 'competition__game', 'submitted_at']
    search_fields = ['participant__in_game_name', 'competition__name', 'score', 'notes']
