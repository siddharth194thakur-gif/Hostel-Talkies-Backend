from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet, StartConversationView, SendMessageView, UnreadMessageCountView,
    CreateGroupView, GroupDetailActionView, AddGroupMembersView, RemoveGroupMemberView,
    LeaveGroupView, AvailableMembersView, MessageReactionView, DeleteMessageView, DownloadAttachmentView,
    ChatPreferenceView, ResetChatPreferenceView
)

router = DefaultRouter()
router.register(r'', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('preferences/', ChatPreferenceView.as_view(), name='global-chat-preference'),
    path('preferences/reset/', ResetChatPreferenceView.as_view(), name='global-reset-chat-preference'),
    path('<int:conversation_id>/preferences/', ChatPreferenceView.as_view(), name='conversation-chat-preference'),
    path('<int:conversation_id>/preferences/reset/', ResetChatPreferenceView.as_view(), name='conversation-reset-chat-preference'),
    path('start/', StartConversationView.as_view(), name='start-conversation'),
    path('unread-count/', UnreadMessageCountView.as_view(), name='unread-message-count'),
    path('available-members/', AvailableMembersView.as_view(), name='available-members'),
    path('groups/create/', CreateGroupView.as_view(), name='create-group'),
    path('groups/<int:group_id>/', GroupDetailActionView.as_view(), name='group-detail-action'),
    path('groups/<int:group_id>/add-members/', AddGroupMembersView.as_view(), name='add-group-members'),
    path('groups/<int:group_id>/remove-member/', RemoveGroupMemberView.as_view(), name='remove-group-member'),
    path('groups/<int:group_id>/leave/', LeaveGroupView.as_view(), name='leave-group'),
    path('<int:conversation_id>/send/', SendMessageView.as_view(), name='send-message'),
    path('messages/<int:message_id>/react/', MessageReactionView.as_view(), name='message-react'),
    path('messages/<int:message_id>/delete/', DeleteMessageView.as_view(), name='delete-message'),
    path('messages/<int:message_id>/attachment/', DownloadAttachmentView.as_view(), name='download-attachment'),
    path('', include(router.urls)),
]
