#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.models import User
from django.contrib.auth.hashers import make_password

# Fix wrong roles
print('Fixing wrong roles...')
wrong_roles = [
    ('AdminIman', 'admin'),
    ('thesuper', 'supervisor'),
    ('theadmin', 'admin'),
]

for username, correct_role in wrong_roles:
    try:
        user = User.objects.get(username=username)
        old_role = user.role
        user.role = correct_role
        user.save()
        print(f'FIXED: {username}: {old_role} → {correct_role}')
    except User.DoesNotExist:
        print(f'NOT FOUND: {username}')

# Create clean test accounts
print('\nCreating clean test accounts...')
test_accounts = [
    ('TestAdmin', 'test123', 'admin'),
    ('TestSupervisor', 'test123', 'supervisor'),
    ('TestTechnician', 'test123', 'technician'),
    ('TestClient', 'test123', 'client'),
]

for username, password, role in test_accounts:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f'{username.lower()}@test.com',
            'role': role,
            'password': make_password(password),
            'is_active': True,
            'first_name': username.replace('Test', ''),
        }
    )
    if created:
        print(f'CREATED: {username} ({role})')
    else:
        user.role = role
        user.password = make_password(password)
        user.save()
        print(f'UPDATED: {username} ({role})')

print('\n' + '='*60)
print('DONE! TEST ACCOUNTS READY:')
print('='*60)
print('Admin:       TestAdmin / test123')
print('Supervisor:  TestSupervisor / test123')
print('Technician:  TestTechnician / test123')
print('Client:      TestClient / test123')
print('='*60)
