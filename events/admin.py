from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'event_date', 'event_time', 'hostel_display',
        'location', 'organizer', 'timing_badge', 'status_badge'
    )
    list_filter = ('event_date', 'hostel', 'is_active')
    search_fields = ('title', 'description', 'location', 'organizer')
    actions = ['activate_events', 'deactivate_events']

    def hostel_display(self, obj):
        if obj.hostel:
            return format_html('<span class="badge badge-primary">{}</span>', obj.hostel.name)
        return format_html('<span class="badge badge-purple">ALL CAMPUS</span>')
    hostel_display.short_description = "Hostel"

    def timing_badge(self, obj):
        today = timezone.now().date()
        if obj.event_date > today:
            return format_html('<span class="badge badge-success">UPCOMING</span>')
        elif obj.event_date == today:
            return format_html('<span class="badge badge-warning">TODAY</span>')
        return format_html('<span class="badge badge-secondary">CONCLUDED</span>')
    timing_badge.short_description = "Timeline"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_events(self, request, queryset):
        queryset.update(is_active=True)
    activate_events.short_description = "Activate selected events"

    def deactivate_events(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_events.short_description = "Deactivate selected events"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)