from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from .models import Report, Feedback, AdminActionLog, SiteSetting
from .serializers import ReportSerializer, FeedbackSerializer, AdminActionLogSerializer, SiteSettingSerializer
from users.permissions import IsNotBlockedOrSuspended, IsAdminOrReadOnly

class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class FeedbackCreateView(generics.CreateAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(
                user=self.request.user,
                name=self.request.user.get_full_name() or self.request.user.username,
                email=self.request.user.email
            )
        else:
            serializer.save()


class SiteSettingView(generics.RetrieveAPIView):
    serializer_class = SiteSettingSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        setting, _ = SiteSetting.objects.get_or_create(id=1)
        return setting


class AdminReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-created_at')
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminFeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all().order_by('-created_at')
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminActionLog.objects.all().order_by('-timestamp')
    serializer_class = AdminActionLogSerializer
    permission_classes = [permissions.IsAdminUser]
