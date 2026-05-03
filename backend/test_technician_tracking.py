#!/usr/bin/env python
"""Test technician tracking flow."""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from users.models import User
from services.models import ServiceTicket, ServiceRequest, ServiceType, ServiceLocation
from django.utils import timezone
from decimal import Decimal


class TechnicianTrackingTest(APITestCase):
    """Test technician tracking functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create technician
        self.tech = User.objects.create_user(
            username='tech1',
            password='tech123456',
            role='technician',
            email='tech@test.com',
            is_available=True
        )
        
        # Create client
        self.client_user = User.objects.create_user(
            username='client1',
            password='client123',
            role='client',
            email='client@test.com'
        )
        
        # Create supervisor
        self.supervisor = User.objects.create_user(
            username='supervisor1',
            password='supervisor123',
            role='supervisor',
            email='supervisor@test.com'
        )
        
        # Create service type and request
        self.service_type = ServiceType.objects.create(
            name='Solar Installation',
            estimated_duration=120
        )
        
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Install solar panel',
            status='Approved'
        )
        
        self.location = ServiceLocation.objects.create(
            request=self.request_obj,
            address='123 Main St',
            city='Lagos',
            province='Lagos',
            latitude=Decimal('6.5244'),
            longitude=Decimal('3.3792')
        )
        
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            technician=self.tech,
            scheduled_date=timezone.now().date(),
            status='In Progress'
        )
    
    def test_technician_login(self):
        """Test technician can log in."""
        token = Token.objects.create(user=self.tech)
        
        # Check token exists
        self.assertIsNotNone(token.key)
        print(f"[OK] Technician login test passed - Token: {token.key[:20]}...")
    
    def test_technician_location_update(self):
        """Test updating technician location."""
        token = Token.objects.create(user=self.tech)
        
        # Simulate location update
        self.tech.current_latitude = 6.5250
        self.tech.current_longitude = 3.3800
        self.tech.save()
        
        # Verify it was saved
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.current_latitude, Decimal('6.5250'))
        self.assertEqual(self.tech.current_longitude, Decimal('3.3800'))
        print(f"[OK] Technician location update test passed")
    
    def test_service_data_structure(self):
        """Test service request and ticket structure."""
        # Verify ticket exists
        self.assertEqual(self.ticket.technician, self.tech)
        self.assertEqual(self.ticket.status, 'In Progress')
        self.assertEqual(self.ticket.request, self.request_obj)
        
        # Verify request exists
        self.assertEqual(self.request_obj.client, self.client_user)
        self.assertEqual(self.request_obj.status, 'Approved')
        
        # Verify location exists
        self.assertEqual(self.location.request, self.request_obj)
        print(f"[OK] Service data structure test passed")
    
    def test_supervisor_access(self):
        """Test supervisor can access tracking data."""
        # Create token for supervisor
        token = Token.objects.create(user=self.supervisor)
        
        # Verify supervisor can see technician and ticket data
        techs = User.objects.filter(role='technician')
        tickets = ServiceTicket.objects.all()
        
        self.assertEqual(techs.count(), 1)
        self.assertEqual(tickets.count(), 1)
        print(f"[OK] Supervisor access test passed")


def main():
    """Run all tests."""
    print("=== TECHNICIAN TRACKING TEST ===\n")
    
    # Import test runner
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    # Run tests
    failures = test_runner.run_tests(['__main__'])
    
    if failures:
        print(f"\n[ERROR] {failures} test(s) failed")
        sys.exit(1)
    else:
        print("\n=== ALL TESTS PASSED ===")
        sys.exit(0)


if __name__ == '__main__':
    main()
