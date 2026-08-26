from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, CurrentUserView, ProfileUpdateView,
    UserDetailView, PasswordResetMockView, BlockUserView, UnblockUserView,
    BlockedUsersListView
)

urlpatterns = [
    # Student / Common Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('profile/', ProfileUpdateView.as_view(), name='profile_update'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/block/', BlockUserView.as_view(), name='block_user'),
    path('users/<int:pk>/unblock/', UnblockUserView.as_view(), name='unblock_user'),
    path('blocked-users/', BlockedUsersListView.as_view(), name='blocked_users_list'),
    path('password-reset/', PasswordResetMockView.as_view(), name='password_reset'),
]


