#!/usr/bin/env python
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.models import User

tech1 = User.objects.get(username='tech1')
print(f"tech1 status: {tech1.status}")
print(f"tech1 is_available: {tech1.is_available}")
print(f"tech1 is_active: {tech1.is_active}")
print(f"tech1 role: {tech1.role}")
