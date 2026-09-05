from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import views, permissions, response
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

import logging
from posts.models import Post, Category
from notices.models import Notice
from events.models import Event
from services.models import HostelService
from study.models import StudyResource
from hostels.models import Hostel
from moderation.models import Report
from gaming.models import Competition

logger = logging.getLogger(__name__)
User = get_user_model()

class GlobalSearchView(views.APIView):
    """Unified search across people/profiles, posts, marketplace, notices, services, study resources, events, and gaming competitions."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = (
            request.query_params.get('q') or
            request.query_params.get('query') or
            request.query_params.get('search') or
            ''
        ).strip()
        clean_user_query = query.lstrip('@').strip()
        clean_id = clean_user_query.lstrip('#')
        is_numeric_id = clean_id.isdigit()
        id_num = int(clean_id) if is_numeric_id else None

        empty_result = {
            'query': query,
            'people': [],
            'posts': [],
            'notices': [],
            'events': [],
            'services': [],
            'study_resources': [],
            'competitions': [],
            'rooms': [],
            'count': 0
        }

        if not query:
            return response.Response(empty_result)

        # 1. People / User Profiles search
        people_data = []
        try:
            from django.db.models import Value, Case, When, IntegerField
            from django.db.models.functions import Concat
            from users.serializers import UserPublicSerializer

            users_qs = User.objects.filter(is_active=True, is_blocked=False).annotate(
                full_name_concat=Concat('first_name', Value(' '), 'last_name')
            )

            user_filter = (
                Q(username__iexact=clean_user_query) |
                Q(username__icontains=clean_user_query) |
                Q(first_name__icontains=clean_user_query) |
                Q(last_name__icontains=clean_user_query) |
                Q(full_name_concat__icontains=clean_user_query) |
                Q(profile__branch__icontains=clean_user_query) |
                Q(profile__programme__icontains=clean_user_query) |
                Q(profile__bio__icontains=clean_user_query) |
                Q(profile__hostel__name__icontains=clean_user_query)
            )
            if clean_user_query.lower() in ['people', 'student', 'students', 'user', 'users']:
                user_filter = Q(is_student=True)
            elif id_num is not None:
                user_filter |= Q(id=id_num)

            ordering = []
            if id_num is not None:
                users_qs = users_qs.annotate(
                    exact_id=Case(
                        When(id=id_num, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                )
                ordering.append('-exact_id')

            users_qs = users_qs.annotate(
                exact_username=Case(
                    When(username__iexact=clean_user_query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
            ordering.extend(['-exact_username', 'username'])

            users_qs = users_qs.filter(user_filter).order_by(*ordering).select_related(
                'profile', 'profile__hostel', 'profile__block', 'profile__room'
            )[:15]

            people_data = UserPublicSerializer(users_qs, many=True, context={'request': request}).data
        except Exception as e:
            logger.error("Error in GlobalSearchView (people): %s", e)
            people_data = []

        # 2. Posts & Marketplace items
        posts_data = []
        try:
            user = getattr(request, 'user', None)
            is_staff = getattr(user, 'is_staff', False)
            if is_staff:
                visibility_filter = Q(is_deleted=False)
            elif user and getattr(user, 'is_authenticated', False):
                visibility_filter = Q(is_deleted=False) & (Q(is_hidden=False) | Q(author=user))
            else:
                visibility_filter = Q(is_deleted=False, is_hidden=False)

            post_query_filter = (
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query) |
                Q(category__name__icontains=query) |
                Q(post_type__icontains=query) |
                Q(author__username__icontains=query) |
                Q(author__first_name__icontains=query) |
                Q(author__last_name__icontains=query)
            )
            if query.lower() in ['post', 'posts', 'marketplace', 'listing', 'listings']:
                post_query_filter = Q(id__isnull=False)

            posts_qs = Post.objects.filter(visibility_filter).filter(
                post_query_filter
            ).select_related('author', 'category').order_by('-created_at')[:15]

            posts_data = [
                {
                    'id': p.id,
                    'title': p.title,
                    'post_type': p.post_type,
                    'price': str(p.price) if p.price else None,
                    'created_at': p.created_at.isoformat() if hasattr(p.created_at, 'isoformat') else str(p.created_at)
                }
                for p in posts_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (posts): %s", e)
            posts_data = []

        # 3. Official Notices
        notices_data = []
        try:
            notice_filter = (
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(priority__icontains=query) |
                Q(target_hostel__name__icontains=query)
            )
            if query.lower() in ['notice', 'notices', 'announcement', 'announcements']:
                notice_filter = Q(id__isnull=False)

            notices_qs = Notice.objects.filter(is_active=True).filter(
                notice_filter
            ).order_by('-priority', '-publish_date')[:10]

            notices_data = [
                {
                    'id': n.id,
                    'title': n.title,
                    'priority': n.priority,
                    'publish_date': str(n.publish_date)
                }
                for n in notices_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (notices): %s", e)
            notices_data = []

        # 4. Campus / Hostel Events
        events_data = []
        try:
            event_filter = (
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query) |
                Q(organizer__icontains=query) |
                Q(hostel__name__icontains=query)
            )
            if query.lower() in ['event', 'events']:
                event_filter = Q(id__isnull=False)

            events_qs = Event.objects.filter(is_active=True).filter(
                event_filter
            ).order_by('event_date')[:10]

            events_data = [
                {
                    'id': e.id,
                    'title': e.title,
                    'event_date': str(e.event_date),
                    'location': e.location
                }
                for e in events_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (events): %s", e)
            events_data = []

        # 5. Hostel Services
        services_data = []
        try:
            service_filter = (
                Q(name__icontains=query) |
                Q(category__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query) |
                Q(contact_person__icontains=query) |
                Q(hostel__name__icontains=query)
            )
            if query.lower() in ['service', 'services']:
                service_filter = Q(id__isnull=False)

            services_qs = HostelService.objects.filter(is_active=True).filter(
                service_filter
            ).order_by('category', 'name')[:10]

            services_data = [
                {
                    'id': s.id,
                    'name': s.name,
                    'category': s.category,
                    'location': s.location
                }
                for s in services_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (services): %s", e)
            services_data = []

        # 6. Study Resources & PYQs
        study_data = []
        try:
            study_filter = (
                Q(title__icontains=query) |
                Q(course_name__icontains=query) |
                Q(course_code__icontains=query) |
                Q(department__icontains=query) |
                Q(description__icontains=query) |
                Q(resource_type__icontains=query) |
                Q(author__icontains=query)
            )
            if query.lower() in ['study', 'resource', 'resources', 'pyq', 'pyqs']:
                study_filter = Q(id__isnull=False)

            study_qs = StudyResource.objects.filter(is_active=True, is_pending_review=False).filter(
                study_filter
            ).order_by('-downloads_count')[:15]

            study_data = [
                {
                    'id': r.id,
                    'title': r.title,
                    'resource_type': r.resource_type,
                    'course_name': r.course_name
                }
                for r in study_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (study): %s", e)
            study_data = []

        # 7. Gaming Competitions (safe optional query)
        comp_list = []
        try:
            from gaming.models import Competition
            competition_filter = (
                Q(name__icontains=query) |
                Q(game__icontains=query) |
                Q(custom_game_name__icontains=query) |
                Q(description__icontains=query) |
                Q(rules__icontains=query)
            )
            if query.lower() in ['game', 'games', 'gaming', 'competition', 'competitions']:
                competition_filter = Q(id__isnull=False)

            competitions_qs = Competition.objects.filter(is_active=True).filter(
                competition_filter
            ).order_by('-start_datetime')[:10]
            comp_list = [
                {
                    'id': c.id,
                    'title': c.name,
                    'name': c.name,
                    'game': getattr(c, 'game_display', c.game),
                    'competition_type': c.competition_type,
                    'start_datetime': c.start_datetime.isoformat() if hasattr(c.start_datetime, 'isoformat') else str(c.start_datetime),
                    'status': c.status
                }
                for c in competitions_qs
            ]
        except Exception as e:
            logger.error("Error in GlobalSearchView (competitions): %s", e)
            comp_list = []

        total_count = (
            len(people_data) +
            len(posts_data) +
            len(notices_data) +
            len(events_data) +
            len(services_data) +
            len(study_data) +
            len(comp_list)
        )

        return response.Response({
            'query': query,
            'people': people_data,
            'posts': posts_data,
            'notices': notices_data,
            'events': events_data,
            'services': services_data,
            'study_resources': study_data,
            'competitions': comp_list,
            'rooms': comp_list,
            'count': total_count
        })


class AdminStatsView(views.APIView):
    """Admin dashboard stats overview."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_students = User.objects.filter(is_student=True).count()
        active_students = User.objects.filter(is_student=True, is_active=True, is_blocked=False).count()
        total_posts = Post.objects.filter(is_deleted=False).count()
        active_listings = Post.objects.filter(is_deleted=False, is_hidden=False, status='available').count()
        total_hostels = Hostel.objects.filter(is_active=True).count()
        pending_reports = Report.objects.filter(status='pending').count()
        
        recent_users = User.objects.order_by('-date_joined')[:5].values('id', 'email', 'first_name', 'last_name', 'date_joined', 'is_blocked', 'is_student')
        recent_posts = Post.objects.filter(is_deleted=False).order_by('-created_at')[:5].values('id', 'title', 'post_type', 'author__email', 'created_at', 'status')
        recent_reports = Report.objects.order_by('-created_at')[:5].values('id', 'report_type', 'target_id', 'reason', 'status', 'created_at')

        return response.Response({
            'total_students': total_students,
            'active_students': active_students,
            'total_posts': total_posts,
            'active_listings': active_listings,
            'total_hostels': total_hostels,
            'pending_reports': pending_reports,
            'recent_users': list(recent_users),
            'recent_posts': list(recent_posts),
            'recent_reports': list(recent_reports),
        })



from django.views.static import serve
from django.urls import re_path

# Django Admin branding & View Site target
admin.site.site_header = "HostelTalkies Administration"
admin.site.site_title = "HostelTalkies Admin"
admin.site.index_title = "Welcome to HostelTalkies Admin Portal"
admin.site.site_url = "https://hostel-talkies-frontend.vercel.app"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/hostels/', include('hostels.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/notices/', include('notices.urls')),
    path('api/events/', include('events.urls')),
    path('api/services/', include('services.urls')),
    path('api/study/', include('study.urls')),
    path('api/gaming/', include('gaming.urls')),
    path('api/messages/', include('messaging.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/moderation/', include('moderation.urls')),
    path('api/search/', GlobalSearchView.as_view(), name='global-search'),
    re_path(r'^api/search/?$', GlobalSearchView.as_view(), name='global-search-slash'),
    path('api/admin-stats/', AdminStatsView.as_view(), name='admin-stats'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
