from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HostelServiceViewSet

router = DefaultRouter()
router.register(r'', HostelServiceViewSet, basename='service')

urlpatterns = [
    path('', include(router.urls)),
]
