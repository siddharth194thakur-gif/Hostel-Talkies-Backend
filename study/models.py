from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class StudyResource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('notes',               'Lecture Notes & Summaries'),
        ('pyq',                 'Previous Year Questions (PYQ)'),
        ('important_questions', 'Important Questions'),
        ('study_material',      'Study Material'),
        ('syllabus',            'Syllabus & Curriculum'),
        ('lab_file',            'Lab Manuals & Practical Files'),
        ('reference_material',  'Reference Material / E-Book'),
        ('pdf',                 'Handout / Cheat Sheet (PDF)'),
        ('assignment',          'Assignments & Solutions'),
        ('other',               'Other Academic Resource'),
    ]

    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True, default='')
    resource_type = models.CharField(
        max_length=30, choices=RESOURCE_TYPE_CHOICES, default='notes'
    )

    # Academic metadata — the single source of truth for categorisation
    course_name  = models.CharField(max_length=150, help_text='e.g. Data Structures, Thermodynamics')
    course_code  = models.CharField(max_length=50, blank=True, default='', help_text='e.g. CS201, ME302')
    semester     = models.CharField(max_length=20, blank=True, default='', help_text='e.g. Sem 1, Sem 3')
    department   = models.CharField(max_length=100, blank=True, default='', help_text='e.g. Computer Science (CSE)')
    unit         = models.CharField(max_length=50, blank=True, default='', help_text='e.g. Unit 1, Unit 2, All Units')

    # Content
    file          = models.FileField(upload_to='study_resources/', null=True, blank=True)
    external_link = models.URLField(blank=True, default='', max_length=500)

    # Source attribution — admin-only, never exposed to students
    source_website = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Internal: e.g. VBSPU PYQ Hub / VbspuEDU'
    )
    source_url = models.URLField(blank=True, default='', max_length=500,
        help_text='Internal: original source page URL'
    )
    author     = models.CharField(max_length=150, blank=True, default='',
        help_text='Faculty or Contributor Name'
    )

    # Review / quality control
    needs_review    = models.BooleanField(default=False,
        help_text='Flagged when automatic classification is uncertain. Admin should verify.'
    )
    is_pending_review = models.BooleanField(default=False,
        help_text='Held from public view pending admin approval.'
    )

    uploader       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_study_resources')
    downloads_count = models.PositiveIntegerField(default=0)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['semester', 'department', 'course_name']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['is_active', 'needs_review']),
        ]

    def __str__(self):
        return f"[{self.get_resource_type_display()}] {self.title} ({self.course_name})"
