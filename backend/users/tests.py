import re

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.contrib.auth.hashers import identify_hasher
from django.core.cache import cache
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from services.models import ServiceLocation, ServiceRequest, ServiceTicket, ServiceType, TechnicianSkill
from .models import AdminSettings, User, UserCapabilityGrant
from .rbac import (
    AFTER_SALES_CASES_MANAGE,
    AFTER_SALES_CASES_VIEW,
    AFTER_SALES_DASHBOARD_VIEW,
    MANAGE_STAFF_CAPABILITIES,
    TECHNICIAN_DASHBOARD_VIEW,
    TECHNICIAN_JOBS_VIEW,
    TECHNICIAN_PROFILE_VIEW,
    USER_DIRECTORY_VIEW,
    can_receive_delegated_authority,
    get_default_admin_scope_for_role,
    is_admin_scoped_role,
    is_admin_workspace_role,
)


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

    def test_superadmin_user_can_create_additional_admin(self):
        superadmin_user = User.objects.create_user(
            username='existing_owner',
            email='existing_owner@example.com',
            password='Password123!',
            role='superadmin'
        )
        token = Token.objects.create(user=superadmin_user)
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

    def test_superadmin_user_can_create_follow_up_user(self):
        superadmin_user = User.objects.create_user(
            username='existing_owner_two',
            email='existing_owner_two@example.com',
            password='Password123!',
            role='superadmin'
        )
        token = Token.objects.create(user=superadmin_user)
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

    def test_superadmin_user_can_deactivate_user(self):
        superadmin_user = User.objects.create_user(
            username='existing_owner_three',
            email='existing_owner_three@example.com',
            password='Password123!',
            role='superadmin'
        )
        managed_user = User.objects.create_user(
            username='tech_user',
            email='tech@example.com',
            password='Password123!',
            role='technician'
        )
        token = Token.objects.create(user=superadmin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.delete(f'/api/admin/users/{managed_user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        managed_user.refresh_from_db()
        self.assertEqual(managed_user.status, 'inactive')
        self.assertFalse(managed_user.is_active)

    def test_admin_user_cannot_create_internal_user(self):
        admin_user = User.objects.create_user(
            username='operations_admin',
            email='operations_admin@example.com',
            password='Password123!',
            role='admin'
        )
        token = Token.objects.create(user=admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.post(self.user_create_url, {
            'username': 'blocked_supervisor',
            'email': 'blocked_supervisor@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'role': 'supervisor'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(username='blocked_supervisor').exists())

    def test_public_registration_rejects_weak_password(self):
        payload = {
            'username': 'weak_password_user',
            'email': 'weak@example.com',
            'password': '123',
            'password_confirm': '123',
            'role': 'client',
        }

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(username='weak_password_user').exists())


class RoleClassificationTests(APITestCase):
    def test_follow_up_is_admin_scoped_but_not_full_admin_workspace(self):
        self.assertTrue(is_admin_scoped_role('follow_up'))
        self.assertTrue(can_receive_delegated_authority('follow_up'))
        self.assertFalse(is_admin_workspace_role('follow_up'))
        self.assertEqual(get_default_admin_scope_for_role('follow_up'), 'service_follow_up')


class UserLoginTests(APITestCase):
    def setUp(self):
        self.login_url = '/api/users/login/'
        cache.clear()

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

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
    def test_login_is_rate_limited_after_too_many_attempts(self):
        User.objects.create_user(
            username='throttle_user',
            email='throttle@example.com',
            password='Password123!',
            role='client'
        )

        for _ in range(10):
            response = self.client.post(self.login_url, {
                'username': 'throttle_user',
                'password': 'wrong-password'
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(self.login_url, {
            'username': 'throttle_user',
            'password': 'wrong-password'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_BASE_URL='http://localhost:5173',
)
class PasswordResetTests(APITestCase):
    def setUp(self):
        self.request_url = '/api/users/password_reset_request/'
        self.confirm_url = '/api/users/password_reset_confirm/'
        self.user = User.objects.create_user(
            username='reset_user',
            email='reset-user@example.com',
            password='Password123!',
            role='client'
        )
        cache.clear()

    def _extract_reset_credentials(self, body):
        match = re.search(r'uid=([^&\s]+)&token=([^\s]+)', body)
        self.assertIsNotNone(match)
        return match.group(1), match.group(2)

    def test_password_reset_request_sends_email_with_reset_link(self):
        response = self.client.post(self.request_url, {
            'identifier': self.user.email
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.username, mail.outbox[0].body)
        self.assertIn('/reset-password?uid=', mail.outbox[0].body)
        self.assertIn('token=', mail.outbox[0].body)

    def test_password_reset_confirm_updates_password_and_revokes_existing_tokens(self):
        existing_token = Token.objects.create(user=self.user)

        self.client.post(self.request_url, {
            'identifier': self.user.email
        }, format='json')
        uid, token = self._extract_reset_credentials(mail.outbox[0].body)

        response = self.client.post(self.confirm_url, {
            'uid': uid,
            'token': token,
            'new_password': 'EvenStrongerPassword456!',
            'password_confirm': 'EvenStrongerPassword456!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('EvenStrongerPassword456!'))
        self.assertFalse(Token.objects.filter(key=existing_token.key).exists())

    def test_password_reset_confirm_rejects_invalid_token(self):
        response = self.client.post(self.confirm_url, {
            'uid': 'invalid',
            'token': 'invalid-token',
            'new_password': 'EvenStrongerPassword456!',
            'password_confirm': 'EvenStrongerPassword456!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


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

    def test_change_password_rejects_weak_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')

        response = self.client.post('/api/users/change_password/', {
            'current_password': 'Password123!',
            'new_password': '123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)


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

    def test_admin_settings_are_persisted_and_returned_on_next_read(self):
        response = self.client.put('/api/admin/settings/', {
            'systemName': 'AFN Updated',
            'supportEmail': 'ops@example.com',
            'enableNotifications': True,
            'autoDispatchEnabled': True,
            'smsNotificationsEnabled': False,
            'defaultTimeZone': 'Asia/Manila',
            'maxTechnicianAssignments': 7,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get('/api/admin/settings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['systemName'], 'AFN Updated')
        self.assertEqual(response.data['supportEmail'], 'ops@example.com')
        self.assertEqual(response.data['defaultTimeZone'], 'Asia/Manila')
        self.assertEqual(response.data['maxTechnicianAssignments'], 7)

        settings_record = AdminSettings.objects.get()
        self.assertEqual(settings_record.updated_by, self.admin_user)


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
        self.superadmin_user = User.objects.create_user(
            username='user_mgmt_owner',
            email='user_mgmt_owner@example.com',
            password='Password123!',
            role='superadmin'
        )
        token = Token.objects.create(user=self.superadmin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_superadmin_can_create_internal_user_with_selected_role(self):
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


class CapabilityGrantApiTests(APITestCase):
    def setUp(self):
        self.superadmin_user = User.objects.create_user(
            username='cap_superadmin',
            email='cap_superadmin@example.com',
            password='Password123!',
            role='superadmin'
        )
        self.admin_user = User.objects.create_user(
            username='cap_admin',
            email='cap_admin@example.com',
            password='Password123!',
            role='admin'
        )
        self.supervisor_user = User.objects.create_user(
            username='cap_supervisor',
            email='cap_supervisor@example.com',
            password='Password123!',
            role='supervisor'
        )
        self.technician_user = User.objects.create_user(
            username='cap_technician',
            email='cap_technician@example.com',
            password='Password123!',
            role='technician'
        )
        self.other_admin = User.objects.create_user(
            username='cap_admin_peer',
            email='cap_admin_peer@example.com',
            password='Password123!',
            role='admin'
        )
        self.client_user = User.objects.create_user(
            username='cap_client',
            email='cap_client@example.com',
            password='Password123!',
            role='client'
        )

    def test_admin_can_grant_direct_capabilities_to_staff(self):
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.put(
            f'/api/users/{self.technician_user.id}/capabilities/',
            {
                'capabilities': [
                    TECHNICIAN_DASHBOARD_VIEW,
                    TECHNICIAN_JOBS_VIEW,
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(UserCapabilityGrant.objects.filter(user=self.technician_user).values_list('capability_code', flat=True)),
            {TECHNICIAN_DASHBOARD_VIEW, TECHNICIAN_JOBS_VIEW}
        )
        self.assertIn(TECHNICIAN_DASHBOARD_VIEW, response.data['effective_capabilities'])

    def test_supervisor_can_only_grant_allowed_staff_capabilities(self):
        token = Token.objects.create(user=self.supervisor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.put(
            f'/api/users/{self.technician_user.id}/capabilities/',
            {
                'capabilities': [
                    TECHNICIAN_PROFILE_VIEW,
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserCapabilityGrant.objects.filter(
                user=self.technician_user,
                capability_code=TECHNICIAN_PROFILE_VIEW,
                granted_by=self.supervisor_user,
            ).exists()
        )

    def test_supervisor_cannot_manage_admin_capabilities(self):
        token = Token.objects.create(user=self.supervisor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(f'/api/users/{self.other_admin.id}/capabilities/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_endpoint_includes_effective_capabilities(self):
        UserCapabilityGrant.objects.create(
            user=self.technician_user,
            capability_code=AFTER_SALES_CASES_VIEW,
            granted_by=self.admin_user,
        )
        token = Token.objects.create(user=self.technician_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/api/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(AFTER_SALES_CASES_VIEW, response.data['capabilities'])

    def test_available_capabilities_are_scoped_to_the_target_staff_role(self):
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(f'/api/users/{self.technician_user.id}/capabilities/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        available_codes = {item['code'] for item in response.data['available_capabilities']}
        self.assertIn(TECHNICIAN_DASHBOARD_VIEW, available_codes)
        self.assertIn(TECHNICIAN_JOBS_VIEW, available_codes)
        self.assertIn(TECHNICIAN_PROFILE_VIEW, available_codes)
        self.assertNotIn(AFTER_SALES_DASHBOARD_VIEW, available_codes)
        self.assertNotIn(MANAGE_STAFF_CAPABILITIES, available_codes)

    def test_direct_staff_capabilities_replace_default_staff_navigation(self):
        UserCapabilityGrant.objects.create(
            user=self.technician_user,
            capability_code=TECHNICIAN_PROFILE_VIEW,
            granted_by=self.admin_user,
        )
        token = Token.objects.create(user=self.technician_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/api/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['capabilities'], [TECHNICIAN_PROFILE_VIEW])

    def test_admin_cannot_manage_client_capabilities(self):
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(f'/api/users/{self.client_user.id}/capabilities/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_without_directory_capability_cannot_list_users(self):
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_grant_directory_capability_to_admin(self):
        token = Token.objects.create(user=self.superadmin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.put(
            f'/api/users/{self.admin_user.id}/capabilities/',
            {
                'capabilities': [
                    USER_DIRECTORY_VIEW,
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserCapabilityGrant.objects.filter(
                user=self.admin_user,
                capability_code=USER_DIRECTORY_VIEW,
                granted_by=self.superadmin_user,
            ).exists()
        )
        self.assertIn(USER_DIRECTORY_VIEW, response.data['effective_capabilities'])

    def test_admin_with_directory_capability_can_list_all_users(self):
        UserCapabilityGrant.objects.create(
            user=self.admin_user,
            capability_code=USER_DIRECTORY_VIEW,
            granted_by=self.superadmin_user,
        )
        token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = {item['username'] for item in response.data}
        self.assertIn(self.admin_user.username, usernames)
        self.assertIn(self.supervisor_user.username, usernames)
        self.assertIn(self.client_user.username, usernames)
