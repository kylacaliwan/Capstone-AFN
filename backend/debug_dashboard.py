import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

from services.views_dashboard import DashboardView
from users.models import User
from rest_framework.test import APIRequestFactory

# Create a mock request
factory = APIRequestFactory()
request = factory.get('/services/dashboard/')

# Create or get admin user
admin, _ = User.objects.get_or_create(
    username='admin',
    defaults={'role': 'admin', 'email': 'admin@test.com'}
)
request.user = admin

# Try to get the admin dashboard
view = DashboardView()
view.request = request

try:
    print("Attempting to get admin dashboard...")
    response = view.get_admin_dashboard()
    print("Success! Dashboard returned data")
    print(f"Response: {response}")
except Exception as e:
    import traceback
    print(f"ERROR: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
