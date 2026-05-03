from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from messages_app.models import Message
from services.models import ServiceLocation, ServiceRequest, ServiceTicket, ServiceType
from users.models import User


class MessageApiTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='message-client',
            password='Password123!',
            role='client',
            phone='+639170000001',
        )
        self.technician_user = User.objects.create_user(
            username='message-tech',
            password='Password123!',
            role='technician',
            phone='+639170000002',
        )
        self.supervisor_user = User.objects.create_user(
            username='message-supervisor',
            password='Password123!',
            role='supervisor',
            phone='+639170000003',
        )
        self.outsider_user = User.objects.create_user(
            username='message-outsider',
            password='Password123!',
            role='client',
            phone='+639170000004',
        )
        self.service_type = ServiceType.objects.create(
            name='Message Test Service',
            description='Message flow',
            estimated_duration=60,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need help with a service request',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='123 Message Street',
            city='Pasig',
            province='Metro Manila',
            latitude='14.580000',
            longitude='121.060000',
        )
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.technician_user,
            supervisor=self.supervisor_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )
        self.token = Token.objects.create(user=self.client_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_list_messages_includes_ui_friendly_fields(self):
        Message.objects.create(
            ticket=self.ticket,
            sender=self.technician_user,
            receiver=self.client_user,
            message_text='Technician update',
        )

        response = self.client.get('/api/messages/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], 'Technician update')
        self.assertEqual(results[0]['sender_name'], 'message-tech')
        self.assertEqual(results[0]['receiver_name'], 'message-client')
        self.assertEqual(results[0]['ticket_id'], self.ticket.id)
        self.assertEqual(results[0]['ticket_address'], '123 Message Street')

    def test_create_message_accepts_frontend_text_payload(self):
        response = self.client.post(
            '/api/messages/',
            {
                'ticket': self.ticket.id,
                'receiver': self.technician_user.id,
                'text': 'Client reply message',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get(id=response.data['id'])
        self.assertEqual(message.sender, self.client_user)
        self.assertEqual(message.receiver, self.technician_user)
        self.assertEqual(message.message_text, 'Client reply message')

    def test_create_message_rejects_receiver_outside_ticket_thread(self):
        response = self.client.post(
            '/api/messages/',
            {
                'ticket': self.ticket.id,
                'receiver': self.outsider_user.id,
                'text': 'This should not be allowed',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('receiver', response.data)

    def test_create_message_rejects_sender_outside_ticket_thread(self):
        outsider_token = Token.objects.create(user=self.outsider_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')

        response = self.client.post(
            '/api/messages/',
            {
                'ticket': self.ticket.id,
                'receiver': self.client_user.id,
                'text': 'This should not be allowed either',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
