import mimetypes
from pathlib import Path

from django.http import Http404, HttpResponse, JsonResponse


FRONTEND_BUILD_DIR = Path(__file__).resolve().parent.parent / 'static' / 'frontend'


def _frontend_file(path):
    file_path = FRONTEND_BUILD_DIR / path
    if not file_path.exists() or not file_path.is_file():
        raise Http404(f'Frontend build asset not found: {path}')
    return file_path


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
                'password_reset_request': '/api/users/password_reset_request/',
                'password_reset_confirm': '/api/users/password_reset_confirm/',
            },
            'dashboards': {
                'role_stats': '/api/dashboard/stats/',
                'admin_analytics': '/api/admin/analytics/',
            },
            'note': 'The legacy Django template UI was removed. Use the React frontend for the main app experience.',
        }
    )


def frontend_app(request):
    """
    Serve the built React SPA when available.

    If the frontend has not been built for Django/PythonAnywhere yet, fall back
    to the backend API landing response with a deployment hint.
    """
    index_path = FRONTEND_BUILD_DIR / 'index.html'
    if not index_path.exists():
        response = backend_home(request)
        response['X-Frontend-Build'] = 'missing'
        return response

    return HttpResponse(index_path.read_text(encoding='utf-8'))


def frontend_public_file(request, filename):
    """Serve top-level frontend build files that need to live at the site root."""
    file_path = _frontend_file(filename)
    content_type, _ = mimetypes.guess_type(file_path.name)
    response = HttpResponse(file_path.read_bytes(), content_type=content_type or 'application/octet-stream')
    if file_path.name == 'firebase-messaging-sw.js':
        response['Service-Worker-Allowed'] = '/'
    return response
