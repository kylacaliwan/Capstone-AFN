# AFN Service Management (Frontend)

Enterprise front-end for AFN Solar Power Engineering Services.

## Tech stack
- React + Vite
- TailwindCSS
- React Router
- Axios (Django REST API)
- Leaflet (GIS map)
- React Icons
- Firebase Cloud Messaging

## Features
- Role-based screens: admin / supervisor / technician / client
- Routing: `/admin/dashboard`, `/supervisor/dashboard`, `/technician/dashboard`, `/client/dashboard`
- Reusable layout (sidebar + topbar + content)
- Live service requests, dispatch, tracking, job updates, and admin settings
- Leaflet map with technicians + service locations

## Start
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Run the Django API separately from the repository root:

```bash
cd backend
python manage.py runserver
```

## Authentication
- Use real accounts created through the Django backend.
- For first-time bootstrap, set `AFN_BOOTSTRAP_ADMIN_PASSWORD` and run `backend/create_admin.py`.

## Build
```bash
npm run build
```

## Production Notes
- Set the frontend API base URL to your deployed Django API.
- Configure backend env vars for `SECRET_KEY`, `ALLOWED_HOSTS`, CORS, database, Firebase, and OpenRouteService.
- Keep demo seed commands out of production environments.
