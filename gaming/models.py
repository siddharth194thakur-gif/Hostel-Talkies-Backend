from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Competition(models.Model):
    GAME_CHOICES = [
        ('bgmi', 'BGMI'),
        ('bgmi_lite', 'BGMI Lite'),
        ('free_fire_max', 'Free Fire MAX'),
        ('other', 'Other Game'),
    ]

    COMPETITION_TYPE_CHOICES = [
        ('solo', 'Solo'),
        ('duo', 'Duo'),
        ('squad', 'Squad'),
        ('1v1', '1v1 Match'),
        ('team', 'Team vs Team'),
        ('custom', 'Custom Format'),
    ]

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('registration_open', 'Registration Open'),
        ('live', 'Live / In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    SCORING_TYPE_CHOICES = [
        ('manual', 'Manual Organizer Entry'),
        ('participant_submission', 'Participant Submission + Organizer Verification'),
        ('points_based', 'Points-Based (Kills + Placement)'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_competitions')
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='gaming_competitions')
    
    name = models.CharField(max_length=200, help_text="e.g. HostelTalkies BGMI Championship, Free Fire MAX Weekend Clash")
    game = models.CharField(max_length=50, choices=GAME_CHOICES, default='bgmi')
    custom_game_name = models.CharField(max_length=100, blank=True, default='', help_text="Game name if 'Other' is selected")
    
    description = models.TextField(blank=True, default='', help_text="Overview and details of the competition")
    rules = models.TextField(blank=True, default='', help_text="Competition rules, device restrictions, screenshot proof requirements")
    
    competition_type = models.CharField(max_length=30, choices=COMPETITION_TYPE_CHOICES, default='squad')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='registration_open')
    
    start_datetime = models.DateTimeField(help_text="Match / Tournament start date and time")
    end_datetime = models.DateTimeField(null=True, blank=True, help_text="Expected end date and time")
    registration_deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline to join")
    
    max_participants = models.PositiveIntegerField(default=50, help_text="Maximum players/slots allowed")
    is_registration_closed_by_organizer = models.BooleanField(default=False)
    
    # In-game Room credentials (optional, updated dynamically by host)
    room_id = models.CharField(max_length=100, blank=True, default='', help_text="In-game Custom Room ID")
    room_password = models.CharField(max_length=100, blank=True, default='', help_text="In-game Room Password")
    
    # Scoring & Rewards
    scoring_type = models.CharField(max_length=30, choices=SCORING_TYPE_CHOICES, default='participant_submission')
    scoring_rules = models.JSONField(blank=True, default=dict, help_text="Custom points configuration e.g. points per kill and placement points")
    prize_pool = models.CharField(max_length=200, blank=True, default='', help_text="Prizes, trophies or bragging rights")
    contact_info = models.CharField(max_length=200, blank=True, default='', help_text="Host WhatsApp group / Room number / Discord")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.game_display}) by {self.creator.email}"

    @property
    def game_display(self):
        if self.game == 'other' and self.custom_game_name:
            return self.custom_game_name
        return dict(self.GAME_CHOICES).get(self.game, self.game)

    @property
    def participants_count(self):
        return self.participants.filter(status='registered').count()

    @property
    def is_registration_open(self):
        if self.is_registration_closed_by_organizer:
            return False
        if self.status not in ['upcoming', 'registration_open']:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        if self.participants_count >= self.max_participants:
            return False
        return True


class CompetitionParticipant(models.Model):
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('confirmed', 'Confirmed'),
        ('disqualified', 'Disqualified'),
    ]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='joined_competitions')
    
    in_game_name = models.CharField(max_length=100, help_text="Player's in-game nickname/IGN")
    game_uid = models.CharField(max_length=100, blank=True, default='', help_text="Informational player UID (no API fetch)")
    team_name = models.CharField(max_length=150, blank=True, default='', help_text="Team or Clan name if applicable")
    team_members = models.TextField(blank=True, default='', help_text="Teammates / roster details")
    contact_number = models.CharField(max_length=50, blank=True, default='')
    
    slot_number = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('competition', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.in_game_name} ({self.user.email}) in {self.competition.name}"


class CompetitionResult(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='results')
    participant = models.ForeignKey(CompetitionParticipant, on_delete=models.CASCADE, related_name='results')
    
    position = models.PositiveIntegerField(null=True, blank=True, help_text="Final placement rank e.g. 1, 2, 3")
    kills = models.PositiveIntegerField(default=0, help_text="Number of kills")
    points = models.FloatField(default=0.0, help_text="Calculated or assigned points")
    score = models.CharField(max_length=100, blank=True, default='', help_text="Match score or outcome e.g. 'Won 16-10', 'Booyah'")
    
    proof_image = models.ImageField(upload_to='gaming/proofs/', null=True, blank=True, help_text="Screenshot proof of match result")
    notes = models.TextField(blank=True, default='', help_text="Submission notes or comments")
    
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_results')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-points', 'position', '-kills', '-submitted_at']

    def __str__(self):
        return f"Result #{self.id} for {self.participant.in_game_name} in {self.competition.name} ({self.verification_status})"
