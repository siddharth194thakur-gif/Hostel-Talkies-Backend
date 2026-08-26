from django.db import models

class Hostel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    gender = models.CharField(max_length=20, choices=[('boys', 'Boys'), ('girls', 'Girls'), ('coed', 'Co-Ed')], default='coed')
    warden_name = models.CharField(max_length=100, blank=True, default='')
    warden_contact = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.replace(" ", "-").upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Block(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='blocks')
    name = models.CharField(max_length=50)
    floors = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hostel', 'name')

    def __str__(self):
        return f"{self.hostel.name} - {self.name}"


class Room(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=20)
    floor = models.IntegerField(default=1)
    capacity = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('block', 'room_number')

    def __str__(self):
        return f"{self.block.hostel.name} - {self.block.name} - Room {self.room_number}"
