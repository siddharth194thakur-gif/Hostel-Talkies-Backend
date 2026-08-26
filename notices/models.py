from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Notice(models.Model):
    PRIORITY_CHOICES = [
        ('normal', 'Normal Notice'),
        ('important', 'Important Notice'),
        ('urgent', 'Urgent Announcement'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    target_hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='notices', help_text='Leave empty to target all hostels')
    target_block = models.ForeignKey('hostels.Block', on_delete=models.SET_NULL, null=True, blank=True, related_name='notices', help_text='Optional block targeting')
    publish_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to='notices/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-publish_date']

    def is_expired(self):
        if self.expiry_date and timezone.now() > self.expiry_date:
            return True
        return False

    def __str__(self):
        target = self.target_hostel.name if self.target_hostel else "All Hostels"
        return f"[{self.get_priority_display()}] {self.title} ({target})"
