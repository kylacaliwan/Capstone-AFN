from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.contrib.auth.hashers import identify_hasher
from django.utils import timezone

from services.models import ServiceLocation, ServiceRequest, ServiceTicket, ServiceType, TechnicianSkill
from .models import User


class UserRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = '/api/users/register/'
        self.user_create_url = '/api/admin/users/'

    def test_public_registration_cannot_create_admin_when_no_admin_exists(self):
        payload = {
            'username': 'admin1',
            'email': 'admin1@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'Admin',
            'last_name': 'One',
            'phone': '1234567890',
            'role': 'admin'
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='admin1').role, 'client')

    def test_public_registration_cannot_create_admin_when_admin_exists(self):
        User.objects.create_user(
            username='existing_admin',
            email='existing_admin@example.com',
            password='Password123!',
            role='admin',
            admin_scope='service_follow_up'
        )

        payload = {
            'username': 'admin2',
            'email': 'admin2@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'Admin',
            'last_name': 'Two',
            'phone': '1234567899',
            'role': 'admin',
            'admin_scope': 'task_management'
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_admin = User.objects.get(username='admin2')
        self.assertEqual(new_admin.role, 'client')

    def test_admin_user_can_create_additional_admin(self):
        admin_user = User.objects.create_user(
            username='existing_admin',
            email='existing_admin@example.com',
            password='Password123!',
            role='admin'
        )
        token = Token.objects.create(user=admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'username': 'admin3',
            'email': 'admin3@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'Admin',
            'last_name': 'Three',
            'role': 'admin'
        }

        response = self.client.post(self.user_create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='admin3').role, 'admin')

    def test_admin_user_can_create_follow_up_user(self):
        admin_user = User.objects.create_user(
            username='existing_admin_two',
            email='existing_admin_two@example.com',
            password='Password123!',
            role='admin'
        )
        token = Token.objects.create(user=admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'username': 'followup1',
            'email': 'followup1@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'Follow',
            'last_name': 'Up',
            'role': 'follow_up'
        }

        response = self.client.post(self.user_create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='followup1')
        self.assertEqual(user.role, 'follow_up')
        self.assertEqual(user.admin_scope, 'service_follow_up')

    def test_admin_user_can_deactivate_user(self):
        admin_user = User.objects.create_user(
            username='existing_admin',
            email='existing_admin@example.com',
            password='Password123!',
            role='admin'
        )
        managed_user = User.objects.create_user(
            username='tech_user',
            email='tech@example.com',
            password='Password123!',
            role='technician'
        )
        token = Token.objects.create(user=admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.delete(f'/api/admin/users/{managed_user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        managed_user.refresh_from_db()
        self.assertEqual(managed_user.status, 'inactive')
        self.assertFalse(managed_user.is_active)


class UserLoginTests(APITestCase):
    def setUp(self):
        self.login_url = '/api/users/login/'

    def test_user_can_login_with_email(self):
        user = User.objects.create_user(
            username='email_login_user',
            email='email-login@example.com',
            password='Password123!',
            role='client'
        )

        response = self.client.post(self.login_url, {
            'username': user.email,
            'password': 'Password123!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], user.username)
        self.assertIn('token', response.data)

    def test_login_recovers_legacy_plain_text_password(self):
        user = User.objects.create(
            username='legacy_user',
            email='legacy@example.com',
            password='legacy-pass',
            role='supervisor',
            is_active=True
        )

        response = self.client.post(self.login_url, {
            'username': user.username,
            'password': 'legacy-pass'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.password.startswith('pbkdf2_'))
        identify_hasher(user.password)

    def test_user_can_login_with_duplicate_email_when_password_matches_later_account(self):
        shared_email = 'shared-login@example.com'
        User.objects.create_user(
            username='shared_email_first',
            email=shared_email,
            password='Password123!',
            role='client'
        )
        matching_user = User.objects.create_user(
            username='shared_email_second',
            email=shared_email,
            password='DifferentPass456!',
            role='admin'
        )

        response = self.client.post(self.login_url, {
            'username': shared_email,
            'password': 'DifferentPass456!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], matching_user.username)
        self.assertEqual(response.data['user']['role'], matching_user.role)
        self.assertIn('token', response.data)

    def test_user_can_login_with_case_insensitive_username(self):
        user = User.objects.create_user(
            username='MixedCaseUser',
            email='mixedcase@example.com',
            password='Password123!',
            role='client'
        )

        response = self.client.post(self.login_url, {
            'username': 'mixedcaseuser',
            'password': 'Password123!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], user.username)


class SelfServiceProfileTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='self_service_client',
            email='self-service-client@example.com',
            password='Password123!',
            role='client',
            phone='1111111111',
            address='Old Address'
        )
        self.client_token = Token.objects.create(user=self.client_user)

        self.technician_user = User.objects.create_user(
            username='self_service_tech',
            email='self-service-tech@example.com',
            password='Password123!',
            role='technician',
            phone='2222222222',
            status='active',
            is_available=True
        )
        self.technician_token = Token.objects.create(user=self.technician_user)

    def test_me_endpoint_allows_safe_profile_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')

        response = self.client.patch('/api/users/me/', {
            'first_name': 'Updated',
            'phone': '9999999999',
            'address': 'New Address'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.first_name, 'Updated')
        self.assertEqual(self.client_user.phone, '9999999999')
        self.assertEqual(self.client_user.address, 'New Address')

    def test_me_endpoint_blocks_privileged_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')

        response = self.client.patch('/api/users/me/', {
            'role': 'admin',
            'admin_scope': 'service_follow_up',
            'status': 'inactive',
            'is_available': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.role, 'client')
        self.assertEqual(self.client_user.admin_scope, 'general')
        self.assertEqual(self.client_user.status, 'active')
        self.assertTrue(self.client_user.is_available)

    def test_technician_profile_update_allows_safe_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.technician_token.key}')

        response = self.client.put('/api/technician/profile/', {
            'phone': '3333333333'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.technician_user.refresh_from_db()
        self.assertEqual(self.technician_user.phone, '3333333333')

    def test_technician_profile_update_blocks_privileged_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.technician_token.key}')

        response = self.client.put('/api/technician/profile/', {
            'role': 'admin',
            'status': 'inactive',
            'is_available': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)
        self.technician_user.refresh_from_db()
        self.assertEqual(self.technician_user.role, 'technician')
        self.assertEqual(self.technician_user.status, 'active')
        self.assertTrue(self.technician_user.is_available)


class AdminSettingsTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='settings_admin',
            email='settings_admin@example.com',
            password='Password123!',
            role='admin'
        )
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_admin_settings_accepts_put_on_collection_route(self):
        response = self.client.put('/api/admin/settings/', {
            'systemName': 'AFN Updated',
            'autoDispatchEnabled': False
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['settings']['systemName'], 'AFN Updated')


class AdminTechnicianAccessTests(APITestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(
            username='dispatch_supervisor',
            email='dispatch_supervisor@example.com',
            password='Password123!',
            role='supervisor'
        )
        self.admin = User.objects.create_user(
            username='dispatch_admin',
            email='dispatch_admin@example.com',
            password='Password123!',
            role='admin'
        )
        self.technician = User.objects.create_user(
            username='dispatch_tech',
            email='dispatch_tech@example.com',
            password='Password123!',
            role='technician',
            status='active',
            is_available=True
        )
        self.supervisor_token = Token.objects.create(user=self.supervisor)
        self.admin_token = Token.objects.create(user=self.admin)

    def test_supervisor_can_list_technicians_for_dispatch(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.supervisor_token.key}')

        response = self.client.get('/api/admin/technicians/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['id'] == self.technician.id for item in response.data))

    def test_supervisor_cannot_create_technician(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.supervisor_token.key}')

        response = self.client.post('/api/admin/technicians/', {
            'username': 'should_fail',
            'email': 'should_fail@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'role': 'technician'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserManagementTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='user_mgmt_admin',
            email='user_mgmt_admin@example.com',
            password='Password123!',
            role='admin'
        )
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_admin_can_create_internal_user_with_selected_role(self):
        response = self.client.post('/api/admin/users/', {
            'username': 'created_supervisor',
            'email': 'created_supervisor@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'role': 'supervisor'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(username='created_supervisor')
        self.assertEqual(created_user.role, 'supervisor')
        self.assertEqual(response.data['role'], 'supervisor')
        self.assertTrue(created_user.is_active)
        self.assertEqual(created_user.status, 'active')


class AdminAnalyticsTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='analytics_admin',
            email='analytics_admin@example.com',
            password='Password123!',
            role='admin'
        )
        self.client_user = User.objects.create_user(
            username='analytics_client',
            email='analytics_client@example.com',
            password='Password123!',
            role='client'
        )
        self.technician_user = User.objects.create_user(
            username='analytics_tech',
            email='analytics_tech@example.com',
            password='Password123!',
            role='technician',
            status='active',
            is_available=True
        )

        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        self.solar = ServiceType.objects.create(
            name='Solar Installation',
            description='Solar setup',
            estimated_duration=120
        )
        self.cctv = ServiceType.objects.create(
            name='CCTV Service',
            description='Security setup',
            estimated_duration=90
        )
        TechnicianSkill.objects.create(
            technician=self.technician_user,
            service_type=self.solar,
            skill_level='expert'
        )

        self._create_request_with_ticket(
            service_type=self.solar,
            request_days_ago=2,
            completed_days_ago=1,
            status='Completed'
        )
        self._create_request_with_ticket(
            service_type=self.solar,
            request_days_ago=5,
            completed_days_ago=3,
            status='Completed'
        )
        self._create_request_with_ticket(
            service_type=self.solar,
            request_days_ago=9,
            status='Approved'
        )
        self._create_request_with_ticket(
            service_type=self.cctv,
            request_days_ago=4,
            status='Approved'
        )
        self._create_request_with_ticket(
            service_type=self.cctv,
            request_days_ago=45,
            completed_days_ago=44,
            status='Completed',
            city='Abuja',
            province='FCT'
        )

    def _create_request_with_ticket(
        self,
        service_type,
        request_days_ago,
        status='Approved',
        completed_days_ago=None,
        city='Lagos',
        province='Lagos'
    ):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=service_type,
            description=f'{service_type.name} request',
            priority='Normal',
            status=status
        )

        request_time = timezone.now() - timezone.timedelta(days=request_days_ago)
        ServiceRequest.objects.filter(pk=request_obj.pk).update(
            request_date=request_time,
            updated_at=request_time
        )
        request_obj.refresh_from_db()

        ServiceLocation.objects.create(
            request=request_obj,
            address=f'{service_type.name} Address',
            city=city,
            province=province,
            latitude=6.5 + (request_days_ago * 0.01),
            longitude=3.3 + (request_days_ago * 0.01)
        )

        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=request_time.date(),
            assigned_at=request_time + timezone.timedelta(hours=2),
            start_time=request_time + timezone.timedelta(hours=4),
            status='Completed' if completed_days_ago is not None else 'Not Started',
            completed_date=(
                timezone.now() - timezone.timedelta(days=completed_days_ago)
                if completed_days_ago is not None else None
            )
        )
        return ticket

    def test_admin_analytics_returns_predictive_metrics_from_live_data(self):
        response = self.client.get('/api/admin/analytics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overview', response.data)
        self.assertIn('predictiveSummary', response.data)
        self.assertIn('serviceForecasts', response.data)
        self.assertIn('busiestMonths', response.data)
        self.assertIn('busiestWeeks', response.data)
        self.assertIn('topRequestedServiceTypes', response.data)
        self.assertIn('cityCompletionTrends', response.data)
        self.assertIn('provinceCompletionTrends', response.data)
        self.assertGreaterEqual(response.data['overview']['totalRequests'], 4)
        self.assertGreaterEqual(response.data['overview']['completedRequests'], 2)
        self.assertEqual(response.data['topTech']['techName'], self.technician_user.username)
        self.assertTrue(any(item['name'] == self.solar.name for item in response.data['jobCountByService']))
        self.assertGreaterEqual(response.data['predictiveSummary']['totalPredictedRequests'], 1)
        self.assertTrue(any(item['serviceType'] == self.solar.name for item in response.data['serviceForecasts']))
        self.assertGreaterEqual(len(response.data['busiestMonths']), 1)
        self.assertGreaterEqual(len(response.data['busiestWeeks']), 1)
        self.assertEqual(response.data['topRequestedServiceTypes'][0]['serviceType'], self.solar.name)
        self.assertTrue(any(item['city'] == 'Lagos' for item in response.data['cityCompletionTrends']))
        self.assertTrue(any(item['province'] == 'Lagos' for item in response.data['provinceCompletionTrends']))
