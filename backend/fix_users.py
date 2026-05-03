#!/usr/bin/env python
"""Check and fix user active status."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.models import User

print("=== USER STATUS ===")
users_to_check = ['tech1', 'client1', 'supervisor1', 'iman']

for username in users_to_check:
    user = User.objects.filter(username=username).first()
    if user:
        print(f"{username}: is_active={user.is_active}, status={user.status}")
    else:
        print(f"{username}: NOT FOUND")

print("\n=== FIXING ===")
# Activate all test users
for username in users_to_check:
    user = User.objects.filter(username=username).first()
    if user and not user.is_active:
        user.is_active = True
        user.status = 'active'
        user.save(update_fields=['is_active', 'status'])
        print(f"✓ Activated {username}")
    elif user:
        print(f"✓ {username} already active")

print("\nAfter fix:")
for username in users_to_check:
    user = User.objects.filter(username=username).first()
    if user:
        print(f"{username}: is_active={user.is_active}, status={user.status}")
