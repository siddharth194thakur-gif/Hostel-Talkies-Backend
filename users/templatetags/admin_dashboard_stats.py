from django import template
from django.contrib.auth import get_user_model
from hostels.models import Hostel, Block, Room
from posts.models import Post, Category, Comment, BorrowRequest
from notices.models import Notice
from events.models import Event
from study.models import StudyResource
from services.models import HostelService
from notifications.models import Notification
from moderation.models import Report, AdminActionLog, Feedback, SiteSetting
from users.models import StudentProfile
from django.utils import timezone
from django.db.models import Count, Q, Sum

register = template.Library()
User = get_user_model()


class RecentAdminLogNode(template.Node):
    def __init__(self, limit, varname):
        self.limit = int(limit) if str(limit).isdigit() else 10
        self.varname = varname

    def render(self, context):
        try:
            logs = AdminActionLog.objects.select_related('admin').order_by('-timestamp')[:self.limit]
            context[self.varname] = list(logs)
        except Exception:
            context[self.varname] = []
        return ''


@register.tag(name='render_recent_log')
def do_render_recent_log(parser, token):
    tokens = token.split_contents()
    limit = 10
    varname = 'admin_log'
    if len(tokens) >= 2:
        limit = tokens[1]
    if len(tokens) == 4 and tokens[2] == 'as':
        varname = tokens[3]
    return RecentAdminLogNode(limit, varname)


