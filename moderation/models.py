from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('post', 'Post / Listing'),
        ('user', 'User Account'),
        ('comment', 'Comment'),
    ]

    REASON_CHOICES = [
        ('spam', 'Spam or Commercial promotion'),
        ('fake_listing', 'Fake or Misleading listing'),
        ('scam', 'Scam or Fraudulent attempt'),
        ('harassment', 'Harassment or Inappropriate behavior'),
        ('inappropriate_content', 'Inappropriate or Offensive content'),
        ('other', 'Other Reason'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewing', 'In Review'),
        ('resolved', 'Resolved / Action Taken'),
        ('dismissed', 'Dismissed / No Violation'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_filed')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    target_id = models.CharField(max_length=100)
    reason = models.CharField(max_length=40, choices=REASON_CHOICES)
    details = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report #{self.id} on {self.report_type}:{self.target_id} by {self.reporter.email}"


class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Reviewing'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    name = models.CharField(max_length=150, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback: {self.subject} ({self.status})"


class AdminActionLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_actions')
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.admin}: {self.action} on {self.target_type}"


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default='HostelTalkies')
    tagline = models.CharField(max_length=255, default='Your Hostel. Your People. Your Talkies.')
    community_rules = models.TextField(blank=True, default='1. Be respectful\n2. Genuine student listings only\n3. Protect hostel property and privacy.')
    guidelines = models.TextField(blank=True, default='Guidelines for posting, trading, and community conduct.')
    contact_email = models.EmailField(default='support@hosteltalkies.com')
    maintenance_mode = models.BooleanField(default=False)

    def __str__(self):
        return self.site_name
