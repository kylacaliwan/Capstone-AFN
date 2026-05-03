# PythonAnywhere Deployment Guide

This guide is for this repo specifically.

## Important constraints in the current codebase

1. The normal frontend dev environment still points to localhost.
   `frontend/.env` contains `VITE_API_BASE_URL=http://localhost:8000/api`

2. Real-time messaging uses WebSockets at `/ws/messages/`.
   Standard PythonAnywhere WSGI hosting will not serve those WebSockets.

Because of that, there are now two supported deployment patterns in this repo:

- Single-domain PythonAnywhere using `npm run build:pythonanywhere`
- Backend on PythonAnywhere plus frontend on a separate static host

## Single-domain option for `capstoneito`

This repo now supports a dedicated PythonAnywhere build that lets Django serve the React app at:

- `https://capstoneito.pythonanywhere.com/`
- API at `https://capstoneito.pythonanywhere.com/api/`

Real-time WebSocket messaging is still limited by normal PythonAnywhere WSGI hosting.

### 1. Create the web app

In PythonAnywhere:

1. Open the `Web` tab
2. Click `Add a new web app`
3. Choose `Manual configuration`
4. Pick Python `3.12+` if available

### 2. Clone the project

Use a simple Linux path with no spaces:

```bash
cd ~
git clone https://github.com/Iman-13/capstone.git caps
cd ~/caps
```

### 3. Create and attach a virtualenv

```bash
mkvirtualenv caps-env --python=/usr/bin/python3.12
pip install -r ~/caps/backend/requirements.txt
```

Then in the `Web` tab, set the virtualenv path to:

```text
/home/capstoneito/.virtualenvs/caps-env
```

### 4. Create the production `.env`

This repo already loads a repo-root `.env`, so place it at:

```text
/home/capstoneito/caps/.env
```

Example:

```env
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=replace-this-with-a-long-random-secret
ALLOWED_HOSTS=capstoneito.pythonanywhere.com

DATABASE_ENGINE=sqlite3
SQLITE_DB_PATH=db.sqlite3

ENABLE_HTTPS=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 5. Build the frontend for Django/PythonAnywhere

This build writes the React output into `backend/static/frontend` and uses `/static/frontend/` asset URLs.

```bash
cd ~/caps
npm install
npm run build:pythonanywhere
```

If you prefer running from the frontend directory directly:

```bash
cd ~/caps/frontend
npm install
npm run build:pythonanywhere
```

### 6. Configure the WSGI file

Open the WSGI configuration file from the `Web` tab and replace it with:

```python
import os
import sys

project_path = "/home/capstoneito/caps/backend"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afn_service_management.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. Run Django setup commands

In a Bash console:

```bash
workon caps-env
cd ~/caps/backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 8. Add static and media mappings

In the `Web` tab:

- URL `/static/` -> `/home/capstoneito/caps/backend/staticfiles`
- URL `/media/` -> `/home/capstoneito/caps/backend/media`

### 9. Reload and test

Reload the site from the `Web` tab, then test:

- `https://capstoneito.pythonanywhere.com/`
- `https://capstoneito.pythonanywhere.com/api/`
- `https://capstoneito.pythonanywhere.com/admin/`

## Recommended path: backend on PythonAnywhere, frontend elsewhere

This is still the easiest path if you do not want Django to serve the SPA.

### 1. Create the web app

In PythonAnywhere:

1. Open the `Web` tab
2. Click `Add a new web app`
3. Choose `Manual configuration`
4. Pick Python `3.12+` if available

### 2. Clone the project

Use a simple Linux path with no spaces:

```bash
cd ~
git clone <your-repo-url> caps
cd ~/caps
```

### 3. Create and attach a virtualenv

```bash
mkvirtualenv caps-env --python=/usr/bin/python3.12
pip install -r ~/caps/backend/requirements.txt
```

Then in the `Web` tab, set the virtualenv path to:

```text
/home/yourusername/.virtualenvs/caps-env
```

### 4. Create the production `.env`

This repo already loads a repo-root `.env`, so place it at:

```text
/home/yourusername/caps/.env
```

Example:

```env
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=replace-this-with-a-long-random-secret
ALLOWED_HOSTS=yourusername.pythonanywhere.com

DATABASE_ENGINE=sqlite3
SQLITE_DB_PATH=db.sqlite3

ENABLE_HTTPS=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

CORS_ALLOWED_ORIGINS=https://your-frontend-domain
CSRF_TRUSTED_ORIGINS=https://your-frontend-domain,https://yourusername.pythonanywhere.com
FRONTEND_BASE_URL=https://your-frontend-domain

OPENROUTESERVICE_API_KEY=...
ORS_API_KEY=...
```

Notes:

- If the frontend is hosted separately, set `CORS_ALLOWED_ORIGINS` to that frontend URL.
- If you do not need cross-site cookies, token auth is simpler.
- SQLite is the easiest starting point on PythonAnywhere.

### 5. Configure the WSGI file

Open the WSGI configuration file from the `Web` tab and replace it with:

```python
import os
import sys

project_path = "/home/yourusername/caps/backend"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afn_service_management.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 6. Run Django setup commands

In a Bash console:

```bash
workon caps-env
cd ~/caps/backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 7. Add static and media mappings

In the `Web` tab:

- URL `/static/` -> `/home/yourusername/caps/backend/staticfiles`
- URL `/media/` -> `/home/yourusername/caps/backend/media`

### 8. Reload and test

Reload the site from the `Web` tab, then test:

- `https://yourusername.pythonanywhere.com/`
- `https://yourusername.pythonanywhere.com/api/`
- `https://yourusername.pythonanywhere.com/admin/`

The root URL will return the built React app only after you run `npm run build:pythonanywhere`.

## Frontend deployment for the recommended path

Deploy the frontend separately and point it at PythonAnywhere.

### 1. Fix the production API URL

Do not build with the current `frontend/.env` value, because it points to localhost.

Create `frontend/.env.production` with:

```env
VITE_API_BASE_URL=https://yourusername.pythonanywhere.com/api
```

### 2. Build

```bash
cd ~/caps/frontend
npm install
npm run build
```

### 3. Deploy the built frontend

Use Vercel, Netlify, or another static host for `frontend/dist`.

## If you want everything on PythonAnywhere

Use the single-domain flow earlier in this guide and make sure you run:

```bash
cd ~/caps
npm install
npm run build:pythonanywhere
```

## WebSocket limitation

This project has WebSocket-based messaging.

Normal PythonAnywhere WSGI deployment will not serve `/ws/messages/`, so real-time chat will not work there as-is. For that you would need PythonAnywhere's ASGI beta or a different host that supports Django Channels/WebSockets cleanly.

## Troubleshooting checklist

- `DisallowedHost`: add your PythonAnywhere hostname to `ALLOWED_HOSTS`
- Frontend calls `localhost`: use `npm run build:pythonanywhere` so `frontend/.env.pythonanywhere` is applied
- Static files missing: rerun `collectstatic` and recheck `/static/` mapping
- CSRF errors: add the frontend URL to `CSRF_TRUSTED_ORIGINS`
- CORS errors: add the frontend URL to `CORS_ALLOWED_ORIGINS`
- Site imports fail: confirm the WSGI file points to `/home/yourusername/caps/backend`

## Recommended next step

For `capstoneito`, the exact single-domain target is `https://capstoneito.pythonanywhere.com/`. If you want the fastest low-maintenance setup instead, deploy only the backend on PythonAnywhere and keep the frontend on a static host.
