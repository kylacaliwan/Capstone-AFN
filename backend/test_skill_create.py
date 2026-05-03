#!/usr/bin/env python
"""Test creating a technician skill"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

# Get tech1 user and token
tech1 = User.objects.get(username='tech1')
token, _ = Token.objects.get_or_create(user=tech1)

# Make API call to create a skill
client = Client()
response = client.post(
    '/api/services/technician-skills/',
    data='{"service_type": 13, "skill_level": "intermediate"}',
    content_type='application/json',
    HTTP_AUTHORIZATION=f'Token {token.key}'
)

print(f"Status: {response.status_code}")
print(f"Response: {response.content.decode()}")
