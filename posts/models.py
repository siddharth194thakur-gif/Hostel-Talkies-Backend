from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class Category(models.Model):
    POST_TYPE_ASSOCIATION = [
        ('all', 'All Post Types'),
        ('marketplace', 'Buy, Sell, Giveaway, Exchange, Borrow'),
        ('lost_found', 'Lost & Found'),
        ('study', 'Study & Academics'),
        ('services', 'Hostel Services'),
        ('roommate', 'Room / Roommate'),
        ('general', 'General Community'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='tag', help_text='Icon identifier e.g. bicycle, laptop, book, shirt')
    post_type = models.CharField(max_length=30, choices=POST_TYPE_ASSOCIATION, default='all')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(models.Model):
    POST_TYPE_CHOICES = [
        ('buy_sell', 'Buy & Sell'),
        ('giveaway', 'Giveaway (Free)'),
        ('exchange', 'Exchange / Barter'),
        ('borrow', 'Borrow Request'),
        ('lend', 'Lend Offer'),
        ('lost', 'Lost Item'),
        ('found', 'Found Item'),
        ('roommate', 'Room / Roommate'),
        ('study', 'Study Discussion'),
        ('help', 'Help / Query'),
        ('service', 'Service Announcement'),
        ('general', 'General Talkies'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Brand New'),
        ('like_new', 'Like New / Barely Used'),
        ('good', 'Good Condition'),
        ('used', 'Used / Fair'),
        ('na', 'Not Applicable'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available / Open'),
        ('sold', 'Sold / Taken'),
        ('closed', 'Closed / Resolved'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    block = models.ForeignKey('hostels.Block', on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    
    post_type = models.CharField(max_length=30, choices=POST_TYPE_CHOICES, default='general')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Leave empty or 0 for free/giveaway/lost items')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='na')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Lost & Found / Location details
    location = models.CharField(max_length=150, blank=True, default='')
    event_date = models.DateField(null=True, blank=True, help_text='Date when item was lost/found or needed')
    
    # Moderation & Visibility
    is_hidden = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_post_type_display()}] {self.title} by {self.author.email}"


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts/')
    caption = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Post #{self.post_id}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user.email} liked Post #{self.post_id}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField()
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on Post #{self.post_id}"


class SavedPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user.email} saved Post #{self.post_id}"


class BorrowRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('accepted', 'Accepted / Active Borrow'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='borrow_requests')
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrow_requests_sent')
    return_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Borrow Request by {self.borrower.email} for Post #{self.post_id} ({self.status})"
