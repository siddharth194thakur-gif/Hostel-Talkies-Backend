from django.contrib import admin
from django.utils.html import format_html
from .models import HostelService


@admin.register(HostelService)
class HostelServiceAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category_badge', 'contact_person', 'phone_number',
        'location', 'hostel_display', 'status_badge'
    )
    list_filter = ('category', 'is_active', 'hostel')
    search_fields = ('name', 'description', 'contact_person', 'phone_number', 'location')
    actions = ['activate_services', 'deactivate_services']

    def category_badge(self, obj):
        return format_html('<span class="badge badge-purple">{}</span>', obj.get_category_display().upper())
    category_badge.short_description = "Service Category"

    def hostel_display(self, obj):
        if obj.hostel:
            return obj.hostel.name
        return "All Hostels"
    hostel_display.short_description = "Location / Hostel"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">ACTIVE</span>')
        return format_html('<span class="badge badge-secondary">INACTIVE</span>')
    status_badge.short_description = "Status"

    def activate_services(self, request, queryset):
        queryset.update(is_active=True)
    activate_services.short_description = "Activate selected services"

    def deactivate_services(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_services.short_description = "Deactivate selected services"