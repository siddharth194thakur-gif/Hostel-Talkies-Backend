from rest_framework import viewsets, permissions, generics
from rest_framework.response import Response
from .models import Hostel, Block, Room
from .serializers import HostelSerializer, HostelDetailSerializer, BlockSerializer, RoomSerializer
from users.permissions import IsAdminOrReadOnly

class HostelViewSet(viewsets.ModelViewSet):
    queryset = Hostel.objects.filter(is_active=True).order_by('name')
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HostelDetailSerializer
        return HostelSerializer

    def get_queryset(self):
        # Admins can see inactive hostels too
        if self.request.user.is_authenticated and (self.request.user.is_staff or getattr(self.request.user, 'is_hostel_admin', False)):
            return Hostel.objects.all().order_by('name')
        return Hostel.objects.filter(is_active=True).order_by('name')


class BlockViewSet(viewsets.ModelViewSet):
    queryset = Block.objects.filter(is_active=True).order_by('name')
    serializer_class = BlockSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Block.objects.filter(is_active=True)
        hostel_id = self.request.query_params.get('hostel')
        if hostel_id:
            queryset = queryset.filter(hostel_id=hostel_id)
        return queryset.order_by('name')


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.filter(is_active=True).order_by('room_number')
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Room.objects.filter(is_active=True)
        block_id = self.request.query_params.get('block')
        if block_id:
            queryset = queryset.filter(block_id=block_id)
        return queryset.order_by('room_number')


class HostelBlocksView(generics.ListAPIView):
    """Returns blocks belonging to a specific hostel for dynamic registration."""
    serializer_class = BlockSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        hostel_id = self.kwargs['hostel_id']
        return Block.objects.filter(hostel_id=hostel_id, is_active=True).order_by('name')


class BlockRoomsView(generics.ListAPIView):
    """Returns rooms belonging to a specific block for dynamic registration."""
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        block_id = self.kwargs['block_id']
        return Room.objects.filter(block_id=block_id, is_active=True).order_by('room_number')
