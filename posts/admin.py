from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Post, PostImage, Like, Comment, SavedPost, BorrowRequest
from moderation.models import AdminActionLog, Report


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'post_type', 'get_posts_count', 'is_active', 'created_at')
    list_filter = ('post_type', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    def get_posts_count(self, obj):
        count = obj.posts.filter(is_deleted=False).count()
        return format_html('<span class="badge badge-primary">{} Listings</span>', count)
    get_posts_count.short_description = "Active Listings"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'post_type_badge', 'author_display', 'hostel',
        'category', 'price_display', 'status_badge', 'reports_count',
        'views_count', 'created_at'
    )
    list_filter = ('post_type', 'category', 'hostel', 'status', 'condition', 'is_hidden', 'is_deleted', 'created_at')
    search_fields = ('title', 'description', 'author__email', 'author__username', 'location')
    inlines = [PostImageInline, CommentInline]
    actions = ['hide_posts', 'restore_posts', 'soft_delete_posts', 'permanently_delete_posts']

    def post_type_badge(self, obj):
        color_map = {
            'buy_sell': 'badge-primary',
            'giveaway': 'badge-success',
            'exchange': 'badge-purple',
            'borrow': 'badge-warning',
            'lend': 'badge-info',
            'lost': 'badge-danger',
            'found': 'badge-info',
            'roommate': 'badge-purple',
            'study': 'badge-primary',
            'help': 'badge-warning',
            'service': 'badge-info',
            'general': 'badge-secondary',
        }
        badge_cls = color_map.get(obj.post_type, 'badge-secondary')
        return format_html('<span class="badge {}">{}</span>', badge_cls, obj.get_post_type_display().upper())
    post_type_badge.short_description = "Type"

    def author_display(self, obj):
        return obj.author.get_full_name() or obj.author.email
    author_display.short_description = "Seller / Resident"

    def price_display(self, obj):
        if obj.post_type == 'giveaway' or not obj.price:
            return format_html('<span style="font-weight:700; color:#10b981;">FREE</span>')
        return format_html('<span style="font-weight:700; color:#4338ca;">₹{}</span>', obj.price)
    price_display.short_description = "Price"

    def status_badge(self, obj):
        if obj.is_deleted:
            return format_html('<span class="badge badge-danger">DELETED</span>')
        if obj.is_hidden:
            return format_html('<span class="badge badge-warning">HIDDEN</span>')
        if obj.status == 'available':
            return format_html('<span class="badge badge-success">AVAILABLE</span>')
        elif obj.status == 'sold':
            return format_html('<span class="badge badge-info">SOLD</span>')
        return format_html('<span class="badge badge-secondary">{}</span>', obj.status.upper())
    status_badge.short_description = "Status"

    def reports_count(self, obj):
        count = Report.objects.filter(report_type='post', target_id=str(obj.id)).count()
        if count > 0:
            return format_html('<span class="badge badge-danger">{} Reports</span>', count)
        return "-"
    reports_count.short_description = "Reports"

    def hide_posts(self, request, queryset):
        count = queryset.update(is_hidden=True)
        for p in queryset:
            AdminActionLog.objects.create(admin=request.user, action="HIDE_POST", target_type="Post", target_id=str(p.id), notes=f"Hidden post '{p.title}'")
        self.message_user(request, f"Successfully hid {count} post(s).")
    hide_posts.short_description = "Hide selected posts"

    def restore_posts(self, request, queryset):
        count = queryset.update(is_hidden=False, is_deleted=False)
        for p in queryset:
            AdminActionLog.objects.create(admin=request.user, action="RESTORE_POST", target_type="Post", target_id=str(p.id), notes=f"Restored post '{p.title}'")
        self.message_user(request, f"Successfully restored {count} post(s).")
    restore_posts.short_description = "Restore selected posts"

    def soft_delete_posts(self, request, queryset):
        count = queryset.update(is_deleted=True)
        for p in queryset:
            AdminActionLog.objects.create(admin=request.user, action="DELETE_POST", target_type="Post", target_id=str(p.id), notes=f"Deleted post '{p.title}'")
        self.message_user(request, f"Successfully deleted {count} post(s).")
    soft_delete_posts.short_description = "Delete selected posts"

    def permanently_delete_posts(self, request, queryset):
        count = queryset.count()
        for p in queryset:
            AdminActionLog.objects.create(admin=request.user, action="HARD_DELETE_POST", target_type="Post", target_id=str(p.id), notes=f"Purged post '{p.title}'")
        queryset.delete()
        self.message_user(request, f"Permanently deleted {count} post(s).")
    permanently_delete_posts.short_description = "Permanently purge selected posts"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_post_title', 'author', 'content_snippet', 'status_badge', 'created_at')
    list_filter = ('is_hidden', 'created_at')
    search_fields = ('content', 'author__email', 'post__title')
    actions = ['hide_comments', 'restore_comments']

    def get_post_title(self, obj):
        return obj.post.title if obj.post else "-"
    get_post_title.short_description = "Post"

    def content_snippet(self, obj):
        return (obj.content[:60] + "...") if len(obj.content) > 60 else obj.content
    content_snippet.short_description = "Comment Preview"

    def status_badge(self, obj):
        if obj.is_hidden:
            return format_html('<span class="badge badge-danger">HIDDEN</span>')
        return format_html('<span class="badge badge-success">ACTIVE</span>')
    status_badge.short_description = "Status"

    def hide_comments(self, request, queryset):
        queryset.update(is_hidden=True)
    hide_comments.short_description = "Hide selected comments"

    def restore_comments(self, request, queryset):
        queryset.update(is_hidden=False)
    restore_comments.short_description = "Restore selected comments"


@admin.register(BorrowRequest)
class BorrowRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_post_title', 'borrower', 'get_owner', 'return_date', 'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('post__title', 'borrower__email')

    def get_post_title(self, obj):
        return obj.post.title if obj.post else "-"
    get_post_title.short_description = "Item"

    def get_owner(self, obj):
        return obj.post.author.email if obj.post and obj.post.author else "-"
    get_owner.short_description = "Item Owner"

    def status_badge(self, obj):
        map_color = {
            'pending': 'badge-warning',
            'accepted': 'badge-success',
            'rejected': 'badge-danger',
            'returned': 'badge-info',
        }
        cls = map_color.get(obj.status, 'badge-secondary')
        return format_html('<span class="badge {}">{}</span>', cls, obj.status.upper())
    status_badge.short_description = "Loan Status"