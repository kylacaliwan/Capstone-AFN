#!/usr/bin/env python
"""Direct authentication test."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.views import authenticate_user_credentials
from django.contrib.auth import authenticate
from users.models import User

print("=== DIRECT AUTH TEST ===\n")

credentials = {
    'tech1': 'tech123456',
    'client1': 'client123',
    'supervisor1': 'supervisor123',
    'iman': 'superadmin'
}

for username, password in credentials.items():
    print(f"Testing {username}:")
    
    # Test 1: authenticate_user_credentials (used by API)
    result1 = authenticate_user_credentials(username, password)
    print(f"  authenticate_user_credentials: {bool(result1)}")
    
    # Test 2: Django's authenticate (lower level)
    result2 = authenticate(username=username, password=password)
    print(f"  Django authenticate: {bool(result2)}")
    
    # Test 3: Check stored password
    user = User.objects.filter(username=username).first()
    if user:
        print(f"  User exists: Yes")
        print(f"  is_active: {user.is_active}")
        print(f"  password hash: {user.password[:30] if user.password else 'None'}")
        
        # Test 4: Manual password check
        if user.check_password(password):
            print(f"  check_password(): True ✓")
        else:
            print(f"  check_password(): False ✗")
    print()
