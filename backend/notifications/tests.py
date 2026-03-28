from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from notifications.models import FirebaseToken, Notification
from users.models import User


class NotificationViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notif_user',
            email='notif@example.com',
            password='Password123!',
            role='client'
        )
        self.other_user = User.objects.create_user(
            username='other_notif_user',
            email='other-notif@example.com',
            password='Password123!',
            role='client'
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_user_can_delete_own_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            title='Own notification',
            message='Hello',
            type='info'
        )

        response = self.client.delete(f'/api/notifications/{notification.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notification.objects.filter(id=notification.id).exists())

    def test_user_cannot_delete_another_users_notification(self):
        notification = Notification.objects.create(
            user=self.other_user,
            title='Other notification',
            message='Hidden',
            type='info'
        )

        response = self.client.delete(f'/api/notifications/{notification.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Notification.objects.filter(id=notification.id).exists())

    def test_user_can_list_own_notifications(self):
        own_notification = Notification.objects.create(
            user=self.user,
            title='Own notification',
            message='Visible',
            type='info'
        )
        Notification.objects.create(
            user=self.other_user,
            title='Other notification',
            message='Hidden',
            type='warning'
        )

        response = self.client.get('/api/notifications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], own_notification.id)
        self.assertEqual(results[0]['related_ticket'], None)
        self.assertEqual(results[0]['related_request'], None)

    def test_mark_read_sets_read_timestamp(self):
        notification = Notification.objects.create(
            user=self.user,
            title='Unread notification',
            message='Please read me',
            type='info'
        )

        response = self.client.post(f'/api/notifications/{notification.id}/mark_read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)
        self.assertIsNotNone(response.data['read_at'])

    def test_mark_all_read_updates_unread_notifications(self):
        first = Notification.objects.create(
            user=self.user,
            title='First',
            message='One',
            type='info'
        )
        second = Notification.objects.create(
            user=self.user,
            title='Second',
            message='Two',
            type='warning'
        )

        response = self.client.post('/api/notifications/mark_all_read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, 'read')
        self.assertEqual(second.status, 'read')
        self.assertIsNotNone(first.read_at)
        self.assertIsNotNone(second.read_at)

    def test_register_reassigns_existing_browser_token_to_current_user(self):
        FirebaseToken.objects.create(
            user=self.other_user,
            fcm_token='shared-browser-token',
            device_name='Shared Browser',
            device_type='web',
            is_active=False,
        )

        response = self.client.post(
            '/api/notifications/firebase-tokens/register/',
            {
                'fcm_token': 'shared-browser-token',
                'device_name': 'Shared Browser',
                'device_type': 'web',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = FirebaseToken.objects.get(fcm_token='shared-browser-token')
        self.assertEqual(token.user, self.user)
        self.assertTrue(token.is_active)
