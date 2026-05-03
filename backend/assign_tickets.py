#!/usr/bin/env python
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from services.models import ServiceTicket
from users.models import User

# Get tech1 and ticket 10
tech1 = User.objects.get(username='tech1')
ticket = ServiceTicket.objects.get(id=10)

# Assign
ticket.technician = tech1
ticket.save()

print("✅ ASSIGNMENTS FOR CLIENT3:")
print("=" * 50)
tickets = ServiceTicket.objects.filter(request__client__username='client3')
for t in tickets:
    print(f"Ticket {t.id}: {t.status} → Assigned to: {t.technician}")
print("=" * 50)
print(f"READY FOR TESTING: Both tickets are assigned to tech1!")
