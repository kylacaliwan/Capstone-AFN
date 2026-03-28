"""Test DRF ORS route endpoint with detailed error logging"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
sys.path.insert(0, 'd:\\Caps - Copy\\backend')
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from services.views import ORSViewSet
from users.models import User as CustomUser

# Create a test user for authentication
try:
    user = CustomUser.objects.first()
    if not user:
        user = CustomUser.objects.create_user(username='testuser', password='test123', is_staff=False)
except Exception as e:
    print(f"User creation error: {e}")
    user = None

factory = APIRequestFactory()

# Create a request
wsgi_request = factory.get('/api/services/ors/route/?start=120.9842,14.5995&end=121.0337,14.5547')
request = Request(wsgi_request)
request.user = user

# Call the view
viewset = ORSViewSet()
viewset.request = request
viewset.format_kwarg = None

try:
    response = viewset.route(request)
    print("Response status:", response.status_code)
    print("Response data:", response.data)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
