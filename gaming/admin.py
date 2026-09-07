from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Competition, CompetitionParticipant, CompetitionResult


class CompetitionParticipantInline(admin.TabularInline):
    model = CompetitionParticipant
    extra = 0
    readonly_fields = ['joined_at']
    fields = ['user', 'in_game_name', 'game_uid', 'team_name', 'slot_number', 'status', 'joined_at']


class CompetitionResultInline(admin.TabularInline):
    model = CompetitionResult
    extra = 0
    readonly_fields = ['submitted_at', 'updated_at']
    fields = ['participant', 'position', 'kills', 'points', 'score', 'verification_status', 'verified_by', 'submitted_at']


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'game_badge',
        'competition_type',
        'creator_display',
        'start_datetime',
        'status_badge',
        'slots_display',
        'room_credentials_display',
        'is_active',
    ]
    list_filter = ['game', 'competition_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'custom_game_name', 'description', 'rules', 'creator__email', 'creator__username', 'room_id']
    inlines = [CompetitionParticipantInline, CompetitionResultInline]
    actions = ['mark_live', 'mark_completed', 'close_registration', 'open_registration']

    fieldsets = (
        ('Competition Info', {
            'fields': ('name', 'game', 'custom_game_name', 'creator', 'hostel', 'description', 'rules', 'is_active')
        }),
        ('Format & Schedule', {
            'fields': ('competition_type', 'status', 'start_datetime', 'end_datetime', 'registration_deadline', 'max_participants', 'is_registration_closed_by_organizer')
        }),
        ('In-Game Custom Room Access', {
            'fields': ('room_id', 'room_password', 'contact_info'),
            'description': 'Custom Room ID and Password will be displayed to registered participants when the match goes live.'
        }),
        ('Scoring & Rewards', {
            'fields': ('scoring_type', 'scoring_rules', 'prize_pool')
        }),
    )

    def game_badge(self, obj):
        colors = {
            'bgmi': '#f97316',
            'bgmi_lite': '#ea580c',
            'free_fire_max': '#e11d48',
            'other': '#6366f1',
        }
        color = colors.get(obj.game, '#64748b')
        return format_html('<span class="badge" style="background:{}; color:#fff; font-weight:600;">{}</span>', color, obj.game_display)
    game_badge.short_description = "Game"

    def creator_display(self, obj):
        return obj.creator.get_full_name() or obj.creator.email
    creator_display.short_description = "Host / Creator"

    def status_badge(self, obj):
        status_map = {
            'upcoming': ('#0284c7', 'UPCOMING'),
            'registration_open': ('#10b981', 'REG OPEN'),
            'live': ('#ef4444', 'LIVE NOW'),
            'completed': ('#64748b', 'COMPLETED'),
            'cancelled': ('#94a3b8', 'CANCELLED'),
        }
        color, label = status_map.get(obj.status, ('#64748b', obj.status.upper()))
        return format_html('<span class="badge" style="background:{}; color:#fff;">{}</span>', color, label)
    status_badge.short_description = "Status"

    def slots_display(self, obj):
        count = obj.participants_count
        max_p = obj.max_participants
        return format_html('<b>{}</b> / {} slots', count, max_p)
    slots_display.short_description = "Participants"

    def room_credentials_display(self, obj):
        if obj.room_id:
            pwd = f" (Pass: {obj.room_password})" if obj.room_password else ""
            return format_html('<span style="font-family:monospace; font-weight:600;">ID: {}{}</span>', obj.room_id, pwd)
        return format_html('<span class="text-muted" style="font-size:12px;">Not Set</span>')
    room_credentials_display.short_description = "Room ID / Password"

    def mark_live(self, request, queryset):
        queryset.update(status='live')
    mark_live.short_description = "Mark selected matches as LIVE"

    def mark_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_completed.short_description = "Mark selected matches as COMPLETED"

    def close_registration(self, request, queryset):
        queryset.update(is_registration_closed_by_organizer=True)
    close_registration.short_description = "Close registration for selected"

    def open_registration(self, request, queryset):
        queryset.update(is_registration_closed_by_organizer=False, status='registration_open')
    open_registration.short_description = "Open registration for selected"


@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'competition', 'user', 'in_game_name', 'game_uid', 'team_name', 'slot_number', 'status_badge', 'joined_at']
    list_filter = ['status', 'competition__game', 'joined_at']
    search_fields = ['in_game_name', 'game_uid', 'team_name', 'user__email', 'competition__name']
    actions = ['confirm_participants', 'disqualify_participants']

    def status_badge(self, obj):
        if obj.status == 'confirmed':
            return format_html('<span class="badge badge-success">CONFIRMED</span>')
        elif obj.status == 'disqualified':
            return format_html('<span class="badge badge-danger">DISQUALIFIED</span>')
        return format_html('<span class="badge badge-primary">REGISTERED</span>')
    status_badge.short_description = "Status"

    def confirm_participants(self, request, queryset):
        queryset.update(status='confirmed')
    confirm_participants.short_description = "Confirm selected participants"

    def disqualify_participants(self, request, queryset):
        queryset.update(status='disqualified')
    disqualify_participants.short_description = "Disqualify selected participants"


@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'competition', 'participant', 'position', 'kills', 'points', 'score', 'verification_badge', 'verified_by', 'submitted_at']
    list_filter = ['verification_status', 'competition__game', 'submitted_at']
    search_fields = ['participant__in_game_name', 'competition__name', 'score', 'notes']
    actions = ['approve_results', 'reject_results']

    def verification_badge(self, obj):
        if obj.verification_status == 'approved':
            return format_html('<span class="badge badge-success">APPROVED</span>')
        elif obj.verification_status == 'rejected':
            return format_html('<span class="badge badge-danger">REJECTED</span>')
        return format_html('<span class="badge badge-warning">PENDING</span>')
    verification_badge.short_description = "Verification"

    def approve_results(self, request, queryset):
        queryset.update(verification_status='approved', verified_by=request.user, verified_at=timezone.now())
    approve_results.short_description = "Approve selected match results"

    def reject_results(self, request, queryset):
        queryset.update(verification_status='rejected', verified_by=request.user, verified_at=timezone.now())
    reject_results.short_description = "Reject selected match results"
