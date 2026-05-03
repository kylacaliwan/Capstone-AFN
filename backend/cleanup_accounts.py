#!/usr/bin/env python
"""Deep cleanup - remove dummy accounts and ALL their related data"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from users.models import User
from services.models import ServiceRequest, ServiceTicket, TechnicianSkill

# Define accounts to KEEP
KEEP_ACCOUNTS = {
    'iman': 'superadmin',
    'admin': 'admin',
    'supervisor1': 'supervisor',
    'tech1': 'technician',
    'client1': 'client',
    'client2': 'client',
    'client3': 'client',
}

print("=" * 70)
print("DEEP CLEANUP - REMOVING DUMMY ACCOUNTS AND RELATED DATA")
print("=" * 70)

# Get all users
all_users = User.objects.all()
print(f"\n1. Total accounts before cleanup: {all_users.count()}")

# Find accounts to delete
dummy_users = []
kept_users = []

for user in all_users:
    if user.username in KEEP_ACCOUNTS:
        kept_users.append(user)
    else:
        dummy_users.append(user)

print(f"   - Accounts to KEEP: {len(kept_users)}")
print(f"   - Accounts to DELETE: {len(dummy_users)}")

# Show what will be deleted
print("\n" + "=" * 70)
print("KEEPING THESE ACCOUNTS:")
print("=" * 70)
for user in sorted(kept_users, key=lambda u: u.role):
    print(f"  ✅ {user.username:15} | Role: {user.role:12}")

print("\n" + "=" * 70)
print("DELETING THESE ACCOUNTS (and their data):")
print("=" * 70)
for user in sorted(dummy_users, key=lambda u: u.username):
    print(f"  ❌ {user.username:15} | Role: {user.role:12}")

# Count related data for dummy accounts
dummy_usernames = [u.username for u in dummy_users]
dummy_user_ids = [u.id for u in dummy_users]

if dummy_users:
    # Count what will be deleted
    client_dummy = [u for u in dummy_users if u.role == 'client']
    tech_dummy = [u for u in dummy_users if u.role == 'technician']
    other_dummy = [u for u in dummy_users if u.role not in ['client', 'technician']]
    
    requests_count = ServiceRequest.objects.filter(client__in=dummy_user_ids).count()
    tickets_count = ServiceTicket.objects.filter(technician__in=dummy_user_ids).count()
    skills_count = TechnicianSkill.objects.filter(technician__in=dummy_user_ids).count()
    
    print("\n" + "=" * 70)
    print("DATA TO BE DELETED:")
    print("=" * 70)
    print(f"  - Service Requests: {requests_count}")
    print(f"  - Service Tickets: {tickets_count}")
    print(f"  - Technician Skills: {skills_count}")
    print(f"  - Dummy User Accounts: {len(dummy_users)}")
    
    # Perform deletion
    print("\n" + "=" * 70)
    print("EXECUTING DELETION...")
    print("=" * 70)
    
    # Delete cascades through ForeignKeys automatically
    deleted_count, deletion_breakdown = User.objects.filter(id__in=dummy_user_ids).delete()
    
    print(f"\n✅ Deletion complete!")
    print(f"   Total items deleted: {deleted_count}")
    print(f"   Breakdown:")
    for model, count in deletion_breakdown.items():
        print(f"     - {model}: {count}")
else:
    print("\n✅ No dummy accounts to delete")

# Verify final state
final_users = User.objects.all()
print("\n" + "=" * 70)
print(f"FINAL STATE: {final_users.count()} accounts")
print("=" * 70)
for user in final_users.order_by('role', 'username'):
    print(f"  {user.username:15} | Role: {user.role:12} | Active: {user.is_active}")

print("\n" + "=" * 70)
print("✅ CLEANUP COMPLETE - DATABASE IS CLEAN AND READY!")
print("=" * 70)
