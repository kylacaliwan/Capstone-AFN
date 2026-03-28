#!/usr/bin/env python
"""
Script to create test users for AFN Service Management
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(r'd:\CAPSTONE\afn_service_management')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')

# Setup Django
django.setup()

from users.models import User

# Test users data
test_users = [
    {
        'username': 'admin',
        'email': 'admin@afn.com',
        'password': 'admin123',
        'role': 'admin',
        'first_name': 'System',
        'last_name': 'Administrator'
    },
    {
        'username': 'supervisor1',
        'email': 'supervisor@afn.com',
        'password': 'super123',
        'role': 'supervisor',
        'first_name': 'John',
        'last_name': 'Supervisor'
    },
    {
        'username': 'tech1',
        'email': 'tech1@afn.com',
        'password': 'tech123',
        'role': 'technician',
        'first_name': 'Mike',
        'last_name': 'Technician',
        'phone': '+1234567890'
    },
    {
        'username': 'client1',
        'email': 'client1@afn.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Alice',
        'last_name': 'Client',
        'phone': '+1234567892'
    }
]

for user_data in test_users:
    if not User.objects.filter(username=user_data['username']).exists():
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            role=user_data['role'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            phone=user_data.get('phone', '')
        )
        print(f"Created user: {user.username} ({user.role})")
    else:
        print(f"User already exists: {user_data['username']}")

print("\nTest Login Credentials:")
print("Admin: admin / admin123")
print("Supervisor: supervisor1 / super123")
print("Technician: tech1 / tech123")
print("Client: client1 / client123")

