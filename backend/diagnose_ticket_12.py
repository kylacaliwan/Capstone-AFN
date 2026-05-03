#!/usr/bin/env python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from services.models import ServiceTicket, TechnicianSkill
from users.models import User

try:
    ticket = ServiceTicket.objects.get(id=12)
    print(f"Ticket 12:")
    print(f"  Status: {ticket.status}")
    print(f"  Service Type: {ticket.request.service_type.name if ticket.request.service_type else 'None'}")
    print(f"  Client: {ticket.request.client.username}")
    print(f"  Currently Assigned To: {ticket.technician if ticket.technician else 'Unassigned'}")
    
    try:
        loc = ticket.request.location
        print(f"  Location: {loc.address} ({loc.latitude}, {loc.longitude})")
    except Exception as e:
        print(f"  Location: NOT SET - {e}")
    
    service_type = ticket.request.service_type
    print(f"\n✓ Technicians with '{service_type.name}' skill:")
    
    skilled = TechnicianSkill.objects.filter(service_type=service_type).select_related('technician')
    if skilled.count() == 0:
        print("  ✗ NO TECHNICIANS WITH THIS SKILL!")
    else:
        for skill in skilled:
            tech = skill.technician
            status_ok = tech.status == 'active'
            avail_ok = tech.is_available
            loc_ok = tech.current_latitude and tech.current_longitude
            
            print(f"  - {tech.username}:")
            print(f"      Status: {tech.status} {'✓' if status_ok else '✗'}")
            print(f"      Available: {avail_ok} {'✓' if avail_ok else '✗'}")
            print(f"      Location: ({tech.current_latitude}, {tech.current_longitude}) {'✓' if loc_ok else '✗'}")
    
    # Check if technician already has tickets
    print(f"\n✓ All Available Technicians:")
    all_active_techs = User.objects.filter(role='technician', status='active', is_available=True)
    for tech in all_active_techs:
        ticket_count = tech.assigned_tickets.filter(status__in=['Not Started', 'In Progress']).count()
        print(f"  - {tech.username}: {ticket_count} active tickets, location=({tech.current_latitude}, {tech.current_longitude})")

except ServiceTicket.DoesNotExist:
    print("✗ Ticket 12 does not exist!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
