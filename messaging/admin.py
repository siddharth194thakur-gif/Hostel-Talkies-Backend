from django.contrib import admin
from .models import Conversation, Message, MessageReaction

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'message_type', 'content', 'file', 'is_read', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_group', 'group_name', 'group_admin', 'get_participants', 'related_post', 'updated_at', 'created_at')
    list_filter = ('is_group', 'created_at')
    search_fields = ('group_name', 'participants__email', 'group_admin__email')
    inlines = [MessageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants').select_related('related_post', 'group_admin')

    def get_participants(self, obj):
        return ", ".join([u.email for u in obj.participants.all()[:5]])
    get_participants.short_description = "Participants"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'message_type', 'content_preview', 'has_file', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('content', 'file_name', 'sender__email')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('conversation', 'sender')

    def content_preview(self, obj):
        return obj.content[:50] if obj.content else f"[{obj.message_type.upper()}]"
    content_preview.short_description = "Content"

    def has_file(self, obj):
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = "Attachment"


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at')
    search_fields = ('user__email', 'reaction')