@register.simple_tag
def get_dashboard_stats():
    now = timezone.now()
    today = now.date()

    # User & Role Stats
    students_qs = User.objects.filter(is_student=True)
    total_students = students_qs.count()
    active_students = students_qs.filter(is_active=True, is_blocked=False, is_suspended=False).count()
    blocked_students = students_qs.filter(is_blocked=True).count()
    suspended_students = students_qs.filter(is_suspended=True).count()
    new_students_this_week = students_qs.filter(date_joined__gte=now - timezone.timedelta(days=7)).count()

    # Hostel Infrastructure Stats
    hostels_qs = Hostel.objects.all()
    total_hostels = hostels_qs.count()
    active_hostels = hostels_qs.filter(is_active=True).count()
    inactive_hostels = hostels_qs.filter(is_active=False).count()
    total_blocks = Block.objects.count()
    active_blocks = Block.objects.filter(is_active=True).count()
    total_rooms = Room.objects.count()
    active_rooms = Room.objects.filter(is_active=True).count()
    total_capacity = Room.objects.aggregate(cap=Sum('capacity'))['cap'] or 0

    # Community Stats
    posts_qs = Post.objects.filter(is_deleted=False)
    total_posts = posts_qs.count()
    active_posts = posts_qs.filter(is_hidden=False, status='available').count()
    sold_posts = posts_qs.filter(status='sold').count()
    giveaway_posts = posts_qs.filter(post_type='giveaway', is_hidden=False).count()
    borrow_posts = posts_qs.filter(post_type='borrow', is_hidden=False).count()
    total_comments = Comment.objects.filter(is_hidden=False).count()
    total_borrows = BorrowRequest.objects.count()
    pending_borrows = BorrowRequest.objects.filter(status='pending').count()
    active_borrows = BorrowRequest.objects.filter(status='accepted').count()

    # Academic & Communication
    study_qs = StudyResource.objects.filter(is_active=True)
    total_study = study_qs.count()
    notes_count = study_qs.filter(resource_type='notes').count()
    pyqs_count = study_qs.filter(resource_type='pyq').count()
    books_count = study_qs.filter(resource_type='book').count()
    total_downloads = study_qs.aggregate(d=Sum('downloads_count'))['d'] or 0

    notices_qs = Notice.objects.all()
    total_notices = notices_qs.count()
    active_notices = notices_qs.filter(is_active=True).count()
    urgent_notices = notices_qs.filter(is_active=True, priority='urgent').count()
    important_notices = notices_qs.filter(is_active=True, priority='important').count()

    events_qs = Event.objects.all()
    total_events = events_qs.count()
    upcoming_events_count = events_qs.filter(is_active=True, event_date__gte=today).count()
    total_notifications = Notification.objects.count()
    unread_notifications = Notification.objects.filter(is_read=False).count()

    # Moderation
    reports_qs = Report.objects.all()
    total_reports = reports_qs.count()
    pending_reports = reports_qs.filter(status='pending').count()
    reviewing_reports = reports_qs.filter(status='reviewing').count()
    resolved_reports = reports_qs.filter(status='resolved').count()
    dismissed_reports = reports_qs.filter(status='dismissed').count()
    pending_feedback = Feedback.objects.filter(status='pending').count()

    # Dynamic Hostel Overview List (Optimized batch queries)
    room_stats = {
        item['block__hostel_id']: item
        for item in Room.objects.values('block__hostel_id').annotate(
            r_count=Count('id'),
            cap=Sum('capacity')
        )
    }

    hostels_summary = []
    hostels_annotated = Hostel.objects.annotate(
        b_count=Count('blocks', distinct=True),
        s_count=Count('students', distinct=True),
    )
    for h in hostels_annotated:
        r_stat = room_stats.get(h.id, {'r_count': 0, 'cap': 0})
        hostels_summary.append({
            'id': h.id,
            'name': h.name,
            'code': h.code,
            'gender': h.gender,
            'is_active': h.is_active,
            'blocks_count': h.b_count,
            'rooms_count': r_stat['r_count'],
            'students_count': h.s_count,
            'capacity': r_stat['cap'] or 0,
        })

    # Dynamic Recent Feeds
    recent_students = User.objects.filter(is_student=True).select_related('profile', 'profile__hostel', 'profile__block', 'profile__room').order_by('-date_joined')[:5]
    recent_posts = Post.objects.filter(is_deleted=False).select_related('author', 'category', 'hostel').order_by('-created_at')[:5]
    recent_reports = Report.objects.select_related('reporter').order_by('-created_at')[:5]
    upcoming_events = Event.objects.filter(is_active=True, event_date__gte=today).select_related('hostel').order_by('event_date', 'event_time')[:5]
    active_priority_notices = Notice.objects.filter(is_active=True).select_related('target_hostel', 'created_by').order_by('-priority', '-publish_date')[:5]
    recent_logs = AdminActionLog.objects.select_related('admin').order_by('-timestamp')[:8]

    return {
        # KPI Totals
        'total_students': total_students,
        'active_students': active_students,
        'blocked_students': blocked_students,
        'suspended_students': suspended_students,
        'new_students_this_week': new_students_this_week,

        'total_hostels': total_hostels,
        'active_hostels': active_hostels,
        'inactive_hostels': inactive_hostels,
        'total_blocks': total_blocks,
        'active_blocks': active_blocks,
        'total_rooms': total_rooms,
        'active_rooms': active_rooms,
        'total_capacity': total_capacity,

        'total_posts': total_posts,
        'active_posts': active_posts,
        'sold_posts': sold_posts,
        'giveaway_posts': giveaway_posts,
        'borrow_posts': borrow_posts,
        'total_comments': total_comments,
        'total_borrows': total_borrows,
        'pending_borrows': pending_borrows,
        'active_borrows': active_borrows,

        'total_study': total_study,
        'notes_count': notes_count,
        'pyqs_count': pyqs_count,
        'books_count': books_count,
        'total_downloads': total_downloads,

        'total_notices': total_notices,
        'active_notices': active_notices,
        'urgent_notices': urgent_notices,
        'important_notices': important_notices,

        'total_events': total_events,
        'upcoming_events_count': upcoming_events_count,
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,

        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'reviewing_reports': reviewing_reports,
        'resolved_reports': resolved_reports,
        'dismissed_reports': dismissed_reports,
        'pending_feedback': pending_feedback,

        # Complex Entities
        'hostels_summary': hostels_summary,
        'recent_students': recent_students,
        'recent_posts': recent_posts,
        'recent_reports': recent_reports,
        'upcoming_events': upcoming_events,
        'active_priority_notices': active_priority_notices,
        'recent_logs': recent_logs,
    }


