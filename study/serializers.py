from rest_framework import serializers
from .models import StudyResource
from users.serializers import UserPublicSerializer


class StudyResourceSerializer(serializers.ModelSerializer):
    """
    Student-facing serializer.
    Source attribution fields (source_website, source_url) are intentionally
    excluded — they are internal import metadata, not student-facing content.
    """
    uploader_detail      = UserPublicSerializer(source='uploader', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)

    class Meta:
        model  = StudyResource
        fields = [
            'id',
            'title',
            'description',
            'resource_type',
            'resource_type_display',
            'course_name',
            'course_code',
            'semester',
            'department',
            'unit',
            'year',
            'exam_session',
            'file',
            'external_link',
            'author',
            'uploader',
            'uploader_detail',
            'downloads_count',
            'is_active',
            'needs_review',
            'created_at',
        ]
        read_only_fields = ['id', 'uploader', 'downloads_count', 'is_active', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        title = ret.get('title')
        if title:
            import re
            from urllib.parse import unquote
            t = unquote(title)
            t = re.sub(r'[\s\-_(]*[💙~]*[∆\u2206][☮\u262e\ufe0f]+[💙~]*[\s\-_)]*', ' ', t)
            t = re.sub(r'[\s~]{2,}', ' ', t)
            ret['title'] = re.sub(r'\s+', ' ', t).strip()
        return ret


class StudyResourceAdminSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer — includes internal source attribution fields
    so administrators can trace the origin of imported resources.
    """
    uploader_detail      = UserPublicSerializer(source='uploader', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)

    class Meta:
        model  = StudyResource
        fields = '__all__'
        read_only_fields = ['id', 'uploader', 'downloads_count', 'created_at']
