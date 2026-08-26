from rest_framework import serializers
from .models import Conversation, Message, MessageReaction, UserChatPreference
from users.serializers import UserPublicSerializer
from posts.models import Post


class UserChatPreferenceSerializer(serializers.ModelSerializer):
    custom_bg_image_url = serializers.SerializerMethodField()

    class Meta:
        model = UserChatPreference
        fields = [
            'id', 'user', 'conversation', 'bg_type', 'bg_value',
            'custom_bg_image', 'custom_bg_image_url', 'bubble_style',
            'theme_mode', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'custom_bg_image_url']

    def get_custom_bg_image_url(self, obj):
        if obj.custom_bg_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.custom_bg_image.url)
            return obj.custom_bg_image.url
        return None


class MessageReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'user_name', 'reaction', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ReplyMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'sender_name', 'content', 'message_type', 'file_name']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class MessageSerializer(serializers.ModelSerializer):
    sender_detail = UserPublicSerializer(source='sender', read_only=True)
    is_me = serializers.SerializerMethodField()
    reply_to_detail = ReplyMessageSerializer(source='reply_to', read_only=True)
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_detail', 'message_type',
            'content', 'file', 'file_name', 'file_size', 'file_type',
            'reply_to', 'reply_to_detail', 'reactions', 'is_deleted_everyone',
            'is_read', 'is_me', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'created_at', 'is_deleted_everyone']

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False

    def get_reactions(self, obj):
        request = self.context.get('request')
        current_user_id = request.user.id if request and request.user.is_authenticated else None

        reactions_map = {}
        for r in obj.reactions.select_related('user').all():
            if r.reaction not in reactions_map:
                reactions_map[r.reaction] = {
                    'emoji': r.reaction,
                    'count': 0,
                    'users': [],
                    'user_reacted': False,
                }
            reactions_map[r.reaction]['count'] += 1
            user_display = r.user.get_full_name() or r.user.username
            reactions_map[r.reaction]['users'].append(user_display)
            if current_user_id and r.user_id == current_user_id:
                reactions_map[r.reaction]['user_reacted'] = True

        return list(reactions_map.values())


class ConversationListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    post_title = serializers.ReadOnlyField(source='related_post.title')
    group_admin_detail = UserPublicSerializer(source='group_admin', read_only=True)
    members_count = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'is_group', 'group_name', 'group_avatar', 'group_admin',
            'group_admin_detail', 'members_count', 'is_admin',
            'other_user', 'related_post', 'post_title',
            'last_message', 'unread_count', 'updated_at', 'created_at'
        ]

    def get_other_user(self, obj):
        if obj.is_group:
            return None
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return UserPublicSerializer(other, context=self.context).data
        return None

    def get_members_count(self, obj):
        return obj.participants.count()

    def get_is_admin(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.is_group:
            return obj.group_admin_id == request.user.id
        return False

    def get_last_message(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        
        qs = obj.messages.all()
        if user:
            qs = qs.exclude(deleted_for_users=user)
        
        last_msg = qs.last()
        if last_msg:
            if last_msg.is_deleted_everyone:
                content_preview = "🚫 This message was deleted"
            elif last_msg.message_type == 'image':
                content_preview = f"📷 {last_msg.content or 'Photo'}"
            elif last_msg.message_type == 'video':
                content_preview = f"🎥 {last_msg.content or 'Video'}"
            elif last_msg.message_type == 'file':
                content_preview = f"📄 {last_msg.file_name or last_msg.content or 'Document'}"
            elif last_msg.message_type == 'audio':
                content_preview = "🎤 Voice message"
            elif last_msg.message_type == 'gif':
                content_preview = "👾 GIF"
            else:
                content_preview = last_msg.content

            return {
                'id': last_msg.id,
                'content': content_preview,
                'message_type': last_msg.message_type,
                'sender_id': last_msg.sender_id,
                'sender_name': last_msg.sender.get_full_name() or last_msg.sender.username,
                'created_at': last_msg.created_at,
                'is_read': last_msg.is_read
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).exclude(deleted_for_users=request.user).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    participants_detail = UserPublicSerializer(source='participants', many=True, read_only=True)
    group_admin_detail = UserPublicSerializer(source='group_admin', read_only=True)
    messages = serializers.SerializerMethodField()
    post_info = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_blocked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'is_group', 'group_name', 'group_avatar', 'group_admin',
            'group_admin_detail', 'members_count', 'is_admin', 'is_blocked_by_me',
            'other_user', 'participants', 'participants_detail', 'related_post',
            'post_info', 'messages', 'created_at', 'updated_at'
        ]

    def get_other_user(self, obj):
        if obj.is_group:
            return None
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return UserPublicSerializer(other, context=self.context).data
        return None

    def get_is_blocked_by_me(self, obj):
        if obj.is_group:
            return False
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            from users.models import UserBlock
            return UserBlock.objects.filter(blocker=request.user, blocked=other).exists()
        return False


    def get_members_count(self, obj):
        return obj.participants.count()

    def get_is_admin(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.is_group:
            return obj.group_admin_id == request.user.id
        return False

    def get_messages(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        qs = obj.messages.select_related('sender', 'reply_to', 'reply_to__sender').prefetch_related('reactions', 'reactions__user')
        if user:
            qs = qs.exclude(deleted_for_users=user)
        return MessageSerializer(qs, many=True, context=self.context).data

    def get_post_info(self, obj):
        if obj.related_post:
            return {
                'id': obj.related_post.id,
                'title': obj.related_post.title,
                'price': str(obj.related_post.price) if obj.related_post.price else None,
                'post_type': obj.related_post.post_type,
                'status': obj.related_post.status,
            }
        return None
