from django.test import TestCase
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.utils import timezone
from notifications.models import Notification
from users.models import User
from users.models import UserCapabilityGrant
from users.rbac import (
    AFTER_SALES_CASES_MANAGE,
    AFTER_SALES_CASES_VIEW,
    AFTER_SALES_DASHBOARD_VIEW,
    SUPERVISOR_TICKETS_VIEW,
    SUPERVISOR_TRACKING_VIEW,
    TECHNICIAN_PROFILE_VIEW,
)
from . import ors_utils
from services.models import (
    AfterSalesCase as FollowUpCase,
    InspectionChecklist,
    MaintenanceSchedule,
    ServiceType,
    ServiceRequest,
    ServiceTicket,
    ServiceLocation,
    ServiceStatusHistory,
    TechnicianSkill,
    TicketCrewAssignment,
)
from services.sla import evaluate_service_request_sla, evaluate_service_ticket_sla


class RoutingFallbackTests(TestCase):
    def test_get_route_returns_synthetic_route_when_external_calls_fail(self):
        with self.settings(IS_TEST=False):
            with patch('services.ors_utils.client', None):
                with patch('requests.get', side_effect=RuntimeError('network blocked')):
                    route = ors_utils.get_route((121.0244, 14.5547), (121.0200, 14.5600))

        self.assertEqual(route['type'], 'FeatureCollection')
        feature = route['features'][0]
        self.assertEqual(feature['properties']['routing_source'], 'synthetic')
        self.assertTrue(feature['properties']['is_fallback'])
        self.assertEqual(
            feature['geometry']['coordinates'],
            [[121.0244, 14.5547], [121.02, 14.56]],
        )
        segment = feature['properties']['segments'][0]
        self.assertTrue(segment['fallback'])
        self.assertGreater(segment['distance'], 0)
        self.assertGreater(segment['duration'], 0)


class DashboardRoleTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client1',
            password='pass',
            role='client',
            email='client1@example.com',
            phone='+15550000001',
            address='45 Client Street',
        )
        self.admin_user = User.objects.create_user(
            username='admin1',
            password='pass',
            role='admin'
        )
        self.supervisor_user = User.objects.create_user(
            username='sup1',
            password='pass',
            role='supervisor'
        )
        self.follow_up_user = User.objects.create_user(
            username='followup1',
            password='pass',
            role='follow_up'
        )
        self.technician_user = User.objects.create_user(
            username='tech1',
            password='pass',
            role='technician'
        )

        self.service_type = ServiceType.objects.create(
            name='Test Service',
            description='Test service',
            estimated_duration=60,
        )

        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Test request',
            priority='Normal',
            status='Pending'
        )

        self.service_location = ServiceLocation.objects.create(
            request=self.request_obj,
            address='123 Test St',
            city='Testville',
            province='Test',
            latitude=10.0,
            longitude=20.0,
        )

        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.technician_user,
            supervisor=self.supervisor_user,
            scheduled_date=timezone.now().date(),
            status='Not Started',
            priority='Normal',
        )

        self.api_client = APIClient()

    def test_admin_dashboard(self):
        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'admin')
        self.assertIn('overview', response.data)
        self.assertEqual(response.data['overview']['total_tickets'], 1)
        self.assertIn('client_schedule', response.data)
        self.assertEqual(len(response.data['client_schedule']), 1)
        self.assertEqual(response.data['client_schedule'][0]['id'], self.ticket.id)

    def test_admin_stats_dashboard_prefers_full_names(self):
        self.client_user.first_name = 'Mia'
        self.client_user.last_name = 'Dela Cruz'
        self.client_user.save(update_fields=['first_name', 'last_name'])
        self.technician_user.first_name = 'Marco'
        self.technician_user.last_name = 'Reyes'
        self.technician_user.save(update_fields=['first_name', 'last_name'])

        self.api_client.force_authenticate(user=self.admin_user)
        response = self.api_client.get('/api/dashboard/stats/', {'role': 'admin'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['client_schedule'][0]['client'], 'Mia Dela Cruz')
        self.assertEqual(response.data['client_schedule'][0]['assigned_technician'], 'Marco Reyes')

    def test_supervisor_dashboard(self):
        self.api_client.force_authenticate(user=self.supervisor_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'supervisor')
        self.assertEqual(response.data['overview']['team_tickets'], 1)
        self.assertEqual(len(response.data['technician_performance']), 1)

    def test_technician_dashboard(self):
        self.api_client.force_authenticate(user=self.technician_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'technician')
        self.assertEqual(response.data['overview']['total_assigned'], 1)
        # ensure active ticket appears in active_work
        self.assertEqual(len(response.data['active_work']), 1)
        self.assertEqual(response.data['active_work'][0]['id'], self.ticket.id)

    def test_supervisor_dashboard_tickets_listed(self):
        self.api_client.force_authenticate(user=self.supervisor_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'supervisor')
        self.assertEqual(response.data['overview']['team_tickets'], 1)
        self.assertTrue(any(t['id'] == self.ticket.id for t in response.data['recent_tickets']))

    def test_invalid_role_returns_bad_request(self):
        unknown_user = User.objects.create_user(
            username='unknown',
            password='pass',
            role='client'
        )
        # monkeypatch role to invalid role for runtime behavior
        unknown_user.role = 'ghost'
        unknown_user.save()

        self.api_client.force_authenticate(user=unknown_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid role', response.data['error'])

    def test_client_dashboard_with_data(self):
        self.api_client.force_authenticate(user=self.client_user)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'client')
        self.assertEqual(response.data['status_breakdown']['pending'], 1)

    def test_client_dashboard_no_requests_boundary(self):
        client2 = User.objects.create_user(
            username='client2',
            password='pass',
            role='client'
        )
        self.api_client.force_authenticate(user=client2)
        response = self.api_client.get('/api/services/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'client')
        self.assertEqual(response.data['status_breakdown']['pending'], 0)

    def test_follow_up_dashboard(self):
        self.ticket.status = 'Completed'
        self.ticket.completed_date = timezone.now()
        self.ticket.save(update_fields=['status', 'completed_date'])
        candidate_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Second completed request',
            priority='Normal',
            status='Completed'
        )
        ServiceLocation.objects.create(
            request=candidate_request,
            address='456 Callback Ave',
            city='Followup City',
            province='Metro Manila',
            latitude=11.0,
            longitude=21.0,
        )
        candidate_ticket = ServiceTicket.objects.create(
            request=candidate_request,
            scheduled_date=timezone.now().date(),
            status='Completed',
            priority='Normal',
            completed_date=timezone.now(),
        )
        case = FollowUpCase.objects.create(
            service_ticket=self.ticket,
            client=self.client_user,
            assigned_to=self.follow_up_user,
            created_by=self.admin_user,
            case_type='follow_up',
            status='open',
            priority='normal',
            summary='Customer requested a callback'
        )

        self.api_client.force_authenticate(user=self.follow_up_user)
        response = self.api_client.get('/api/services/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'follow_up')
        self.assertEqual(response.data['overview']['total_cases'], 1)
        self.assertEqual(response.data['recent_cases'][0]['id'], case.id)
        self.assertEqual(response.data['recent_cases'][0]['client_email'], 'client1@example.com')
        self.assertEqual(response.data['recent_cases'][0]['client_phone'], '+15550000001')
        self.assertEqual(response.data['recent_cases'][0]['service_address'], '123 Test St')
        self.assertEqual(response.data['overview']['follow_up_candidates'], 1)
        self.assertEqual(response.data['follow_up_candidates'][0]['ticket_id'], candidate_ticket.id)
        self.assertEqual(response.data['follow_up_candidates'][0]['client_phone'], '+15550000001')
        self.assertEqual(response.data['follow_up_candidates'][0]['service_address'], '456 Callback Ave')


class ServiceRequestTicketLifecycleTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='request-client',
            password='pass',
            role='client',
        )
        self.admin_user = User.objects.create_user(
            username='request-admin',
            password='pass',
            role='admin',
        )
        self.service_type = ServiceType.objects.create(
            name='Installation',
            description='Installation service',
            estimated_duration=90,
        )
        self.other_client_user = User.objects.create_user(
            username='other-client',
            password='pass',
            role='client',
        )
        self.technician_user = User.objects.create_user(
            username='request-tech',
            password='pass',
            role='technician',
        )

    def test_creating_request_stays_pending_until_reviewed(self):
        self.client.force_authenticate(user=self.client_user)

        response = self.client.post(
            '/api/services/service-requests/',
            {
                'client': self.other_client_user.id,
                'service_type': self.service_type.id,
                'description': 'Need an installation visit',
                'priority': 'Normal',
                'location_address': '123 Workflow Street',
                'location_city': 'Makati',
                'location_province': 'Metro Manila',
                'latitude': '14.554700',
                'longitude': '121.024400',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=response.data['id'])
        self.assertEqual(request_obj.client, self.client_user)
        self.assertEqual(request_obj.status, 'Pending')
        self.assertFalse(request_obj.auto_ticket_created)
        self.assertEqual(ServiceTicket.objects.filter(request=request_obj).count(), 0)
        self.assertEqual(ServiceStatusHistory.objects.filter(ticket__request=request_obj).count(), 0)
        self.assertTrue(hasattr(request_obj, 'location'))
        self.assertEqual(request_obj.location.address, '123 Workflow Street')
        self.assertEqual(float(request_obj.location.latitude), 14.5547)
        self.assertEqual(float(request_obj.location.longitude), 121.0244)

    def test_legacy_request_payload_is_mapped_and_persisted(self):
        self.client.force_authenticate(user=self.client_user)

        response = self.client.post(
            '/api/services/service-requests/',
            {
                'service': self.service_type.name,
                'notes': 'Legacy request payload still works',
                'lat': '14.600000',
                'lng': '121.050000',
                'locationDesc': 'Legacy landmark payload',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=response.data['id'])
        self.assertEqual(request_obj.service_type, self.service_type)
        self.assertEqual(request_obj.description, 'Legacy request payload still works')
        self.assertEqual(request_obj.location.address, 'Legacy landmark payload')
        self.assertEqual(request_obj.location.city, 'Unspecified')
        self.assertEqual(request_obj.location.province, 'Unspecified')

    def test_high_precision_coordinates_are_rounded_for_service_request(self):
        self.client.force_authenticate(user=self.client_user)

        response = self.client.post(
            '/api/services/service-requests/',
            {
                'service_type': self.service_type.id,
                'description': 'High precision map coordinates',
                'priority': 'Normal',
                'location_address': 'Precision Street',
                'location_city': 'Makati',
                'location_province': 'Metro Manila',
                'latitude': '14.599499999987',
                'longitude': '120.984200000019',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=response.data['id'])
        self.assertEqual(request_obj.location.latitude, Decimal('14.599500'))
        self.assertEqual(request_obj.location.longitude, Decimal('120.984200'))

    def test_frontend_payload_with_optional_nulls_creates_request(self):
        self.client.force_authenticate(user=self.client_user)

        response = self.client.post(
            '/api/services/service-requests/',
            {
                'service_type': self.service_type.id,
                'description': 'Frontend payload with optional fields omitted',
                'priority': 'Normal',
                'preferred_date': None,
                'preferred_time_slot': None,
                'scheduling_notes': None,
                'location_address': '123 Solar Street, Green City',
                'location_city': '',
                'location_province': '',
                'latitude': '14.599499999987',
                'longitude': '120.984200000019',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=response.data['id'])
        self.assertIsNone(request_obj.preferred_date)
        self.assertIsNone(request_obj.preferred_time_slot)
        self.assertIsNone(request_obj.scheduling_notes)
        self.assertEqual(request_obj.location.address, '123 Solar Street, Green City')
        self.assertEqual(request_obj.location.city, 'Unspecified')
        self.assertEqual(request_obj.location.province, 'Unspecified')
        self.assertEqual(request_obj.location.latitude, Decimal('14.599500'))
        self.assertEqual(request_obj.location.longitude, Decimal('120.984200'))

    def test_completed_ticket_becomes_heatmap_ready(self):
        self.client.force_authenticate(user=self.client_user)

        create_response = self.client.post(
            '/api/services/service-requests/',
            {
                'service_type': self.service_type.id,
                'description': 'Heatmap ready workflow',
                'priority': 'Normal',
                'location_address': '456 Completion Avenue',
                'location_city': 'Pasig',
                'location_province': 'Metro Manila',
                'latitude': '14.576400',
                'longitude': '121.085100',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=create_response.data['id'])

        self.client.force_authenticate(user=self.admin_user)
        approve_response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        ticket = ServiceTicket.objects.get(request=request_obj)
        ticket.technician = self.technician_user
        ticket.save(update_fields=['technician'])

        self.client.force_authenticate(user=self.technician_user)
        start_response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/start_work/',
            {},
            format='json',
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/complete_work/',
            {},
            format='json',
        )

        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(ticket.status, 'Completed')
        self.assertIsNotNone(ticket.completed_date)
        self.assertEqual(request_obj.status, 'Completed')

        self.client.force_authenticate(user=self.admin_user)
        heatmap_response = self.client.get('/api/services/coverage-heatmap/service_density/')

        self.assertEqual(heatmap_response.status_code, status.HTTP_200_OK)
        self.assertEqual(heatmap_response.data['total_points'], 1)
        self.assertEqual(heatmap_response.data['heatmap_data'][0]['address'], '456 Completion Avenue')
        self.assertEqual(heatmap_response.data['heatmap_data'][0]['count'], 1)


class FollowUpCaseApiTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='follow-up-client',
            password='pass',
            role='client',
            email='followup-client@example.com',
            phone='+15550000002',
            address='100 Queue Lane',
        )
        self.admin_user = User.objects.create_user(
            username='follow-up-admin',
            password='pass',
            role='admin',
        )
        self.follow_up_user = User.objects.create_user(
            username='follow-up-agent',
            password='pass',
            role='follow_up',
        )
        self.service_type = ServiceType.objects.create(
            name='Maintenance',
            description='Maintenance service',
            estimated_duration=45,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Routine maintenance request',
            priority='Normal',
            status='Completed',
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='321 Service Road',
            city='Makati',
            province='Metro Manila',
            latitude=14.554700,
            longitude=121.024400,
        )
        self.completed_ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=None,
            supervisor=None,
            scheduled_date=timezone.now().date(),
            status='Completed',
            priority='Normal',
            completed_date=timezone.now(),
        )
        self.pending_ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=None,
            supervisor=None,
            scheduled_date=timezone.now().date(),
            status='Not Started',
            priority='Normal',
        )

    def test_follow_up_user_can_create_case_for_completed_ticket(self):
        self.client.force_authenticate(user=self.follow_up_user)

        response = self.client.post(
            '/api/services/follow-up-cases/',
            {
                'service_ticket': self.completed_ticket.id,
                'case_type': 'follow_up',
                'status': 'open',
                'priority': 'high',
                'summary': 'Confirm installation quality',
                'details': 'Customer requested a follow-up call.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        case = FollowUpCase.objects.get(id=response.data['id'])
        self.assertEqual(case.client, self.client_user)
        self.assertEqual(case.created_by, self.follow_up_user)
        self.assertEqual(case.assigned_to, self.follow_up_user)
        self.assertEqual(case.service_ticket, self.completed_ticket)
        self.assertEqual(response.data['client_email'], 'followup-client@example.com')
        self.assertEqual(response.data['client_phone'], '+15550000002')
        self.assertEqual(response.data['service_address'], '321 Service Road')

    def test_follow_up_case_creation_rejects_non_completed_ticket(self):
        self.client.force_authenticate(user=self.follow_up_user)

        response = self.client.post(
            '/api/services/follow-up-cases/',
            {
                'service_ticket': self.pending_ticket.id,
                'case_type': 'complaint',
                'status': 'open',
                'priority': 'normal',
                'summary': 'Attempted early complaint case',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('service_ticket', response.data)
        self.assertEqual(FollowUpCase.objects.count(), 0)

    def test_approving_auto_created_request_does_not_create_duplicate_ticket(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need a follow-up visit',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.now().date(),
            status='Not Started',
        )
        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status='Not Started',
            changed_by=self.client_user,
            notes='Initial ticket created',
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'Approved')
        self.assertTrue(request_obj.auto_ticket_created)
        self.assertEqual(ServiceTicket.objects.filter(request=request_obj).count(), 1)
        self.assertEqual(ServiceStatusHistory.objects.filter(ticket__request=request_obj).count(), 1)


class CapabilityBasedAfterSalesAccessTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='capability_admin',
            password='pass',
            role='admin',
        )
        self.capability_user = User.objects.create_user(
            username='capability_user',
            password='pass',
            role='follow_up',
        )
        self.client_user = User.objects.create_user(
            username='capability_client',
            password='pass',
            role='client',
            email='capability-client@example.com',
            phone='+15550000003',
            address='88 Capability Street',
        )
        self.service_type = ServiceType.objects.create(
            name='Capability Service',
            description='Capability-based follow-up access test',
            estimated_duration=60,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Completed request for capability test',
            priority='Normal',
            status='Completed',
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='500 Capability Avenue',
            city='Pasig',
            province='Metro Manila',
            latitude=14.5764,
            longitude=121.0851,
        )
        self.completed_ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            scheduled_date=timezone.now().date(),
            status='Completed',
            priority='Normal',
            completed_date=timezone.now(),
        )

        for capability_code in (
            AFTER_SALES_DASHBOARD_VIEW,
            AFTER_SALES_CASES_VIEW,
            AFTER_SALES_CASES_MANAGE,
        ):
            UserCapabilityGrant.objects.create(
                user=self.capability_user,
                capability_code=capability_code,
                granted_by=self.admin_user,
            )

    def test_capability_granted_user_can_open_after_sales_dashboard(self):
        self.client.force_authenticate(user=self.capability_user)

        response = self.client.get('/api/dashboard/stats/', {'role': 'follow_up'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'follow_up')

    def test_capability_granted_user_can_manage_follow_up_cases(self):
        self.client.force_authenticate(user=self.capability_user)

        response = self.client.post(
            '/api/services/follow-up-cases/',
            {
                'service_ticket': self.completed_ticket.id,
                'case_type': 'follow_up',
                'status': 'open',
                'priority': 'normal',
                'summary': 'Capability-based after-sales case',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['client_email'], 'capability-client@example.com')

    def test_capability_granted_user_can_request_after_sales_ticket_workspace(self):
        self.client.force_authenticate(user=self.capability_user)

        response = self.client.get('/api/services/service-tickets/', {'workspace': 'after_sales'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_results = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(ticket_results), 1)
        self.assertEqual(ticket_results[0]['id'], self.completed_ticket.id)


class StaffWorkspaceCapabilityAccessTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='staff_cap_admin',
            password='pass',
            role='admin',
        )
        self.supervisor_user = User.objects.create_user(
            username='staff_cap_supervisor',
            password='pass',
            role='supervisor',
        )
        self.technician_user = User.objects.create_user(
            username='staff_cap_technician',
            password='pass',
            role='technician',
            status='active',
            is_available=True,
        )
        self.client_user = User.objects.create_user(
            username='staff_cap_client',
            password='pass',
            role='client',
            email='staff-cap-client@example.com',
        )
        self.service_type = ServiceType.objects.create(
            name='Staff Capability Service',
            description='Role-scoped capability access test',
            estimated_duration=60,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Assigned request',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='100 Staff Capability Lane',
            city='Pasig',
            province='Metro Manila',
            latitude=14.5764,
            longitude=121.0851,
        )
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            supervisor=self.supervisor_user,
            technician=self.technician_user,
            scheduled_date=timezone.now().date(),
            status='Not Started',
            priority='Normal',
        )

    def test_supervisor_with_tracking_only_capability_cannot_open_supervisor_dashboard(self):
        UserCapabilityGrant.objects.create(
            user=self.supervisor_user,
            capability_code=SUPERVISOR_TRACKING_VIEW,
            granted_by=self.admin_user,
        )
        self.client.force_authenticate(user=self.supervisor_user)

        dashboard_response = self.client.get('/api/dashboard/stats/', {'role': 'supervisor'})
        tracking_response = self.client.get('/api/tracking/')

        self.assertEqual(dashboard_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(tracking_response.status_code, status.HTTP_200_OK)

    def test_superadmin_can_open_admin_tracking(self):
        superadmin_user = User.objects.create_user(
            username='staff_cap_superadmin',
            password='pass',
            role='superadmin',
        )
        self.client.force_authenticate(user=superadmin_user)

        tracking_response = self.client.get('/api/tracking/')

        self.assertEqual(tracking_response.status_code, status.HTTP_200_OK)

    def test_supervisor_without_tracking_capability_cannot_access_technician_location_feeds(self):
        limited_supervisor = User.objects.create_user(
            username='staff_cap_limited_supervisor',
            password='pass',
            role='supervisor',
        )
        UserCapabilityGrant.objects.create(
            user=limited_supervisor,
            capability_code=SUPERVISOR_TICKETS_VIEW,
            granted_by=self.admin_user,
        )
        self.client.force_authenticate(user=limited_supervisor)

        history_response = self.client.get('/api/services/technician-locations/')
        all_locations_response = self.client.get('/api/services/technician-locations/all_technicians_locations/')

        self.assertEqual(history_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(all_locations_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_with_tracking_capability_can_access_technician_location_feeds(self):
        self.technician_user.current_latitude = 14.5764
        self.technician_user.current_longitude = 121.0851
        self.technician_user.save(update_fields=['current_latitude', 'current_longitude'])
        UserCapabilityGrant.objects.create(
            user=self.supervisor_user,
            capability_code=SUPERVISOR_TRACKING_VIEW,
            granted_by=self.admin_user,
        )
        self.client.force_authenticate(user=self.supervisor_user)

        history_response = self.client.get('/api/services/technician-locations/')
        all_locations_response = self.client.get('/api/services/technician-locations/all_technicians_locations/')

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(all_locations_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(all_locations_response.data), 1)
        self.assertEqual(all_locations_response.data[0]['id'], self.technician_user.id)

    def test_technician_with_profile_only_capability_cannot_open_dashboard_or_jobs(self):
        UserCapabilityGrant.objects.create(
            user=self.technician_user,
            capability_code=TECHNICIAN_PROFILE_VIEW,
            granted_by=self.admin_user,
        )
        self.client.force_authenticate(user=self.technician_user)

        dashboard_response = self.client.get('/api/technician/dashboard/')
        jobs_response = self.client.get('/api/technician/jobs/')
        profile_response = self.client.get('/api/technician/profile/')

        self.assertEqual(dashboard_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(jobs_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)


class OperationalDataAccessTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='ops_client',
            password='pass',
            role='client',
        )
        self.supervisor_user = User.objects.create_user(
            username='ops_supervisor',
            password='pass',
            role='supervisor',
        )

    def test_client_cannot_access_operational_intelligence_endpoints(self):
        self.client.force_authenticate(user=self.client_user)

        endpoints = [
            '/api/services/gis-dashboard/dashboard_data/',
            '/api/services/analytics/',
            '/api/services/technician-performance/',
            '/api/services/demand-forecasts/',
            '/api/services/service-trends/',
            '/api/services/coverage-heatmap/service_density/',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, endpoint)

    def test_supervisor_can_access_operational_dashboards(self):
        self.client.force_authenticate(user=self.supervisor_user)

        for endpoint in (
            '/api/services/gis-dashboard/dashboard_data/',
            '/api/services/analytics/',
            '/api/services/coverage-heatmap/service_density/',
        ):
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK, endpoint)


class CoverageHeatmapTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='heatmap_admin',
            password='pass',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin_user)

        self.client_user = User.objects.create_user(
            username='heatmap_client',
            password='pass',
            role='client'
        )
        self.service_type = ServiceType.objects.create(
            name='Heatmap Service',
            description='Heatmap test service',
            estimated_duration=60
        )

    def test_service_density_route_returns_grouped_hotspots(self):
        first_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Completed request 1',
            priority='Normal',
            status='Completed'
        )
        second_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Completed request 2',
            priority='Normal',
            status='Completed'
        )

        ServiceLocation.objects.create(
            request=first_request,
            address='12 Heatmap Street',
            city='Lagos',
            province='Lagos',
            latitude=6.5001,
            longitude=3.3001
        )
        ServiceLocation.objects.create(
            request=second_request,
            address='12 Heatmap Street',
            city='Lagos',
            province='Lagos',
            latitude=6.5001,
            longitude=3.3001
        )

        response = self.client.get('/api/services/coverage-heatmap/service_density/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_points'], 1)
        self.assertEqual(response.data['max_density'], 2)
        self.assertEqual(response.data['heatmap_data'][0]['count'], 2)


class MaintenanceWorkflowTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='maintenance-client',
            password='pass',
            role='client',
        )
        self.admin_user = User.objects.create_user(
            username='maintenance-admin',
            password='pass',
            role='admin',
        )
        self.follow_up_user = User.objects.create_user(
            username='maintenance-follow-up',
            password='pass',
            role='follow_up',
        )
        self.technician_user = User.objects.create_user(
            username='maintenance-tech',
            password='pass',
            role='technician',
        )
        self.service_type = ServiceType.objects.create(
            name='Installation',
            description='Installation service',
            estimated_duration=90,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Install equipment with maintenance plan',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='789 Service Road',
            city='Pasig',
            province='Metro Manila',
            latitude=14.5764,
            longitude=121.0851,
        )
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

    def test_checklist_submission_and_completion_create_maintenance_schedule(self):
        self.client.force_authenticate(user=self.technician_user)

        checklist_response = self.client.post(
            '/api/checklist/',
            {
                'jobId': self.ticket.id,
                'completed': {'0': True, '1': True, '2': True},
                'notes': 'Installation complete and site assessed.',
                'photos': ['before.jpg', 'after.jpg'],
                'maintenance_required': True,
                'maintenance_profile': 'commercial_area',
                'maintenance_notes': 'Retail frontage with daily dust exposure.',
            },
            format='json',
        )

        self.assertEqual(checklist_response.status_code, status.HTTP_200_OK)
        checklist = InspectionChecklist.objects.get(ticket=self.ticket)
        self.assertTrue(checklist.maintenance_required)
        self.assertEqual(checklist.maintenance_profile, 'commercial_area')
        self.assertEqual(checklist.maintenance_interval_days, 90)

        start_response = self.client.post(
            f'/api/technician/jobs/{self.ticket.id}/status/',
            {'status': 'in_progress'},
            format='json',
        )

        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        complete_response = self.client.post(
            f'/api/technician/jobs/{self.ticket.id}/status/',
            {'status': 'completed'},
            format='json',
        )

        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        schedule = MaintenanceSchedule.objects.get(service_ticket=self.ticket)
        self.ticket.refresh_from_db()
        self.assertEqual(schedule.client, self.client_user)
        self.assertEqual(schedule.service_type, self.service_type)
        self.assertEqual(schedule.interval_days, 90)
        self.assertEqual(
            schedule.next_due_date,
            self.ticket.completed_date.date() + timedelta(days=90),
        )
        self.assertEqual(schedule.notify_on_date, schedule.next_due_date - timedelta(days=14))
        self.assertEqual(schedule.status, 'scheduled')

    def test_due_soon_alerts_create_maintenance_case_notifications_and_dashboard_queue(self):
        InspectionChecklist.objects.create(
            ticket=self.ticket,
            is_completed=True,
            completed_at=timezone.now(),
            completed_by=self.technician_user,
            site_accessible=True,
            electrical_available=True,
            electrical_adequate=True,
            safety_equipment_present=True,
            recommendation='Approved',
            maintenance_required=True,
            maintenance_profile='commercial_area',
            maintenance_interval_days=90,
            maintenance_notes='Commercial site maintenance plan.',
        )

        self.ticket.status = 'Completed'
        self.ticket.completed_date = timezone.now() - timedelta(days=85)
        self.ticket.end_time = self.ticket.completed_date
        self.ticket.save(update_fields=['status', 'completed_date', 'end_time'])
        self.request_obj.status = 'Completed'
        self.request_obj.save(update_fields=['status'])

        schedule = MaintenanceSchedule.objects.create(
            service_ticket=self.ticket,
            client=self.client_user,
            service_type=self.service_type,
            maintenance_profile='commercial_area',
            interval_days=90,
            follow_up_window_days=14,
            last_service_date=(timezone.localdate() - timedelta(days=85)),
            next_due_date=timezone.localdate() + timedelta(days=5),
            notify_on_date=timezone.localdate(),
            status='scheduled',
            maintenance_notes='Commercial site maintenance plan.',
        )

        call_command('send_maintenance_alerts')

        schedule.refresh_from_db()
        self.assertEqual(schedule.status, 'due_soon')
        self.assertIsNotNone(schedule.due_soon_notified_at)
        case = FollowUpCase.objects.get(service_ticket=self.ticket, case_type='maintenance')
        self.assertEqual(case.status, 'open')
        self.assertEqual(case.due_date, schedule.next_due_date)

        recipients = Notification.objects.filter(ticket=self.ticket, type='reminder')
        self.assertEqual(recipients.count(), 2)

        self.client.force_authenticate(user=self.follow_up_user)
        response = self.client.get('/api/services/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['overview']['maintenance_due_soon'], 1)
        self.assertEqual(len(response.data['maintenance_queue']), 1)
        self.assertEqual(response.data['maintenance_queue'][0]['ticket_id'], self.ticket.id)


class SchedulingWarrantyAndAssignmentTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='structured-client',
            password='pass',
            role='client',
        )
        self.admin_user = User.objects.create_user(
            username='structured-admin',
            password='pass',
            role='admin',
        )
        self.supervisor_user = User.objects.create_user(
            username='structured-supervisor',
            password='pass',
            role='supervisor',
        )
        self.follow_up_user = User.objects.create_user(
            username='structured-follow-up',
            password='pass',
            role='follow_up',
        )
        self.technician_user = User.objects.create_user(
            username='structured-tech',
            password='pass',
            role='technician',
            status='active',
            is_available=True,
            current_latitude='14.560000',
            current_longitude='121.020000',
        )
        self.backup_technician = User.objects.create_user(
            username='backup-tech',
            password='pass',
            role='technician',
            status='active',
            is_available=True,
            current_latitude='14.580000',
            current_longitude='121.030000',
        )
        self.service_type = ServiceType.objects.create(
            name='Structured Service',
            description='Structured service type',
            estimated_duration=120,
        )
        TechnicianSkill.objects.create(
            technician=self.technician_user,
            service_type=self.service_type,
            skill_level='expert',
        )
        TechnicianSkill.objects.create(
            technician=self.backup_technician,
            service_type=self.service_type,
            skill_level='beginner',
        )

    def test_request_preferences_seed_ticket_schedule_and_reschedule_workflow(self):
        preferred_date = timezone.localdate() + timedelta(days=3)
        self.client.force_authenticate(user=self.client_user)

        create_response = self.client.post(
            '/api/services/service-requests/',
            {
                'service_type': self.service_type.id,
                'description': 'Need an appointment slot',
                'priority': 'Normal',
                'preferred_date': preferred_date.isoformat(),
                'preferred_time_slot': 'afternoon',
                'scheduling_notes': 'Please avoid lunch hours.',
                'location_address': '100 Scheduling Street',
                'location_city': 'Pasig',
                'location_province': 'Metro Manila',
                'latitude': '14.572000',
                'longitude': '121.049000',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(id=create_response.data['id'])

        self.client.force_authenticate(user=self.admin_user)
        approve_response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        ticket = ServiceTicket.objects.get(request=request_obj)
        self.assertEqual(ticket.scheduled_date, preferred_date)
        self.assertEqual(ticket.scheduled_time_slot, 'afternoon')
        self.assertEqual(ticket.scheduled_time.strftime('%H:%M'), '15:00')

        self.client.force_authenticate(user=self.client_user)
        reschedule_response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/request_reschedule/',
            {
                'preferred_date': (preferred_date + timedelta(days=2)).isoformat(),
                'preferred_time_slot': 'evening',
                'reason': 'Building access is only allowed after 5 PM.',
            },
            format='json',
        )

        self.assertEqual(reschedule_response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertTrue(ticket.reschedule_requested)
        self.assertEqual(ticket.reschedule_reason, 'Building access is only allowed after 5 PM.')
        self.assertEqual(request_obj.preferred_time_slot, 'evening')

        self.client.force_authenticate(user=self.admin_user)
        confirm_response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/reschedule/',
            {
                'scheduled_date': (preferred_date + timedelta(days=2)).isoformat(),
                'scheduled_time_slot': 'evening',
                'notes': 'Confirmed with dispatch.',
            },
            format='json',
        )

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertFalse(ticket.reschedule_requested)
        self.assertEqual(ticket.scheduled_time_slot, 'evening')
        self.assertEqual(ticket.scheduled_time.strftime('%H:%M'), '18:00')

    def test_checklist_submission_tracks_warranty_and_proof_media(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Install with warranty',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='200 Warranty Lane',
            city='Quezon City',
            province='Metro Manila',
            latitude='14.650000',
            longitude='121.040000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.technician_user)
        checklist_response = self.client.post(
            '/api/checklist/',
            {
                'jobId': ticket.id,
                'completed': {'0': True, '1': True},
                'notes': 'Captured completion evidence.',
                'photos': ['before.jpg'],
                'videos': ['walkthrough.mp4'],
                'warranty_provided': True,
                'warranty_period_days': 60,
                'warranty_notes': 'Labor warranty only.',
                'maintenance_required': False,
            },
            format='json',
        )

        self.assertEqual(checklist_response.status_code, status.HTTP_200_OK)
        checklist = InspectionChecklist.objects.get(ticket=ticket)
        self.assertEqual(len(checklist.proof_media), 2)
        self.assertTrue(any(item['type'] == 'video' for item in checklist.proof_media))
        self.assertTrue(checklist.warranty_provided)
        self.assertEqual(checklist.warranty_period_days, 60)

        start_response = self.client.post(
            f'/api/technician/jobs/{ticket.id}/status/',
            {'status': 'in_progress'},
            format='json',
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post(
            f'/api/technician/jobs/{ticket.id}/status/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertEqual(ticket.warranty_status, 'active')
        self.assertEqual(ticket.warranty_period_days, 60)
        self.assertEqual(ticket.warranty_end_date, ticket.completed_date.date() + timedelta(days=60))

    def test_warranty_case_requires_active_coverage(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Completed work',
            priority='Normal',
            status='Completed',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate(),
            status='Completed',
            completed_date=timezone.now(),
            priority='Normal',
        )

        self.client.force_authenticate(user=self.follow_up_user)
        rejected = self.client.post(
            '/api/services/follow-up-cases/',
            {
                'service_ticket': ticket.id,
                'case_type': 'warranty',
                'summary': 'Customer says part failed',
                'priority': 'high',
            },
            format='json',
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        ticket.warranty_status = 'active'
        ticket.warranty_period_days = 45
        ticket.warranty_start_date = timezone.localdate()
        ticket.warranty_end_date = timezone.localdate() + timedelta(days=45)
        ticket.save(update_fields=[
            'warranty_status',
            'warranty_period_days',
            'warranty_start_date',
            'warranty_end_date',
            'updated_at',
        ])

        accepted = self.client.post(
            '/api/services/follow-up-cases/',
            {
                'service_ticket': ticket.id,
                'case_type': 'warranty',
                'summary': 'Customer says part failed',
                'priority': 'high',
            },
            format='json',
        )
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)

    def test_completion_flow_auto_creates_follow_up_case_from_checklist_handoff(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need revisit after completion',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='250 Handoff Avenue',
            city='Pasig',
            province='Metro Manila',
            latitude='14.575000',
            longitude='121.035000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )
        due_date = timezone.localdate() + timedelta(days=4)

        self.client.force_authenticate(user=self.technician_user)
        checklist_response = self.client.post(
            '/api/checklist/',
            {
                'jobId': ticket.id,
                'completed': {'0': True, '1': True},
                'notes': 'System commissioned, but customer wants a final alignment revisit.',
                'maintenance_required': False,
                'warranty_provided': True,
                'warranty_period_days': 30,
                'warranty_notes': 'Standard warranty applies.',
                'follow_up_required': True,
                'follow_up_case_type': 'revisit',
                'follow_up_due_date': due_date.isoformat(),
                'follow_up_summary': 'Return to fine tune panel alignment.',
                'follow_up_details': 'Customer requested one more visit after observing roof shading.',
            },
            format='json',
        )
        self.assertEqual(checklist_response.status_code, status.HTTP_200_OK)

        start_response = self.client.post(
            f'/api/technician/jobs/{ticket.id}/status/',
            {'status': 'in_progress'},
            format='json',
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post(
            f'/api/technician/jobs/{ticket.id}/status/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        follow_up_case = FollowUpCase.objects.get(service_ticket=ticket, creation_source='completion_flow')
        self.assertEqual(follow_up_case.case_type, 'revisit')
        self.assertEqual(follow_up_case.status, 'open')
        self.assertEqual(follow_up_case.created_by, self.technician_user)
        self.assertTrue(follow_up_case.requires_revisit)
        self.assertEqual(follow_up_case.summary, 'Return to fine tune panel alignment.')
        self.assertEqual(follow_up_case.due_date, due_date)

        self.client.force_authenticate(user=self.follow_up_user)
        dashboard_response = self.client.get('/api/services/dashboard/', format='json')
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['overview']['completion_handoffs'], 1)
        self.assertEqual(dashboard_response.data['overview']['follow_up_candidates'], 0)
        self.assertEqual(dashboard_response.data['recent_cases'][0]['creation_source'], 'completion_flow')

    def test_updating_completed_checklist_updates_existing_completion_follow_up_case(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need complaint handoff',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='255 Recovery Avenue',
            city='Taguig',
            province='Metro Manila',
            latitude='14.540000',
            longitude='121.050000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Completed',
            priority='Normal',
            completed_date=timezone.now(),
        )

        self.client.force_authenticate(user=self.technician_user)
        initial_response = self.client.post(
            '/api/checklist/',
            {
                'jobId': ticket.id,
                'completed': {'0': True, '1': True},
                'notes': 'Client asked for a manager callback.',
                'maintenance_required': False,
                'warranty_provided': False,
                'follow_up_required': True,
                'follow_up_case_type': 'complaint',
                'follow_up_summary': 'Customer is dissatisfied with the finish quality.',
                'follow_up_details': 'Escalate to after-sales for customer recovery.',
            },
            format='json',
        )
        self.assertEqual(initial_response.status_code, status.HTTP_200_OK)

        updated_response = self.client.post(
            '/api/checklist/',
            {
                'jobId': ticket.id,
                'completed': {'0': True, '1': True},
                'notes': 'Client asked for a same-day callback from management.',
                'maintenance_required': False,
                'warranty_provided': False,
                'follow_up_required': True,
                'follow_up_case_type': 'complaint',
                'follow_up_summary': 'Urgent customer recovery callback needed.',
                'follow_up_details': 'Customer remains dissatisfied and wants a manager response today.',
            },
            format='json',
        )
        self.assertEqual(updated_response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            FollowUpCase.objects.filter(service_ticket=ticket, creation_source='completion_flow').count(),
            1,
        )
        follow_up_case = FollowUpCase.objects.get(service_ticket=ticket, creation_source='completion_flow')
        self.assertEqual(follow_up_case.summary, 'Urgent customer recovery callback needed.')
        self.assertIn('manager response today', follow_up_case.details)

    def test_auto_assign_returns_smart_assignment_metadata(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need smart dispatch',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='300 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/auto_assign/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.smart_assignment_score)
        self.assertTrue(ticket.smart_assignment_summary)
        self.assertIn('assignment_score', response.data)
        self.assertGreater(len(response.data['candidate_ranking']), 0)

    @patch('notifications.firebase_utils.send_push_notification', return_value=True)
    @patch('services.views.send_notification_email')
    def test_auto_assign_notifies_assignee_and_supervisor_team(self, mock_send_email, mock_send_push):
        existing_team_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Existing team workload',
            priority='Normal',
            status='Approved',
        )
        ServiceTicket.objects.create(
            request=existing_team_request,
            technician=self.backup_technician,
            supervisor=self.supervisor_user,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='In Progress',
            priority='Normal',
        )

        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need smart dispatch with team awareness',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='302 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
            supervisor=self.supervisor_user,
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/auto_assign/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignee_notification = Notification.objects.filter(
            user=self.technician_user,
            ticket=ticket,
            type='ticket_assigned',
        ).first()
        team_notification = Notification.objects.filter(
            user=self.backup_technician,
            ticket=ticket,
            type='ticket_assigned',
        ).first()

        self.assertIsNotNone(assignee_notification)
        self.assertIn(f'auto-assigned to ticket #{ticket.id}', assignee_notification.message)
        self.assertIsNotNone(team_notification)
        self.assertIn(f'Ticket #{ticket.id} was auto-assigned to {self.technician_user.username}', team_notification.message)
        self.assertEqual(mock_send_email.call_count, 1)
        self.assertGreaterEqual(mock_send_push.call_count, 2)

    def test_auto_assign_returns_conflict_when_no_eligible_technician_exists(self):
        self.technician_user.is_available = False
        self.technician_user.save(update_fields=['is_available'])
        self.backup_technician.is_available = False
        self.backup_technician.save(update_fields=['is_available'])

        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Need smart dispatch but nobody is available',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='400 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/auto_assign/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['success'], False)
        self.assertIn('No available technicians', response.data['error'])

    def test_supervisor_can_assign_ticket_when_status_is_assignable(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Supervisor dispatch assignment',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='301 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
            supervisor=self.supervisor_user,
        )

        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/assign/',
            {'technician_id': self.technician_user.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertEqual(ticket.technician, self.technician_user)

    def test_supervisor_can_assign_ticket_with_crew_and_crew_member_can_work_it(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Supervisor dispatch assignment with crew',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='301 Crew Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
            supervisor=self.supervisor_user,
        )

        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/assign/',
            {
                'technician_id': self.technician_user.id,
                'crew_ids': [self.backup_technician.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.backup_technician.refresh_from_db()

        self.assertEqual(ticket.technician, self.technician_user)
        self.assertTrue(
            TicketCrewAssignment.objects.filter(
                ticket=ticket,
                technician=self.backup_technician,
            ).exists()
        )
        self.assertEqual(len(response.data['crew_members']), 1)
        self.assertFalse(self.backup_technician.is_available)

        self.client.force_authenticate(user=self.backup_technician)
        jobs_response = self.client.get('/api/technician/jobs/')
        self.assertEqual(jobs_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(jobs_response.data), 1)
        self.assertEqual(jobs_response.data[0]['assignment_role'], 'crew')

        start_response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/start_work/',
            {},
            format='json',
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'In Progress')

    def test_supervisor_approval_creates_supervisor_owned_ticket(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Supervisor-owned approval flow',
            priority='Normal',
            status='Pending',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='302 Supervisor Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )

        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket = ServiceTicket.objects.get(request=request_obj)
        self.assertEqual(ticket.supervisor, self.supervisor_user)

    def test_admin_approval_keeps_ticket_visible_in_supervisor_queue_until_claimed(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Admin-created queue work',
            priority='Normal',
            status='Pending',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='401 Shared Queue Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )

        self.client.force_authenticate(user=self.admin_user)
        approve_response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )

        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        ticket = ServiceTicket.objects.get(request=request_obj)
        self.assertIsNone(ticket.supervisor)

        self.client.force_authenticate(user=self.supervisor_user)
        queue_response = self.client.get('/api/services/service-tickets/')
        dashboard_response = self.client.get('/api/services/dashboard/')

        self.assertEqual(queue_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertIn(ticket.id, [item['id'] for item in queue_response.data['results']])
        self.assertTrue(any(item['id'] == ticket.id for item in dashboard_response.data['recent_tickets']))

    def test_supervisor_without_ticket_queue_capability_cannot_approve_request(self):
        limited_supervisor = User.objects.create_user(
            username='tracking_only_supervisor',
            password='pass',
            role='supervisor',
        )
        UserCapabilityGrant.objects.create(
            user=limited_supervisor,
            capability_code=SUPERVISOR_TRACKING_VIEW,
            granted_by=self.admin_user,
        )

        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Approval should be blocked',
            priority='Normal',
            status='Pending',
        )

        self.client.force_authenticate(user=limited_supervisor)
        response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/approve/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ServiceTicket.objects.filter(request=request_obj).exists())

    def test_checklist_accepts_uploaded_proof_files(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Checklist proof upload',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

        photo = SimpleUploadedFile(
            'site-photo.jpg',
            b'fake-image-bytes',
            content_type='image/jpeg',
        )
        video = SimpleUploadedFile(
            'site-video.mp4',
            b'fake-video-bytes',
            content_type='video/mp4',
        )

        self.client.force_authenticate(user=self.technician_user)
        response = self.client.post(
            '/api/checklist/',
            {
                'jobId': ticket.id,
                'completed': '{"0": true, "1": true}',
                'notes': 'Uploaded proof files are attached.',
                'maintenance_required': 'false',
                'warranty_provided': 'false',
                'follow_up_required': 'false',
                'photo_files': [photo],
                'video_files': [video],
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checklist = InspectionChecklist.objects.get(ticket=ticket)
        self.assertEqual(len(checklist.proof_media), 2)
        self.assertTrue(all(item['url'].startswith('http://testserver/media/checklists/') for item in checklist.proof_media))

    @patch('notifications.firebase_utils.send_push_notification', return_value=True)
    @patch('services.views.send_notification_email')
    def test_assign_notifies_assignee_and_existing_team_members(self, mock_send_email, mock_send_push):
        existing_team_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Existing scheduled work',
            priority='Normal',
            status='Approved',
        )
        ServiceTicket.objects.create(
            request=existing_team_request,
            technician=self.backup_technician,
            supervisor=self.supervisor_user,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
        )

        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Supervisor dispatch assignment with team awareness',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=request_obj,
            address='303 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.565000',
            longitude='121.025000',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
            supervisor=self.supervisor_user,
        )

        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/assign/',
            {'technician_id': self.technician_user.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignee_notification = Notification.objects.filter(
            user=self.technician_user,
            ticket=ticket,
            type='ticket_assigned',
        ).first()
        team_notification = Notification.objects.filter(
            user=self.backup_technician,
            ticket=ticket,
            type='ticket_assigned',
        ).first()

        self.assertIsNotNone(assignee_notification)
        self.assertIn(f'assigned to ticket #{ticket.id}', assignee_notification.message)
        self.assertIsNotNone(team_notification)
        self.assertIn(f'Ticket #{ticket.id} was assigned to {self.technician_user.username}', team_notification.message)
        self.assertEqual(mock_send_email.call_count, 1)
        self.assertGreaterEqual(mock_send_push.call_count, 2)

    def test_supervisor_tracking_only_returns_owned_open_tickets(self):
        owned_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Owned supervisor ticket',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=owned_request,
            address='302 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.566000',
            longitude='121.026000',
        )
        owned_ticket = ServiceTicket.objects.create(
            request=owned_request,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='On Hold',
            priority='Normal',
            supervisor=self.supervisor_user,
        )

        other_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Unowned supervisor ticket',
            priority='Normal',
            status='Approved',
        )
        ServiceLocation.objects.create(
            request=other_request,
            address='303 Dispatch Avenue',
            city='Makati',
            province='Metro Manila',
            latitude='14.567000',
            longitude='121.027000',
        )
        other_ticket = ServiceTicket.objects.create(
            request=other_request,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.get('/api/tracking')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_ids = [item['id'] for item in response.data['ticketMarkers']]
        self.assertIn(owned_ticket.id, ticket_ids)
        self.assertNotIn(other_ticket.id, ticket_ids)

    def test_complete_work_requires_in_progress_ticket(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Completion guard',
            priority='Normal',
            status='Approved',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.technician_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/complete_work/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot move ticket', response.data['error'])

    def test_parts_request_requires_started_work(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Parts guard',
            priority='Normal',
            status='Approved',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.technician_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/request_parts/',
            {'parts': 'Replacement sensor'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be requested after work has started', response.data['error'])

    def test_cancel_request_cascades_to_open_ticket(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Cancel request cascade',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )
        self.technician_user.is_available = False
        self.technician_user.save(update_fields=['is_available'])

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/cancel/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_obj.refresh_from_db()
        ticket.refresh_from_db()
        self.technician_user.refresh_from_db()
        self.assertEqual(request_obj.status, 'Cancelled')
        self.assertEqual(ticket.status, 'Cancelled')
        self.assertTrue(self.technician_user.is_available)
        self.assertTrue(ServiceStatusHistory.objects.filter(ticket=ticket, status='Cancelled').exists())

    def test_technician_cannot_cancel_assigned_request(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Technician cancellation guard',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

        self.client.force_authenticate(user=self.technician_user)
        response = self.client.post(
            f'/api/services/service-requests/{request_obj.id}/cancel/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        request_obj.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(request_obj.status, 'Approved')
        self.assertEqual(ticket.status, 'Not Started')

    def test_client_cannot_request_reschedule_after_work_starts(self):
        request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Reschedule guard',
            priority='Normal',
            status='In Progress',
            preferred_date=timezone.localdate() + timedelta(days=1),
            preferred_time_slot='morning',
        )
        ticket = ServiceTicket.objects.create(
            request=request_obj,
            technician=self.technician_user,
            scheduled_date=timezone.localdate(),
            status='In Progress',
            start_time=timezone.now(),
            priority='Normal',
        )

        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(
            f'/api/services/service-tickets/{ticket.id}/request_reschedule/',
            {
                'preferred_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
                'preferred_time_slot': 'afternoon',
                'reason': 'Need another slot',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('before work has started', response.data['error'])


class SLAEvaluationTests(TestCase):
    def setUp(self):
        self.now = timezone.make_aware(datetime(2026, 3, 22, 10, 0, 0))
        self.client_user = User.objects.create_user(
            username='sla-client',
            password='pass',
            role='client',
        )
        self.technician_user = User.objects.create_user(
            username='sla-tech',
            password='pass',
            role='technician',
        )
        self.service_type = ServiceType.objects.create(
            name='SLA Service',
            description='Service with SLA coverage',
            estimated_duration=60,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Pending request',
            priority='Normal',
            status='Pending',
        )
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.technician_user,
            scheduled_date=self.now.date(),
            scheduled_time=time(hour=9, minute=0),
            status='Not Started',
            priority='Normal',
        )

    def _update_request(self, **updates):
        ServiceRequest.objects.filter(pk=self.request_obj.pk).update(**updates)
        self.request_obj.refresh_from_db()

    def _update_ticket(self, **updates):
        ServiceTicket.objects.filter(pk=self.ticket.pk).update(**updates)
        self.ticket.refresh_from_db()

    def test_pending_request_transitions_to_warning(self):
        self._update_request(request_date=self.now - timedelta(hours=5))

        evaluation = evaluate_service_request_sla(self.request_obj, now=self.now)

        self.assertEqual(evaluation['rule'], 'approval_delay')
        self.assertEqual(evaluation['state'], 'warning')
        self.assertEqual(evaluation['action_required'], 'Review request')
        self.assertEqual(evaluation['minutes_to_breach'], 180)

    def test_pending_request_transitions_to_overdue(self):
        self._update_request(request_date=self.now - timedelta(hours=9))

        evaluation = evaluate_service_request_sla(self.request_obj, now=self.now)

        self.assertEqual(evaluation['state'], 'overdue')
        self.assertEqual(evaluation['minutes_to_breach'], 0)
        self.assertEqual(evaluation['minutes_overdue'], 60)

    def test_unassigned_ticket_uses_assignment_delay_rule(self):
        self._update_ticket(
            technician=None,
            created_at=self.now - timedelta(hours=3),
            scheduled_time=time(hour=11, minute=0),
        )

        evaluation = evaluate_service_ticket_sla(self.ticket, now=self.now)

        self.assertEqual(evaluation['rule'], 'assignment_delay')
        self.assertEqual(evaluation['state'], 'warning')
        self.assertEqual(evaluation['action_required'], 'Assign technician')

    def test_assigned_ticket_uses_start_delay_rule(self):
        self._update_ticket(
            technician=self.technician_user,
            scheduled_date=self.now.date(),
            scheduled_time=(self.now - timedelta(minutes=70)).time(),
            status='Not Started',
        )

        evaluation = evaluate_service_ticket_sla(self.ticket, now=self.now)

        self.assertEqual(evaluation['rule'], 'start_delay')
        self.assertEqual(evaluation['state'], 'overdue')
        self.assertEqual(evaluation['minutes_overdue'], 10)
        self.assertEqual(evaluation['action_required'], 'Start work')

    def test_in_progress_ticket_uses_execution_delay_rule(self):
        self._update_ticket(
            status='In Progress',
            start_time=self.now - timedelta(minutes=100),
            technician=self.technician_user,
        )

        evaluation = evaluate_service_ticket_sla(self.ticket, now=self.now)

        self.assertEqual(evaluation['rule'], 'execution_delay')
        self.assertEqual(evaluation['state'], 'warning')
        self.assertEqual(evaluation['minutes_to_breach'], 20)
        self.assertEqual(evaluation['action_required'], 'Complete work')

    def test_reschedule_requested_ticket_uses_reschedule_delay_rule(self):
        self._update_ticket(
            status='Not Started',
            reschedule_requested=True,
            reschedule_requested_at=self.now - timedelta(hours=13),
        )

        evaluation = evaluate_service_ticket_sla(self.ticket, now=self.now)

        self.assertEqual(evaluation['rule'], 'reschedule_delay')
        self.assertEqual(evaluation['state'], 'overdue')
        self.assertEqual(evaluation['minutes_overdue'], 60)
        self.assertEqual(evaluation['action_required'], 'Review reschedule request')

    def test_completed_ticket_pauses_sla(self):
        self._update_ticket(status='Completed', completed_date=self.now)

        evaluation = evaluate_service_ticket_sla(self.ticket, now=self.now)

        self.assertEqual(evaluation['state'], 'paused')
        self.assertIsNone(evaluation['rule'])
        self.assertFalse(evaluation['is_active'])


class SLAApiIntegrationTests(APITestCase):
    def setUp(self):
        self.now = timezone.make_aware(datetime(2026, 3, 22, 10, 0, 0))
        self.admin_user = User.objects.create_user(
            username='sla-admin',
            password='pass',
            role='admin',
        )
        self.supervisor_user = User.objects.create_user(
            username='sla-supervisor',
            password='pass',
            role='supervisor',
        )
        self.client_user = User.objects.create_user(
            username='sla-api-client',
            password='pass',
            role='client',
        )
        self.technician_user = User.objects.create_user(
            username='sla-api-tech',
            password='pass',
            role='technician',
        )
        self.service_type = ServiceType.objects.create(
            name='SLA API Service',
            description='SLA serializer coverage',
            estimated_duration=60,
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Request awaiting approval',
            priority='Normal',
            status='Pending',
        )
        self.warning_ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.technician_user,
            supervisor=self.supervisor_user,
            scheduled_date=self.now.date(),
            scheduled_time=(self.now - timedelta(minutes=20)).time(),
            status='Not Started',
            priority='Normal',
        )
        self.execution_request = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Execution delay ticket',
            priority='Normal',
            status='In Progress',
        )
        self.execution_ticket = ServiceTicket.objects.create(
            request=self.execution_request,
            technician=self.technician_user,
            supervisor=self.supervisor_user,
            scheduled_date=self.now.date(),
            scheduled_time=time(hour=8, minute=30),
            status='In Progress',
            priority='Normal',
            start_time=self.now - timedelta(minutes=100),
        )

        ServiceRequest.objects.filter(pk=self.request_obj.pk).update(
            request_date=self.now - timedelta(hours=9),
        )
        ServiceTicket.objects.filter(pk=self.warning_ticket.pk).update(
            created_at=self.now - timedelta(hours=1),
        )
        self.request_obj.refresh_from_db()
        self.warning_ticket.refresh_from_db()
        self.execution_ticket.refresh_from_db()

        self.client.force_authenticate(user=self.admin_user)

    def test_service_request_list_includes_sla_payload(self):
        with patch('services.sla.timezone.now', return_value=self.now):
            response = self.client.get('/api/services/service-requests/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_request = response.data['results'][0]
        self.assertIn('sla', first_request)
        self.assertEqual(first_request['sla']['rule'], 'approval_delay')
        self.assertEqual(first_request['sla']['state'], 'overdue')

    def test_service_ticket_list_includes_sla_payload(self):
        with patch('services.sla.timezone.now', return_value=self.now):
            response = self.client.get('/api/services/service-tickets/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_ticket = response.data['results'][0]
        self.assertIn('sla', first_ticket)
        self.assertIn(first_ticket['sla']['rule'], {'start_delay', 'execution_delay'})
        self.assertIn(first_ticket['sla']['state'], {'warning', 'overdue'})

    def test_admin_dashboard_includes_sla_overview_and_queue(self):
        with patch('services.views_dashboard.process_maintenance_alerts'):
            with patch('services.views_dashboard.timezone.now', return_value=self.now):
                response = self.client.get('/api/services/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sla_overview', response.data)
        self.assertIn('sla_queue', response.data)
        self.assertEqual(response.data['sla_overview']['approval_risk'], 1)
        self.assertEqual(response.data['sla_overview']['start_delay_risk'], 1)
        self.assertEqual(response.data['sla_overview']['execution_risk'], 1)
        self.assertEqual(response.data['sla_overview']['overdue_count'], 1)
        self.assertEqual(response.data['sla_overview']['warning_count'], 2)
        self.assertEqual(response.data['sla_queue'][0]['entity_type'], 'request')
        self.assertEqual(response.data['sla_queue'][0]['sla']['state'], 'overdue')

    def test_supervisor_dashboard_includes_team_sla_summary(self):
        self.client.force_authenticate(user=self.supervisor_user)

        with patch('services.views_dashboard.timezone.now', return_value=self.now):
            response = self.client.get('/api/services/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sla_overview', response.data)
        self.assertEqual(response.data['sla_overview']['start_delay_risk'], 1)
        self.assertEqual(response.data['sla_overview']['execution_risk'], 1)
        self.assertEqual(len(response.data['sla_queue']), 2)

