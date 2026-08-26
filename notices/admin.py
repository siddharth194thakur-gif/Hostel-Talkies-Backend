from django.contrib import admin
from django.utils.html import format_html
from .models import Notice
from moderation.models import AdminActionLog


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'priority_badge', 'target_hostel_display',
        'publish_date', 'expiry_date', 'status_badge', 'created_by_display'
    )
    list_filter = ('priority', 'is_active', 'target_hostel', 'publish_date')
    search_fields = ('title', 'content', 'created_by__email')
    actions = ['activate_notices', 'deactivate_notices']

    def priority_badge(self, obj):
        if obj.priority == 'urgent':
            return format_html('<span class="badge badge-danger">URGENT</span>')
        elif obj.priority == 'important':
            return format_html('<span class="badge badge-warning">IMPORTANT</span>')
        return format_html('<span class="badge badge-secondary">NORMAL</span>')
    priority_badge.short_description = "Priority"

    def target_hostel_display(self, obj):
        if obj.target_hostel:
            return format_html('<span class="badge badge-primary">{}</span>', obj.target_hostel.name)
        return format_html('<span class="badge badge-purple">ALL HOSTELS</span>')
    target_hostel_display.short_description = "Target Scope"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">PUBLISHED</span>')
        return format_html('<span class="badge badge-secondary">DRAFT / HIDDEN</span>')
    status_badge.short_description = "Status"

    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return "System / Admin"
    created_by_display.short_description = "Author"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        AdminActionLog.objects.create(
            admin=request.user,
            action="CREATE_NOTICE" if not change else "UPDATE_NOTICE",
            target_type="Notice",
            target_id=str(obj.id),
            notes=f"Notice: '{obj.title}' (Priority: {obj.priority})"
        )

    def activate_notices(self, request, queryset):
        queryset.update(is_active=True)
    activate_notices.short_description = "Publish/Activate selected notices"

    def deactivate_notices(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_notices.short_description = "Unpublish/Deactivate selected notices"