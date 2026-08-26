from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from hostels.models import Hostel
from posts.models import Post, Category, Like, Comment
from users.models import StudentProfile

User = get_user_model()

class PostAndCommunityTests(APITestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name='Alpha Hostel', code='AH-1')
        self.user1 = User.objects.create_user(username='student1', email='student1@hostel.edu', password='PassWord@123')
        StudentProfile.objects.create(user=self.user1, hostel=self.hostel)
        
        self.user2 = User.objects.create_user(username='student2', email='student2@hostel.edu', password='PassWord@123')
        StudentProfile.objects.create(user=self.user2, hostel=self.hostel)

        self.category = Category.objects.create(name='Electronics', icon='laptop')

    def test_post_creation_and_ownership(self):
        login_res = self.client.post(reverse('login'), {'email': 'student1@hostel.edu', 'password': 'PassWord@123'})
        token1 = login_res.data['tokens']['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        create_res = self.client.post('/api/posts/', {
            'title': 'Selling Gaming Mouse',
            'description': 'RGB gaming mouse with high DPI.',
            'post_type': 'buy_sell',
            'price': '450.00',
            'condition': 'like_new',
            'category': self.category.id
        })
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        post_id = create_res.data['id']

        # User 2 tries to edit User 1's post (should fail with 403)
        login_res2 = self.client.post(reverse('login'), {'email': 'student2@hostel.edu', 'password': 'PassWord@123'})
        token2 = login_res2.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        edit_res = self.client.patch(f'/api/posts/{post_id}/', {'title': 'Hacked Title'})
        self.assertEqual(edit_res.status_code, status.HTTP_403_FORBIDDEN)

        # User 2 likes the post
        like_res = self.client.post(f'/api/posts/{post_id}/toggle_like/')
        self.assertEqual(like_res.status_code, status.HTTP_200_OK)
        self.assertTrue(like_res.data['liked'])

        # User 2 adds a comment
        comment_res = self.client.post(f'/api/posts/{post_id}/add_comment/', {'content': 'Is this still available?'})
        self.assertEqual(comment_res.status_code, status.HTTP_201_CREATED)
