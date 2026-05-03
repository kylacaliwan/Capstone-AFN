#!/usr/bin/env python
"""Simple credential test."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from django.contrib.auth import authenticate
from users.models import User

# Test 1: Check if users exist
print("=== EXISTING USERS ===")
for user in User.objects.filter(username__in=['iman', 'tech1', 'supervisor1']):
    print(f"{user.username} - role={user.role}, active={user.is_active}")

# Test 2: Try direct authenticate
print("\n=== TEST CREDENTIALS ===")

# YOU FILL IN YOUR PASSWORD HERE
TEST_PASSWORD = "superadmin"

users_to_test = ['iman', 'tech1', 'supervisor1']

for username in users_to_test:
    user = User.objects.filter(username=username).first()
    if not user:
        print(f"{username}: NOT FOUND")
        continue
    
    # Try authenticate
    result = authenticate(username=username, password=TEST_PASSWORD)
    if result:
        print(f"{username}: ✓ LOGIN WORKS")
    else:
        print(f"{username}: ✗ Login failed - password wrong?")
        # Try if user is active
        print(f"   - is_active: {user.is_active}")
        print(f"   - has password: {bool(user.password)}")
