from django.db import models

class HostelService(models.Model):
    SERVICE_CATEGORIES = [
        ('laundry', 'Laundry & Ironing'),
        ('printing', 'Printing & Photocopy'),
        ('repair', 'Repairs & Electrician'),
        ('barber', 'Barber & Grooming'),
        ('tailor', 'Tailoring'),
        ('cleaning', 'Cleaning & Housekeeping'),
        ('canteen', 'Canteen & Mess'),
        ('other', 'Other Essential Service'),
    ]

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=40, choices=SERVICE_CATEGORIES, default='other')
    description = models.TextField(blank=True, default='')
    contact_person = models.CharField(max_length=100, blank=True, default='')
    phone_number = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=150, help_text='e.g. Ground floor Block B, Near Main Gate')
    timings = models.CharField(max_length=150, help_text='e.g. 9:00 AM - 8:00 PM (Daily)')
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
