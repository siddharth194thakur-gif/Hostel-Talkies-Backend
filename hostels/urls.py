from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import HostelViewSet, BlockViewSet, RoomViewSet, HostelBlocksView, BlockRoomsView

router = DefaultRouter()
router.register(r'', HostelViewSet, basename='hostel')
router.register(r'blocks', BlockViewSet, basename='block')
router.register(r'rooms', RoomViewSet, basename='room')

urlpatterns = [
    path('<int:hostel_id>/blocks/', HostelBlocksView.as_view(), name='hostel-blocks'),
    re_path(r'^(?P<hostel_id>\d+)/blocks/?$', HostelBlocksView.as_view(), name='hostel-blocks-slash'),
    path('blocks/<int:block_id>/rooms/', BlockRoomsView.as_view(), name='block-rooms'),
    re_path(r'^blocks/(?P<block_id>\d+)/rooms/?$', BlockRoomsView.as_view(), name='block-rooms-slash'),
    path('', include(router.urls)),
]
