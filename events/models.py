from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=150)
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='events', help_text='Leave blank for campus-wide events')
    organizer = models.CharField(max_length=150, help_text='Hostel Committee, Sports Club, Student Name, etc.')
    banner_image = models.ImageField(upload_to='events/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event_date', 'event_time']

    def __str__(self):
        return f"{self.title} on {self.event_date} ({self.location})"
