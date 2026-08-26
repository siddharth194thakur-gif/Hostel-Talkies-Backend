from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from .models import StudyResource
from hostels.models import Hostel, Block, Room

User = get_user_model()

class StudyResourceTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='AdminPassword@123'
        )
        self.student_user = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='StudentPassword@123',
            is_student=True
        )
        self.client = Client()

    def test_admin_changelist_loads_cleanly(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:study_studyresource_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Study Notes & PYQs')

    def test_admin_add_study_resource(self):
        self.client.force_login(self.admin_user)
        add_url = reverse('admin:study_studyresource_add')
        
        pdf_file = SimpleUploadedFile("unit1_notes.pdf", b"%PDF-1.4 dummy pdf content", content_type="application/pdf")
        
        data = {
            'title': 'Operating Systems Unit 1 Notes',
            'resource_type': 'notes',
            'department': 'Computer Science',
            'course_name': 'Operating Systems',
            'course_code': 'CS301',
            'semester': 'Sem 4',
            'file': pdf_file,
            'description': 'Comprehensive unit 1 OS notes covering threads and process scheduling.',
            'is_active': 'on',
            'uploader': self.admin_user.id,
        }
        response = self.client.post(add_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StudyResource.objects.filter(title='Operating Systems Unit 1 Notes').exists())
        
        resource = StudyResource.objects.get(title='Operating Systems Unit 1 Notes')
        self.assertEqual(resource.course_name, 'Operating Systems')
        self.assertEqual(resource.resource_type, 'notes')
        self.assertTrue(resource.is_active)

    def test_admin_activate_and_deactivate_bulk_actions(self):
        self.client.force_login(self.admin_user)
        res1 = StudyResource.objects.create(
            title='DSA Notes',
            course_name='Data Structures',
            resource_type='notes',
            uploader=self.admin_user,
            is_active=False
        )
        res2 = StudyResource.objects.create(
            title='DBMS PYQ 2024',
            course_name='Database Systems',
            resource_type='pyq',
            uploader=self.admin_user,
            is_active=False
        )

        changelist_url = reverse('admin:study_studyresource_changelist')
        
        # Test Activate Action
        data = {
            'action': 'activate_resources',
            '_selected_action': [res1.id, res2.id],
            'index': '0',
        }
        response = self.client.post(changelist_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        res1.refresh_from_db()
        res2.refresh_from_db()
        self.assertTrue(res1.is_active)
        self.assertTrue(res2.is_active)

        # Test Deactivate Action
        data = {
            'action': 'deactivate_resources',
            '_selected_action': [res1.id, res2.id],
            'index': '0',
        }
        response = self.client.post(changelist_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        res1.refresh_from_db()
        res2.refresh_from_db()
        self.assertFalse(res1.is_active)
        self.assertFalse(res2.is_active)


class StudyResourcePermissionAPITests(APITestCase):
    def setUp(self):
        # 1. Chief Admin / Superuser
        self.chief_admin = User.objects.create_superuser(
            username='chief_admin',
            email='admin@hosteltalkies.com',
            password='AdminPassword@123'
        )

        # 2. Regular Student
        self.student = User.objects.create_user(
            username='student_user',
            email='student@hosteltalkies.com',
            password='StudentPassword@123',
            is_student=True,
            is_staff=False,
            is_superuser=False
        )

        # 3. Hostel Warden
        self.warden = User.objects.create_user(
            username='warden_user',
            email='warden@hosteltalkies.com',
            password='WardenPassword@123',
            is_hostel_admin=True,
            is_staff=False,
            is_superuser=False
        )

        # 4. Sample active study resource
        self.sample_resource = StudyResource.objects.create(
            title='DSA Trees & Graphs Lecture Notes',
            course_name='Data Structures',
            course_code='CS201',
            resource_type='notes',
            department='Computer Science',
            semester='Sem 3',
            uploader=self.chief_admin,
            is_active=True
        )

    def test_1_chief_admin_can_create_study_resource(self):
        self.client.force_authenticate(user=self.chief_admin)
        data = {
            'title': 'Machine Learning Unit 2 Notes',
            'course_name': 'Machine Learning',
            'course_code': 'CS401',
            'resource_type': 'notes',
            'department': 'Computer Science',
            'semester': 'Sem 7',
            'description': 'Supervised and Unsupervised Learning notes.'
        }
        response = self.client.post('/api/study/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StudyResource.objects.filter(title='Machine Learning Unit 2 Notes').exists())

    def test_2_student_can_view_and_download_resources(self):
        self.client.force_authenticate(user=self.student)
        
        # View resources list
        response = self.client.get('/api/study/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Track download
        download_response = self.client.post(f'/api/study/{self.sample_resource.id}/track_download/')
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.sample_resource.refresh_from_db()
        self.assertEqual(self.sample_resource.downloads_count, 1)

    def test_3_student_cannot_create_study_resource(self):
        self.client.force_authenticate(user=self.student)
        data = {
            'title': 'Unauthorized Student Upload Notes',
            'course_name': 'Hacking 101',
            'resource_type': 'notes'
        }
        response = self.client.post('/api/study/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(StudyResource.objects.filter(title='Unauthorized Student Upload Notes').exists())

    def test_4_student_cannot_edit_or_delete_study_resource(self):
        self.client.force_authenticate(user=self.student)
        
        # Try PUT
        put_response = self.client.put(f'/api/study/{self.sample_resource.id}/', {
            'title': 'Malicious Title Edit',
            'course_name': 'CompSci',
            'resource_type': 'notes'
        })
        self.assertEqual(put_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try DELETE
        del_response = self.client.delete(f'/api/study/{self.sample_resource.id}/')
        self.assertEqual(del_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(StudyResource.objects.filter(id=self.sample_resource.id).exists())

    def test_5_warden_cannot_create_study_resource(self):
        self.client.force_authenticate(user=self.warden)
        data = {
            'title': 'Warden Uploaded Study Resource',
            'course_name': 'Civil Engineering',
            'resource_type': 'notes'
        }
        response = self.client.post('/api/study/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(StudyResource.objects.filter(title='Warden Uploaded Study Resource').exists())

    def test_6_unauthenticated_user_cannot_create_study_resource(self):
        data = {
            'title': 'Anonymous Upload',
            'course_name': 'Unknown',
            'resource_type': 'notes'
        }
        response = self.client.post('/api/study/', data)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertFalse(StudyResource.objects.filter(title='Anonymous Upload').exists())

