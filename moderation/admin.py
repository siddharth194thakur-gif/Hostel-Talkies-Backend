from django.contrib import admin
from django.utils.html import format_html
from .models import Report, Feedback, AdminActionLog, SiteSetting


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'reporter_display', 'report_type_badge', 'target_id',
        'reason', 'status_badge', 'created_at'
    )
    list_filter = ('report_type', 'reason', 'status', 'created_at')
    search_fields = ('reporter__email', 'target_id', 'details')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_reviewing', 'mark_resolved', 'mark_dismissed']

    def reporter_display(self, obj):
        if obj.reporter:
            return obj.reporter.get_full_name() or obj.reporter.email
        return "Anonymous"
    reporter_display.short_description = "Reporter"

    def report_type_badge(self, obj):
        return format_html('<span class="badge badge-purple">{}</span>', obj.report_type.upper())
    report_type_badge.short_description = "Target Type"

    def status_badge(self, obj):
        if obj.status == 'pending':
            return format_html('<span class="badge badge-danger">PENDING</span>')
        elif obj.status == 'reviewing':
            return format_html('<span class="badge badge-warning">IN REVIEW</span>')
        elif obj.status == 'resolved':
            return format_html('<span class="badge badge-success">RESOLVED</span>')
        return format_html('<span class="badge badge-secondary">DISMISSED</span>')
    status_badge.short_description = "Status"

    def mark_reviewing(self, request, queryset):
        queryset.update(status='reviewing')
    mark_reviewing.short_description = "Mark selected as In Review"

    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_resolved.short_description = "Mark selected as Resolved"

    def mark_dismissed(self, request, queryset):
        queryset.update(status='dismissed')
    mark_dismissed.short_description = "Mark selected as Dismissed"


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user_or_email', 'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'message', 'email', 'name')
    actions = ['mark_reviewing', 'mark_resolved']

    def user_or_email(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return obj.email or obj.name or "Anonymous"
    user_or_email.short_description = "Submitted By"

    def status_badge(self, obj):
        if obj.status == 'pending':
            return format_html('<span class="badge badge-warning">PENDING</span>')
        elif obj.status == 'reviewing':
            return format_html('<span class="badge badge-info">REVIEWING</span>')
        return format_html('<span class="badge badge-success">RESOLVED</span>')
    status_badge.short_description = "Status"

    def mark_reviewing(self, request, queryset):
        queryset.update(status='reviewing')
    mark_reviewing.short_description = "Mark as reviewing"

    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_resolved.short_description = "Mark as resolved"


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'admin_display', 'action_badge', 'target_type', 'target_id', 'notes')
    list_filter = ('action', 'target_type', 'timestamp')
    search_fields = ('admin__email', 'action', 'target_id', 'notes')
    readonly_fields = ('admin', 'action', 'target_type', 'target_id', 'notes', 'timestamp')

    def admin_display(self, obj):
        if obj.admin:
            return obj.admin.get_full_name() or obj.admin.username
        return "System"
    admin_display.short_description = "Admin User"

    def action_badge(self, obj):
        act = obj.action.upper()
        if "CREATE" in act:
            return format_html('<span class="badge badge-success">{}</span>', act)
        elif "DELETE" in act or "BLOCK" in act or "PURGE" in act:
            return format_html('<span class="badge badge-danger">{}</span>', act)
        elif "SUSPEND" in act or "HIDE" in act:
            return format_html('<span class="badge badge-warning">{}</span>', act)
        return format_html('<span class="badge badge-primary">{}</span>', act)
    action_badge.short_description = "Action"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'tagline', 'contact_email', 'maintenance_badge')

    def maintenance_badge(self, obj):
        if obj.maintenance_mode:
            return format_html('<span class="badge badge-danger">MAINTENANCE ON</span>')
        return format_html('<span class="badge badge-success">LIVE</span>')
    maintenance_badge.short_description = "System Status"