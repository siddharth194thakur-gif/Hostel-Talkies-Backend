from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date

from events.models import Event
from hostels.models import Hostel

class SIHHackathonEventTests(APITestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name='Aryabhata Hostel', code='TH-TEST')

        # Existing other event
        self.other_event = Event.objects.create(
            title='Campus Sports Meet',
            description='Sports meet for hostelers',
            event_date=date(2026, 9, 10),
            location='Campus Ground',
            hostel=self.hostel,
            organizer='Hostel Sports Committee',
            is_active=True
        )

    def test_sih_event_exists_with_accurate_details(self):
        sih = Event.objects.filter(title__icontains='Smart India Hackathon').first()
        self.assertIsNotNone(sih, "SIH 2026 event was not found in the database")
        self.assertIn('SIH', sih.title)
        self.assertEqual(sih.event_date, date(2026, 9, 15))
        self.assertIsNone(sih.hostel, "SIH event should be campus-wide (hostel=None) to be visible to all students")
        self.assertTrue(sih.is_active)
        self.assertIn('https://forms.gle/YLZTDtHaQTDESos7', sih.description)
        self.assertIn('6 Members', sih.description)
        self.assertIn('female member', sih.description.lower())
        self.assertIn('Dr. Satyam Kumar Upadhyay', sih.description)

    def test_sih_event_appears_first_in_events_api(self):
        url = reverse('event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertGreater(len(data), 0)

        # First event MUST be SIH Hackathon
        first_event = data[0]
        self.assertIn('Smart India Hackathon', first_event['title'])
        self.assertIsNone(first_event['hostel'])

    def test_sih_event_appears_when_filtered_by_any_hostel(self):
        url = reverse('event-list') + f'?hostel={self.hostel.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        event_titles = [e['title'] for e in data]
        self.assertIn('Smart India Hackathon (SIH) 2026 – Internal Round', event_titles)
        self.assertEqual(data[0]['title'], 'Smart India Hackathon (SIH) 2026 – Internal Round')
