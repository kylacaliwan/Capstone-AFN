#!/usr/bin/env python
"""Direct test of technician tracking - bypassing Django test client host issues."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, force_authenticate

from api.urls import tracking_view
from services.models import TechnicianLocationHistory
from services.views import TechnicianLocationHistoryViewSet
from users.models import User


def required_env(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise SystemExit(f'Set {name} before creating debug users.')
    return value


def main():
    print("=== DIRECT TECHNICIAN TRACKING TEST ===\n")

    tech, created = User.objects.get_or_create(
        username='tech_direct',
        defaults={
            'role': 'technician',
            'email': 'tech_direct@test.com',
            'is_available': True
        }
    )
    if created:
        tech.set_password(required_env('AFN_DEBUG_TECH_PASSWORD'))
        tech.save(update_fields=['password'])
    print(f"[OK] Technician: {tech.username}")

    supervisor, created = User.objects.get_or_create(
        username='tracking_supervisor',
        defaults={
            'role': 'supervisor',
            'email': 'tracking_supervisor@test.com',
        }
    )
    if created:
        supervisor.set_password(required_env('AFN_DEBUG_SUPERVISOR_PASSWORD'))
        supervisor.save(update_fields=['password'])

    token, _ = Token.objects.get_or_create(user=tech)
    print(f"[OK] Token: {token.key[:20]}...")

    factory = APIRequestFactory()
    request = factory.post(
        '/api/services/technician/location/',
        {
            'latitude': 6.5244,
            'longitude': 3.3792,
            'accuracy': 10.5
        },
        format='json'
    )
    force_authenticate(request, user=tech, token=token)

    print("\n--- Test 1: Update Location ---")
    update_view = TechnicianLocationHistoryViewSet.as_view({'post': 'update_location'})

    try:
        response = update_view(request)
        print(f"[OK] Response: {response.data}")

        tech.refresh_from_db()
        print(f"[OK] Tech location saved: ({tech.current_latitude}, {tech.current_longitude})")

        history = TechnicianLocationHistory.objects.filter(technician=tech).last()
        print(f"[OK] Last location history: ({history.latitude}, {history.longitude}) at {history.timestamp}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- Test 2: Tracking Data ---")
    request2 = factory.get('/api/tracking')
    force_authenticate(request2, user=supervisor)

    try:
        response = tracking_view(request2)
        data = response.data
        print(f"[OK] Tech markers: {len(data['techMarkers'])}")
        print(f"[OK] Ticket markers: {len(data['ticketMarkers'])}")

        tech_in_list = any(t['id'] == tech.id for t in data['techMarkers'])
        print(f"[OK] Our technician in tracking list: {tech_in_list}")

        if data['techMarkers']:
            print(f"\nFirst tech marker:")
            print(f"  - Name: {data['techMarkers'][0]['name']}")
            print(f"  - Status: {data['techMarkers'][0]['status']}")
            print(f"  - Location: {data['techMarkers'][0]['lat']}, {data['techMarkers'][0]['lng']}")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== TESTS COMPLETE ===")


if __name__ == '__main__':
    main()
