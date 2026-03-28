"""Test ORS client initialization within Django context"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
sys.path.insert(0, 'd:\\Caps - Copy\\backend')
django.setup()

from django.conf import settings
print(f"ORS_API_KEY configured: {bool(settings.ORS_API_KEY)}")
print(f"ORS_API_KEY value (first 30 chars): {settings.ORS_API_KEY[:30] if settings.ORS_API_KEY else 'NOT SET'}")

# Now test the ors_utils module initialization
from services import ors_utils
print(f"\nORS client initialized: {bool(ors_utils.client)}")

if ors_utils.client:
    print("Using OpenRouteService (ORS) client")
    try:
        result = ors_utils.get_route([120.9842, 14.5995], [121.0337, 14.5547])
        print(f"✓ ORS routing works: got {len(result.get('features', []))} features")
    except Exception as e:
        print(f"✗ ORS routing failed: {type(e).__name__}: {e}")
else:
    print("ORS client not initialized, will use OSRM fallback")
    try:
        result = ors_utils.get_route([120.9842, 14.5995], [121.0337, 14.5547])
        print(f"✓ OSRM fallback works: got {len(result.get('features', []))} features")
    except Exception as e:
        print(f"✗ OSRM fallback failed: {type(e).__name__}: {e}")
