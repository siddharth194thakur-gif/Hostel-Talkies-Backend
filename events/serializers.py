from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source='hostel.name')

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'event_date', 'event_time',
            'location', 'hostel', 'hostel_name', 'organizer',
            'banner_image', 'is_active', 'created_at'
        ]
