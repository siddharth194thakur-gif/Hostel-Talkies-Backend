from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from datetime import timedelta

from .models import User, StudentProfile, Student
from hostels.models import Hostel
from moderation.models import AdminActionLog


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Hostel Student Profile'
    fk_name = 'user'
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_cell', 'get_academic_info', 'get_hostel', 'get_room', 'status_badge', 'date_joined')
    list_filter = ('profile__hostel', 'profile__gender', 'profile__programme', 'is_blocked', 'is_active', 'is_suspended', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'profile__room__room_number', 'profile__phone_number', 'profile__branch', 'profile__programme')
    ordering = ('-date_joined',)
    inlines = [StudentProfileInline]
    list_per_page = 25
    actions = ['block_students', 'unblock_students', 'suspend_7_days', 'unsuspend_students', 'activate_students', 'deactivate_students']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_student=True).select_related('profile__hostel', 'profile__block', 'profile__room')

    def student_cell(self, obj):
        name = obj.get_full_name() or obj.username
        initial = (name[0] if name else "S").upper()
        return format_html(
            '<div style="display:flex; align-items:center; gap:10px;">'
            '<div style="width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg,#4f46e5,#7c3aed); color:#fff; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center;">{}</div>'
            '<div>'
            '<div style="font-weight:600; color:#1e293b; font-size:13px;">{}</div>'
            '<div style="font-size:11px; color:#64748b;">{}</div>'
            '</div>'
            '</div>',
            initial,
            name,
            obj.email
        )
    student_cell.short_description = "Student"

    def get_academic_info(self, obj):
        if hasattr(obj, 'profile'):
            prog = obj.profile.programme or ""
            branch = obj.profile.branch or ""
            if prog and branch:
                return format_html(
                    '<span style="font-weight:600; color:#334155;">{}</span><div style="font-size:11px; color:#64748b;">{}</div>',
                    prog,
                    branch
                )
            elif prog or branch:
                return prog or branch
        return "—"
    get_academic_info.short_description = "Programme / Branch"

    def get_hostel(self, obj):
        if hasattr(obj, 'profile') and obj.profile.hostel:
            return format_html(
                '<span class="badge" style="background:#e0f2fe; color:#0369a1; font-weight:600;">{}</span>',
                obj.profile.hostel.name
            )
        return "—"
    get_hostel.short_description = "Hostel"

    def get_room(self, obj):
        if hasattr(obj, 'profile') and obj.profile.room:
            blk = obj.profile.block.name if obj.profile.block else ""
            return format_html(
                '<span style="font-weight:500; color:#334155;">{} - Room {}</span>',
                blk,
                obj.profile.room.room_number
            )
        return "—"
    get_room.short_description = "Room Allotted"

    def status_badge(self, obj):
        if obj.is_blocked:
            return format_html('<span class="badge badge-danger">BLOCKED</span>')
        if obj.is_currently_suspended():
            return format_html('<span class="badge badge-warning">SUSPENDED</span>')
        if not obj.is_active:
            return format_html('<span class="badge badge-secondary">INACTIVE</span>')
        return format_html('<span class="badge badge-success">ACTIVE</span>')
    status_badge.short_description = "Status"

    def block_students(self, request, queryset):
        c = queryset.update(is_blocked=True, block_reason="Blocked by Admin")
        for u in queryset:
            AdminActionLog.objects.create(admin=request.user, action="BLOCK_STUDENT", target_type="Student", target_id=str(u.id), notes=f"Blocked account {u.email}")
        self.message_user(request, f"Successfully blocked {c} student account(s).")
    block_students.short_description = "🚫 Block selected students"

    def unblock_students(self, request, queryset):
        c = queryset.update(is_blocked=False, block_reason="")
        for u in queryset:
            AdminActionLog.objects.create(admin=request.user, action="UNBLOCK_STUDENT", target_type="Student", target_id=str(u.id), notes=f"Unblocked account {u.email}")
        self.message_user(request, f"Successfully unblocked {c} student account(s).")
    unblock_students.short_description = "✅ Unblock selected students"

    def activate_students(self, request, queryset):
        c = queryset.update(is_active=True)
        self.message_user(request, f"Successfully activated {c} student account(s).")
    activate_students.short_description = "🟢 Activate selected students"

    def deactivate_students(self, request, queryset):
        c = queryset.update(is_active=False)
        self.message_user(request, f"Successfully deactivated {c} student account(s).")
    deactivate_students.short_description = "⏸️ Deactivate selected students"

    def suspend_7_days(self, request, queryset):
        until = timezone.now() + timedelta(days=7)
        c = queryset.update(is_suspended=True, suspended_until=until, block_reason="Temporary suspension for 7 days")
        for u in queryset:
            AdminActionLog.objects.create(admin=request.user, action="SUSPEND_STUDENT", target_type="Student", target_id=str(u.id), notes=f"Suspended account {u.email} until {until.strftime('%Y-%m-%d')}")
        self.message_user(request, f"Successfully suspended {c} student(s) for 7 days.")
    suspend_7_days.short_description = "⏳ Suspend selected (7 Days)"

    def unsuspend_students(self, request, queryset):
        c = queryset.update(is_suspended=False, suspended_until=None, block_reason="")
        self.message_user(request, f"Successfully removed suspension for {c} student(s).")
    unsuspend_students.short_description = "🔄 Remove suspension"


@admin.register(User)
class AllUserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'role_badge', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_student', 'is_hostel_admin', 'is_staff', 'is_blocked', 'is_active', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    inlines = [StudentProfileInline]

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Roles', {'fields': ('is_student', 'is_hostel_admin')}),
        ('Account Status & Moderation', {'fields': ('is_active', 'is_blocked', 'is_suspended', 'suspended_until', 'block_reason')}),
        ('Django Staff / Superuser Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    def role_badge(self, obj):
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            return format_html('<span class="badge badge-warning">ADMIN</span>')
        return format_html('<span class="badge badge-primary">STUDENT</span>')
    role_badge.short_description = "Role"

