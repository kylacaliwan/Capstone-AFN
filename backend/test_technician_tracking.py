#!/usr/bin/env python
"""Test technician tracking flow."""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from rest_framework.test import APIClient
from users.models import User
from services.models import ServiceTicket, ServiceRequest, ServiceType, ServiceLocation
from django.utils import timezone
from decimal import Decimal


def main():
    print("=== TECHNICIAN TRACKING TEST ===\n")

    try:
        tech = User.objects.get(username='tech1')
    except User.DoesNotExist:
        tech = User.objects.create_user(
            username='tech1',
            password='tech123',
            role='technician',
            email='tech@test.com',
            is_available=True
        )
        print(f"[OK] Created technician: {tech.username}")

    try:
        client = User.objects.get(username='client1')
    except User.DoesNotExist:
        client = User.objects.create_user(
            username='client1',
            password='client123',
            role='client',
            email='client@test.com'
        )
        print(f"[OK] Created client: {client.username}")

    service_type, _ = ServiceType.objects.get_or_create(
        name='Solar Installation',
        defaults={'estimated_duration': 120}
    )

    request_obj = ServiceRequest.objects.create(
        client=client,
        service_type=service_type,
        description='Install solar panel',
        status='Approved'
    )
    print(f"[OK] Created service request: {request_obj.id}")

    location, _ = ServiceLocation.objects.get_or_create(
        request=request_obj,
        defaults={
            'address': '123 Main St',
            'city': 'Lagos',
            'province': 'Lagos',
            'latitude': Decimal('6.5244'),
            'longitude': Decimal('3.3792')
        }
    )
    print(f"[OK] Created location: {location.address}")

    ticket = ServiceTicket.objects.create(
        request=request_obj,
        technician=tech,
        scheduled_date=timezone.now().date(),
        status='In Progress'
    )
    print(f"[OK] Created ticket: {ticket.id}")

    print("\n--- Test 1: Technician Login ---")
    api_client = APIClient()
    response = api_client.post('/api/users/login/', {
        'username': 'tech1',
        'password': 'tech123'
    }, format='json')

    if response.status_code == 200:
        token = response.json().get('token')
        print(f"[OK] Login successful, token: {token[:20]}...")
    else:
        print(f"[ERROR] Login failed: {response.status_code}")
        print(f"Response: {response.json()}")
        sys.exit(1)

    print("\n--- Test 2: Update Technician Location ---")
    response = api_client.post(
        '/api/services/technician/location/',
        {
            'latitude': 6.5250,
            'longitude': 3.3800,
            'accuracy': 10.5
        },
        HTTP_AUTHORIZATION=f'Token {token}',
        format='json'
    )
    print(f"Response [{response.status_code}]: {response.json()}")

    tech.refresh_from_db()
    print(f"Technician location in DB: {tech.current_latitude}, {tech.current_longitude}")

    print("\n--- Test 3: Fetch Tracking Data ---")
    supervisor, _ = User.objects.get_or_create(
        username='tracking_supervisor',
        defaults={
            'password': 'track123',
            'role': 'supervisor',
            'email': 'tracking_supervisor@test.com'
        }
    )
    if _:
        supervisor.set_password('track123')
        supervisor.save(update_fields=['password'])

    supervisor_client = APIClient()
    supervisor_client.force_authenticate(user=supervisor)
    response = supervisor_client.get('/api/tracking', format='json')
    print(f"Response [{response.status_code}]:")
    if response.status_code == 200:
        data = response.json()
        print(f"Tech markers: {len(data.get('techMarkers', []))}")
        print(f"Ticket markers: {len(data.get('ticketMarkers', []))}")

        if data.get('techMarkers'):
            print(f"First tech: {data['techMarkers'][0]}")
        if data.get('ticketMarkers'):
            print(f"First ticket: {data['ticketMarkers'][0]}")
    else:
        print(f"[ERROR] {response.json()}")

    print("\n=== TESTS COMPLETE ===")


if __name__ == '__main__':
    main()
