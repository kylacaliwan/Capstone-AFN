import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiActivity,
  FiAlertTriangle,
  FiBox,
  FiClipboard,
  FiFileText,
  FiMap,
  FiSettings,
  FiShield,
  FiUsers
} from 'react-icons/fi';
import { Circle, MapContainer, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import QuickNavGrid from '../../components/QuickNavGrid';
import { fetchCoverageHeatmap, fetchDashboardStats } from '../../api/api';

const getHeatmapColor = (count, maxDensity) => {
  const safeMax = maxDensity || 1;
  const intensity = count / safeMax;
  if (intensity > 0.8) return '#dc2626';
  if (intensity > 0.6) return '#ea580c';
  if (intensity > 0.4) return '#ca8a04';
  if (intensity > 0.2) return '#16a34a';
  return '#22c55e';
};

const getHeatmapRadius = (count) => Math.max(180, Math.min(700, count * 120));

const formatDate = (value) => {
  if (!value) return 'No date available';

  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(new Date(value));
  } catch {
    return value;
  }
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [heatmapData, setHeatmapData] = useState([]);
  const [heatmapStats, setHeatmapStats] = useState({ totalPoints: 0, maxDensity: 0 });
  const [error, setError] = useState('');
  const [heatmapError, setHeatmapError] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  useEffect(() => {
    Promise.allSettled([fetchDashboardStats('admin'), fetchCoverageHeatmap()]).then(
      ([statsResult, heatmapResult]) => {
        if (statsResult.status === 'fulfilled') {
          setStats(statsResult.value);
          setError('');
        } else {
          setStats(null);
          setError(statsResult.reason?.message || 'Unable to load admin dashboard.');
        }

        if (heatmapResult.status === 'fulfilled') {
          const response = heatmapResult.value || {};
          setHeatmapData(response.heatmap_data || []);
          setHeatmapStats({
            totalPoints: response.total_points || 0,
            maxDensity: response.max_density || 0
          });
          setHeatmapError('');
        } else {
          setHeatmapData([]);
          setHeatmapStats({ totalPoints: 0, maxDensity: 0 });
          setHeatmapError(heatmapResult.reason?.message || 'Unable to load service coverage heatmap.');
        }
      }
    );
  }, []);

  const overview = stats?.overview || {};
  const pendingRequests = stats?.pending_requests || [];
  const clientSchedule = stats?.client_schedule || [];
  const recentTickets = stats?.recent_activity?.tickets || [];
  const recentRequests = stats?.recent_activity?.requests || [];
  const hotspotList = [...heatmapData].sort((a, b) => (b.count || 0) - (a.count || 0)).slice(0, 4);
  const mapCenter = heatmapData.length > 0 ? [heatmapData[0].lat, heatmapData[0].lng] : [6.55, 3.35];

  const quickLinks = [
    {
      label: 'Service Tickets',
      path: '/admin/service-tickets',
      description: 'Review queue health and move blockers fast.',
      icon: <FiClipboard />
    },
    {
      label: 'Dispatch Board',
      path: '/admin/dispatch-board',
      description: 'Balance assignments and technician coverage.',
      icon: <FiMap />
    },
    {
      label: 'Technicians',
      path: '/admin/technicians',
      description: 'Manage staffing, skills, and availability.',
      icon: <FiUsers />
    },
    {
      label: 'Analytics',
      path: '/admin/analytics',
      description: 'Watch trends, risk, and predicted demand.',
      icon: <FiFileText />
    }
  ];

  const doAction = (path, label) => {
    setActionMessage(`${label} opening...`);
    navigate(path);
  };

  return (
    <Layout>
      <section className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200">Operations Control</p>
            <h1 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">Command the operation in one sweep.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
              Current operations platforms work best when the first screen answers three things quickly:
              what needs attention, what is moving, and where capacity is getting tight. This dashboard now
              follows that pattern.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[340px]">
            <button
              onClick={() => doAction('/admin/service-tickets', 'Service Tickets')}
              className="inline-flex items-center justify-center rounded-2xl bg-white/15 px-4 py-3 text-sm font-medium text-white backdrop-blur transition hover:bg-white/20"
            >
              <FiClipboard className="mr-2" />
              Review Tickets
            </button>
            <button
              onClick={() => doAction('/admin/analytics', 'Predictive Analytics')}
              className="inline-flex items-center justify-center rounded-2xl bg-sky-400 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-sky-300"
            >
              <FiFileText className="mr-2" />
              Open Analytics
            </button>
          </div>
        </div>
        {actionMessage && (
          <div className="mt-4 rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-sky-100">
            {actionMessage}
          </div>
        )}
      </section>

      <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Active tickets" value={overview.active_tickets ?? 0} color="text-sky-600" />
        <StatsCard title="Pending approvals" value={pendingRequests.length} color="text-amber-600" />
        <StatsCard title="Ready technicians" value={overview.active_technicians ?? 0} color="text-emerald-600" />
        <StatsCard title="Low-stock items" value={overview.low_stock_items ?? 0} color="text-rose-600" />
      </section>

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      <section className="mt-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">Primary Workflows</h2>
            <p className="text-sm text-slate-500">Use the areas that ops teams touch repeatedly throughout the day.</p>
          </div>
        </div>
        <QuickNavGrid items={quickLinks} />
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-[1.3fr_0.9fr]">
        <div className="space-y-4">
          <div className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-amber-100 p-3 text-xl text-amber-700">
                <FiAlertTriangle />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">Action Queue</h2>
                <p className="text-sm text-slate-500">The items most likely to cause friction if they sit untouched.</p>
              </div>
            </div>
            <div className="mt-5 space-y-3">
              {pendingRequests.length > 0 ? (
                pendingRequests.slice(0, 4).map((request) => (
                  <div key={request.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{request.client}</div>
                        <div className="mt-1 text-sm text-slate-500">{request.service_type}</div>
                      </div>
                      <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                        {request.status}
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-slate-500">Requested {formatDate(request.request_date)}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  No pending approvals right now.
                </div>
              )}
            </div>
          </div>

          <div className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-rose-100 p-3 text-xl text-rose-700">
                <FiShield />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">Risk Signals</h2>
                <p className="text-sm text-slate-500">Systemwide alerts that usually matter most to admins.</p>
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Out of stock</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.out_of_stock ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total users</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.total_users ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total inventory</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.total_inventory ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Completed today</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.completed_today ?? 0}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="card overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-sky-100 p-3 text-xl text-sky-700">
                <FiMap />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">Service Coverage Heatmap</h2>
                <p className="text-sm text-slate-500">Places where your completed service work is concentrated.</p>
              </div>
            </div>
            <button
              onClick={() => doAction('/admin/coverage-heatmap', 'Coverage Heatmap')}
              className="hidden rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 sm:inline-flex"
            >
              View Full Map
            </button>
          </div>

          {heatmapError ? (
            <div className="p-5 text-sm text-red-800">{heatmapError}</div>
          ) : heatmapData.length === 0 ? (
            <div className="p-5 text-sm text-slate-500">No completed service hotspots are available yet.</div>
          ) : (
            <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="h-[340px] min-h-[340px]">
                <MapContainer center={mapCenter} zoom={11} scrollWheelZoom={true} className="h-full w-full">
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  {heatmapData.map((point, index) => (
                    <Circle
                      key={`dashboard-heatmap-${index}`}
                      center={[point.lat, point.lng]}
                      radius={getHeatmapRadius(point.count)}
                      pathOptions={{
                        color: getHeatmapColor(point.count, heatmapStats.maxDensity),
                        fillColor: getHeatmapColor(point.count, heatmapStats.maxDensity),
                        fillOpacity: 0.45,
                        weight: 2
                      }}
                    >
                      <Popup>
                        <div className="text-center text-sm">
                          <strong>Service Hotspot</strong>
                          <br />
                          {point.count} completed requests
                          <br />
                          <small>{(point.service_types || []).join(', ')}</small>
                        </div>
                      </Popup>
                    </Circle>
                  ))}
                </MapContainer>
              </div>

              <div className="space-y-4 border-t border-slate-200 p-5 lg:border-l lg:border-t-0 sm:p-6">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Service Areas</div>
                    <div className="mt-2 text-2xl font-bold text-slate-900">{heatmapStats.totalPoints}</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Peak Density</div>
                    <div className="mt-2 text-2xl font-bold text-slate-900">{heatmapStats.maxDensity}</div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Top Hotspots</h3>
                  <div className="mt-3 space-y-3">
                    {hotspotList.map((point, index) => (
                      <div key={`${point.address}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-semibold text-slate-900">{point.address || 'Service Area'}</div>
                            <div className="mt-1 text-sm text-slate-500">
                              {(point.service_types || []).join(', ') || 'Completed services'}
                            </div>
                          </div>
                          <div className="rounded-full bg-slate-900 px-3 py-1 text-sm font-semibold text-white">
                            {point.count}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => doAction('/admin/coverage-heatmap', 'Coverage Heatmap')}
                  className="inline-flex items-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
                >
                  <FiMap className="mr-2" />
                  Explore Full Heatmap
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="card p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-emerald-100 p-3 text-xl text-emerald-700">
              <FiActivity />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">Upcoming Schedule</h2>
              <p className="text-sm text-slate-500">Appointments already booked and needing execution readiness.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {clientSchedule.length > 0 ? (
              clientSchedule.slice(0, 4).map((ticket) => (
                <div key={ticket.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{ticket.client}</div>
                      <div className="mt-1 text-sm text-slate-500">{ticket.service_type}</div>
                    </div>
                    <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                      {ticket.status}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                    <span>{formatDate(ticket.scheduled_date)}</span>
                    <span>{ticket.scheduled_time || 'Time pending'}</span>
                    <span>{ticket.assigned_technician || 'Unassigned technician'}</span>
                  </div>
                  <div className="mt-2 text-sm text-slate-500">{ticket.location || 'Location pending'}</div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                Upcoming scheduled work will appear here once appointments are assigned.
              </div>
            )}
          </div>
        </div>

        <div className="card p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-amber-100 p-3 text-xl text-amber-700">
              <FiSettings />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">Recent Activity</h2>
              <p className="text-sm text-slate-500">What just changed across requests and tickets.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {[...recentTickets, ...recentRequests].slice(0, 6).map((item, index) => (
              <div
                key={`${item.id}-${index}`}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
              >
                <div className="font-semibold text-slate-900">{item.client}</div>
                <div className="mt-1">{item.service_type}</div>
                <div className="mt-2 flex flex-wrap gap-3 text-xs font-medium uppercase tracking-wide text-slate-400">
                  <span>{item.status}</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 grid gap-3">
            <button
              onClick={() => doAction('/admin/technicians', 'Technicians')}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <span className="flex items-center gap-3">
                <FiUsers className="text-primary" />
                Manage technicians and clients
              </span>
            </button>
            <button
              onClick={() => doAction('/admin/inventory', 'Inventory')}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <span className="flex items-center gap-3">
                <FiBox className="text-primary" />
                Manage inventory thresholds
              </span>
            </button>
            <button
              onClick={() => doAction('/admin/reports', 'Reports')}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <span className="flex items-center gap-3">
                <FiFileText className="text-primary" />
                Generate reports and exports
              </span>
            </button>
          </div>
        </div>
      </section>
    </Layout>
  );
}
