from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    related_post = models.ForeignKey('posts.Post', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=150, blank=True, default='')
    group_avatar = models.ImageField(upload_to='group_avatars/', null=True, blank=True)
    group_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='administered_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.is_group:
            return f"Group '{self.group_name}' (#{self.id})"
        return f"Conversation #{self.id} (updated {self.updated_at.strftime('%Y-%m-%d %H:%M')})"


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image / Photo'),
        ('video', 'Video'),
        ('file', 'Document / File'),
        ('audio', 'Voice / Audio Note'),
        ('gif', 'GIF / Sticker'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    content = models.TextField(blank=True, default='')
    
    file = models.FileField(upload_to='chat_attachments/%Y/%m/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Size in bytes')
    file_type = models.CharField(max_length=100, blank=True, default='', help_text='MIME type or category')

    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    deleted_for_users = models.ManyToManyField(User, related_name='deleted_messages', blank=True)
    is_deleted_everyone = models.BooleanField(default=False)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.message_type}] Message #{self.id} from {self.sender.email} in #{self.conversation_id}"


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction} to msg #{self.message_id}"


class UserChatPreference(models.Model):
    BG_TYPE_CHOICES = [
        ('default', 'Default Pattern'),
        ('solid', 'Solid Color'),
        ('gradient', 'Gradient'),
        ('wallpaper', 'Pattern/Wallpaper'),
        ('custom', 'Custom Photo/Image'),
    ]

    BUBBLE_STYLE_CHOICES = [
        ('classic', 'Classic'),
        ('rounded', 'Rounded'),
        ('minimal', 'Minimal'),
        ('compact', 'Compact'),
    ]

    THEME_MODE_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_preferences')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='user_customizations')

    bg_type = models.CharField(max_length=20, choices=BG_TYPE_CHOICES, default='default')
    bg_value = models.CharField(max_length=255, blank=True, default='')
    custom_bg_image = models.ImageField(upload_to='chat_backgrounds/%Y/%m/', null=True, blank=True)

    bubble_style = models.CharField(max_length=20, choices=BUBBLE_STYLE_CHOICES, default='classic')
    theme_mode = models.CharField(max_length=20, choices=THEME_MODE_CHOICES, default='system')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'conversation')

    def __str__(self):
        conv_str = f"Conv #{self.conversation_id}" if self.conversation_id else "Global"
        return f"ChatPref ({conv_str}) for {self.user.email}"

