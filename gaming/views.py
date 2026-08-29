from rest_framework import views, viewsets, permissions, status, response
from django.db.models import Q
from .models import GamingProfile, Tournament
from .serializers import GamingProfileSerializer, TournamentSerializer
from .services import fetch_freefire_profile

class FetchFreeFireStatsAPIView(views.APIView):
    """
    Public / Authenticated endpoint to auto-lookup Free Fire player info by UID.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid', '').strip()
        region = request.data.get('region', 'IND').strip()

        if not uid:
            return response.Response(
                {'error': 'Free Fire UID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = fetch_freefire_profile(uid, region=region)
        return response.Response(data, status=status.HTTP_200_OK)


class MyGamingProfileView(views.APIView):
    """
    Retrieve or update the logged-in user's gaming profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game_type = request.query_params.get('game_type', 'free_fire')
        profile = GamingProfile.objects.filter(user=request.user, game_type=game_type).first()
        if not profile:
            return response.Response({'profile': None})
        serializer = GamingProfileSerializer(profile, context={'request': request})
        return response.Response({'profile': serializer.data})

    def post(self, request):
        game_type = request.data.get('game_type', 'free_fire')
        uid = request.data.get('uid', '').strip()

        if not uid:
            return response.Response(
                {'error': 'Free Fire UID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Look up existing or create new
        profile, created = GamingProfile.objects.get_or_create(
            user=request.user,
            game_type=game_type,
            defaults={'uid': uid, 'in_game_name': request.data.get('in_game_name', f"Player_{uid[-4:]}")}
        )

        # Update profile fields from request
        profile.uid = uid
        if 'in_game_name' in request.data:
            profile.in_game_name = request.data.get('in_game_name') or profile.in_game_name
        if 'level' in request.data:
            profile.level = int(request.data.get('level') or profile.level)
        if 'likes' in request.data:
            profile.likes = int(request.data.get('likes') or profile.likes)
        if 'br_rank' in request.data:
            profile.br_rank = request.data.get('br_rank') or profile.br_rank
        if 'br_rank_points' in request.data:
            profile.br_rank_points = int(request.data.get('br_rank_points') or profile.br_rank_points)
        if 'kd_ratio' in request.data:
            profile.kd_ratio = float(request.data.get('kd_ratio') or profile.kd_ratio)
        if 'total_booyahs' in request.data:
            profile.total_booyahs = int(request.data.get('total_booyahs') or profile.total_booyahs)
        if 'avatar_url' in request.data:
            profile.avatar_url = request.data.get('avatar_url')
        if 'region' in request.data:
            profile.region = request.data.get('region') or 'IND'

        if 'proof_screenshot' in request.FILES:
            profile.proof_screenshot = request.FILES['proof_screenshot']

        profile.is_verified = True
        profile.save()

        serializer = GamingProfileSerializer(profile, context={'request': request})
        return response.Response(
            {
                'message': 'Gaming Profile updated successfully! 🏆',
                'profile': serializer.data
            },
            status=status.HTTP_200_OK
        )


class SyncStatsAPIView(views.APIView):
    """
    1-Click Auto-sync real stats from Free Fire server.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        game_type = request.data.get('game_type', 'free_fire')
        profile = GamingProfile.objects.filter(user=request.user, game_type=game_type).first()
        if not profile:
            return response.Response({'error': 'Profile not found. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

        live_data = fetch_freefire_profile(profile.uid, region=profile.region or 'ind')
        if live_data.get('success'):
            profile.in_game_name = live_data.get('in_game_name') or profile.in_game_name
            profile.level = live_data.get('level') or profile.level
            profile.likes = live_data.get('likes') or profile.likes
            profile.br_rank = live_data.get('br_rank') or profile.br_rank
            profile.br_rank_points = live_data.get('br_rank_points') or profile.br_rank_points
            profile.save()

            serializer = GamingProfileSerializer(profile, context={'request': request})
            return response.Response({
                'message': 'Stats synced from game server! 🔥',
                'profile': serializer.data
            })
        
        return response.Response({'error': 'Could not sync live stats. Try again.'}, status=status.HTTP_400_BAD_REQUEST)


class GamingLeaderboardView(views.APIView):
    """
    Leaderboard of all registered hostel players ranked by score descending.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        game_type = request.query_params.get('game_type', 'free_fire')
        hostel_id = request.query_params.get('hostel')
        search = request.query_params.get('search', '').strip()

        qs = GamingProfile.objects.filter(game_type=game_type).select_related(
            'user', 'user__profile', 'user__profile__hostel', 'user__profile__block', 'user__profile__room'
        )

        if hostel_id:
            qs = qs.filter(user__profile__hostel_id=hostel_id)

        if search:
            qs = qs.filter(
                Q(in_game_name__icontains=search) |
                Q(uid__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__username__icontains=search)
            )

        profiles = qs.order_by('-score')[:100]
        serializer = GamingProfileSerializer(profiles, many=True, context={'request': request})

        # Calculate statistics
        total_players = qs.count()
        top_booyahs = max([p.total_booyahs for p in profiles], default=0)
        top_score = profiles[0].score if profiles.exists() else 0

        return response.Response({
            'results': serializer.data,
            'total_players': total_players,
            'top_score': top_score,
            'top_booyahs': top_booyahs,
        })


class TournamentViewSet(viewsets.ModelViewSet):
    """
    Hostel Free Fire Custom Room Match / Tournament desk.
    """
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
