from rest_framework import serializers
from .models import StudyResource
from users.serializers import UserPublicSerializer

class StudyResourceSerializer(serializers.ModelSerializer):
    uploader_detail = UserPublicSerializer(source='uploader', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)

    class Meta:
        model = StudyResource
        fields = [
            'id', 'title', 'description', 'resource_type', 'resource_type_display',
            'course_name', 'course_code', 'semester', 'department',
            'file', 'external_link', 'uploader', 'uploader_detail',
            'downloads_count', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'uploader', 'downloads_count', 'is_active', 'created_at']
