from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import views, permissions, response
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from posts.models import Post, Category
from notices.models import Notice
from events.models import Event
from services.models import HostelService
from study.models import StudyResource
from hostels.models import Hostel
from moderation.models import Report

User = get_user_model()

class GlobalSearchView(views.APIView):
    """Unified search across people/profiles, posts, marketplace, notices, services, study resources, and events."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query or len(query) < 2:
            return response.Response({
                'query': query,
                'people': [],
                'posts': [],
                'notices': [],
                'events': [],
                'services': [],
                'study_resources': []
            })

        # People / User Profiles search (authenticated only to protect student privacy)
        people_data = []
        if request.user and request.user.is_authenticated:
            users_qs = User.objects.filter(is_active=True, is_blocked=False).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query)
            ).select_related('profile', 'profile__hostel', 'profile__block', 'profile__room')[:8]

            from users.serializers import UserPublicSerializer
            people_data = UserPublicSerializer(users_qs, many=True, context={'request': request}).data

        posts_qs = Post.objects.filter(is_deleted=False, is_hidden=False, status='available').filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query)
        )[:10]

        notices_qs = Notice.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )[:5]

        events_qs = Event.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query)
        )[:5]

        services_qs = HostelService.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query)
        )[:5]

        study_qs = StudyResource.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(course_name__icontains=query) | Q(course_code__icontains=query)
        )[:5]

        return response.Response({
            'query': query,
            'people': people_data,
            'posts': [
                {'id': p.id, 'title': p.title, 'post_type': p.post_type, 'price': str(p.price) if p.price else None, 'created_at': p.created_at}
                for p in posts_qs
            ],
            'notices': [
                {'id': n.id, 'title': n.title, 'priority': n.priority, 'publish_date': n.publish_date}
                for n in notices_qs
            ],
            'events': [
                {'id': e.id, 'title': e.title, 'event_date': e.event_date, 'location': e.location}
                for e in events_qs
            ],
            'services': [
                {'id': s.id, 'name': s.name, 'category': s.category, 'location': s.location}
                for s in services_qs
            ],
            'study_resources': [
                {'id': r.id, 'title': r.title, 'resource_type': r.resource_type, 'course_name': r.course_name}
                for r in study_qs
            ],
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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/hostels/', include('hostels.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/notices/', include('notices.urls')),
    path('api/events/', include('events.urls')),
    path('api/services/', include('services.urls')),
    path('api/study/', include('study.urls')),
    path('api/messages/', include('messaging.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/moderation/', include('moderation.urls')),
    path('api/search/', GlobalSearchView.as_view(), name='global-search'),
    path('api/admin-stats/', AdminStatsView.as_view(), name='admin-stats'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
