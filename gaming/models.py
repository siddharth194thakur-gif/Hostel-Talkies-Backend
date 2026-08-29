from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class GamingProfile(models.Model):
    GAME_CHOICES = (
        ('free_fire', 'Free Fire MAX / Free Fire'),
        ('bgmi', 'BGMI / PUBG Mobile'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gaming_profiles')
    game_type = models.CharField(max_length=20, choices=GAME_CHOICES, default='free_fire')
    uid = models.CharField(max_length=32, db_index=True)
    in_game_name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(default=1)
    likes = models.PositiveIntegerField(default=0)
    br_rank = models.CharField(max_length=50, default='Platinum')
    br_rank_points = models.PositiveIntegerField(default=1000)
    cs_rank = models.CharField(max_length=50, default='Gold')
    kd_ratio = models.FloatField(default=1.0)
    total_booyahs = models.PositiveIntegerField(default=0)
    headshot_rate = models.FloatField(default=0.0)
    score = models.IntegerField(default=0, db_index=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=20, default='IND')
    proof_screenshot = models.ImageField(upload_to='gaming_proofs/', blank=True, null=True)
    is_verified = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']
        unique_together = ('user', 'game_type')

    def calculate_score(self):
        # Base rank points
        pts = self.br_rank_points or 1000
        # Level multiplier
        level_pts = (self.level or 1) * 50
        # Likes bonus
        likes_pts = (self.likes or 0) * 2
        # Booyahs bonus
        booyah_pts = (self.total_booyahs or 0) * 30
        # KD bonus
        kd_pts = int((self.kd_ratio or 1.0) * 100)
        
        self.score = pts + level_pts + likes_pts + booyah_pts + kd_pts
        return self.score

    def save(self, *args, **kwargs):
        self.calculate_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.in_game_name} ({self.uid}) - Score: {self.score}"


class Tournament(models.Model):
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming Match'),
        ('live', 'Match Live Now 🔥'),
        ('completed', 'Completed'),
    )

    MATCH_TYPE_CHOICES = (
        ('squad_br', 'Full Map Battle Royale (Squad)'),
        ('clash_squad', 'Clash Squad (4v4 CS)'),
        ('solo_br', 'Solo Full Map BR'),
        ('duo_br', 'Duo Full Map BR'),
    )

    title = models.CharField(max_length=150)
    game_type = models.CharField(max_length=20, default='free_fire')
    match_type = models.CharField(max_length=30, choices=MATCH_TYPE_CHOICES, default='clash_squad')
    banner = models.ImageField(upload_to='tournaments/', blank=True, null=True)
    description = models.TextField(blank=True)
    room_id = models.CharField(max_length=50, blank=True, help_text="Custom Room ID (Revealed to participants)")
    room_password = models.CharField(max_length=50, blank=True, help_text="Room Password")
    start_time = models.DateTimeField()
    prize_pool = models.CharField(max_length=100, default='Campus Glory & Winner Badge 🏆')
    entry_fee = models.CharField(max_length=50, default='FREE')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    max_teams = models.PositiveIntegerField(default=12)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tournaments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
