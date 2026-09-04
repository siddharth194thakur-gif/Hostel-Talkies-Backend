from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.utils import timezone

from .models import Competition, CompetitionParticipant, CompetitionResult
from .serializers import (
    CompetitionSerializer,
    CompetitionParticipantSerializer,
    CompetitionResultSerializer,
)

class IsOrganizerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Allow any user to view competitions and participate (join, leave, submit_result).
    Only the creator or admin can update, delete, verify results, or manage settings.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False

        # Participant actions allowed for any authenticated user
        if getattr(view, 'action', None) in ['join', 'leave', 'submit_result']:
            return True

        # Organizer actions restricted to creator or admin
        return (
            obj.creator_id == request.user.id
            or request.user.is_staff
            or getattr(request.user, 'is_hostel_admin', False)
            or getattr(request.user, 'is_superuser', False)
        )


class CompetitionViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizerOrAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'custom_game_name', 'description', 'rules', 'creator__first_name', 'creator__last_name', 'creator__username']
    ordering_fields = ['start_datetime', 'created_at']
    ordering = ['-start_datetime', '-created_at']

    def get_queryset(self):
        qs = Competition.objects.filter(is_active=True).select_related(
            'creator', 'creator__profile', 'hostel'
        ).prefetch_related(
            'participants', 'participants__user', 'participants__user__profile',
            'results', 'results__participant', 'results__participant__user'
        )

        game = self.request.query_params.get('game')
        if game:
            if game in ['bgmi', 'bgmi_lite', 'free_fire_max', 'other']:
                qs = qs.filter(game=game)

        status_param = self.request.query_params.get('status')
        if status_param in ['upcoming', 'registration_open', 'live', 'completed', 'cancelled']:
            qs = qs.filter(status=status_param)

        creator_param = self.request.query_params.get('creator')
        if creator_param:
            qs = qs.filter(creator_id=creator_param)

        hostel_param = self.request.query_params.get('hostel')
        if hostel_param:
            qs = qs.filter(hostel_id=hostel_param)

        my_joined = self.request.query_params.get('joined')
        if my_joined and self.request.user.is_authenticated:
            qs = qs.filter(participants__user=self.request.user, participants__status='registered')

        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(custom_game_name__icontains=search) |
                Q(description__icontains=search) |
                Q(rules__icontains=search) |
                Q(creator__first_name__icontains=search) |
                Q(creator__last_name__icontains=search) |
                Q(creator__username__icontains=search)
            )

        return qs.distinct()

    def perform_create(self, serializer):
        user = self.request.user
        hostel = getattr(user.profile, 'hostel', None) if hasattr(user, 'profile') else None
        serializer.save(creator=user, hostel=hostel)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        if not competition.is_registration_open:
            return Response(
                {'detail': 'Registration for this competition is currently closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if CompetitionParticipant.objects.filter(competition=competition, user=user, status='registered').exists():
            return Response(
                {'detail': 'You have already registered for this competition.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        in_game_name = request.data.get('in_game_name', '').strip()
        if not in_game_name:
            in_game_name = user.first_name or user.username

        # Informational only game UID (NO external API fetch)
        game_uid = request.data.get('game_uid', '').strip()
        team_name = request.data.get('team_name', '').strip()
        team_members = request.data.get('team_members', '').strip()
        contact_number = request.data.get('contact_number', '').strip()

        slot_number = competition.participants_count + 1

        # Check existing participant record if previously left
        participant = CompetitionParticipant.objects.filter(competition=competition, user=user).first()
        if participant:
            participant.in_game_name = in_game_name
            participant.game_uid = game_uid
            participant.team_name = team_name
            participant.team_members = team_members
            participant.contact_number = contact_number
            participant.slot_number = slot_number
            participant.status = 'registered'
            participant.save()
        else:
            participant = CompetitionParticipant.objects.create(
                competition=competition,
                user=user,
                in_game_name=in_game_name,
                game_uid=game_uid,
                team_name=team_name,
                team_members=team_members,
                contact_number=contact_number,
                slot_number=slot_number,
                status='registered'
            )

        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': f'Successfully registered slot #{slot_number} as {in_game_name}!',
                'competition': serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def leave(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        participant = CompetitionParticipant.objects.filter(competition=competition, user=user, status='registered').first()
        if not participant:
            return Response(
                {'detail': 'You are not registered in this competition.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant.delete()
        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': 'You have left the competition.',
                'competition': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch', 'post'], permission_classes=[permissions.IsAuthenticated])
    def update_credentials(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        if competition.creator_id != user.id and not user.is_staff and not getattr(user, 'is_superuser', False):
            return Response(
                {'detail': 'Only the competition organizer can update Room ID and Password.'},
                status=status.HTTP_403_FORBIDDEN
            )

        room_id = request.data.get('room_id')
        room_password = request.data.get('room_password')
        status_val = request.data.get('status')

        if room_id is not None:
            competition.room_id = str(room_id).strip()
        if room_password is not None:
            competition.room_password = str(room_password).strip()
        if status_val in ['upcoming', 'registration_open', 'live', 'completed', 'cancelled']:
            competition.status = status_val

        competition.save()
        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': 'In-game credentials updated successfully.',
                'competition': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_registration(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        if competition.creator_id != user.id and not user.is_staff and not getattr(user, 'is_superuser', False):
            return Response(
                {'detail': 'Only the competition organizer can manage registration state.'},
                status=status.HTTP_403_FORBIDDEN
            )

        competition.is_registration_closed_by_organizer = not competition.is_registration_closed_by_organizer
        competition.save()
        
        state_msg = "closed" if competition.is_registration_closed_by_organizer else "re-opened"
        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': f'Registration has been {state_msg}.',
                'competition': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_result(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        participant = CompetitionParticipant.objects.filter(competition=competition, user=user, status='registered').first()
        is_organizer = competition.creator_id == user.id or user.is_staff or getattr(user, 'is_superuser', False)

        # If organizer is submitting on behalf of a participant
        participant_id = request.data.get('participant_id')
        if is_organizer and participant_id:
            participant = CompetitionParticipant.objects.filter(competition=competition, id=participant_id).first()

        if not participant:
            return Response(
                {'detail': 'You are not registered in this competition.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        position = request.data.get('position')
        kills = request.data.get('kills', 0)
        score = request.data.get('score', '').strip()
        points = request.data.get('points')
        notes = request.data.get('notes', '').strip()
        proof_image = request.FILES.get('proof_image')

        # Points calculation if points_based rules exist and points not explicitly passed
        pos_num = int(position) if position and str(position).isdigit() else None
        kill_num = int(kills) if kills and str(kills).isdigit() else 0

        calculated_points = 0.0
        if points is not None and str(points).replace('.', '', 1).isdigit():
            calculated_points = float(points)
        elif competition.scoring_rules:
            # e.g. points_per_kill and placement_points
            ppk = float(competition.scoring_rules.get('points_per_kill', 1))
            calculated_points += kill_num * ppk
            if pos_num:
                placement_table = competition.scoring_rules.get('placement_points', {})
                calculated_points += float(placement_table.get(str(pos_num), 0))

        # Direct auto-approval if submitted by organizer, else pending
        init_status = 'approved' if is_organizer else 'pending'

        result = CompetitionResult.objects.create(
            competition=competition,
            participant=participant,
            position=pos_num,
            kills=kill_num,
            points=calculated_points,
            score=score,
            proof_image=proof_image,
            notes=notes,
            verification_status=init_status,
            verified_by=user if is_organizer else None,
            verified_at=timezone.now() if is_organizer else None,
        )

        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': 'Result submitted successfully!' if not is_organizer else 'Result entered and approved!',
                'result': CompetitionResultSerializer(result, context={'request': request}).data,
                'competition': serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def verify_result(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        if competition.creator_id != user.id and not user.is_staff and not getattr(user, 'is_superuser', False):
            return Response(
                {'detail': 'Only the competition organizer can verify submitted results.'},
                status=status.HTTP_403_FORBIDDEN
            )

        result_id = request.data.get('result_id')
        action_type = request.data.get('action') # 'approve' or 'reject'

        if not result_id or action_type not in ['approve', 'reject']:
            return Response(
                {'detail': 'Valid result_id and action (approve/reject) are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = CompetitionResult.objects.filter(competition=competition, id=result_id).first()
        if not result:
            return Response(
                {'detail': 'Result not found in this competition.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if action_type == 'approve':
            result.verification_status = 'approved'
            result.verified_by = user
            result.verified_at = timezone.now()
            # Allow optional point overrides on approval
            override_points = request.data.get('points')
            if override_points is not None and str(override_points).replace('.', '', 1).isdigit():
                result.points = float(override_points)
        else:
            result.verification_status = 'rejected'
            result.verified_by = user
            result.verified_at = timezone.now()

        result.save()
        serializer = self.get_serializer(competition, context={'request': request})
        return Response(
            {
                'detail': f'Result {action_type}d successfully!',
                'result': CompetitionResultSerializer(result, context={'request': request}).data,
                'competition': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def pending_results(self, request, pk=None):
        competition = self.get_object()
        user = request.user

        if competition.creator_id != user.id and not user.is_staff and not getattr(user, 'is_superuser', False):
            return Response(
                {'detail': 'Only the organizer can view pending results.'},
                status=status.HTTP_403_FORBIDDEN
            )

        pending = competition.results.filter(verification_status='pending').select_related(
            'participant', 'participant__user'
        ).order_by('-submitted_at')
        return Response(CompetitionResultSerializer(pending, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def leaderboard(self, request, pk=None):
        competition = self.get_object()
        approved_results = competition.results.filter(verification_status='approved').select_related(
            'participant', 'participant__user', 'participant__user__profile'
        ).order_by('-points', 'position', '-kills', '-submitted_at')
        return Response(CompetitionResultSerializer(approved_results, many=True, context={'request': request}).data)
