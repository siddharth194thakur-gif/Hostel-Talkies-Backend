from rest_framework import serializers
from .models import Category, Post, PostImage, Like, Comment, SavedPost, BorrowRequest
from users.serializers import UserPublicSerializer
from hostels.serializers import HostelSerializer, BlockSerializer

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


class PostListSerializer(serializers.ModelSerializer):
    author_detail = UserPublicSerializer(source='author', read_only=True)
    category_name = serializers.ReadOnlyField(source='category.name')
    hostel_name = serializers.ReadOnlyField(source='hostel.name')
    block_name = serializers.ReadOnlyField(source='block.name')
    images = PostImageSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
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
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
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
        comments = obj.comments.filter(is_hidden=False).order_by('created_at')
        return CommentSerializer(comments, many=True, context=self.context).data

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
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = [
            'id', 'post_type', 'category', 'title', 'description',
            'price', 'condition', 'status', 'location', 'event_date',
            'uploaded_images'
        ]

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
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
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        for img in images_data:
            PostImage.objects.create(post=instance, image=img)

        return instance
