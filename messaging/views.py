import os
from PIL import Image
from rest_framework import viewsets, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse, Http404
from django.conf import settings

from .models import Conversation, Message, MessageReaction, UserChatPreference
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer, MessageSerializer,
    MessageReactionSerializer, UserChatPreferenceSerializer
)
from users.permissions import IsNotBlockedOrSuspended
from users.models import UserBlock
from users.serializers import UserPublicSerializer
from notifications.models import Notification

User = get_user_model()

# Configurable Upload limits & validation
MAX_UPLOAD_SIZE_MB = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 25)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.mkv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.webm'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.csv'}
ALL_ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).distinct().order_by('-updated_at')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Mark messages sent by others in this conversation as read
        instance.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class StartConversationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        post_id = request.data.get('post_id')
        initial_message = request.data.get('message', '').strip()

        if not recipient_id:
            return Response({'detail': 'Recipient ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient_id_int = int(recipient_id)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid recipient ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if recipient_id_int == request.user.id:
            return Response({'detail': 'You cannot start a conversation with yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        recipient = get_object_or_404(User, id=recipient_id_int)

        # Enforce user blocking
        if UserBlock.objects.filter(blocker=request.user, blocked=recipient).exists():
            return Response({'detail': 'You have blocked this user. Unblock them to start a conversation.'}, status=status.HTTP_403_FORBIDDEN)
        if UserBlock.objects.filter(blocker=recipient, blocked=request.user).exists():
            return Response({'detail': 'You cannot start a conversation with this user.'}, status=status.HTTP_403_FORBIDDEN)

        # Check if conversation already exists between these 2 users (and optionally related post)
        conversations = Conversation.objects.filter(participants=request.user).filter(participants=recipient)
        if post_id:
            conv = conversations.filter(related_post_id=post_id).first()
        else:
            conv = conversations.first()

        is_new_conversation = not conv
        if not conv:
            conv = Conversation.objects.create(related_post_id=post_id if post_id else None)
            conv.participants.add(request.user, recipient)

        if initial_message:
            msg = Message.objects.create(conversation=conv, sender=request.user, content=initial_message, message_type='text')
            conv.save()  # triggers updated_at
            
            # Create notification for recipient
            sender_name = request.user.get_full_name() or request.user.username
            Notification.objects.create(
                recipient=recipient,
                sender=request.user,
                notification_type='message',
                title='New Message',
                message=f'{sender_name}: {initial_message[:60]}',
                link=f'/messages/{conv.id}'
            )

        serializer = ConversationDetailSerializer(conv, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if is_new_conversation else status.HTTP_200_OK)


class SendMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation, id=conversation_id)

        # Server-side security check: Only participants can send messages
        if not conv.participants.filter(id=request.user.id).exists():
            return Response({'detail': 'You are not a member of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        # Enforce user blocking in direct chats
        if not conv.is_group:
            other_user = conv.participants.exclude(id=request.user.id).first()
            if other_user:
                if UserBlock.objects.filter(blocker=request.user, blocked=other_user).exists():
                    return Response({'detail': 'You have blocked this user. Unblock them to send messages.'}, status=status.HTTP_403_FORBIDDEN)
                if UserBlock.objects.filter(blocker=other_user, blocked=request.user).exists():
                    return Response({'detail': 'You cannot send messages to this user.'}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content', '').strip()

        message_type = request.data.get('message_type', 'text').strip().lower()
        file = request.FILES.get('file')
        reply_to_id = request.data.get('reply_to_id')

        file_name = ''
        file_size = None
        file_type = ''

        if file:
            # Validate file size
            if file.size > MAX_UPLOAD_SIZE_BYTES:
                return Response(
                    {'detail': f'File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_MB}MB.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate extension
            _, ext = os.path.splitext(file.name.lower())
            if ext not in ALL_ALLOWED_EXTENSIONS:
                return Response(
                    {'detail': f'Unsupported file type "{ext}". Allowed formats include photos, videos, audio, PDFs, and office documents.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Automatically categorize message_type if not explicitly set
            if ext in IMAGE_EXTENSIONS and message_type != 'gif':
                try:
                    img = Image.open(file)
                    img.verify()
                    file.seek(0)
                except Exception:
                    return Response({'detail': 'The uploaded file is not a valid image.'}, status=status.HTTP_400_BAD_REQUEST)
                message_type = 'image'
            elif ext in VIDEO_EXTENSIONS:
                message_type = 'video'
            elif ext in AUDIO_EXTENSIONS:
                message_type = 'audio'
            elif ext in DOCUMENT_EXTENSIONS:
                message_type = 'file'

            file_name = file.name
            file_size = file.size
            file_type = file.content_type or ext.lstrip('.')
        elif not content and message_type != 'audio':
            return Response({'detail': 'Message content or file attachment cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional reply message linkage
        reply_to_msg = None
        if reply_to_id:
            reply_to_msg = conv.messages.filter(id=reply_to_id).first()

        msg = Message.objects.create(
            conversation=conv,
            sender=request.user,
            message_type=message_type,
            content=content,
            file=file,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            reply_to=reply_to_msg
        )
        conv.save()

        # Send notifications
        sender_name = request.user.get_full_name() or request.user.username
        if message_type == 'image':
            notif_text = f"📷 {content or 'Photo'}"
        elif message_type == 'video':
            notif_text = f"🎥 {content or 'Video'}"
        elif message_type == 'file':
            notif_text = f"📄 {file_name or 'Document'}"
        elif message_type == 'audio':
            notif_text = "🎤 Voice message"
        elif message_type == 'gif':
            notif_text = "👾 GIF"
        else:
            notif_text = content[:50]

        if conv.is_group:
            for participant in conv.participants.exclude(id=request.user.id):
                Notification.objects.create(
                    recipient=participant,
                    sender=request.user,
                    notification_type='message',
                    title=f"💬 {conv.group_name}",
                    message=f"{sender_name}: {notif_text}",
                    link=f"/messages/{conv.id}"
                )
        else:
            other_user = conv.participants.exclude(id=request.user.id).first()
            if other_user:
                Notification.objects.create(
                    recipient=other_user,
                    sender=request.user,
                    notification_type='message',
                    title='New Message',
                    message=f"{sender_name}: {notif_text}",
                    link=f"/messages/{conv.id}"
                )

        return Response(MessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)


class MessageReactionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)

        # Verify participant
        if not msg.conversation.participants.filter(id=request.user.id).exists():
            return Response({'detail': 'You are not a member of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        reaction_str = request.data.get('reaction', '').strip()
        if not reaction_str:
            return Response({'detail': 'Reaction emoji is required.'}, status=status.HTTP_400_BAD_REQUEST)

        existing = MessageReaction.objects.filter(message=msg, user=request.user).first()
        if existing:
            if existing.reaction == reaction_str:
                # Toggle off
                existing.delete()
            else:
                # Change reaction
                existing.reaction = reaction_str
                existing.save()
        else:
            MessageReaction.objects.create(message=msg, user=request.user, reaction=reaction_str)

        # Return updated reactions
        serializer = MessageSerializer(msg, context={'request': request})
        return Response(serializer.data['reactions'], status=status.HTTP_200_OK)


class DeleteMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)

        # Verify participant
        if not msg.conversation.participants.filter(id=request.user.id).exists():
            return Response({'detail': 'You are not a member of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        delete_type = request.data.get('delete_type', 'for_me')

        if delete_type == 'for_everyone':
            # Only sender or group admin or staff can delete for everyone
            is_sender = (msg.sender_id == request.user.id)
            is_admin = (msg.conversation.is_group and msg.conversation.group_admin_id == request.user.id)
            if not (is_sender or is_admin or request.user.is_staff):
                return Response({'detail': 'You can only delete your own messages for everyone.'}, status=status.HTTP_403_FORBIDDEN)

            msg.is_deleted_everyone = True
            msg.content = "🚫 This message was deleted"
            if msg.file:
                try:
                    msg.file.delete(save=False)
                except Exception:
                    pass
                msg.file = None
                msg.file_name = ''
            msg.save()
            return Response({'detail': 'Message deleted for everyone.', 'delete_type': 'for_everyone'}, status=status.HTTP_200_OK)
        else:
            # Delete for me
            msg.deleted_for_users.add(request.user)
            return Response({'detail': 'Message deleted for you.', 'delete_type': 'for_me'}, status=status.HTTP_200_OK)


class DownloadAttachmentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)

        # Strictly check conversation membership
        if not msg.conversation.participants.filter(id=request.user.id).exists() and not request.user.is_staff:
            return Response({'detail': 'You do not have permission to access this attachment.'}, status=status.HTTP_403_FORBIDDEN)

        if not msg.file:
            raise Http404("Attachment not found.")

        try:
            return FileResponse(
                msg.file.open('rb'),
                as_attachment=True,
                filename=msg.file_name or os.path.basename(msg.file.name)
            )
        except Exception:
            raise Http404("File could not be opened.")


class CreateGroupView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request):
        group_name = request.data.get('group_name', '').strip()
        if not group_name:
            return Response({'detail': 'Group name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        group_avatar = request.FILES.get('group_avatar')
        member_ids_raw = request.data.get('member_ids', [])
        
        # Handle stringified JSON or list
        if isinstance(member_ids_raw, str):
            import json
            try:
                member_ids = json.loads(member_ids_raw)
            except Exception:
                member_ids = [m.strip() for m in member_ids_raw.split(',') if m.strip()]
        else:
            member_ids = member_ids_raw

        group = Conversation.objects.create(
            is_group=True,
            group_name=group_name,
            group_avatar=group_avatar,
            group_admin=request.user
        )
        group.participants.add(request.user)

        if member_ids:
            for m_id in member_ids:
                try:
                    user_to_add = User.objects.filter(id=int(m_id), is_blocked=False).first()
                    if user_to_add:
                        group.participants.add(user_to_add)
                except (ValueError, TypeError):
                    continue

        initial_message = request.data.get('message', '').strip()
        if initial_message:
            Message.objects.create(conversation=group, sender=request.user, content=initial_message, message_type='text')
            group.save()

        # Send notifications to added members
        for member in group.participants.exclude(id=request.user.id):
            Notification.objects.create(
                recipient=member,
                sender=request.user,
                notification_type='message',
                title='Added to Group',
                message=f"{request.user.get_full_name() or request.user.username} added you to group '{group_name}'",
                link=f"/messages/{group.id}"
            )

        serializer = ConversationDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GroupDetailActionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def patch(self, request, group_id):
        group = get_object_or_404(Conversation, id=group_id, is_group=True, participants=request.user)
        if group.group_admin_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only the group admin can modify group details.'}, status=status.HTTP_403_FORBIDDEN)

        group_name = request.data.get('group_name')
        if group_name is not None:
            group_name = group_name.strip()
            if not group_name:
                return Response({'detail': 'Group name cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            group.group_name = group_name

        if 'group_avatar' in request.FILES:
            group.group_avatar = request.FILES['group_avatar']

        group.save()
        serializer = ConversationDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, group_id):
        group = get_object_or_404(Conversation, id=group_id, is_group=True, participants=request.user)
        if group.group_admin_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only the group admin can delete this group.'}, status=status.HTTP_403_FORBIDDEN)

        group.delete()
        return Response({'detail': 'Group deleted successfully.'}, status=status.HTTP_200_OK)


class AddGroupMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, group_id):
        group = get_object_or_404(Conversation, id=group_id, is_group=True, participants=request.user)
        if group.group_admin_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only the group admin can add members.'}, status=status.HTTP_403_FORBIDDEN)

        member_ids_raw = request.data.get('member_ids', [])
        if hasattr(request.data, 'getlist') and not isinstance(request.data.get('member_ids'), (list, dict)):
            list_data = request.data.getlist('member_ids')
            if len(list_data) > 1 or (list_data and not isinstance(list_data[0], list)):
                member_ids_raw = list_data

        if isinstance(member_ids_raw, (int, float)):
            member_ids = [member_ids_raw]
        elif isinstance(member_ids_raw, str):
            import json
            try:
                member_ids = json.loads(member_ids_raw)
                if not isinstance(member_ids, list):
                    member_ids = [member_ids]
            except Exception:
                member_ids = [m.strip() for m in member_ids_raw.split(',') if m.strip()]
        elif isinstance(member_ids_raw, (list, tuple, set)):
            member_ids = list(member_ids_raw)
        else:
            member_ids = []

        added_users = []
        for m_id in member_ids:
            try:
                user_to_add = User.objects.filter(id=int(m_id), is_blocked=False).first()
                if user_to_add and user_to_add not in group.participants.all():
                    group.participants.add(user_to_add)
                    added_users.append(user_to_add)
            except (ValueError, TypeError):
                continue

        for user in added_users:
            Notification.objects.create(
                recipient=user,
                sender=request.user,
                notification_type='message',
                title='Added to Group',
                message=f"{request.user.get_full_name() or request.user.username} added you to '{group.group_name}'",
                link=f"/messages/{group.id}"
            )

        serializer = ConversationDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RemoveGroupMemberView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, group_id):
        group = get_object_or_404(Conversation, id=group_id, is_group=True, participants=request.user)
        if group.group_admin_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only the group admin can remove members.'}, status=status.HTTP_403_FORBIDDEN)

        member_id = request.data.get('member_id')
        if not member_id:
            return Response({'detail': 'member_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member_id_int = int(member_id)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid member_id.'}, status=status.HTTP_400_BAD_REQUEST)

        if member_id_int == group.group_admin_id:
            return Response({'detail': 'Group admin cannot be removed. Transfer admin or delete the group instead.'}, status=status.HTTP_400_BAD_REQUEST)

        target_user = get_object_or_404(User, id=member_id_int)
        group.participants.remove(target_user)

        serializer = ConversationDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveGroupView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, group_id):
        group = get_object_or_404(Conversation, id=group_id, is_group=True, participants=request.user)
        group.participants.remove(request.user)

        # If admin leaves, transfer admin to another participant if available
        if group.group_admin_id == request.user.id:
            remaining = group.participants.first()
            if remaining:
                group.group_admin = remaining
                group.save()
            else:
                group.delete()
                return Response({'detail': 'You have left the group. The empty group was deleted.'}, status=status.HTTP_200_OK)

        return Response({'detail': 'You have left the group successfully.'}, status=status.HTTP_200_OK)


class AvailableMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        qs = User.objects.filter(is_active=True, is_blocked=False).exclude(id=request.user.id)
        if search:
            clean_user_query = search.lstrip('@').strip()
            clean_id = clean_user_query.lstrip('#')
            is_numeric_id = clean_id.isdigit()
            id_num = int(clean_id) if is_numeric_id else None

            from django.db.models import Value, Case, When, IntegerField
            from django.db.models.functions import Concat

            qs = qs.annotate(
                full_name_concat=Concat('first_name', Value(' '), 'last_name')
            )
            user_filter = (
                Q(username__iexact=clean_user_query) |
                Q(username__icontains=clean_user_query) |
                Q(first_name__icontains=clean_user_query) |
                Q(last_name__icontains=clean_user_query) |
                Q(full_name_concat__icontains=clean_user_query)
            )
            if id_num is not None:
                user_filter |= Q(id=id_num)

            ordering = []
            if id_num is not None:
                qs = qs.annotate(
                    exact_id=Case(
                        When(id=id_num, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                )
                ordering.append('-exact_id')

            qs = qs.annotate(
                exact_username=Case(
                    When(username__iexact=clean_user_query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
            ordering.extend(['-exact_username', 'username'])
            qs = qs.filter(user_filter).order_by(*ordering)

        qs = qs.select_related('profile__hostel')[:30]
        serializer = UserPublicSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class UnreadMessageCountView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).exclude(deleted_for_users=request.user).count()
        return Response({'unread_count': count})


class ChatPreferenceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get(self, request, conversation_id=None):
        conv = None
        if conversation_id:
            conv = get_object_or_404(Conversation, id=conversation_id)
            if not conv.participants.filter(id=request.user.id).exists():
                return Response({'detail': 'You are not a participant of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        # Look for conversation-specific preference, then fallback to global preference
        pref = UserChatPreference.objects.filter(user=request.user, conversation=conv).first()
        if not pref and conv:
            pref = UserChatPreference.objects.filter(user=request.user, conversation=None).first()

        if pref:
            return Response(UserChatPreferenceSerializer(pref, context={'request': request}).data)

        # Default fallback response
        return Response({
            'bg_type': 'default',
            'bg_value': '',
            'custom_bg_image': None,
            'custom_bg_image_url': None,
            'bubble_style': 'classic',
            'theme_mode': 'system',
        })

    def post(self, request, conversation_id=None):
        conv = None
        if conversation_id:
            conv = get_object_or_404(Conversation, id=conversation_id)
            if not conv.participants.filter(id=request.user.id).exists():
                return Response({'detail': 'You are not a participant of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        pref, created = UserChatPreference.objects.get_or_create(
            user=request.user,
            conversation=conv,
            defaults={
                'bg_type': 'default',
                'bg_value': '',
                'bubble_style': 'classic',
                'theme_mode': 'system'
            }
        )

        bg_type = request.data.get('bg_type')
        bg_value = request.data.get('bg_value')
        bubble_style = request.data.get('bubble_style')
        theme_mode = request.data.get('theme_mode')

        if bg_type is not None and bg_type in dict(UserChatPreference.BG_TYPE_CHOICES):
            pref.bg_type = bg_type

        if bg_value is not None:
            pref.bg_value = str(bg_value).strip()

        if bubble_style is not None and bubble_style in dict(UserChatPreference.BUBBLE_STYLE_CHOICES):
            pref.bubble_style = bubble_style

        if theme_mode is not None and theme_mode in dict(UserChatPreference.THEME_MODE_CHOICES):
            pref.theme_mode = theme_mode

        if 'custom_bg_image' in request.FILES:
            custom_img = request.FILES['custom_bg_image']
            if custom_img.size > MAX_UPLOAD_SIZE_BYTES:
                return Response(
                    {'detail': f'Custom background image exceeds max allowed limit of {MAX_UPLOAD_SIZE_MB}MB.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            _, ext = os.path.splitext(custom_img.name.lower())
            if ext not in IMAGE_EXTENSIONS:
                return Response(
                    {'detail': 'Only image files (.jpg, .jpeg, .png, .webp) are supported for custom backgrounds.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            pref.custom_bg_image = custom_img
            pref.bg_type = 'custom'

        pref.save()
        return Response(UserChatPreferenceSerializer(pref, context={'request': request}).data, status=status.HTTP_200_OK)


class ResetChatPreferenceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, conversation_id=None):
        conv = None
        if conversation_id:
            conv = get_object_or_404(Conversation, id=conversation_id)
            if not conv.participants.filter(id=request.user.id).exists():
                return Response({'detail': 'You are not a participant of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        deleted_count, _ = UserChatPreference.objects.filter(user=request.user, conversation=conv).delete()

        return Response({
            'detail': 'Chat preference reset to default.',
            'bg_type': 'default',
            'bg_value': '',
            'custom_bg_image': None,
            'custom_bg_image_url': None,
            'bubble_style': 'classic',
            'theme_mode': 'system',
        }, status=status.HTTP_200_OK)

