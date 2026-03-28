# AFN Service Management (Frontend)

Enterprise front-end for AFN Solar Power Engineering Services.

## Tech stack
- React + Vite
- TailwindCSS
- React Router
- Axios (mock API)
- Leaflet (GIS map)
- React Icons

## Features
- Role-based screens: admin / supervisor / technician / client
- Routing: `/admin/dashboard`, `/supervisor/dashboard`, `/technician/dashboard`, `/client/dashboard`
- Reusable layout (sidebar + topbar + content)
- Mock data, service tickets, dispatch, tracking, job updates
- Leaflet map with technicians + service locations

## Start
```bash
cd d:\tryfrontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Demo logins
- Role: `admin`, `supervisor`, `technician`, `client`
- Username: any value

## Build
```bash
npm run build
```

## Further improvements
- Replace `src/api/mockApi.js` with real API endpoints
- Add auth + JWT
- Add charts for analytics and reports
- Add persistent notification system
- Add unit/integration tests
