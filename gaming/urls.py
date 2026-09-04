from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompetitionViewSet

router = DefaultRouter()
router.register(r'competitions', CompetitionViewSet, basename='competition')
# Also keep alias 'rooms' for backwards compatibility
router.register(r'rooms', CompetitionViewSet, basename='competition-rooms')

urlpatterns = [
    path('', include(router.urls)),
]
