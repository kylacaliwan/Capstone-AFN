#!/usr/bin/env python
"""
Bootstrap the single superadmin owner account using environment variables.

Required:
    AFN_BOOTSTRAP_ADMIN_PASSWORD

Optional:
    AFN_BOOTSTRAP_ADMIN_USERNAME (default: admin)
    AFN_BOOTSTRAP_ADMIN_EMAIL (default: admin@example.com)
    AFN_BOOTSTRAP_ADMIN_FIRST_NAME (default: System)
    AFN_BOOTSTRAP_ADMIN_LAST_NAME (default: Administrator)
"""
import os
import sys
from pathlib import Path

import django


BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')

django.setup()

from users.models import User  # noqa: E402


def main():
    username = os.environ.get('AFN_BOOTSTRAP_ADMIN_USERNAME', 'admin').strip() or 'admin'
    email = os.environ.get('AFN_BOOTSTRAP_ADMIN_EMAIL', 'admin@example.com').strip() or 'admin@example.com'
    password = os.environ.get('AFN_BOOTSTRAP_ADMIN_PASSWORD', '').strip()
    first_name = os.environ.get('AFN_BOOTSTRAP_ADMIN_FIRST_NAME', 'System').strip()
    last_name = os.environ.get('AFN_BOOTSTRAP_ADMIN_LAST_NAME', 'Administrator').strip()

    if not password:
        raise SystemExit('Set AFN_BOOTSTRAP_ADMIN_PASSWORD before running this script.')

    existing_owner = User.objects.filter(role='superadmin').exclude(username=username).first()
    if existing_owner:
        raise SystemExit(
            f"Superadmin '{existing_owner.username}' already exists. "
            f"Use that account or promote a different owner manually."
        )

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'role': 'superadmin',
            'is_staff': True,
            'is_superuser': True,
            'first_name': first_name,
            'last_name': last_name,
            'status': 'active',
        },
    )

    updated_fields = []
    if user.email != email:
        user.email = email
        updated_fields.append('email')
    if user.role != 'superadmin':
        user.role = 'superadmin'
        updated_fields.append('role')
    if not user.is_staff:
        user.is_staff = True
        updated_fields.append('is_staff')
    if not user.is_superuser:
        user.is_superuser = True
        updated_fields.append('is_superuser')
    if user.first_name != first_name:
        user.first_name = first_name
        updated_fields.append('first_name')
    if user.last_name != last_name:
        user.last_name = last_name
        updated_fields.append('last_name')
    if user.status != 'active':
        user.status = 'active'
        updated_fields.append('status')

    user.set_password(password)
    updated_fields.append('password')
    user.save(update_fields=updated_fields)

    action = 'Created' if created else 'Updated'
    print(f"{action} superadmin user '{username}'.")


if __name__ == '__main__':
    main()
