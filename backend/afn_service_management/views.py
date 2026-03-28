from django.http import JsonResponse
from django.shortcuts import redirect


def backend_home(request):
    """Lightweight API landing page for the Django backend."""
    return JsonResponse(
        {
            'name': 'AFN Service Management API',
            'status': 'ok',
            'api_root': '/api/',
            'auth': {
                'login': '/api/users/login/',
                'register': '/api/users/register/',
                'logout': '/api/users/logout/',
            },
            'dashboards': {
                'role_stats': '/api/dashboard/stats/',
                'admin_analytics': '/api/admin/analytics/',
            },
            'note': 'The legacy Django template UI was removed. Use the React frontend for the main app experience.',
        }
    )


def legacy_ui_redirect(request):
    """Redirect retired template-era routes to the API root instead of raising template errors."""
    return redirect('/api/')
