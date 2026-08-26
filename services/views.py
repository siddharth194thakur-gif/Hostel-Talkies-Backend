from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import HostelService
from .serializers import HostelServiceSerializer
from users.permissions import IsAdminOrReadOnly

class HostelServiceViewSet(viewsets.ModelViewSet):
    queryset = HostelService.objects.filter(is_active=True).order_by('category', 'name')
    serializer_class = HostelServiceSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = HostelService.objects.filter(is_active=True)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        hostel = self.request.query_params.get('hostel')
        if hostel:
            queryset = queryset.filter(Q(hostel__isnull=True) | Q(hostel_id=hostel))

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search) |
                Q(contact_person__icontains=search)
            )

        return queryset.order_by('category', 'name')
