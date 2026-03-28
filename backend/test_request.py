from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User


class RequestTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client2',
            password='testpass123',
            role='client'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.client_user)

    def test_dashboard_endpoint_returns_200(self):
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('role'), 'client')

