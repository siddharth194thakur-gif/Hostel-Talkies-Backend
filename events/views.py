from rest_framework import viewsets, permissions
from django.db.models import Q
from django.utils import timezone
from .models import Event
from .serializers import EventSerializer
from users.permissions import IsAdminOrReadOnly

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.filter(is_active=True).order_by('event_date', 'event_time')
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Event.objects.filter(is_active=True)
        
        hostel = self.request.query_params.get('hostel')
        if hostel:
            queryset = queryset.filter(Q(hostel__isnull=True) | Q(hostel_id=hostel))

        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            queryset = queryset.filter(event_date__gte=timezone.now().date())

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search) |
                Q(organizer__icontains=search)
            )

        from django.db.models import Case, When, Value, IntegerField
        return queryset.annotate(
            is_featured_sih=Case(
                When(title__icontains='Smart India Hackathon', then=Value(0)),
                When(title__icontains='SIH', then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            )
        ).order_by('is_featured_sih', 'event_date', 'event_time')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
