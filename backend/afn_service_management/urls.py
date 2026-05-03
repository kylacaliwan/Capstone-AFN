"""URL configuration for afn_service_management project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .views import frontend_app, frontend_public_file


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('favicon.svg', frontend_public_file, {'filename': 'favicon.svg'}, name='frontend-favicon'),
    path(
        'firebase-messaging-sw.js',
        frontend_public_file,
        {'filename': 'firebase-messaging-sw.js'},
        name='frontend-firebase-sw',
    ),

    # React handles the non-API application routes after the initial HTML load.
    re_path(r'^(?!api/|admin/|static/|media/).*$', frontend_app, name='frontend-app'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
