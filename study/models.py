from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class StudyResource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('notes', 'Lecture Notes & Summaries'),
        ('book', 'E-Book / Reference Book'),
        ('pyq', 'Previous Year Questions (PYQ)'),
        ('pdf', 'Handout / Cheat Sheet (PDF)'),
        ('assignment', 'Assignments & Solutions'),
        ('study_group', 'Study Group / Peer Learning'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPE_CHOICES, default='notes')
    course_name = models.CharField(max_length=150, help_text='e.g. Data Structures, Thermodynamics')
    course_code = models.CharField(max_length=50, blank=True, default='', help_text='e.g. CS201, ME302')
    semester = models.CharField(max_length=20, blank=True, default='', help_text='e.g. Sem 1, Sem 2, etc.')
    department = models.CharField(max_length=100, blank=True, default='', help_text='e.g. Computer Science, Mechanical')
    
    file = models.FileField(upload_to='study_resources/', null=True, blank=True)
    external_link = models.URLField(blank=True, default='')
    
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_study_resources')
    downloads_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_resource_type_display()}] {self.title} ({self.course_name})"
