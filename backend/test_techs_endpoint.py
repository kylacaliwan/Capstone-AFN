#!/usr/bin/env python
"""Test the techs API endpoint"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

# Get admin user
admin = User.objects.get(username='admin')
token = Token.objects.get(user=admin)

# Make API call
client = Client()
response = client.get('/api/admin/technicians/', HTTP_AUTHORIZATION=f'Token {token.key}')

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
