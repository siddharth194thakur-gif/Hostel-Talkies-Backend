from rest_framework import views, viewsets, permissions, status, response
from django.db.models import Q
from .models import GamingProfile, Tournament
from .serializers import GamingProfileSerializer, TournamentSerializer
from .services import FreeFireService, fetch_freefire_profile

class FetchFreeFireStatsAPIView(views.APIView):
    """
    Public / Authenticated endpoint to auto-lookup Free Fire player info by UID.
    Uses FreeFireService with multi-provider fallback, caching (5 min) & rate-limiting.
    """
    permission_classes = [permissions.AllowAny]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def get(self, request):
        uid = request.query_params.get('uid', '').strip()
        region = request.query_params.get('region', 'IND').strip()
        return self._lookup(request, uid, region)

    def post(self, request):
        uid = request.data.get('uid', '').strip()
        region = request.data.get('region', 'IND').strip()
        return self._lookup(request, uid, region)

    def _lookup(self, request, uid, region):
        if not uid:
            return response.Response(
                {'success': False, 'error': 'Free Fire UID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_ip = self.get_client_ip(request)
        data = FreeFireService.get_player_profile(uid, region=region, client_ip=client_ip)
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
        region = request.data.get('region', 'IND').strip() or 'IND'

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

        profile.uid = uid
        profile.region = region
        if 'in_game_name' in request.data and request.data.get('in_game_name'):
            profile.in_game_name = request.data.get('in_game_name')
        if 'level' in request.data and request.data.get('level') is not None:
            profile.level = int(request.data.get('level'))
        if 'likes' in request.data and request.data.get('likes') is not None:
            profile.likes = int(request.data.get('likes'))
        if 'br_rank' in request.data and request.data.get('br_rank'):
            profile.br_rank = request.data.get('br_rank')
        if 'br_rank_points' in request.data and request.data.get('br_rank_points') is not None:
            profile.br_rank_points = int(request.data.get('br_rank_points'))
        if 'cs_rank' in request.data and request.data.get('cs_rank'):
            profile.cs_rank = request.data.get('cs_rank')
        if 'kd_ratio' in request.data and request.data.get('kd_ratio') is not None:
            profile.kd_ratio = float(request.data.get('kd_ratio'))
        if 'total_booyahs' in request.data and request.data.get('total_booyahs') is not None:
            profile.total_booyahs = int(request.data.get('total_booyahs'))
        if 'avatar_url' in request.data:
            profile.avatar_url = request.data.get('avatar_url')

        if 'proof_screenshot' in request.FILES:
            profile.proof_screenshot = request.FILES['proof_screenshot']

        profile.is_verified = True
        profile.save()

        serializer = GamingProfileSerializer(profile, context={'request': request})
        return response.Response(
            {
                'message': 'Gaming Profile linked & competition score updated! 🏆',
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
