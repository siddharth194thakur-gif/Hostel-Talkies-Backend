from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F
from .models import Category, Post, PostImage, Like, Comment, SavedPost, BorrowRequest
from .serializers import (
    CategorySerializer, PostListSerializer, PostDetailSerializer,
    PostCreateUpdateSerializer, CommentSerializer, BorrowRequestSerializer
)
from users.permissions import IsNotBlockedOrSuspended, IsOwnerOrReadOnly, IsAdminOrReadOnly
from notifications.models import Notification

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True).order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Category.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(is_active=True)
        post_type = self.request.query_params.get('post_type')
        if post_type:
            queryset = queryset.filter(Q(post_type=post_type) | Q(post_type='all'))
        return queryset.order_by('name')


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsNotBlockedOrSuspended, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        queryset = Post.objects.filter(is_deleted=False)
        
        # Non-staff cannot see hidden posts unless they are the author
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            if self.request.user.is_authenticated:
                queryset = queryset.filter(Q(is_hidden=False) | Q(author=self.request.user))
            else:
                queryset = queryset.filter(is_hidden=False)

        # Filters
        post_type = self.request.query_params.get('post_type')
        if post_type:
            if post_type == 'marketplace':
                queryset = queryset.filter(post_type__in=['buy_sell', 'giveaway', 'exchange', 'borrow', 'lend'])
            elif post_type == 'lost_found':
                queryset = queryset.filter(post_type__in=['lost', 'found'])
            else:
                queryset = queryset.filter(post_type=post_type)

        category = self.request.query_params.get('category')
        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=category)
            else:
                queryset = queryset.filter(category__slug=category)

        hostel = self.request.query_params.get('hostel')
        if hostel:
            queryset = queryset.filter(hostel_id=hostel)

        block = self.request.query_params.get('block')
        if block:
            queryset = queryset.filter(block_id=block)

        condition = self.request.query_params.get('condition')
        if condition:
            queryset = queryset.filter(condition=condition)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )

        my_posts = self.request.query_params.get('my_posts')
        if my_posts and self.request.user.is_authenticated:
            queryset = queryset.filter(author=self.request.user)

        author_param = self.request.query_params.get('author')
        if author_param:
            queryset = queryset.filter(author_id=author_param)

        saved = self.request.query_params.get('saved')
        if saved and self.request.user.is_authenticated:
            saved_post_ids = SavedPost.objects.filter(user=self.request.user).values_list('post_id', flat=True)
            queryset = queryset.filter(id__in=saved_post_ids)

        return queryset.select_related('author', 'category', 'hostel', 'block').prefetch_related('images', 'likes', 'comments')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment views atomically
        Post.objects.filter(id=instance.id).update(views_count=F('views_count') + 1)
        instance.views_count += 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsNotBlockedOrSuspended])
    def toggle_like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({'liked': False, 'likes_count': post.likes.count()})
        else:
            # Create notification for author if not liking own post
            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='like',
                    title='New Like',
                    message=f"{request.user.get_full_name() or request.user.username} liked your post '{post.title[:30]}'",
                    link=f"/posts/{post.id}"
                )
            return Response({'liked': True, 'likes_count': post.likes.count()})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsNotBlockedOrSuspended])
    def toggle_save(self, request, pk=None):
        post = self.get_object()
        saved, created = SavedPost.objects.get_or_create(post=post, user=request.user)
        if not created:
            saved.delete()
            return Response({'saved': False})
        return Response({'saved': True})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsNotBlockedOrSuspended])
    def add_comment(self, request, pk=None):
        post = self.get_object()
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': 'Comment content cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = Comment.objects.create(post=post, author=request.user, content=content)
        
        # Notify author
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='comment',
                title='New Comment',
                message=f"{request.user.get_full_name() or request.user.username} commented on '{post.title[:30]}'",
                link=f"/posts/{post.id}"
            )

        return Response(CommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsNotBlockedOrSuspended])
    def request_borrow(self, request, pk=None):
        post = self.get_object()
        if post.author == request.user:
            return Response({'detail': 'You cannot borrow your own item.'}, status=status.HTTP_400_BAD_REQUEST)
        
        return_date = request.data.get('return_date')
        note = request.data.get('note', '')

        borrow_req, created = BorrowRequest.objects.get_or_create(
            post=post,
            borrower=request.user,
            defaults={'return_date': return_date, 'note': note, 'status': 'pending'}
        )
        if not created:
            borrow_req.return_date = return_date
            borrow_req.note = note
            borrow_req.status = 'pending'
            borrow_req.save()

        # Notify post owner
        Notification.objects.create(
            recipient=post.author,
            sender=request.user,
            notification_type='borrow_request',
            title='Borrow Request',
            message=f"{request.user.get_full_name() or request.user.username} requested to borrow '{post.title[:30]}'",
            link=f"/posts/{post.id}"
        )

        return Response(BorrowRequestSerializer(borrow_req).data, status=status.HTTP_200_OK)


class CommentDetailView(generics.DestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def perform_destroy(self, instance):
        instance.delete()


class BorrowRequestUpdateView(generics.UpdateAPIView):
    queryset = BorrowRequest.objects.all()
    serializer_class = BorrowRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlockedOrSuspended]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Only post owner can accept/reject; borrower or owner can mark returned
        new_status = request.data.get('status')
        if new_status in ['accepted', 'rejected'] and instance.post.author != request.user and not request.user.is_staff:
            return Response({'detail': 'Only the item owner can accept or reject requests.'}, status=status.HTTP_403_FORBIDDEN)
        
        if new_status == 'returned' and instance.post.author != request.user and instance.borrower != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        instance.status = new_status
        instance.save()

        # Notify borrower
        if instance.post.author == request.user:
            Notification.objects.create(
                recipient=instance.borrower,
                sender=request.user,
                notification_type='borrow_request',
                title=f'Borrow Request {new_status.capitalize()}',
                message=f"Your borrow request for '{instance.post.title[:30]}' was updated to {new_status}.",
                link=f"/posts/{instance.post.id}"
            )

        return Response(BorrowRequestSerializer(instance).data)
