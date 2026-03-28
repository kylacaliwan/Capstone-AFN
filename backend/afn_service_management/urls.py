"""URL configuration for afn_service_management project."""

from django.contrib import admin
from django.urls import include, path

from .views import backend_home, legacy_ui_redirect


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # Retired template-era routes now fall back safely to the API root.
    path('dashboard/', legacy_ui_redirect, name='dashboard'),
    path('gis-dashboard/', legacy_ui_redirect, name='gis_dashboard'),
    path('inspection/', legacy_ui_redirect, name='inspection'),
    path('technicians/', legacy_ui_redirect, name='technicians'),
    path('service-types/', legacy_ui_redirect, name='service_types'),
    path('services/requests/', legacy_ui_redirect, name='service_requests'),
    path('users/register/', legacy_ui_redirect, name='register'),
    path('dashboard/admin/', legacy_ui_redirect, name='admin_dashboard'),
    path('dashboard/technician/', legacy_ui_redirect, name='technician_dashboard'),
    path('dashboard/client/', legacy_ui_redirect, name='client_dashboard'),

    path('', backend_home, name='home'),
]
