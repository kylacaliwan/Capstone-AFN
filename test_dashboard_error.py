#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

django.setup()

from rest_framework.test import APIClient
from users.models import User

try:
    admin = User.objects.get(username='admin')
except User.DoesNotExist:
    admin = User.objects.create_user(
        username='admin',
        password='admin123',
        role='admin',
        email='admin@test.com'
    )

client = APIClient()
client.force_authenticate(user=admin)

try:
    response = client.get('/services/dashboard/')
    print(f'Status: {response.status_code}')
    if response.status_code != 200:
        print(f'\nError content:\n{response.content.decode()}')
    else:
        import json
        print(f'Success!\n{json.dumps(response.data, indent=2, default=str)}')
except Exception as e:
    import traceback
    print(f'Exception: {e}')
    traceback.print_exc()
