from django.contrib import admin
from django.utils.html import format_html
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient_display', 'type_badge', 'title', 'read_badge', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__email', 'recipient__username')
    actions = ['mark_as_read']

    def recipient_display(self, obj):
        if obj.recipient:
            return obj.recipient.get_full_name() or obj.recipient.email
        return "-"
    recipient_display.short_description = "Recipient"

    def type_badge(self, obj):
        return format_html('<span class="badge badge-primary">{}</span>', obj.notification_type.upper())
    type_badge.short_description = "Type"

    def read_badge(self, obj):
        if obj.is_read:
            return format_html('<span class="badge badge-success">READ</span>')
        return format_html('<span class="badge badge-warning">UNREAD</span>')
    read_badge.short_description = "Status"

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"