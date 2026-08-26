from rest_framework import serializers
from .models import Report, Feedback, AdminActionLog, SiteSetting
from users.serializers import UserPublicSerializer

class ReportSerializer(serializers.ModelSerializer):
    reporter_detail = UserPublicSerializer(source='reporter', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_detail', 'report_type',
            'target_id', 'reason', 'details', 'status',
            'admin_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reporter', 'status', 'admin_notes', 'created_at', 'updated_at']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'name', 'email', 'subject', 'message', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']


class AdminActionLogSerializer(serializers.ModelSerializer):
    admin_name = serializers.ReadOnlyField(source='admin.email')

    class Meta:
        model = AdminActionLog
        fields = ['id', 'admin', 'admin_name', 'action', 'target_type', 'target_id', 'notes', 'timestamp']


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['id', 'site_name', 'tagline', 'community_rules', 'guidelines', 'contact_email', 'maintenance_mode']
