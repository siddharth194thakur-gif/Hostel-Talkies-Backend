from rest_framework import serializers
from .models import HostelService

class HostelServiceSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source='hostel.name')
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = HostelService
        fields = [
            'id', 'name', 'category', 'category_display', 'description',
            'contact_person', 'phone_number', 'location', 'timings',
            'hostel', 'hostel_name', 'is_active', 'created_at'
        ]
