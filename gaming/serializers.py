from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import GamingProfile, Tournament

User = get_user_model()

class GamingUserMetaSerializer(serializers.ModelSerializer):
    hostel_name = serializers.SerializerMethodField()
    room_info = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'hostel_name', 'room_info']

    def get_hostel_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.hostel:
            return obj.profile.hostel.name
        return 'Campus Resident'

    def get_room_info(self, obj):
        if hasattr(obj, 'profile'):
            block = obj.profile.block.name if obj.profile.block else ''
            room = obj.profile.room.room_number if obj.profile.room else ''
            if block and room:
                return f"Block {block} • Rm {room}"
            elif room:
                return f"Rm {room}"
        return ''

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.avatar.url)
            return obj.profile.avatar.url
        return None


class GamingProfileSerializer(serializers.ModelSerializer):
    user_details = GamingUserMetaSerializer(source='user', read_only=True)
    rank_position = serializers.SerializerMethodField()

    class Meta:
        model = GamingProfile
        fields = [
            'id',
            'user',
            'user_details',
            'game_type',
            'uid',
            'in_game_name',
            'level',
            'likes',
            'br_rank',
            'br_rank_points',
            'cs_rank',
            'kd_ratio',
            'total_booyahs',
            'headshot_rate',
            'score',
            'avatar_url',
            'region',
            'proof_screenshot',
            'is_verified',
            'rank_position',
            'last_synced_at',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'score', 'created_at', 'last_synced_at']

    def get_rank_position(self, obj):
        # Calculate live rank position among same game type
        higher_scores = GamingProfile.objects.filter(
            game_type=obj.game_type,
            score__gt=obj.score
        ).count()
        return higher_scores + 1


class TournamentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Tournament
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_at']
