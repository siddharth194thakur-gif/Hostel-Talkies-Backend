from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from messaging.models import Conversation, Message, MessageReaction, UserChatPreference

User = get_user_model()

class MessagingAPITests(APITestCase):
    def setUp(self):
        # 1. Users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@student.edu',
            password='Password@123',
            first_name='Rahul',
            last_name='Sharma',
            is_student=True
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@student.edu',
            password='Password@123',
            first_name='Ananya',
            last_name='Iyer',
            is_student=True
        )

        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@student.edu',
            password='Password@123',
            first_name='Sneha',
            last_name='Patel',
            is_student=True
        )

        # 2. Direct Conversation between user1 and user2
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.user1, self.user2)

        # 3. Private Group
        self.group = Conversation.objects.create(
            is_group=True,
            group_name='Aryabhata LAN Gamers',
            group_admin=self.user1
        )
        self.group.participants.add(self.user1, self.user2)

    def test_1_send_text_message(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f'/api/messages/{self.conv.id}/send/', {
            'content': 'Hey Ananya! Are you free for badminton tonight? 🏸',
            'message_type': 'text'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Hey Ananya! Are you free for badminton tonight? 🏸')
        self.assertEqual(response.data['message_type'], 'text')
        self.assertTrue(Message.objects.filter(conversation=self.conv, sender=self.user1).exists())

    def test_2_send_image_attachment(self):
        self.client.force_authenticate(user=self.user1)
        test_image = SimpleUploadedFile("campus_photo.jpg", b"fake image bytes content", content_type="image/jpeg")
        response = self.client.post(f'/api/messages/{self.conv.id}/send/', {
            'file': test_image,
            'content': 'Check out this sunset from Block A! 🌅',
            'message_type': 'image'
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message_type'], 'image')
        self.assertEqual(response.data['file_name'], 'campus_photo.jpg')
        self.assertTrue(response.data['file'])

    def test_3_send_document_attachment(self):
        self.client.force_authenticate(user=self.user1)
        test_pdf = SimpleUploadedFile("physics_assignment.pdf", b"%PDF-1.4 dummy assignment pdf", content_type="application/pdf")
        response = self.client.post(f'/api/messages/{self.conv.id}/send/', {
            'file': test_pdf,
            'content': 'Here is the physics assignment sheet.',
            'message_type': 'file'
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message_type'], 'file')
        self.assertEqual(response.data['file_name'], 'physics_assignment.pdf')

    def test_4_reply_to_message(self):
        self.client.force_authenticate(user=self.user1)
        msg1 = Message.objects.create(conversation=self.conv, sender=self.user1, content='Let us meet at 6 PM.')
        
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/messages/{self.conv.id}/send/', {
            'content': 'Perfect, see you there!',
            'message_type': 'text',
            'reply_to_id': msg1.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reply_to'], msg1.id)
        self.assertIsNotNone(response.data['reply_to_detail'])
        self.assertEqual(response.data['reply_to_detail']['content'], 'Let us meet at 6 PM.')

    def test_5_message_reactions(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.user1, content='Tournament winner! 🏆')
        
        # User 2 adds a reaction
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/messages/messages/{msg.id}/react/', {'reaction': '🔥'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['emoji'], '🔥')
        self.assertEqual(response.data[0]['count'], 1)

        # User 2 toggles off the reaction
        response_toggle = self.client.post(f'/api/messages/messages/{msg.id}/react/', {'reaction': '🔥'})
        self.assertEqual(response_toggle.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_toggle.data), 0)

    def test_6_delete_message_for_me_and_everyone(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.user1, content='Mistake text')

        # User 1 deletes for everyone
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f'/api/messages/messages/{msg.id}/delete/', {'delete_type': 'for_everyone'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg.refresh_from_db()
        self.assertTrue(msg.is_deleted_everyone)
        self.assertEqual(msg.content, '🚫 This message was deleted')

    def test_7_attachment_security_blocks_outsiders(self):
        test_file = SimpleUploadedFile("confidential_notes.pdf", b"secret student data", content_type="application/pdf")
        msg = Message.objects.create(conversation=self.conv, sender=self.user1, file=test_file, file_name='confidential_notes.pdf')

        # Outsider tries to download attachment
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(f'/api/messages/messages/{msg.id}/attachment/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authorized participant downloads attachment
        self.client.force_authenticate(user=self.user2)
        response_auth = self.client.get(f'/api/messages/messages/{msg.id}/attachment/')
        self.assertEqual(response_auth.status_code, status.HTTP_200_OK)

    def test_8_group_privacy_enforcement(self):
        # Outsider tries to send message in private group
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post(f'/api/messages/{self.group.id}/send/', {'content': 'Infiltrator message'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Outsider cannot fetch group detail
        detail_response = self.client.get(f'/api/messages/{self.group.id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_9_user_specific_chat_customization(self):
        # User 1 customizes conversation with solid background and rounded bubbles
        self.client.force_authenticate(user=self.user1)
        custom_resp = self.client.post(f'/api/messages/{self.conv.id}/preferences/', {
            'bg_type': 'solid',
            'bg_value': '#EEF2FF',
            'bubble_style': 'rounded',
            'theme_mode': 'dark'
        })
        self.assertEqual(custom_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(custom_resp.data['bg_type'], 'solid')
        self.assertEqual(custom_resp.data['bg_value'], '#EEF2FF')
        self.assertEqual(custom_resp.data['bubble_style'], 'rounded')
        self.assertEqual(custom_resp.data['theme_mode'], 'dark')

        # User 2 views their preferences for the same conversation - should still be default!
        self.client.force_authenticate(user=self.user2)
        user2_pref = self.client.get(f'/api/messages/{self.conv.id}/preferences/')
        self.assertEqual(user2_pref.status_code, status.HTTP_200_OK)
        self.assertEqual(user2_pref.data['bg_type'], 'default')
        self.assertEqual(user2_pref.data['bubble_style'], 'classic')

        # User 1 resets customization to default
        self.client.force_authenticate(user=self.user1)
        reset_resp = self.client.post(f'/api/messages/{self.conv.id}/preferences/reset/')
        self.assertEqual(reset_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reset_resp.data['bg_type'], 'default')

