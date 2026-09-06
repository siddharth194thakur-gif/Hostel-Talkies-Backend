from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import StudyResource

User = get_user_model()


class StudyResourceUploaderSerializer(serializers.ModelSerializer):
    """
    High-performance, lightweight uploader serializer for Study Resources.
    Avoids expensive N+1 queries (UserBlock, Hostel, Block, Room) while
    remaining 100% compatible with the frontend PublicUser interface.
    """
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    hostel_name = serializers.CharField(default=None, allow_null=True)
    is_blocked_by_me = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name',
            'role',
            'role_display',
            'hostel_name',
            'profile_picture',
            'is_student',
            'is_staff',
            'is_superuser',
            'is_blocked_by_me',
            'date_joined',
        ]

    def get_full_name(self, obj):
        full_name = (obj.get_full_name() or '').strip()
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            if not full_name or full_name.lower() in ['chief warden', 'chief administrator', 'warden', 'administrator']:
                return "Admin"
            return full_name
        return full_name or obj.username

    def get_role(self, obj):
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            return "Admin"
        if getattr(obj, 'is_student', False):
            return "Student"
        return "Hostel Resident"

    def get_role_display(self, obj):
        return self.get_role(obj)

    def get_profile_picture(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.avatar.url)
            return profile.avatar.url
        return None


class StudyResourceSerializer(serializers.ModelSerializer):
    """
    Student-facing serializer.
    Source attribution fields (source_website, source_url) are intentionally
    excluded — they are internal import metadata, not student-facing content.
    """
    uploader_detail       = StudyResourceUploaderSerializer(source='uploader', read_only=True)
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
    uploader_detail       = StudyResourceUploaderSerializer(source='uploader', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)

    class Meta:
        model  = StudyResource
        fields = '__all__'
        read_only_fields = ['id', 'uploader', 'downloads_count', 'created_at']
