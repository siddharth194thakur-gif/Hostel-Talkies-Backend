from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_student = models.BooleanField(default=True)
    is_hostel_admin = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspended_until = models.DateTimeField(null=True, blank=True)
    block_reason = models.TextField(blank=True, default='')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def is_currently_suspended(self):
        if self.is_suspended:
            if self.suspended_until and timezone.now() > self.suspended_until:
                self.is_suspended = False
                self.suspended_until = None
                self.save(update_fields=['is_suspended', 'suspended_until'])
                return False
            return True
        return False

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.email})"


class StudentProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    block = models.ForeignKey('hostels.Block', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    room = models.ForeignKey('hostels.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, default='')
    programme = models.CharField(max_length=50, blank=True, default='', help_text='Course / Programme e.g. B.Tech, BCA, MCA')
    branch = models.CharField(max_length=100, blank=True, default='', help_text='Branch / Specialisation')
    bio = models.TextField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class Student(User):
    class Meta:
        proxy = True
        verbose_name = 'Student'
        verbose_name_plural = 'Students'


class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_relations')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_relations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.blocker.email} blocked {self.blocked.email}"




