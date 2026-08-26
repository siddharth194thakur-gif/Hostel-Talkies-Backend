from rest_framework import serializers
from .models import Notification
from users.serializers import UserPublicSerializer

class NotificationSerializer(serializers.ModelSerializer):
    sender_detail = UserPublicSerializer(source='sender', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'sender_detail', 'notification_type', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'notification_type', 'title', 'message', 'link', 'created_at']
