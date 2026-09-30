from rest_framework import serializers
from .models import Hostel, Block, Room

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'block', 'room_number', 'floor', 'capacity', 'is_active']


class BlockSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source='hostel.name')
    rooms_count = serializers.IntegerField(source='rooms.count', read_only=True)

    class Meta:
        model = Block
        fields = ['id', 'hostel', 'hostel_name', 'name', 'floors', 'is_active', 'rooms_count']


class HostelSerializer(serializers.ModelSerializer):
    blocks_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Hostel
        fields = [
            'id', 'name', 'code', 'description', 'gender',
            'warden_name', 'warden_contact', 'is_active',
            'blocks_count', 'students_count', 'created_at'
        ]

    def get_blocks_count(self, obj):
        try:
            val = getattr(obj, 'blocks_count', None)
            return val if val is not None else obj.blocks.filter(is_active=True).count()
        except Exception:
            return 0

    def get_students_count(self, obj):
        try:
            val = getattr(obj, 'students_count', None)
            return val if val is not None else obj.students.count()
        except Exception:
            return 0


class HostelDetailSerializer(serializers.ModelSerializer):
    blocks = BlockSerializer(many=True, read_only=True)
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Hostel
        fields = [
            'id', 'name', 'code', 'description', 'gender',
            'warden_name', 'warden_contact', 'is_active',
            'blocks', 'students_count', 'created_at'
        ]

    def get_students_count(self, obj):
        try:
            val = getattr(obj, 'students_count', None)
            return val if val is not None else obj.students.count()
        except Exception:
            return 0
