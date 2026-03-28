import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FiBell,
  FiCalendar,
  FiCheckSquare,
  FiClipboard,
  FiFileText,
  FiMap,
  FiMessageSquare,
  FiSettings
} from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import QuickNavGrid from '../../components/QuickNavGrid';
import { fetchNotifications, fetchTechnicianDashboard, updateTechnicianLocation } from '../../api/api';
import { useGPSTracking } from '../../hooks/useGPSTracking';
import GPSStatusIndicator from '../../components/GPSStatusIndicator';

const EMPTY_DASHBOARD = {
  technician: {
    is_available: false,
    current_location: null
  },
  stats: {
    total_assigned: 0,
    completed_today: 0,
    pending_jobs: 0,
    active_jobs: 0
  },
  todays_schedule: [],
  active_jobs: [],
  recent_activity: []
};

const normalizeStatus = (status) => String(status || '').toLowerCase().replace(/\s+/g, '_');

const formatStatusLabel = (status) =>
  normalizeStatus(status)
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown';

const formatTimeSlot = (value) => {
  const normalized = normalizeStatus(value);
  if (!normalized) return '';
  return normalized
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const formatDateLabel = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
};

const formatTimeLabel = (value) => {
  if (!value) return '';
  const date = new Date(`1970-01-01T${value}`);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit'
  });
};

const formatNotificationTime = (value) => {
  if (!value) return 'Just now';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Just now';
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
};

