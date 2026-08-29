from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FetchFreeFireStatsAPIView,
    MyGamingProfileView,
    SyncStatsAPIView,
    GamingLeaderboardView,
    TournamentViewSet,
)

router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='tournaments')

urlpatterns = [
    path('lookup/', FetchFreeFireStatsAPIView.as_view(), name='gaming-lookup'),
    path('my-profile/', MyGamingProfileView.as_view(), name='gaming-my-profile'),
    path('sync/', SyncStatsAPIView.as_view(), name='gaming-sync'),
    path('leaderboard/', GamingLeaderboardView.as_view(), name='gaming-leaderboard'),
    path('', include(router.urls)),
]
