from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import StudyResource


@admin.register(StudyResource)
class StudyResourceAdmin(admin.ModelAdmin):
    list_display = (
        'title_display', 'resource_type_badge', 'course_info', 'department_badge',
        'semester_badge', 'file_preview_badge', 'uploader_display', 'downloads_count', 'status_badge', 'created_at'
    )
    list_filter = ('resource_type', 'department', 'semester', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'course_name', 'course_code', 'uploader__email', 'uploader__first_name', 'uploader__last_name')
    list_per_page = 25
    actions = ['activate_resources', 'deactivate_resources']
    
    fieldsets = (
        ('📚 Academic Resource Details', {
            'fields': (
                ('title', 'resource_type'),
                ('department', 'course_name'),
                ('course_code', 'semester'),
            ),
            'description': 'Specify course subject details, department classification, and academic semester.'
        }),
        ('📄 PDF / Document Attachment', {
            'fields': (
                'file',
                'external_link',
                'description',
            ),
            'description': 'Upload the primary PDF / study document or provide an external drive/reference URL.'
        }),
        ('⚙️ Ownership & Publication Status', {
            'fields': (
                ('uploader', 'is_active'),
            ),
            'description': 'Manage publication visibility across the student portal.'
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.uploader_id:
            obj.uploader = request.user
        super().save_model(request, obj, form, change)

    def title_display(self, obj):
        icons = {
            'notes': '📝',
            'pyq': '📋',
            'book': '📚',
            'pdf': '📄',
            'assignment': '📁',
            'study_group': '👥',
        }
        icon = icons.get(obj.resource_type, '📄')
        return format_html(
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="font-size:16px;">{}</span>'
            '<div>'
            '<span style="font-weight:600; color:#1e293b;">{}</span>'
            '{}'
            '</div>'
            '</div>',
            icon,
            obj.title,
            format_html('<div style="font-size:11px; color:#64748b;">{}</div>', obj.course_code) if obj.course_code else ''
        )
    title_display.short_description = "Resource Title"

    def course_info(self, obj):
        return format_html(
            '<span style="font-weight:500; color:#334155;">{}</span>',
            obj.course_name or "—"
        )
    course_info.short_description = "Course / Subject"

    def department_badge(self, obj):
        if not obj.department:
            return "—"
        return format_html(
            '<span class="badge" style="background:#e0f2fe; color:#0369a1; font-weight:600;">{}</span>',
            obj.department
        )
    department_badge.short_description = "Department"

    def semester_badge(self, obj):
        if not obj.semester:
            return "—"
        return format_html(
            '<span class="badge" style="background:#f1f5f9; color:#475569; font-weight:600;">{}</span>',
            obj.semester
        )
    semester_badge.short_description = "Semester"

    def file_preview_badge(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" class="ht-btn-table-action" style="color:#4f46e5; text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-weight:600; font-size:11px; background:#eef2ff; padding:3px 8px; border-radius:6px;">'
                '<span>📄 View PDF</span>'
                '</a>',
                obj.file.url
            )
        elif obj.external_link:
            return format_html(
                '<a href="{}" target="_blank" style="color:#0284c7; text-decoration:none; font-size:11px; font-weight:600;">'
                '🔗 Link ↗'
                '</a>',
                obj.external_link
            )
        return format_html('<span style="color:#94a3b8; font-size:11px;">No file</span>')
    file_preview_badge.short_description = "Attachment"

    def resource_type_badge(self, obj):
        type_colors = {
            'notes': 'badge-primary',
            'pyq': 'badge-info',
            'book': 'badge-success',
            'pdf': 'badge-purple',
            'assignment': 'badge-warning',
            'study_group': 'badge-primary',
        }
        cls = type_colors.get(obj.resource_type, 'badge-secondary')
        return format_html('<span class="badge {}">{}</span>', cls, obj.get_resource_type_display().upper())
    resource_type_badge.short_description = "Type"

    def uploader_display(self, obj):
        if obj.uploader:
            name = obj.uploader.get_full_name() or obj.uploader.username
            return format_html(
                '<div style="font-size:12px;"><span style="font-weight:600; color:#1e293b;">{}</span>'
                '<div style="font-size:11px; color:#64748b;">{}</div></div>',
                name,
                obj.uploader.email
            )
        return "System Admin"
    uploader_display.short_description = "Uploader"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_resources(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Successfully activated {count} study resource(s).")
    activate_resources.short_description = "🟢 Activate selected resources"

    def deactivate_resources(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Successfully deactivated {count} study resource(s).")
    deactivate_resources.short_description = "⏸️ Deactivate selected resources"