@register.simple_tag
def get_changelist_kpis(app_label, model_name):
    """
    Generates tailored, real database KPI cards above the changelist table for each model.
    """
    now = timezone.now()
    today = now.date()
    kpis = []

    if app_label == 'users' and model_name == 'student':
        qs = User.objects.filter(is_student=True)
        kpis = [
            {'label': 'Total Students', 'value': qs.count(), 'color': '#4f46e5', 'sub': 'Registered Residents'},
            {'label': 'Active Accounts', 'value': qs.filter(is_active=True, is_blocked=False, is_suspended=False).count(), 'color': '#10b981', 'sub': 'In Good Standing'},
            {'label': 'Blocked Accounts', 'value': qs.filter(is_blocked=True).count(), 'color': '#ef4444', 'sub': 'Restricted by Admin'},
            {'label': 'Suspended Accounts', 'value': qs.filter(is_suspended=True).count(), 'color': '#f59e0b', 'sub': 'Temporary Timeouts'},
            {'label': 'Joined This Week', 'value': qs.filter(date_joined__gte=now - timezone.timedelta(days=7)).count(), 'color': '#8b5cf6', 'sub': 'Recent Enrollments'},
        ]
    elif app_label == 'users' and model_name == 'user':
        kpis = [
            {'label': 'Total Accounts', 'value': User.objects.count(), 'color': '#4f46e5', 'sub': 'Database Users'},
            {'label': 'Students', 'value': User.objects.filter(is_student=True).count(), 'color': '#0284c7', 'sub': 'Residents'},
            {'label': 'Staff / Admins', 'value': User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count(), 'color': '#f59e0b', 'sub': 'Supervisory Access'},
            {'label': 'Active Users', 'value': User.objects.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Enabled Accounts'},
        ]
    elif app_label == 'hostels' and model_name == 'hostel':
        kpis = [
            {'label': 'Total Hostels', 'value': Hostel.objects.count(), 'color': '#0284c7', 'sub': 'Campus Residences'},
            {'label': 'Active Hostels', 'value': Hostel.objects.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Operational'},
            {'label': 'Total Blocks', 'value': Block.objects.count(), 'color': '#7c3aed', 'sub': 'Hostel Wings'},
            {'label': 'Total Rooms', 'value': Room.objects.count(), 'color': '#4f46e5', 'sub': 'Allotted Units'},

            {'label': 'Enrolled Students', 'value': StudentProfile.objects.filter(hostel__isnull=False).count(), 'color': '#f59e0b', 'sub': 'Resident Population'},
        ]
    elif app_label == 'hostels' and model_name == 'block':
        kpis = [
            {'label': 'Total Blocks', 'value': Block.objects.count(), 'color': '#7c3aed', 'sub': 'Hostel Wings'},
            {'label': 'Active Blocks', 'value': Block.objects.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Occupied Wings'},
            {'label': 'Total Rooms', 'value': Room.objects.count(), 'color': '#4f46e5', 'sub': 'Across All Blocks'},
            {'label': 'Students in Blocks', 'value': StudentProfile.objects.filter(block__isnull=False).count(), 'color': '#0284c7', 'sub': 'Assigned Block'},
        ]
    elif app_label == 'hostels' and model_name == 'room':
        total_r = Room.objects.count()
        occupied_r = Room.objects.annotate(st_cnt=Count('students')).filter(st_cnt__gt=0).count()
        vacant_r = Room.objects.annotate(st_cnt=Count('students')).filter(st_cnt=0).count()
        total_cap = Room.objects.aggregate(c=Sum('capacity'))['c'] or 0
        kpis = [
            {'label': 'Total Rooms', 'value': total_r, 'color': '#4f46e5', 'sub': 'Configured Rooms'},
            {'label': 'Occupied Rooms', 'value': occupied_r, 'color': '#10b981', 'sub': 'Has 1+ Student'},
            {'label': 'Vacant Rooms', 'value': vacant_r, 'color': '#0284c7', 'sub': '0 Residents'},
            {'label': 'Total Capacity', 'value': total_cap, 'color': '#7c3aed', 'sub': 'Student Beds Available'},
        ]
    elif app_label == 'posts' and model_name == 'post':
        p_qs = Post.objects.filter(is_deleted=False)
        kpis = [
            {'label': 'Total Posts', 'value': p_qs.count(), 'color': '#4f46e5', 'sub': 'Community Listings'},
            {'label': 'Available Listings', 'value': p_qs.filter(status='available', is_hidden=False).count(), 'color': '#10b981', 'sub': 'Open on Marketplace'},
            {'label': 'Sold / Completed', 'value': p_qs.filter(status='sold').count(), 'color': '#0284c7', 'sub': 'Completed Deals'},
            {'label': 'Free Giveaways', 'value': p_qs.filter(post_type='giveaway').count(), 'color': '#7c3aed', 'sub': 'Zero Cost Items'},
            {'label': 'Hidden / Moderated', 'value': p_qs.filter(is_hidden=True).count(), 'color': '#ef4444', 'sub': 'Hidden by Admin'},
        ]
    elif app_label == 'posts' and model_name == 'category':
        c_qs = Category.objects.all()
        kpis = [
            {'label': 'Total Categories', 'value': c_qs.count(), 'color': '#4f46e5', 'sub': 'Taxonomy Groups'},
            {'label': 'Active Categories', 'value': c_qs.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Visible to Students'},
            {'label': 'Categories with Posts', 'value': c_qs.annotate(p_cnt=Count('posts')).filter(p_cnt__gt=0).count(), 'color': '#7c3aed', 'sub': 'Has Active Content'},
        ]
    elif app_label == 'posts' and model_name == 'comment':
        cm_qs = Comment.objects.all()
        kpis = [
            {'label': 'Total Comments', 'value': cm_qs.count(), 'color': '#4f46e5', 'sub': 'Community Inquiries'},
            {'label': 'Active Comments', 'value': cm_qs.filter(is_hidden=False).count(), 'color': '#10b981', 'sub': 'Visible Discussions'},
            {'label': 'Hidden Comments', 'value': cm_qs.filter(is_hidden=True).count(), 'color': '#ef4444', 'sub': 'Moderated / Spam'},
        ]
    elif app_label == 'posts' and model_name == 'borrowrequest':
        br_qs = BorrowRequest.objects.all()
        kpis = [
            {'label': 'Total Borrow Requests', 'value': br_qs.count(), 'color': '#4f46e5', 'sub': 'Item Loans Tracked'},
            {'label': 'Pending Approval', 'value': br_qs.filter(status='pending').count(), 'color': '#f59e0b', 'sub': 'Awaiting Owner'},
            {'label': 'Approved & Active', 'value': br_qs.filter(status='accepted').count(), 'color': '#10b981', 'sub': 'Currently Borrowed'},
            {'label': 'Returned Items', 'value': br_qs.filter(status='returned').count(), 'color': '#0284c7', 'sub': 'Loan Completed'},
            {'label': 'Rejected Requests', 'value': br_qs.filter(status='rejected').count(), 'color': '#ef4444', 'sub': 'Declined'},
        ]
    elif app_label == 'study' and model_name == 'studyresource':
        st_qs = StudyResource.objects.all()
        kpis = [
            {'label': 'Total Resources', 'value': st_qs.count(), 'color': '#8b5cf6', 'sub': 'Academic Files'},
            {'label': 'Handwritten Notes', 'value': st_qs.filter(resource_type='notes').count(), 'color': '#4f46e5', 'sub': 'Class Notes'},
            {'label': 'PYQs Papers', 'value': st_qs.filter(resource_type='pyq').count(), 'color': '#0284c7', 'sub': 'Past Exams'},
            {'label': 'Books & Guides', 'value': st_qs.filter(resource_type='book').count(), 'color': '#10b981', 'sub': 'Reference Texts'},
            {'label': 'Total Downloads', 'value': st_qs.aggregate(d=Sum('downloads_count'))['d'] or 0, 'color': '#f59e0b', 'sub': 'Student Downloads'},
        ]
    elif app_label == 'notices' and model_name == 'notice':
        nt_qs = Notice.objects.all()
        kpis = [
            {'label': 'Total Notices', 'value': nt_qs.count(), 'color': '#4f46e5', 'sub': 'Circulars Published'},
            {'label': 'Active Notices', 'value': nt_qs.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Live on Notice Board'},
            {'label': 'Urgent Priority', 'value': nt_qs.filter(is_active=True, priority='urgent').count(), 'color': '#ef4444', 'sub': 'High Importance'},
            {'label': 'Important Notices', 'value': nt_qs.filter(is_active=True, priority='important').count(), 'color': '#f59e0b', 'sub': 'Priority Circulars'},
        ]
    elif app_label == 'events' and model_name == 'event':
        ev_qs = Event.objects.all()
        kpis = [
            {'label': 'Total Events', 'value': ev_qs.count(), 'color': '#f59e0b', 'sub': 'Campus Activities'},
            {'label': 'Upcoming Events', 'value': ev_qs.filter(is_active=True, event_date__gte=today).count(), 'color': '#10b981', 'sub': 'Future Dates'},
            {'label': 'Active Events', 'value': ev_qs.filter(is_active=True).count(), 'color': '#0284c7', 'sub': 'Published'},
            {'label': 'Past / Completed', 'value': ev_qs.filter(event_date__lt=today).count(), 'color': '#64748b', 'sub': 'Concluded Events'},
        ]
    elif app_label == 'services' and model_name == 'hostelservice':
        sv_qs = HostelService.objects.all()
        kpis = [
            {'label': 'Total Services', 'value': sv_qs.count(), 'color': '#4f46e5', 'sub': 'Campus Vendors'},
            {'label': 'Active Services', 'value': sv_qs.filter(is_active=True).count(), 'color': '#10b981', 'sub': 'Listed & Available'},
            {'label': 'Service Types', 'value': sv_qs.values('category').distinct().count(), 'color': '#7c3aed', 'sub': 'Categories'},
        ]
    elif app_label == 'notifications' and model_name == 'notification':
        nf_qs = Notification.objects.all()
        kpis = [
            {'label': 'Total Notifications', 'value': nf_qs.count(), 'color': '#4f46e5', 'sub': 'Alerts Sent'},
            {'label': 'Unread Notifications', 'value': nf_qs.filter(is_read=False).count(), 'color': '#f59e0b', 'sub': 'Pending Student Read'},
            {'label': 'Read Notifications', 'value': nf_qs.filter(is_read=True).count(), 'color': '#10b981', 'sub': 'Acknowledged'},
        ]
    elif app_label == 'moderation' and model_name == 'report':
        rp_qs = Report.objects.all()
        kpis = [
            {'label': 'Total Reports', 'value': rp_qs.count(), 'color': '#ef4444', 'sub': 'Complaints Filed'},
            {'label': 'Pending Action', 'value': rp_qs.filter(status='pending').count(), 'color': '#dc2626', 'sub': 'Requires Triage'},
            {'label': 'In Review', 'value': rp_qs.filter(status='reviewing').count(), 'color': '#f59e0b', 'sub': 'Under Investigation'},
            {'label': 'Resolved Reports', 'value': rp_qs.filter(status='resolved').count(), 'color': '#10b981', 'sub': 'Action Taken'},
            {'label': 'Dismissed', 'value': rp_qs.filter(status='dismissed').count(), 'color': '#64748b', 'sub': 'Invalid / Closed'},
        ]
    elif app_label == 'moderation' and model_name == 'feedback':
        fb_qs = Feedback.objects.all()
        kpis = [
            {'label': 'Total Feedback', 'value': fb_qs.count(), 'color': '#4f46e5', 'sub': 'User Submissions'},
            {'label': 'Pending Feedback', 'value': fb_qs.filter(status='pending').count(), 'color': '#f59e0b', 'sub': 'Unreviewed'},
            {'label': 'Resolved', 'value': fb_qs.filter(status='resolved').count(), 'color': '#10b981', 'sub': 'Addressed'},
        ]
    elif app_label == 'gaming' and model_name == 'gamingprofile':
        try:
            from gaming.models import GamingProfile
            g_qs = GamingProfile.objects.all()
            kpis = [
                {'label': 'Total Gamers', 'value': g_qs.count(), 'color': '#8b5cf6', 'sub': 'Registered Profiles'},
                {'label': 'Grandmasters', 'value': g_qs.filter(br_rank__icontains='Grandmaster').count(), 'color': '#f59e0b', 'sub': 'Top Tier Rank 👑'},
                {'label': 'Verified Players', 'value': g_qs.filter(is_verified=True).count(), 'color': '#10b981', 'sub': 'UID Verified'},
                {'label': 'Avg K/D Ratio', 'value': round(g_qs.aggregate(kd=Sum('kd_ratio'))['kd'] / (g_qs.count() or 1), 2), 'color': '#0284c7', 'sub': 'Skill Metric'},
            ]
        except Exception:
            pass
    elif app_label == 'gaming' and model_name == 'tournament':
        try:
            from gaming.models import Tournament
            t_qs = Tournament.objects.all()
            kpis = [
                {'label': 'Total Matches', 'value': t_qs.count(), 'color': '#8b5cf6', 'sub': 'Custom Rooms'},
                {'label': 'Upcoming Matches', 'value': t_qs.filter(status='upcoming').count(), 'color': '#f59e0b', 'sub': 'Scheduled'},
                {'label': 'Live Rooms', 'value': t_qs.filter(status='live').count(), 'color': '#ef4444', 'sub': 'Playing Now 🔥'},
                {'label': 'Completed', 'value': t_qs.filter(status='completed').count(), 'color': '#10b981', 'sub': 'Finished'},
            ]
        except Exception:
            pass

    return kpis