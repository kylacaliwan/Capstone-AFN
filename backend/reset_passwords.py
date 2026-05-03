#!/usr/bin/env python
"""Reset test user passwords."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.models import User

# Reset passwords
users_to_reset = {
    'iman': 'superadmin',
    'tech1': 'tech123456',
    'supervisor1': 'supervisor123',
    'client1': 'client123'
}

for username, password in users_to_reset.items():
    user = User.objects.filter(username=username).first()
    if not user:
        print(f"{username}: NOT FOUND")
        continue
    
    user.set_password(password)
    user.save(update_fields=['password'])
    print(f"✓ Reset {username} password to: {password}")

print("\nNow test with these credentials:")
for username, password in users_to_reset.items():
    print(f"  {username} / {password}")
