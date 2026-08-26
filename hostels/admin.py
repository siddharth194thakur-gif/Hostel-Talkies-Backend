from django.contrib import admin
from django.utils.html import format_html
from .models import Hostel, Block, Room
from users.models import StudentProfile


class BlockInline(admin.TabularInline):
    model = Block
    extra = 1
    show_change_link = True


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'gender',
        'get_blocks_count', 'get_rooms_count', 'get_students_count',
        'status_badge', 'created_at'
    )
    list_filter = ('gender', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    inlines = [BlockInline]
    actions = ['activate_hostels', 'deactivate_hostels']

    def get_blocks_count(self, obj):
        count = obj.blocks.count()
        return format_html('<span style="font-weight:600;">{} Blocks</span>', count)
    get_blocks_count.short_description = "Wings/Blocks"

    def get_rooms_count(self, obj):
        count = Room.objects.filter(block__hostel=obj).count()
        return format_html('<span style="font-weight:600;">{} Rooms</span>', count)
    get_rooms_count.short_description = "Total Rooms"

    def get_students_count(self, obj):
        count = StudentProfile.objects.filter(hostel=obj).count()
        return format_html('<span class="badge badge-primary">{} Students</span>', count)
    get_students_count.short_description = "Residents"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_hostels(self, request, queryset):
        queryset.update(is_active=True)
    activate_hostels.short_description = "Activate selected hostels"

    def deactivate_hostels(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_hostels.short_description = "Deactivate selected hostels"


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'hostel', 'floors', 'get_rooms_count',
        'get_students_count', 'status_badge', 'created_at'
    )
    list_filter = ('hostel', 'is_active', 'created_at')
    search_fields = ('name', 'hostel__name', 'hostel__code')
    inlines = [RoomInline]
    actions = ['activate_blocks', 'deactivate_blocks']

    def get_rooms_count(self, obj):
        return format_html('<span style="font-weight:600;">{} Rooms</span>', obj.rooms.count())
    get_rooms_count.short_description = "Rooms"

    def get_students_count(self, obj):
        count = StudentProfile.objects.filter(block=obj).count()
        return format_html('<span class="badge badge-primary">{} Students</span>', count)
    get_students_count.short_description = "Residents"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_blocks(self, request, queryset):
        queryset.update(is_active=True)
    activate_blocks.short_description = "Activate selected blocks"

    def deactivate_blocks(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_blocks.short_description = "Deactivate selected blocks"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'room_number', 'block', 'get_hostel', 'floor',
        'capacity', 'get_occupancy_display', 'occupancy_status_badge',
        'status_badge', 'created_at'
    )
    list_filter = ('block__hostel', 'block', 'floor', 'is_active')
    search_fields = ('room_number', 'block__name', 'block__hostel__name')
    actions = ['activate_rooms', 'deactivate_rooms']

    def get_hostel(self, obj):
        if obj.block and obj.block.hostel:
            return obj.block.hostel.name
        return "-"
    get_hostel.short_description = "Hostel"

    def get_occupancy_display(self, obj):
        count = obj.students.count()
        return f"{count} / {obj.capacity} students"
    get_occupancy_display.short_description = "Occupancy"

    def occupancy_status_badge(self, obj):
        count = obj.students.count()
        if count >= obj.capacity:
            return format_html('<span class="badge badge-danger">FULL</span>')
        elif count > 0:
            return format_html('<span class="badge badge-warning">OCCUPIED</span>')
        return format_html('<span class="badge badge-info">VACANT</span>')
    occupancy_status_badge.short_description = "Room State"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_rooms(self, request, queryset):
        queryset.update(is_active=True)
    activate_rooms.short_description = "Activate selected rooms"

    def deactivate_rooms(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_rooms.short_description = "Deactivate selected rooms"