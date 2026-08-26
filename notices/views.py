from rest_framework import viewsets, permissions
from django.db.models import Q
from django.utils import timezone
from .models import Notice
from .serializers import NoticeSerializer
from users.permissions import IsAdminOrReadOnly

class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        now = timezone.now()
        queryset = Notice.objects.filter(is_active=True, publish_date__lte=now)
        
        # Non-staff users only see non-expired notices
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gt=now))
            
            # If user is a student, filter notices targeted to all or their specific hostel
            if self.request.user.is_authenticated and hasattr(self.request.user, 'profile') and self.request.user.profile.hostel:
                user_hostel = self.request.user.profile.hostel
                queryset = queryset.filter(Q(target_hostel__isnull=True) | Q(target_hostel=user_hostel))

        # Query parameter filters
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        hostel_id = self.request.query_params.get('hostel')
        if hostel_id:
            queryset = queryset.filter(Q(target_hostel__isnull=True) | Q(target_hostel_id=hostel_id))

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return queryset.order_by('-priority', '-publish_date')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
