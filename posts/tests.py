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

        # User 2 tries to add a public comment to marketplace post (should be rejected with 400)
        comment_res = self.client.post(f'/api/posts/{post_id}/add_comment/', {'content': 'Is this still available?'})
        self.assertEqual(comment_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Public comments are disabled for marketplace listings", comment_res.data['detail'])

        # Detail view returns empty comments for marketplace post
        detail_res = self.client.get(f'/api/posts/{post_id}/')
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data['comments'], [])
        self.assertEqual(detail_res.data['comments_count'], 0)

    def test_marketplace_security_validations(self):
        login_res = self.client.post(reverse('login'), {'email': 'student1@hostel.edu', 'password': 'PassWord@123'})
        token = login_res.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 1. Custom category is rejected
        res = self.client.post('/api/posts/', {
            'title': 'Test Item',
            'description': 'Description',
            'post_type': 'buy_sell',
            'custom_category': 'My Random Custom Category',
            'price': '100'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('custom_category', res.data)

        # 2. Marketplace post without category is rejected
        res2 = self.client.post('/api/posts/', {
            'title': 'Test Item',
            'description': 'Description',
            'post_type': 'buy_sell',
            'price': '100'
        })
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', res2.data)

        # 3. Marketplace post with inactive category is rejected
        inactive_cat = Category.objects.create(name='Old Category', is_active=False)
        res3 = self.client.post('/api/posts/', {
            'title': 'Test Item',
            'description': 'Description',
            'post_type': 'buy_sell',
            'category': inactive_cat.id,
            'price': '100'
        })
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', res3.data)

        # 4. Description > 1000 characters is rejected
        res4 = self.client.post('/api/posts/', {
            'title': 'Test Item',
            'description': 'X' * 1001,
            'post_type': 'buy_sell',
            'category': self.category.id,
            'price': '100'
        })
        self.assertEqual(res4.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('description', res4.data)

        # 5. HTML tags are stripped from title and description
        res5 = self.client.post('/api/posts/', {
            'title': '<script>alert("hack")</script>Clean Title',
            'description': '<p>Valid text with <b>HTML</b></p>',
            'post_type': 'buy_sell',
            'category': self.category.id,
            'price': '100'
        })
        self.assertEqual(res5.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res5.data['title'], 'Clean Title')
        self.assertNotIn('<p>', res5.data['description'])
        self.assertNotIn('<b>', res5.data['description'])

        # 6. Non-marketplace post (e.g. general) allows comments
        res6 = self.client.post('/api/posts/', {
            'title': 'General Campus Discussion',
            'description': 'Who wants to play cricket this evening?',
            'post_type': 'general',
            'category': self.category.id
        })
        self.assertEqual(res6.status_code, status.HTTP_201_CREATED)
        gen_post_id = res6.data['id']

        comment_res = self.client.post(f'/api/posts/{gen_post_id}/add_comment/', {'content': 'I am in!'})
        self.assertEqual(comment_res.status_code, status.HTTP_201_CREATED)
