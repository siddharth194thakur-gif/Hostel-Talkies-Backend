import re
from rest_framework import serializers
from django.utils.text import slugify
from django.utils.html import strip_tags
from .models import Category, Post, PostImage, Like, Comment, SavedPost, BorrowRequest
from .profanity import validate_clean_content
from users.serializers import UserPublicSerializer
from hostels.serializers import HostelSerializer, BlockSerializer

def sanitize_text(text):
    if not text or not isinstance(text, str):
        return text
    # Strip script and style blocks with their contents completely
    cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining HTML tags
    return strip_tags(cleaned).strip()

class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(source='posts.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'post_type', 'is_active', 'posts_count']


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'caption', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author_detail = UserPublicSerializer(source='author', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_detail', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class BorrowRequestSerializer(serializers.ModelSerializer):
    borrower_detail = UserPublicSerializer(source='borrower', read_only=True)
    post_title = serializers.ReadOnlyField(source='post.title')

    class Meta:
        model = BorrowRequest
        fields = [
            'id', 'post', 'post_title', 'borrower', 'borrower_detail',
            'return_date', 'note', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'borrower', 'created_at', 'updated_at']


MARKETPLACE_POST_TYPES = {'buy_sell', 'giveaway', 'exchange', 'borrow', 'lend'}


class PostListSerializer(serializers.ModelSerializer):
    author_detail = UserPublicSerializer(source='author', read_only=True)
    category_name = serializers.ReadOnlyField(source='category.name')
    hostel_name = serializers.ReadOnlyField(source='hostel.name')
    block_name = serializers.ReadOnlyField(source='block.name')
    images = PostImageSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_detail', 'hostel', 'hostel_name', 'block', 'block_name',
            'post_type', 'category', 'category_name', 'title', 'description',
            'price', 'condition', 'status', 'location', 'event_date',
            'images', 'likes_count', 'comments_count', 'is_liked', 'is_saved',
            'views_count', 'created_at'
        ]

    def get_comments_count(self, obj):
        if obj.post_type in MARKETPLACE_POST_TYPES:
            return 0
        return obj.comments.filter(is_hidden=False).count()

    def get_is_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.likes.filter(user=user).exists()
        return False

    def get_is_saved(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.saved_by.filter(user=user).exists()
        return False


class PostDetailSerializer(serializers.ModelSerializer):
    author_detail = UserPublicSerializer(source='author', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    hostel_detail = HostelSerializer(source='hostel', read_only=True)
    block_detail = BlockSerializer(source='block', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    borrow_requests = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_detail', 'hostel', 'hostel_detail', 'block', 'block_detail',
            'post_type', 'category', 'category_detail', 'title', 'description',
            'price', 'condition', 'status', 'location', 'event_date',
            'images', 'comments', 'borrow_requests', 'likes_count', 'comments_count',
            'is_liked', 'is_saved', 'views_count', 'created_at', 'updated_at'
        ]

    def get_comments(self, obj):
        # Public comments are completely disabled for marketplace listings
        if obj.post_type in MARKETPLACE_POST_TYPES:
            return []
        comments = obj.comments.filter(is_hidden=False).order_by('created_at')
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_comments_count(self, obj):
        if obj.post_type in MARKETPLACE_POST_TYPES:
            return 0
        return obj.comments.filter(is_hidden=False).count()

    def get_borrow_requests(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        # Only post author or the borrower can view borrow requests
        if obj.author == request.user or request.user.is_staff:
            return BorrowRequestSerializer(obj.borrow_requests.all(), many=True).data
        return BorrowRequestSerializer(obj.borrow_requests.filter(borrower=request.user), many=True).data

    def get_is_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.likes.filter(user=user).exists()
        return False

    def get_is_saved(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.saved_by.filter(user=user).exists()
        return False


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    custom_category = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=100
    )

    class Meta:
        model = Post
        fields = [
            'id', 'post_type', 'category', 'custom_category', 'title', 'description',
            'price', 'condition', 'status', 'location', 'event_date',
            'uploaded_images'
        ]

    def validate(self, attrs):
        post_type = attrs.get('post_type') or (self.instance.post_type if self.instance else 'general')
        uploaded_images = attrs.get('uploaded_images', [])
        custom_category = attrs.get('custom_category', '').strip()
        category = attrs.get('category') or (self.instance.category if self.instance else None)
        title = attrs.get('title', '').strip()
        description = attrs.get('description', '').strip()
        location = attrs.get('location', '').strip()

        # 1. Custom category is completely disallowed for students
        if custom_category:
            raise serializers.ValidationError({
                'custom_category': 'Custom categories are disabled. Please choose an approved category from the list.'
            })

        # 2. Public user media uploads are disabled across all post types to ensure campus safety
        if uploaded_images:
            raise serializers.ValidationError({
                'uploaded_images': 'Public photo and video uploads are disabled on community posts to protect student privacy.'
            })

        # 3. Profanity filter check on all user-entered text fields
        if title:
            validate_clean_content(title, 'title')
        if description:
            validate_clean_content(description, 'description')
        if location:
            validate_clean_content(location, 'location')

        # 4. Category-specific field rules
        if post_type in MARKETPLACE_POST_TYPES:
            # Require approved category
            if not category:
                raise serializers.ValidationError({
                    'category': 'Category is required for marketplace listings. Please select an approved category.'
                })
            # Auto-assign title from category name
            attrs['title'] = category.name
            # Location is strictly omitted for marketplace listings
            attrs['location'] = ''
            # Free-text description is omitted for marketplace listings to keep it clean and structured
            attrs['description'] = f"Category: {category.name} | Condition: {attrs.get('condition', 'good').replace('_', ' ').capitalize()} | Availability: {attrs.get('status', 'available').capitalize()}"
            if post_type == 'giveaway':
                attrs['price'] = 0.00
            elif post_type == 'buy_sell':
                price = attrs.get('price')
                if price is None or str(price).strip() == '':
                    raise serializers.ValidationError({'price': 'Price is required for Buy & Sell listings.'})

        elif post_type == 'roommate':
            attrs['price'] = None
            attrs['condition'] = 'na'
            attrs['location'] = ''
            if not title:
                attrs['title'] = 'Roommate & Accommodation Requirement'

        elif post_type in ('lost', 'found'):
            attrs['price'] = None
            attrs['condition'] = 'na'
            if not title:
                if category:
                    attrs['title'] = f"{post_type.capitalize()} Item - {category.name}"
                else:
                    attrs['title'] = f"{post_type.capitalize()} Item Report"

        elif post_type == 'general':
            attrs['price'] = None
            attrs['condition'] = 'na'
            if not title:
                raise serializers.ValidationError({
                    'title': 'Subject/title is required for General Talkies.'
                })
            if description and len(description) > 500:
                raise serializers.ValidationError({
                    'description': f'General Talkies message cannot exceed 500 characters (currently {len(description)}).'
                })
        else:
            if not title:
                raise serializers.ValidationError({
                    'title': 'Post title is required.'
                })

        # 5. Category validation: active and matches section post_type
        if category:
            if not category.is_active:
                raise serializers.ValidationError({
                    'category': 'The selected category is currently inactive. Please choose an active category.'
                })
            # Enforce strict post_type <-> category matching (no cross-category mixing)
            if post_type in MARKETPLACE_POST_TYPES and category.post_type != 'marketplace':
                raise serializers.ValidationError({
                    'category': f'The category "{category.name}" does not belong to Buy & Sell / Marketplace.'
                })
            elif post_type in ['lost', 'found'] and category.post_type != 'lost_found':
                raise serializers.ValidationError({
                    'category': f'The category "{category.name}" does not belong to Lost & Found.'
                })
            elif post_type == 'roommate' and category.post_type != 'roommate':
                raise serializers.ValidationError({
                    'category': f'The category "{category.name}" does not belong to Roommate & Accommodation.'
                })
            elif post_type == 'general' and category.post_type != 'general':
                raise serializers.ValidationError({
                    'category': f'The category "{category.name}" does not belong to General Talkies.'
                })

        # 6. Description length limit (max 1000 chars default)
        if description and len(description) > 1000:
            raise serializers.ValidationError({
                'description': f'Description cannot exceed 1000 characters (currently {len(description)}).'
            })

        # 7. Sanitize text fields against HTML/script injection
        if title:
            attrs['title'] = sanitize_text(title)
        if description:
            attrs['description'] = sanitize_text(description)
        if attrs.get('location'):
            attrs['location'] = sanitize_text(attrs['location'])

        return attrs

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        validated_data.pop('custom_category', None)
        user = self.context['request'].user

        # Set hostel and block from user profile if not explicitly set
        profile = getattr(user, 'profile', None)
        hostel = profile.hostel if profile else None
        block = profile.block if profile else None

        post = Post.objects.create(
            author=user,
            hostel=hostel,
            block=block,
            **validated_data
        )

        for img in images_data:
            PostImage.objects.create(post=post, image=img)

        return post

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        validated_data.pop('custom_category', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        for img in images_data:
            PostImage.objects.create(post=instance, image=img)

        return instance
