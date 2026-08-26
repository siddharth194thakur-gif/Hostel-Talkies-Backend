from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F
from .models import StudyResource
from .serializers import StudyResourceSerializer
from users.permissions import IsChiefAdminOrReadOnly

class StudyResourceViewSet(viewsets.ModelViewSet):
    queryset = StudyResource.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = StudyResourceSerializer
    permission_classes = [IsChiefAdminOrReadOnly]

    def get_queryset(self):
        queryset = StudyResource.objects.filter(is_active=True)
        
        resource_type = self.request.query_params.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)

        semester = self.request.query_params.get('semester')
        if semester:
            queryset = queryset.filter(semester__icontains=semester)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(course_name__icontains=search) |
                Q(course_code__icontains=search)
            )

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def track_download(self, request, pk=None):
        resource = self.get_object()
        StudyResource.objects.filter(id=resource.id).update(downloads_count=F('downloads_count') + 1)
        resource.refresh_from_db(fields=['downloads_count'])
        return Response({'downloads_count': resource.downloads_count})
