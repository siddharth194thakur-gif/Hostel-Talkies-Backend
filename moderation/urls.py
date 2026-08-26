from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReportCreateView, FeedbackCreateView, SiteSettingView,
    AdminReportViewSet, AdminFeedbackViewSet, AdminActionLogViewSet
)

router = DefaultRouter()
router.register(r'reports', AdminReportViewSet, basename='admin-report')
router.register(r'feedback', AdminFeedbackViewSet, basename='admin-feedback')
router.register(r'action-logs', AdminActionLogViewSet, basename='admin-action-log')

urlpatterns = [
    path('report/', ReportCreateView.as_view(), name='report-create'),
    path('feedback/', FeedbackCreateView.as_view(), name='feedback-create'),
    path('settings/', SiteSettingView.as_view(), name='site-settings'),
    path('admin/', include(router.urls)),
]