export default function TechnicianDashboard() {
  const { user } = useAuth();
  const techName = user?.username || 'Technician';
  const [dashboard, setDashboard] = useState(EMPTY_DASHBOARD);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const {
    location,
    error: gpsError,
    permission: gpsPermission
  } = useGPSTracking({
    updateInterval: 20000,
    autoStart: true,
    onLocationUpdate: async (loc) => {
      try {
        await updateTechnicianLocation({
          techName,
          lat: loc.latitude,
          lng: loc.longitude,
          accuracy: loc.accuracy,
          speed: loc.speed,
          heading: loc.heading
        });
      } catch (err) {
        console.error('Failed to update location:', err);
      }
    }
  });

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [dashboardData, notificationData] = await Promise.all([
          fetchTechnicianDashboard(techName),
          fetchNotifications()
        ]);

        const sortedNotifications = [...notificationData].sort(
          (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
        );

        setDashboard(dashboardData || EMPTY_DASHBOARD);
        setNotifications(sortedNotifications.slice(0, 5));
        setError('');
      } catch (err) {
        setDashboard(EMPTY_DASHBOARD);
        setNotifications([]);
        setError(err.message || 'Unable to load technician dashboard.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [techName]);

  const todaysSchedule = Array.isArray(dashboard.todays_schedule) ? dashboard.todays_schedule : [];
  const activeJobs = Array.isArray(dashboard.active_jobs) ? dashboard.active_jobs : [];
  const recentActivity = Array.isArray(dashboard.recent_activity) ? dashboard.recent_activity : [];
  const unreadNotifications = notifications.filter((item) => item.status === 'unread').length;

  const currentJob =
    activeJobs.find((job) => normalizeStatus(job.status) === 'in_progress') ||
    todaysSchedule.find((job) => normalizeStatus(job.status) !== 'completed') ||
    activeJobs[0] ||
    null;

  const nextJob =
    todaysSchedule.find((job) => job.id !== currentJob?.id && normalizeStatus(job.status) !== 'completed') ||
    null;

  const gpsLatitude = location?.latitude ?? Number(dashboard.technician?.current_location?.latitude);
  const gpsLongitude = location?.longitude ?? Number(dashboard.technician?.current_location?.longitude);
  const gpsAccuracy = location?.accuracy;

  const quickLinks = [
    { label: 'My Jobs', path: '/technician/my-jobs', description: 'Manage assigned jobs and status.', icon: <FiClipboard /> },
    { label: 'Schedule', path: '/technician/schedule', description: "Review today's appointments.", icon: <FiCalendar /> },
    { label: 'Map Navigation', path: '/technician/map-navigation', description: 'Open the live route experience.', icon: <FiMap /> },
    { label: 'Digital Checklist', path: '/technician/checklist', description: 'Complete service procedures.', icon: <FiCheckSquare /> },
    { label: 'Messages', path: '/technician/messages', description: 'Communicate with supervisors.', icon: <FiMessageSquare /> },
    { label: 'Job History', path: '/technician/job-history', description: 'Review completed work.', icon: <FiFileText /> },
    { label: 'Profile', path: '/technician/profile', description: 'Update account and metrics.', icon: <FiSettings /> }
  ];

  return (
    <Layout>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-800">Welcome back, {techName}</h2>
        <p className="text-slate-500">Your technician workspace now shows live job focus, schedule, alerts, and GPS health.</p>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mb-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Today's Jobs" value={todaysSchedule.length} color="text-blue-600" />
        <StatsCard title="Active Jobs" value={dashboard.stats?.active_jobs || 0} color="text-orange-600" />
        <StatsCard title="Completed Today" value={dashboard.stats?.completed_today || 0} color="text-green-600" />
        <StatsCard title="Unread Alerts" value={unreadNotifications} color="text-rose-600" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <section className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Current Focus</p>
              <h3 className="mt-2 text-xl font-semibold text-slate-900">
                {currentJob ? `Ticket #${currentJob.id}: ${currentJob.service_type}` : 'No active field job right now'}
              </h3>
              <p className="mt-2 text-sm text-slate-500">
                {currentJob
                  ? `${currentJob.client} • ${currentJob.location || 'Location pending'}`
                  : 'When a job is assigned or started, it will appear here with quick actions.'}
              </p>
            </div>
            <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              {currentJob ? formatStatusLabel(currentJob.status) : 'Idle'}
            </div>
          </div>

          {currentJob ? (
            <>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Schedule</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">
                    {formatDateLabel(currentJob.scheduled_date)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatTimeLabel(currentJob.scheduled_time) || formatTimeSlot(currentJob.scheduled_time_slot) || 'Time not set'}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Client</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">{currentJob.client}</p>
                  <p className="mt-1 text-xs text-slate-500">{currentJob.priority || 'Normal'} priority</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Address</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">{currentJob.location || 'Location pending'}</p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  to="/technician/my-jobs"
                  className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Open My Jobs
                </Link>
                <Link
                  to={`/technician/map-navigation?ticketId=${currentJob.id}`}
                  className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600"
                >
                  Navigate to Job
                </Link>
                <Link
                  to={`/technician/checklist?ticketId=${currentJob.id}`}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open Checklist
                </Link>
              </div>
            </>
          ) : (
            <div className="mt-5">
              <Link
                to="/technician/schedule"
                className="inline-flex rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Check Schedule
              </Link>
            </div>
          )}

          {nextJob && (
            <div className="mt-6 rounded-2xl border border-indigo-200 bg-indigo-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">Up Next</p>
              <p className="mt-2 text-sm font-semibold text-indigo-950">
                Ticket #{nextJob.id}: {nextJob.service_type}
              </p>
              <p className="mt-1 text-sm text-indigo-900">
                {nextJob.client} • {formatDateLabel(nextJob.scheduled_date)}
                {formatTimeLabel(nextJob.scheduled_time) ? ` • ${formatTimeLabel(nextJob.scheduled_time)}` : ''}
              </p>
            </div>
          )}
        </section>

        <section className="rounded-2xl bg-gradient-to-br from-emerald-500 to-green-600 p-5 text-white shadow-lg">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-100">GPS Status</p>
              <h3 className="mt-2 text-xl font-semibold">Live Technician Tracking</h3>
              <p className="mt-2 text-sm text-emerald-50">
                Supervisors rely on this feed for route visibility and dispatch coordination.
              </p>
            </div>
            <GPSStatusIndicator status={gpsPermission} accuracy={gpsAccuracy} className="rounded-full bg-white/15 px-3 py-1.5" />
          </div>

          <div className="mt-5 space-y-3 rounded-2xl bg-white/10 p-4 backdrop-blur">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">Availability</p>
              <p className="mt-1 text-sm font-medium">
                {dashboard.technician?.is_available ? 'Available for dispatch' : 'Currently on a job'}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">Coordinates</p>
              <p className="mt-1 text-sm font-medium">
                {Number.isFinite(gpsLatitude) && Number.isFinite(gpsLongitude)
                  ? `${gpsLatitude.toFixed(6)}, ${gpsLongitude.toFixed(6)}`
                  : 'Waiting for GPS fix'}
              </p>
            </div>
            {gpsError && (
              <div className="rounded-xl border border-white/20 bg-white/10 p-3 text-sm text-white">
                {gpsError.message}
              </div>
            )}
          </div>
        </section>
      </div>

      <QuickNavGrid items={quickLinks} />

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-slate-900">Today's Schedule</h3>
            <Link to="/technician/schedule" className="text-sm font-medium text-blue-600 hover:text-blue-700">
              View full schedule
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {loading ? (
              <div className="text-sm text-slate-500">Loading schedule...</div>
            ) : todaysSchedule.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                No jobs scheduled for today.
              </div>
            ) : (
              todaysSchedule.slice(0, 4).map((job) => (
                <div key={job.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">{job.service_type}</p>
                      <p className="text-sm text-slate-600">{job.client}</p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                      {formatStatusLabel(job.status)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-500">
                    {formatDateLabel(job.scheduled_date)}
                    {formatTimeLabel(job.scheduled_time) ? ` • ${formatTimeLabel(job.scheduled_time)}` : ''}
                    {!formatTimeLabel(job.scheduled_time) && job.scheduled_time_slot ? ` • ${formatTimeSlot(job.scheduled_time_slot)}` : ''}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">{job.location || 'Location pending'}</p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <FiBell className="text-blue-600" />
              Notifications
            </h3>
            <Link to="/technician/messages" className="text-sm font-medium text-blue-600 hover:text-blue-700">
              Open messages
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {loading ? (
              <div className="text-sm text-slate-500">Loading notifications...</div>
            ) : notifications.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                No recent notifications.
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`rounded-xl border p-4 ${
                    notification.status === 'unread' ? 'border-blue-200 bg-blue-50' : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">
                        {notification.title || formatStatusLabel(notification.type)}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">{notification.message}</p>
                    </div>
                    {notification.status === 'unread' && (
                      <span className="rounded-full bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white">
                        Unread
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{formatNotificationTime(notification.created_at)}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-slate-900">Recent Activity</h3>
          <Link to="/technician/job-history" className="text-sm font-medium text-blue-600 hover:text-blue-700">
            Open history
          </Link>
        </div>
        <div className="mt-4 space-y-3">
          {loading ? (
            <div className="text-sm text-slate-500">Loading activity...</div>
          ) : recentActivity.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              No recent technician activity yet.
            </div>
          ) : (
            recentActivity.slice(0, 5).map((item) => (
              <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900">
                      Ticket #{item.id}: {item.service_type}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">{item.client}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {formatStatusLabel(item.status)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </Layout>
  );
}
