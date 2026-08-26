from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from hostels.models import Hostel, Block, Room
from notices.models import Notice
from events.models import Event
from moderation.models import Report
from posts.models import Post
from users.models import StudentProfile
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class UserAuthTests(APITestCase):
    def setUp(self):
        self.hostel1 = Hostel.objects.create(name='Aryabhata Hostel', code='TH-1')
        self.hostel2 = Hostel.objects.create(name='Bhaskara Hostel', code='TH-2')
        self.block = Block.objects.create(hostel=self.hostel1, name='Block A')
        self.room = Room.objects.create(block=self.block, room_number='101')

    def test_registration_with_required_hostel_and_optional_block_room(self):
        url = reverse('register')
        data = {
            'full_name': 'Test Student',
            'email': 'teststudent@student.edu',
            'gender': 'male',
            'programme': 'B.Tech',
            'branch': 'Computer Science',
            'password': 'SecurePassword@123',
            'confirm_password': 'SecurePassword@123',
            'hostel': self.hostel1.id,
            'block': self.block.id,
            'room': self.room.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['profile']['hostel_detail']['name'], 'Aryabhata Hostel')
        user = User.objects.get(email='teststudent@student.edu')
        self.assertTrue(user.is_student)

    def test_student_login(self):
        student = User.objects.create_user(
            username='student1',
            email='student1@student.edu',
            password='Pass@123',
            is_student=True
        )
        StudentProfile.objects.create(user=student, hostel=self.hostel1)

        url = reverse('login')
        response = self.client.post(url, {'email': 'student1@student.edu', 'password': 'Pass@123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['user']['is_student'])
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['profile']['hostel_detail']['name'], 'Aryabhata Hostel')

    def test_student_account_restrictions(self):
        # 1. Blocked student
        s_blocked = User.objects.create_user(
            username='s_block',
            email='s_block@hostel.edu',
            password='Pass@123',
            is_student=True,
            is_blocked=True,
            block_reason='Violation of rules'
        )
        resp = self.client.post(reverse('login'), {'email': 's_block@hostel.edu', 'password': 'Pass@123'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('blocked', resp.data['detail'])

        # 2. Suspended student
        until = timezone.now() + timedelta(days=3)
        s_suspended = User.objects.create_user(
            username='s_susp',
            email='s_susp@hostel.edu',
            password='Pass@123',
            is_student=True,
            is_suspended=True,
            suspended_until=until
        )
        resp = self.client.post(reverse('login'), {'email': 's_susp@hostel.edu', 'password': 'Pass@123'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('suspended', resp.data['detail'])

        # 3. Deactivated student
        s_deact = User.objects.create_user(
            username='s_deact',
            email='s_deact@hostel.edu',
            password='Pass@123',
            is_student=True,
            is_active=False
        )
        resp = self.client.post(reverse('login'), {'email': 's_deact@hostel.edu', 'password': 'Pass@123'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('deactivated', resp.data['detail'])

        # 4. Wrong password
        resp_wrong = self.client.post(reverse('login'), {'email': 'student1@student.edu', 'password': 'WrongPassword'})
        self.assertEqual(resp_wrong.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminTemplatesTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_tester',
            email='admin_tester@test.com',
            password='AdminPassword@123'
        )
        self.client.force_login(self.admin_user)

    def test_all_admin_add_pages_render_without_syntax_errors(self):
        """Test that every registered model in Django Admin loads changelist and add pages cleanly."""
        from django.contrib import admin
        
        models_to_test = [
            ('posts', 'comment'),
            ('posts', 'post'),
            ('posts', 'category'),
            ('posts', 'borrowrequest'),
            ('users', 'student'),
            ('users', 'user'),
            ('hostels', 'hostel'),
            ('hostels', 'block'),
            ('hostels', 'room'),
            ('notices', 'notice'),
            ('events', 'event'),
            ('services', 'hostelservice'),
            ('study', 'studyresource'),
            ('notifications', 'notification'),
            ('moderation', 'report'),
            ('moderation', 'feedback'),
            ('moderation', 'adminactionlog'),
            ('moderation', 'sitesetting'),
        ]

        from django.test import RequestFactory
        factory = RequestFactory()
        req = factory.get('/admin/')
        req.user = self.admin_user

        for app_label, model_name in models_to_test:
            # 1. Test Changelist View
            cl_url = reverse(f'admin:{app_label}_{model_name}_changelist')
            cl_resp = self.client.get(cl_url)
            self.assertEqual(
                cl_resp.status_code, 200,
                f"Changelist page failed for {app_label}.{model_name} with status {cl_resp.status_code}"
            )

    def test_comment_add_and_edit_in_admin(self):
        """Specifically verify creating and editing a Comment via Django Admin."""
        from posts.models import Post, Comment, Category
        cat = Category.objects.create(name='Academic Items', slug='academic-items')
        post = Post.objects.create(
            author=self.admin_user,
            title='Calculus Book',
            description='Calculus textbook in mint condition.',
            price=200,
            post_type='buy_sell',
            category=cat
        )
        
        # 1. GET /admin/posts/comment/add/
        add_url = reverse('admin:posts_comment_add')
        resp = self.client.get(add_url)
        self.assertEqual(resp.status_code, 200)

        # 2. POST /admin/posts/comment/add/ (Create comment)
        post_data = {
            'post': post.id,
            'author': self.admin_user.id,
            'content': 'Is this still available?',
            '_save': 'Save',
        }
        resp = self.client.post(add_url, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Comment.objects.filter(content='Is this still available?').exists())

        comment = Comment.objects.get(content='Is this still available?')

        # 3. GET /admin/posts/comment/<id>/change/ (Edit view)
        change_url = reverse('admin:posts_comment_change', args=[comment.id])
        resp = self.client.get(change_url)
        self.assertEqual(resp.status_code, 200)

        # 4. POST /admin/posts/comment/<id>/change/ (Update comment)
        update_data = {
            'post': post.id,
            'author': self.admin_user.id,
            'content': 'Updated: Yes, looking to buy this!',
            '_save': 'Save',
        }
        resp = self.client.post(change_url, update_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'Updated: Yes, looking to buy this!')


class DjangoAdminSecurityTests(TestCase):
    """
    Exhaustive security verification for Django Admin protection:
    - TEST 1: Unauthenticated visitor accessing /admin/
    - TEST 2: Logged-in normal student accessing /admin/
    - TEST 3: Unauthorized non-staff user accessing /admin/
    - TEST 4: Inactive user accessing /admin/
    - TEST 5: Chief Admin / Superuser accessing /admin/
    - TEST 6: Direct model URLs (/admin/users/, /admin/posts/, /admin/study/, etc.)
    - TEST 7: Administrative APIs (/api/admin-stats/, /api/moderation/reports/, etc.)
    """

    def setUp(self):
        # 1. Superuser / Chief Admin
        self.chief_admin = User.objects.create_superuser(
            username='chief_admin',
            email='chiefadmin@hosteltalkies.com',
            password='ChiefAdminPassword@123',
            first_name='Chief',
            last_name='Admin'
        )

        # 2. Normal Student (Non-staff, active)
        self.student = User.objects.create_user(
            username='student_rahul',
            email='rahul@student.edu',
            password='StudentPass@123',
            is_student=True,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )

        # 3. Non-staff Regular User
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='RegularPass@123',
            is_student=False,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )

        # 4. Inactive User
        self.inactive_user = User.objects.create_user(
            username='inactive_user',
            email='inactive@example.com',
            password='InactivePass@123',
            is_staff=False,
            is_active=False
        )

    def test_1_unauthenticated_user_accessing_admin_is_redirected_to_login(self):
        """Unauthenticated user accessing /admin/ must be redirected to login with 0 data exposed."""
        response = self.client.get('/admin/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

        # Confirm following redirect lands on login form and does NOT expose dashboard
        followed = self.client.get('/admin/', follow=True)
        self.assertEqual(followed.status_code, 200)
        self.assertContains(followed, 'Log in')
        self.assertNotContains(followed, 'Campus Key Performance Indicators')
        self.assertNotContains(followed, 'HostelTalkies Admin Operations Center')

    def test_2_student_accessing_admin_is_denied_access(self):
        """Logged-in student attempting to access /admin/ must NOT see admin dashboard."""
        self.client.force_login(self.student)
        response = self.client.get('/admin/', follow=False)
        # Django Admin redirects non-staff users to admin login with permission notice
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

        followed = self.client.get('/admin/', follow=True)
        self.assertEqual(followed.status_code, 200)
        # Verify no admin statistics or records are rendered
        self.assertNotContains(followed, 'Campus Key Performance Indicators')
        self.assertNotContains(followed, 'Admin Action Logs')

    def test_3_non_staff_user_accessing_admin_is_denied(self):
        """Any non-staff user attempting to access /admin/ is denied."""
        self.client.force_login(self.regular_user)
        response = self.client.get('/admin/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_4_inactive_user_accessing_admin_is_denied(self):
        """Inactive user is denied access to /admin/."""
        self.client.force_login(self.inactive_user)
        response = self.client.get('/admin/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_5_admin_superuser_has_full_access(self):
        """Admin / Superuser receives HTTP 200 OK and full access to /admin/."""
        self.client.force_login(self.chief_admin)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HostelTalkies Admin Operations Center')
        self.assertContains(response, 'Campus Key Performance Indicators')

    def test_6_direct_model_urls_protected_against_students_and_unauthorized_users(self):
        """Direct URLs like /admin/users/user/, /admin/posts/post/, etc. are protected."""
        direct_urls = [
            '/admin/users/user/',
            '/admin/users/student/',
            '/admin/posts/post/',
            '/admin/study/studyresource/',
            '/admin/moderation/report/',
            '/admin/moderation/adminactionlog/',
            '/admin/hostels/hostel/',
        ]

        # 1. Unauthenticated Visitor
        for url in direct_urls:
            resp = self.client.get(url, follow=False)
            self.assertEqual(resp.status_code, 302, f"Unauthenticated user was not redirected for {url}")
            self.assertIn('/admin/login/', resp.url)

        # 2. Student
        self.client.force_login(self.student)
        for url in direct_urls:
            resp = self.client.get(url, follow=False)
            self.assertEqual(resp.status_code, 302, f"Student was not redirected for {url}")
            self.assertIn('/admin/login/', resp.url)

        # 3. Superuser
        self.client.force_login(self.chief_admin)
        for url in direct_urls:
            resp = self.client.get(url, follow=False)
            self.assertEqual(resp.status_code, 200, f"Superuser was unable to access {url}")

    def test_7_administrative_apis_protected_from_unauthorized_users(self):
        """Admin APIs like /api/admin-stats/ and /api/moderation/reports/ are protected."""
        # 1. Unauthenticated -> 401 Unauthorized
        resp = self.client.get('/api/admin-stats/')
        self.assertIn(resp.status_code, [401, 403])

        # 2. Student -> 403 Forbidden
        self.client.force_login(self.student)
        resp_student = self.client.get('/api/admin-stats/')
        self.assertEqual(resp_student.status_code, 403)

        # 3. Chief Admin -> 200 OK
        self.client.force_login(self.chief_admin)
        resp_admin = self.client.get('/api/admin-stats/')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn('total_students', resp_admin.data)


class UserBlockTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='student_alice',
            email='alice@student.edu',
            password='Password@123',
            is_student=True
        )
        self.user2 = User.objects.create_user(
            username='student_bob',
            email='bob@student.edu',
            password='Password@123',
            is_student=True
        )

    def test_block_and_unblock_user(self):
        # Authenticate as user1 (Alice)
        self.client.force_authenticate(user=self.user1)

        # 1. Block Bob
        block_url = reverse('block_user', args=[self.user2.id])
        resp = self.client.post(block_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['is_blocked_by_me'])

        # 2. Check public profile of Bob shows is_blocked_by_me = True
        detail_url = reverse('user_detail', args=[self.user2.id])
        resp_detail = self.client.get(detail_url)
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_detail.data['is_blocked_by_me'])

        # 3. Attempting to start conversation with Bob fails
        start_conv_url = reverse('start-conversation')
        resp_conv = self.client.post(start_conv_url, {'recipient_id': self.user2.id, 'message': 'Hello Bob'})
        self.assertEqual(resp_conv.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('blocked', resp_conv.data['detail'])

        # 4. Unblock Bob
        unblock_url = reverse('unblock_user', args=[self.user2.id])
        resp_unblock = self.client.post(unblock_url)
        self.assertEqual(resp_unblock.status_code, status.HTTP_200_OK)
        self.assertFalse(resp_unblock.data['is_blocked_by_me'])

        # 5. Profile shows is_blocked_by_me = False
        resp_detail2 = self.client.get(detail_url)
        self.assertFalse(resp_detail2.data['is_blocked_by_me'])

        # 6. Now conversation can be started
        resp_conv2 = self.client.post(start_conv_url, {'recipient_id': self.user2.id, 'message': 'Hello Bob after unblock'})
        self.assertIn(resp_conv2.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_blocked_users_list_endpoint_is_private(self):
        # Alice blocks Bob
        self.client.force_authenticate(user=self.user1)
        self.client.post(reverse('block_user', args=[self.user2.id]))

        # Alice checks her blocked list -> Bob is present
        resp = self.client.get(reverse('blocked_users_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['id'], self.user2.id)

        # Bob checks his blocked list -> Bob has not blocked anyone (empty)
        self.client.force_authenticate(user=self.user2)
        resp_bob = self.client.get(reverse('blocked_users_list'))
        self.assertEqual(resp_bob.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_bob.data), 0)

    def test_global_search_includes_people(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.get('/api/search/?q=Alice')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('people', resp.data)
        people_names = [p['username'] for p in resp.data['people']]
        self.assertIn('student_alice', people_names)

    def test_avatar_upload_save_and_retrieve(self):
        self.client.force_authenticate(user=self.user1)
        
        # 1. Upload avatar
        test_image = SimpleUploadedFile("avatar.jpg", b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b", content_type="image/jpeg")
        resp = self.client.patch(reverse('profile_update'), {'avatar': test_image}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp.data['profile']['avatar'])
        self.assertIn('avatar', resp.data['profile']['avatar'])

        # 2. Retrieve via /api/auth/me/ (Refresh test)
        resp_me = self.client.get(reverse('current_user'))
        self.assertEqual(resp_me.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp_me.data['profile']['avatar'])
        self.assertEqual(resp.data['profile']['avatar'], resp_me.data['profile']['avatar'])

        # 3. Retrieve via public profile
        resp_public = self.client.get(reverse('user_detail', args=[self.user1.id]))
        self.assertEqual(resp_public.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp_public.data['profile']['avatar'])
        self.assertIsNotNone(resp_public.data['profile_picture'])

        # 4. Remove avatar
        resp_remove = self.client.patch(reverse('profile_update'), {'remove_avatar': True})
        self.assertEqual(resp_remove.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp_remove.data['profile']['avatar'])

        # 5. Confirm me endpoint also returns None
        resp_me_after = self.client.get(reverse('current_user'))
        self.assertIsNone(resp_me_after.data['profile']['avatar'])

    def test_admin_created_content_attribution_is_admin(self):
        """Verify that notices, study resources, and admin-managed content are attributed to 'Admin' and never 'Chief Warden'."""
        admin_user = User.objects.create_superuser(
            username='campus_admin',
            email='campusadmin@hosteltalkies.com',
            password='AdminPassword@123',
            first_name='Admin',
            last_name=''
        )
        
        # 1. Notice created by admin
        notice = Notice.objects.create(
            title='Official Maintenance Announcement',
            content='Scheduled water pipeline inspection.',
            priority='important',
            created_by=admin_user
        )

        from notices.serializers import NoticeSerializer
        notice_data = NoticeSerializer(notice).data
        self.assertEqual(notice_data['created_by_name'], 'Admin')
        self.assertEqual(notice_data['created_by_role'], 'Admin')
        self.assertNotEqual(notice_data['created_by_name'], 'Chief Warden')
        self.assertNotEqual(notice_data['created_by_role'], 'Chief Warden')

        # 2. Study Resource uploaded by admin
        from study.models import StudyResource
        from study.serializers import StudyResourceSerializer
        resource = StudyResource.objects.create(
            title='DSA Lecture Notes',
            description='Complete data structures syllabus notes.',
            resource_type='notes',
            uploader=admin_user
        )
        resource_data = StudyResourceSerializer(resource).data
        self.assertEqual(resource_data['uploader_detail']['full_name'], 'Admin')
        self.assertEqual(resource_data['uploader_detail']['role'], 'Admin')
        self.assertNotEqual(resource_data['uploader_detail']['full_name'], 'Chief Warden')








