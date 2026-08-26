from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import StudentProfile, UserBlock
from hostels.models import Hostel, Block, Room
from hostels.serializers import HostelSerializer, BlockSerializer, RoomSerializer

User = get_user_model()

class StudentProfileSerializer(serializers.ModelSerializer):
    hostel_detail = HostelSerializer(source='hostel', read_only=True)
    block_detail = BlockSerializer(source='block', read_only=True)
    room_detail = RoomSerializer(source='room', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'hostel', 'hostel_detail', 'block', 'block_detail',
            'room', 'room_detail', 'gender', 'programme', 'branch',
            'bio', 'phone_number', 'avatar',
            'created_at', 'updated_at'
        ]

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.avatar.url)
        return obj.avatar.url


class UserSerializer(serializers.ModelSerializer):
    profile = StudentProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'is_student', 'is_hostel_admin', 'is_staff', 'is_superuser',
            'is_blocked', 'is_suspended', 'suspended_until', 'block_reason',
            'profile', 'date_joined'
        ]
        read_only_fields = [
            'id', 'is_hostel_admin', 'is_staff', 'is_superuser',
            'is_blocked', 'is_suspended', 'suspended_until', 'block_reason',
            'date_joined'
        ]

    def get_full_name(self, obj):
        full_name = (obj.get_full_name() or '').strip()
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            if not full_name or full_name.lower() in ['chief warden', 'chief administrator', 'warden', 'administrator']:
                return "Admin"
            return full_name
        return full_name or obj.username



class UserPublicSerializer(serializers.ModelSerializer):
    """Safe public serializer that protects sensitive info."""
    profile = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    hostel_name = serializers.SerializerMethodField()
    is_blocked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'role', 'role_display',
            'hostel_name', 'profile_picture', 'is_student', 'is_staff', 'is_superuser',
            'is_blocked_by_me', 'profile', 'date_joined'
        ]

    def get_is_blocked_by_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserBlock.objects.filter(blocker=request.user, blocked=obj).exists()
        return False

    def get_full_name(self, obj):
        full_name = (obj.get_full_name() or '').strip()
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            if not full_name or full_name.lower() in ['chief warden', 'chief administrator', 'warden', 'administrator']:
                return "Admin"
            return full_name
        return full_name or obj.username

    def get_role(self, obj):
        if obj.is_superuser or obj.is_staff or getattr(obj, 'is_hostel_admin', False):
            return "Admin"
        if getattr(obj, 'is_student', False):
            return "Student"
        return "Hostel Resident"

    def get_role_display(self, obj):
        return self.get_role(obj)

    def get_hostel_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.hostel:
            return obj.profile.hostel.name
        return None

    def get_profile_picture(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.avatar.url)
            return obj.profile.avatar.url
        return None

    def get_profile(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            p = obj.profile
            avatar_url = None
            if p.avatar:
                request = self.context.get('request')
                avatar_url = request.build_absolute_uri(p.avatar.url) if request else p.avatar.url
            return {
                'id': p.id,
                'avatar': avatar_url,
                'bio': p.bio,
                'gender': p.gender,
                'programme': p.programme,
                'branch': p.branch,
                'hostel_name': p.hostel.name if p.hostel else None,
                'hostel_id': p.hostel_id,
                'block_name': p.block.name if p.block else None,
                'block_id': p.block_id,
                'room_number': p.room.room_number if p.room else None,
                'room_id': p.room_id,
            }
        return None


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    gender = serializers.ChoiceField(choices=StudentProfile.GENDER_CHOICES, required=False, allow_blank=True, default='')
    programme = serializers.CharField(max_length=50, required=True)
    branch = serializers.CharField(max_length=100, required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, required=True)
    hostel = serializers.PrimaryKeyRelatedField(queryset=Hostel.objects.all(), required=True)
    block = serializers.PrimaryKeyRelatedField(queryset=Block.objects.all(), required=False, allow_null=True)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs['password'])

        hostel = attrs.get('hostel')
        block = attrs.get('block')
        room = attrs.get('room')

        if block and block.hostel != hostel:
            raise serializers.ValidationError({'block': f"The selected block '{block.name}' does not belong to {hostel.name}."})

        if room and block and room.block != block:
            raise serializers.ValidationError({'room': f"The selected room '{room.room_number}' does not belong to {block.name}."})

        if room and not block:
            raise serializers.ValidationError({'room': "You must select a block before selecting a room."})

        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        username = email.split('@')[0]
        # Guarantee unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        full_name = validated_data['full_name'].strip()
        names = full_name.split(' ', 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            is_student=True,
            is_active=True
        )

        hostel = validated_data.get('hostel')
        block = validated_data.get('block')
        room = validated_data.get('room')
        gender = validated_data.get('gender', '')
        programme = validated_data.get('programme', '')
        branch = validated_data.get('branch', '')

        StudentProfile.objects.create(
            user=user,
            hostel=hostel,
            block=block,
            room=room,
            gender=gender,
            programme=programme,
            branch=branch
        )
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    remove_avatar = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = StudentProfile
        fields = [
            'first_name', 'last_name', 'gender', 'programme', 'branch',
            'bio', 'phone_number', 'avatar', 'hostel', 'block', 'room',
            'remove_avatar'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
        instance.user.save()

        remove_avatar = validated_data.pop('remove_avatar', False)
        if remove_avatar:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = None

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
