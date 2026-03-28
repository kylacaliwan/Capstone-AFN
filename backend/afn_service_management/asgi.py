"""
ASGI config for afn_service_management project.

The project currently runs as an HTTP-only Django app. Channels/websocket
inventory code remains out of the active runtime until that subsystem is
intentionally re-enabled in settings and routing.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')

application = get_asgi_application()
