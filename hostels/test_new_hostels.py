from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from hostels.models import Hostel, Block, Room
from users.models import StudentProfile

User = get_user_model()

class NewHostelsVerificationTests(APITestCase):
    """
    Exhaustive verification of the four new hostels:
    - Meerabai Hostel (girls)
    - Lakshmibai Hostel (girls)
    - Draupadi Hostel (girls)
    - Srinivas Ramanujan PG Hostel (boys)
    """

    def test_1_all_four_new_hostels_exist_with_correct_gender_and_description(self):
        expected_hostels = {
            'Meerabai Hostel': {'gender': 'girls', 'desc': 'Girls hostel for students.'},
            'Lakshmibai Hostel': {'gender': 'girls', 'desc': 'Girls hostel for students.'},
            'Draupadi Hostel': {'gender': 'girls', 'desc': 'Girls hostel for students.'},
            'Srinivas Ramanujan PG Hostel': {'gender': 'boys', 'desc': 'Boys hostel for students.'},
        }

        for name, data in expected_hostels.items():
            self.assertTrue(Hostel.objects.filter(name=name).exists(), f"Hostel {name} does not exist in DB")
            h = Hostel.objects.get(name=name)
            self.assertEqual(h.gender, data['gender'], f"Hostel {name} gender mismatch")
            self.assertEqual(h.description, data['desc'], f"Hostel {name} description mismatch")
            self.assertTrue(h.is_active, f"Hostel {name} is not active")
            # Verify blocks and rooms were also provisioned
            self.assertGreater(h.blocks.count(), 0, f"Hostel {name} has no blocks")

    def test_2_hostels_api_list_includes_new_hostels_and_existing_hostels(self):
        url = reverse('hostel-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        hostel_names = [item['name'] for item in data]

        # All 4 new hostels must be present
        self.assertIn('Meerabai Hostel', hostel_names)
        self.assertIn('Lakshmibai Hostel', hostel_names)
        self.assertIn('Draupadi Hostel', hostel_names)
        self.assertIn('Srinivas Ramanujan PG Hostel', hostel_names)

        # Check gender serialization
        for item in data:
            if item['name'] in ['Meerabai Hostel', 'Lakshmibai Hostel', 'Draupadi Hostel']:
                self.assertEqual(item['gender'], 'girls')
            elif item['name'] == 'Srinivas Ramanujan PG Hostel':
                self.assertEqual(item['gender'], 'boys')

    def test_3_complete_flow_registration_login_and_verify_for_each_new_hostel(self):
        """
        Tests the complete student lifecycle for all four new hostels:
        Register -> Select Hostel -> Select Block & Room -> Create Account -> Login -> Verify Profile
        """
        test_cases = [
            {
                'name': 'Meerabai Hostel',
                'full_name': 'Meera Kumari',
                'email': 'meera@student.edu',
                'gender': 'female',
            },
            {
                'name': 'Lakshmibai Hostel',
                'full_name': 'Lakshmi Rao',
                'email': 'lakshmi@student.edu',
                'gender': 'female',
            },
            {
                'name': 'Draupadi Hostel',
                'full_name': 'Draupadi Sharma',
                'email': 'draupadi@student.edu',
                'gender': 'female',
            },
            {
                'name': 'Srinivas Ramanujan PG Hostel',
                'full_name': 'Srinivas Raman',
                'email': 'srinivas@student.edu',
                'gender': 'male',
            },
        ]

        register_url = reverse('register')
        login_url = reverse('login')
        me_url = reverse('current_user')

        for tc in test_cases:
            hostel = Hostel.objects.get(name=tc['name'])
            block = hostel.blocks.first()
            room = block.rooms.first() if block else None

            reg_payload = {
                'full_name': tc['full_name'],
                'email': tc['email'],
                'gender': tc['gender'],
                'programme': 'B.Tech',
                'branch': 'Computer Science & Engineering',
                'password': 'SecureStudentPass@123',
                'confirm_password': 'SecureStudentPass@123',
                'hostel': hostel.id,
                'block': block.id if block else None,
                'room': room.id if room else None,
            }

            # 1. Register
            reg_resp = self.client.post(register_url, reg_payload)
            self.assertEqual(
                reg_resp.status_code, status.HTTP_201_CREATED,
                f"Registration failed for {tc['name']}: {reg_resp.data}"
            )
            self.assertIn('tokens', reg_resp.data)
            self.assertEqual(reg_resp.data['user']['profile']['hostel_detail']['name'], tc['name'])

            # 2. Verify User & StudentProfile in database
            user = User.objects.get(email=tc['email'])
            self.assertTrue(user.is_student)
            profile = user.profile
            self.assertEqual(profile.hostel, hostel)
            if block:
                self.assertEqual(profile.block, block)
            if room:
                self.assertEqual(profile.room, room)

            # 3. Login
            login_resp = self.client.post(login_url, {
                'email': tc['email'],
                'password': 'SecureStudentPass@123',
            })
            self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
            access_token = login_resp.data['tokens']['access']

            # 4. Verify /api/auth/me/ endpoint returns correct hostel profile
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            me_resp = self.client.get(me_url)
            self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(me_resp.data['profile']['hostel_detail']['name'], tc['name'])
            self.assertEqual(me_resp.data['profile']['hostel_detail']['gender'], hostel.gender)
            self.client.credentials()  # Reset credentials for next test case


class DjangoAdminHostelsVerificationTests(TestCase):
    """
    Verifies that the new hostels are completely manageable via Django Admin:
    - Viewable in changelist
    - Viewable in changeform
    - Editable (change description, change gender)
    """

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='hostel_admin_tester',
            email='admin_hostels_test@hosteltalkies.com',
            password='AdminPassword@123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_admin_changelist_displays_new_hostels(self):
        resp = self.client.get(reverse('admin:hostels_hostel_changelist'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Meerabai Hostel')
        self.assertContains(resp, 'Lakshmibai Hostel')
        self.assertContains(resp, 'Draupadi Hostel')
        self.assertContains(resp, 'Srinivas Ramanujan PG Hostel')

    def test_admin_can_edit_hostel_gender_and_description(self):
        hostel = Hostel.objects.get(name='Meerabai Hostel')
        change_url = reverse('admin:hostels_hostel_change', args=[hostel.id])

        resp = self.client.get(change_url)
        self.assertEqual(resp.status_code, 200)

        # Update description and save via admin POST
        post_data = {
            'name': 'Meerabai Hostel',
            'code': hostel.code,
            'gender': 'girls',
            'description': 'Updated description for Meerabai girls hostel.',
            'warden_name': hostel.warden_name,
            'warden_contact': hostel.warden_contact,
            'is_active': 'on',
            'blocks-TOTAL_FORMS': '0',
            'blocks-INITIAL_FORMS': '0',
            '_save': 'Save',
        }
        post_resp = self.client.post(change_url, post_data, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        hostel.refresh_from_db()
        self.assertEqual(hostel.description, 'Updated description for Meerabai girls hostel.')
