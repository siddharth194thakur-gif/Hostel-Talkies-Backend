from rest_framework import serializers
from .models import Notice
from hostels.serializers import HostelSerializer, BlockSerializer
from users.serializers import UserPublicSerializer

class NoticeSerializer(serializers.ModelSerializer):
    target_hostel_name = serializers.ReadOnlyField(source='target_hostel.name')
    target_block_name = serializers.ReadOnlyField(source='target_block.name')
    created_by_name = serializers.SerializerMethodField()
    created_by_role = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'content', 'priority', 'target_hostel', 'target_hostel_name',
            'target_block', 'target_block_name', 'publish_date', 'expiry_date',
            'attachment', 'is_active', 'created_by_name', 'created_by_role', 'created_at'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            if obj.created_by.is_superuser or obj.created_by.is_staff or getattr(obj.created_by, 'is_hostel_admin', False):
                full_name = obj.created_by.get_full_name().strip()
                if not full_name or full_name.lower() in ['chief warden', 'chief administrator', 'warden', 'hostel administration', 'admin']:
                    return "Admin"
                return full_name
            return obj.created_by.get_full_name() or obj.created_by.username
        return "Admin"

    def get_created_by_role(self, obj):
        if obj.created_by:
            if obj.created_by.is_superuser or obj.created_by.is_staff or getattr(obj.created_by, 'is_hostel_admin', False):
                return "Admin"
            return "Student"
        return "Admin"
