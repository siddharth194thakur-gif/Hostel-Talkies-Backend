from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Hostel, Block, Room

User = get_user_model()

class HostelAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_hostels',
            email='admin_hostels@test.com',
            password='AdminPassword@123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

        self.hostel = Hostel.objects.create(
            name='Aryabhata Hostel',
            code='TH-1',
            gender='boys'
        )
        self.block = Block.objects.create(
            hostel=self.hostel,
            name='Block A1',
            floors=4
        )
        self.room = Room.objects.create(
            block=self.block,
            room_number='101',
            floor=1,
            capacity=2
        )

    def test_hostel_changelist_and_add(self):
        resp = self.client.get(reverse('admin:hostels_hostel_changelist'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aryabhata Hostel')

        add_resp = self.client.post(reverse('admin:hostels_hostel_add'), {
            'name': 'Gargi Hostel',
            'code': 'TH-3',
            'gender': 'girls',
            'is_active': 'on',
            'blocks-TOTAL_FORMS': '0',
            'blocks-INITIAL_FORMS': '0',
        }, follow=True)
        self.assertEqual(add_resp.status_code, 200)
        self.assertTrue(Hostel.objects.filter(name='Gargi Hostel').exists())

    def test_block_and_room_changelists(self):
        block_resp = self.client.get(reverse('admin:hostels_block_changelist'))
        self.assertEqual(block_resp.status_code, 200)
        self.assertContains(block_resp, 'Block A1')

        room_resp = self.client.get(reverse('admin:hostels_room_changelist'))
        self.assertEqual(room_resp.status_code, 200)
        self.assertContains(room_resp, '101')
