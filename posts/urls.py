from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, PostViewSet, CommentDetailView, BorrowRequestUpdateView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'', PostViewSet, basename='post')

urlpatterns = [
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('borrow-requests/<int:pk>/', BorrowRequestUpdateView.as_view(), name='borrow-request-update'),
    path('', include(router.urls)),
]
