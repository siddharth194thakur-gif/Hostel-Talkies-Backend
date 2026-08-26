from django.conf import settings
from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from .models import StudentProfile, UserBlock
from .serializers import (
    UserSerializer, UserPublicSerializer, RegisterSerializer, ProfileUpdateSerializer
)
from .permissions import IsNotBlockedOrSuspended

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            user_data = UserSerializer(user).data
            return Response({
                'message': 'Registration successful! Welcome to HostelTalkies.',
                'user': user_data,
                'tokens': tokens,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email_or_username = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not email_or_username or not password:
            return Response({'detail': 'Please provide both email and password.'}, status=status.HTTP_400_BAD_REQUEST)

        # Look up user by email or username
        user = None
        if '@' in email_or_username:
            user = User.objects.filter(email__iexact=email_or_username).first()
        else:
            user = User.objects.filter(username__iexact=email_or_username).first()

        if not user or not user.check_password(password):
            return Response({'detail': 'Invalid email/username or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'detail': 'This account has been deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        if user.is_blocked:
            return Response({
                'detail': 'Your account has been blocked by an administrator.',
                'reason': user.block_reason
            }, status=status.HTTP_403_FORBIDDEN)

        if user.is_currently_suspended():
            return Response({
                'detail': f'Your account is suspended until {user.suspended_until.strftime("%b %d, %Y %H:%M") if user.suspended_until else "further notice"}.',
                'reason': user.block_reason
            }, status=status.HTTP_403_FORBIDDEN)

        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user, context={'request': request}).data
        return Response({
            'message': 'Login successful.',
            'user': user_data,
            'tokens': tokens,
        }, status=status.HTTP_200_OK)




class CurrentUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        profile, _ = StudentProfile.objects.get_or_create(user=self.request.user)
        return profile

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Force refresh user from database so new profile image and relations are freshly loaded
        self.request.user.refresh_from_db()
        return Response(UserSerializer(self.request.user, context={'request': request}).data)


class UserDetailView(generics.RetrieveAPIView):
    """Public profile for viewing other students without leaking sensitive info."""
    queryset = User.objects.filter(is_active=True, is_blocked=False)
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]


class PasswordResetMockView(views.APIView):
    """Allows simulated password reset request for students."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f'If an account exists with {email}, password reset instructions have been dispatched.'
        }, status=status.HTTP_200_OK)


class BlockUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        if target_user.id == request.user.id:
            return Response({'detail': 'You cannot block yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        block_rel, created = UserBlock.objects.get_or_create(blocker=request.user, blocked=target_user)
        return Response({
            'detail': f'You have blocked {target_user.get_full_name() or target_user.username}.',
            'is_blocked_by_me': True,
        }, status=status.HTTP_200_OK)


class UnblockUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        deleted_count, _ = UserBlock.objects.filter(blocker=request.user, blocked=target_user).delete()
        return Response({
            'detail': f'You have unblocked {target_user.get_full_name() or target_user.username}.',
            'is_blocked_by_me': False,
        }, status=status.HTTP_200_OK)


class BlockedUsersListView(views.APIView):
    """Private endpoint returning only the users blocked by request.user."""
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def get(self, request):
        blocked_relations = UserBlock.objects.filter(blocker=request.user).select_related('blocked', 'blocked__profile')
        blocked_users = [rel.blocked for rel in blocked_relations]
        serializer = UserPublicSerializer(blocked_users, many=True, context={'request': request})
        return Response(serializer.data)


