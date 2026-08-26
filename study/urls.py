from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudyResourceViewSet

router = DefaultRouter()
router.register(r'', StudyResourceViewSet, basename='study-resource')

urlpatterns = [
    path('', include(router.urls)),
]
