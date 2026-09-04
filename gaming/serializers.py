from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Competition, CompetitionParticipant, CompetitionResult
from users.serializers import UserPublicSerializer
from hostels.serializers import HostelSerializer

User = get_user_model()

class CompetitionResultSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source='participant.in_game_name', read_only=True)
    participant_user_detail = UserPublicSerializer(source='participant.user', read_only=True)
    verified_by_detail = UserPublicSerializer(source='verified_by', read_only=True)

    class Meta:
        model = CompetitionResult
        fields = [
            'id',
            'competition',
            'participant',
            'participant_name',
            'participant_user_detail',
            'position',
            'kills',
            'points',
            'score',
            'proof_image',
            'notes',
            'verification_status',
            'verified_by',
            'verified_by_detail',
            'verified_at',
            'submitted_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'verified_by', 'verified_at', 'submitted_at', 'updated_at']


class CompetitionParticipantSerializer(serializers.ModelSerializer):
    user_detail = UserPublicSerializer(source='user', read_only=True)
    results = CompetitionResultSerializer(many=True, read_only=True)

    class Meta:
        model = CompetitionParticipant
        fields = [
            'id',
            'competition',
            'user',
            'user_detail',
            'in_game_name',
            'game_uid',
            'team_name',
            'team_members',
            'contact_number',
            'slot_number',
            'status',
            'joined_at',
            'results',
        ]
        read_only_fields = ['id', 'user', 'joined_at']


class CompetitionSerializer(serializers.ModelSerializer):
    creator_detail = UserPublicSerializer(source='creator', read_only=True)
    hostel_detail = HostelSerializer(source='hostel', read_only=True)
    hostel_name = serializers.CharField(source='hostel.name', read_only=True, default=None)
    game_display = serializers.CharField(read_only=True)
    participants_count = serializers.IntegerField(read_only=True)
    is_registration_open = serializers.BooleanField(read_only=True)
    is_creator = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    my_participant_info = serializers.SerializerMethodField()
    leaderboard = serializers.SerializerMethodField()
    participants = CompetitionParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Competition
        fields = [
            'id',
            'creator',
            'creator_detail',
            'hostel',
            'hostel_name',
            'hostel_detail',
            'name',
            'game',
            'custom_game_name',
            'game_display',
            'description',
            'rules',
            'competition_type',
            'status',
            'start_datetime',
            'end_datetime',
            'registration_deadline',
            'max_participants',
            'is_registration_closed_by_organizer',
            'is_registration_open',
            'room_id',
            'room_password',
            'scoring_type',
            'scoring_rules',
            'prize_pool',
            'contact_info',
            'is_active',
            'participants_count',
            'is_creator',
            'is_joined',
            'my_participant_info',
            'leaderboard',
            'participants',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def get_is_creator(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.creator_id == request.user.id or request.user.is_staff or getattr(request.user, 'is_superuser', False)
        return False

    def get_is_joined(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.participants.filter(user=request.user, status='registered').exists()
        return False

    def get_my_participant_info(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            participant = obj.participants.filter(user=request.user).first()
            if participant:
                return CompetitionParticipantSerializer(participant, context=self.context).data
        return None

    def get_leaderboard(self, obj):
        # Only return approved results sorted by points desc, position asc, kills desc
        approved_results = obj.results.filter(verification_status='approved').select_related(
            'participant', 'participant__user', 'participant__user__profile'
        ).order_by('-points', 'position', '-kills', '-submitted_at')
        return CompetitionResultSerializer(approved_results, many=True, context=self.context).data
