#!/usr/bin/env python
"""
Shell-friendly wrapper for the capstone demo data command.

Run:
    python manage.py shell < create_test_data.py
"""

from django.core.management import call_command

call_command("create_test_data")
