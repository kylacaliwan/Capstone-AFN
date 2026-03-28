import { useEffect, useRef, useState } from 'react';
import Layout from '../../components/Layout';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  fetchTrackingData,
  fetchServiceTickets,
  assignTechnician,
  fetchNavigationRoute
} from '../../api/api';
import StatusBadge from '../../components/StatusBadge';

const DEFAULT_CENTER = [12.8797, 121.7740];
const ASSIGNABLE_STATUSES = new Set(['not_started', 'on_hold']);

const hasCoordinates = (item) => Number.isFinite(item?.lat) && Number.isFinite(item?.lng);

const isTicketAssignable = (ticket) => ASSIGNABLE_STATUSES.has(String(ticket?.status || '').toLowerCase());

export default function SupervisorTracking() {
  const [data, setData] = useState({ techMarkers: [], ticketMarkers: [] });
  const [filterStatus, setFilterStatus] = useState('all');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [selectedTechId, setSelectedTechId] = useState('');
  const [focusedTicket, setFocusedTicket] = useState(null);
  const [route, setRoute] = useState({ coords: [], distance: 0, eta: 0, ticketId: null });
  const [routeLoading, setRouteLoading] = useState(false);
  const mapRef = useRef(null);

  const loadData = async () => {
    try {
      const newData = await fetchTrackingData();
      setData(newData);
      setError('');
    } catch (err) {
      setData({ techMarkers: [], ticketMarkers: [] });
      setError(err.message || 'Unable to load tracking data.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const refreshData = async () => {
    setMessage('Refreshing tracking data...');
    await loadData();
    setMessage('Tracking data refreshed.');
    setTimeout(() => setMessage(''), 3000);
  };

  const filteredTechs = data.techMarkers.filter((tech) => filterStatus === 'all' || tech.status === filterStatus);
  const filteredTickets = data.ticketMarkers.filter((ticket) => ticket.status !== 'completed');
  const selectedTech = data.techMarkers.find((tech) => String(tech.id) === selectedTechId);

  const focusOnTicket = (ticket) => {
    setFocusedTicket(ticket.id);
    if (mapRef.current && hasCoordinates(ticket)) {
      mapRef.current.flyTo([ticket.lat, ticket.lng], 12, { duration: 1.2 });
    }
  };

  const handleTechnicianSelect = (techId) => {
    setSelectedTechId(techId);
    const tech = data.techMarkers.find((item) => String(item.id) === techId);
    if (tech && mapRef.current && hasCoordinates(tech)) {
      mapRef.current.flyTo([tech.lat, tech.lng], 12, { duration: 1.2 });
    }
  };

  const showRouteToTicket = async (ticket) => {
    if (!selectedTechId) {
      setMessage('Select technician before routing.');
      return;
    }

    const tech = data.techMarkers.find((item) => String(item.id) === selectedTechId);
    if (!tech || !hasCoordinates(tech)) {
      setMessage('Selected technician has no known coordinates.');
      return;
    }
    if (!hasCoordinates(ticket)) {
      setMessage('This ticket does not have complete coordinates for routing.');
      return;
    }

    try {
      setRouteLoading(true);
      const routeData = await fetchNavigationRoute(tech.lat, tech.lng, ticket.lat, ticket.lng);
      setRoute({
        coords: routeData.routeCoords,
        distance: routeData.distanceKm,
        eta: routeData.estimatedTimeMin,
        ticketId: ticket.id
      });
      if (mapRef.current) {
        mapRef.current.fitBounds(routeData.routeCoords, { padding: [24, 24] });
      }
      setMessage(`Route set from ${tech.name} to ticket #${ticket.id}: ${routeData.distanceKm} km, ETA ${routeData.estimatedTimeMin} min.`);
    } catch (routeError) {
      setMessage(routeError.message || 'Route fetch failed.');
    } finally {
      setRouteLoading(false);
    }
  };

  const handleAssign = async (ticket) => {
    if (!selectedTech) {
      setMessage('Select a technician first.');
      return;
    }
    if (!isTicketAssignable(ticket)) {
      setMessage('Only queued or on-hold tickets can be assigned from this screen.');
      return;
    }

    try {
      setMessage(`Assigning ticket ${ticket.id} to ${selectedTech.name}...`);
      await assignTechnician({ ticketId: ticket.id, technicianId: selectedTech.id });
      await loadData();
      await fetchServiceTickets();
      setRoute({ coords: [], distance: 0, eta: 0, ticketId: null });
      setMessage(`Assigned ticket ${ticket.id} to ${selectedTech.name}.`);
      setTimeout(() => setMessage(''), 3000);
    } catch (assignError) {
      setMessage(assignError.message || 'Assignment failed.');
    }
  };

  return (
    <Layout>
      <div className="mb-4 flex flex-col gap-4 lg:flex-row">
        <h2 className="flex-1 text-2xl font-semibold text-slate-800">Supervisor Technician Tracking</h2>
        <div className="flex gap-2">
          <button onClick={refreshData} className="rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600">
            Refresh
          </button>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded border px-3 py-2">
            <option value="all">All Status</option>
            <option value="available">Available</option>
            <option value="on_job">On Job</option>
            <option value="offline">Offline</option>
          </select>
        </div>
      </div>

      {message && <p className="mb-4 rounded-lg bg-green-100 p-3 text-green-800">{message}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-100 p-3 text-red-800">{error}</p>}
      {selectedTech && (
        <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
          <div className="font-semibold">Selected technician: {selectedTech.name}</div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={selectedTech.status} size="sm" />
            <span>
              Coordinates:{' '}
              {hasCoordinates(selectedTech)
                ? `${selectedTech.lat.toFixed(6)}, ${selectedTech.lng.toFixed(6)}`
                : 'Unavailable'}
            </span>
          </div>
        </div>
      )}
      {route.coords.length > 0 && (
        <div className="mb-4 rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
          Route ready for ticket #{route.ticketId}: {route.distance} km, ETA {route.eta} min.
        </div>
      )}

      <div className="relative mb-4 h-[70vh] overflow-hidden rounded-xl shadow-lg">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={6}
          scrollWheelZoom={true}
          className="h-full w-full"
          whenCreated={(mapInstance) => {
            mapRef.current = mapInstance;
          }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {filteredTechs.map((tech) => (
            <Marker key={tech.id} position={hasCoordinates(tech) ? [tech.lat, tech.lng] : DEFAULT_CENTER}>
              <Popup>
                <div className="text-sm">
                  <strong>{tech.name}</strong>
                  <br />
                  Status: {tech.status}
                  <br />
                  Job: {tech.currentJob || 'None'}
                </div>
              </Popup>
            </Marker>
          ))}
          {filteredTickets.map((ticket) => (
            <Marker key={`t-${ticket.id}`} position={hasCoordinates(ticket) ? [ticket.lat, ticket.lng] : DEFAULT_CENTER}>
              <Popup>
                <div className="text-sm">
                  <strong>Ticket #{ticket.id}</strong>
                  <br />
                  {ticket.service}
                  <br />
                  {ticket.locationDesc || 'No landmark'}
                  <br />
                  {hasCoordinates(ticket) ? `${ticket.lat.toFixed(6)}, ${ticket.lng.toFixed(6)}` : 'Coordinates unavailable'}
                </div>
              </Popup>
            </Marker>
          ))}
          {route.coords.length > 0 && (
            <Polyline positions={route.coords} pathOptions={{ color: '#2563eb', weight: 4 }} />
          )}
        </MapContainer>
        <div className="absolute left-4 top-4 rounded-xl border bg-white/90 p-4 shadow-lg backdrop-blur">
          Live tracking: {filteredTechs.length}/{data.techMarkers.length} technicians active
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold">Technicians</h3>
          {filteredTechs.length ? (
            <ul className="space-y-2">
              {filteredTechs.map((tech) => (
                <li key={tech.id} className="rounded border p-2">
                  <div className="font-medium">{tech.name} ({tech.status})</div>
                  <div className="text-sm">Current job: {tech.currentJob || 'None'}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No technicians found with selected status.</p>
          )}
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold">Ticket Assign</h3>
          {filteredTickets.length ? (
            filteredTickets.map((ticket) => (
              <div
                key={ticket.id}
                className={`mb-2 rounded border p-3 ${focusedTicket === ticket.id ? 'bg-blue-50 ring-2 ring-blue-400' : ''}`}
              >
                <div className="font-medium">
                  Ticket #{ticket.id}: {ticket.client} / {ticket.service}
                </div>
                <div className="mb-1 mt-1">
                  <StatusBadge status={ticket.status} size="sm" />
                </div>
                <div className="text-sm mb-1">
                  Location: {hasCoordinates(ticket) ? `${ticket.lat.toFixed(6)}, ${ticket.lng.toFixed(6)}` : 'n/a'}
                </div>
                <div className="mb-2 text-sm">Landmark/Desc: {ticket.locationDesc || 'Not provided'}</div>
                <button
                  onClick={() => focusOnTicket(ticket)}
                  className="mb-2 w-full rounded bg-indigo-500 px-3 py-2 text-white hover:bg-indigo-600"
                >
                  Focus on map
                </button>
                <button
                  onClick={() => showRouteToTicket(ticket)}
                  disabled={!selectedTechId || routeLoading || !hasCoordinates(ticket)}
                  className="mb-2 w-full rounded bg-cyan-500 px-3 py-2 text-white hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {routeLoading ? 'Loading route...' : 'Show route from selected technician'}
                </button>
                <select
                  value={selectedTechId}
                  onChange={(e) => handleTechnicianSelect(e.target.value)}
                  className="mb-2 w-full rounded border px-2 py-1"
                >
                  <option value="">Select Technician</option>
                  {filteredTechs.map((tech) => (
                    <option key={tech.id} value={String(tech.id)}>
                      {tech.name} ({tech.status})
                    </option>
                  ))}
                </select>
                {!isTicketAssignable(ticket) && (
                  <div className="mb-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    Assignment is only available for queued or on-hold tickets. This ticket is currently {ticket.status}.
                  </div>
                )}
                <button
                  onClick={() => handleAssign(ticket)}
                  disabled={!selectedTechId || !isTicketAssignable(ticket)}
                  className="w-full rounded bg-green-500 px-3 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Assign
                </button>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No tickets available.</p>
          )}
        </div>
      </div>
    </Layout>
  );
}
