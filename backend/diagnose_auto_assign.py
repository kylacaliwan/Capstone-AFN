#!/usr/bin/env python
"""Diagnose auto_assign failure for ticket 12"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from services.models import ServiceTicket, TechnicianSkill, ServiceType
from users.models import User

print("=" * 70)
print("TICKET 12 AUTO-ASSIGN DIAGNOSTICS")
print("=" * 70)

# Get ticket 12
try:
    ticket = ServiceTicket.objects.get(id=12)
except:
    print("❌ TICKET 12 NOT FOUND")
    sys.exit(1)

print(f"\n📋 TICKET 12 STATUS:")
print(f"  Status: {ticket.status}")
print(f"  Service Type: {ticket.request.service_type.name} (ID: {ticket.request.service_type.id})")
print(f"  Client: {ticket.request.client.username}")
print(f"  Currently Assigned: {ticket.technician.username if ticket.technician else 'None'}")

try:
    loc = ticket.request.location
    print(f"  Location: {loc.address} ({loc.latitude}, {loc.longitude})")
except Exception as e:
    print(f"  Location: ❌ ERROR - {e}")

# Check if status is assignable
ASSIGNABLE_STATUSES = ['Not Started', 'On Hold']
print(f"\n✓ Assignable status? {ticket.status in ASSIGNABLE_STATUSES}")

# Try to find skilled technicians
print(f"\n🔍 SEARCHING FOR SKILLED TECHNICIANS:")
service_type = ticket.request.service_type

skilled_ids = TechnicianSkill.objects.filter(
    service_type=service_type
).values_list('technician_id', flat=True)

print(f"  {service_type.name} skill holders: {list(skilled_ids)}")

# Fallback to General Services
if not skilled_ids.exists():
    print(f"  ⚠️ No exact match, trying General Services...")
    try:
        general = ServiceType.objects.get(name='General Services')
        general_ids = TechnicianSkill.objects.filter(
            service_type=general
        ).values_list('technician_id', flat=True)
        print(f"  General Services skill holders: {list(general_ids)}")
    except:
        print(f"  ❌ General Services not found")

# Check all active technicians
print(f"\n👥 ALL ACTIVE TECHNICIANS:")
all_techs = User.objects.filter(role='technician', status='active')
for tech in all_techs:
    active_tickets = tech.assigned_tickets.filter(
        status__in=['Not Started', 'In Progress']
    ).count()
    
    print(f"  - {tech.username}:")
    print(f"      Available: {tech.is_available}")
    print(f"      Location: ({tech.current_latitude}, {tech.current_longitude})")
    print(f"      Active tickets: {active_tickets}")
    
    # Check skills
    skills = TechnicianSkill.objects.filter(technician=tech).select_related('service_type')
    skill_names = [s.service_type.name for s in skills]
    print(f"      Skills: {skill_names if skill_names else 'NONE'}")

# Try to find available technicians (exact match)
print(f"\n🎯 AVAILABLE TECHNICIANS FOR '{service_type.name}':")
available = User.objects.filter(
    id__in=skilled_ids,
    role='technician',
    is_available=True,
    status='active'
).exclude(
    assigned_tickets__status__in=['Not Started', 'In Progress']
)

print(f"  Count: {available.count()}")
for tech in available:
    print(f"  - {tech.username}")

if available.count() == 0:
    print(f"\n⚠️ NO AVAILABLE TECHNICIANS")
    print(f"  Reason 1: No one has '{service_type.name}' skill")
    print(f"  Reason 2: All who have it are already busy")

print("\n" + "=" * 70)
