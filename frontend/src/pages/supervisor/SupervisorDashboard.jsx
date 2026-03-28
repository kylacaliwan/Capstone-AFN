import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiArrowRight, FiClipboard, FiMap, FiUsers } from 'react-icons/fi';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import QuickNavGrid from '../../components/QuickNavGrid';
import { fetchDashboardStats } from '../../api/api';

const formatDate = (value) => {
  if (!value) return 'No schedule set';

  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric'
    }).format(new Date(value));
  } catch {
    return value;
  }
};

export default function SupervisorDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardStats('supervisor')
      .then((data) => {
        setStats(data);
        setError('');
      })
      .catch((err) => {
        setStats(null);
        setError(err.message || 'Unable to load supervisor dashboard.');
      });
  }, []);

  const overview = stats?.overview || {};
  const technicianPerformance = stats?.technician_performance || [];
  const recentTickets = stats?.recent_tickets || [];
  const availableTechnicians = technicianPerformance.filter((tech) => tech.is_available).length;
  const topPerformers = technicianPerformance.slice(0, 5);

  const quickLinks = [
    {
      label: 'Dispatch Board',
      path: '/supervisor/dispatch-board',
      description: 'Assign jobs and keep the field load balanced.',
      icon: <FiMap />
    },
    {
      label: 'Service Tickets',
      path: '/supervisor/service-tickets',
      description: 'Review open ticket flow and team workload.',
      icon: <FiClipboard />
    },
    {
      label: 'Technician Monitoring',
      path: '/supervisor/technician-tracking',
      description: 'Track technician availability and live movement.',
      icon: <FiUsers />
    }
  ];

  return (
    <Layout>
      <section className="rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">Team Operations</p>
            <h2 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">Run the day from the queue, not from guesswork.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
              Strong modern supervisor views prioritize current workload, technician readiness, and the next
              action needed to keep service moving. This dashboard now follows that pattern.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[320px]">
            <button
              onClick={() => navigate('/supervisor/dispatch-board')}
              className="inline-flex items-center justify-center rounded-2xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
            >
              <FiMap className="mr-2" />
              Open Dispatch Board
            </button>
            <button
              onClick={() => navigate('/supervisor/technician-tracking')}
              className="inline-flex items-center justify-center rounded-2xl bg-white/10 px-4 py-3 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/20"
            >
              <FiUsers className="mr-2" />
              Monitor Technicians
            </button>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Team tickets" value={overview.team_tickets ?? 0} />
        <StatsCard title="Active tickets" value={overview.active_team_tickets ?? 0} color="text-sky-600" />
        <StatsCard title="Pending approvals" value={overview.pending_approvals ?? 0} color="text-amber-600" />
        <StatsCard title="Available technicians" value={availableTechnicians} color="text-emerald-600" />
      </section>

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      <section className="mt-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-slate-900">Primary Actions</h3>
            <p className="text-sm text-slate-500">The tools supervisors use most should stay visible first.</p>
          </div>
        </div>
        <QuickNavGrid items={quickLinks} />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-semibold text-slate-900">Technician Readiness</h3>
                <p className="mt-1 text-sm text-slate-500">Availability and completed work from the last 30 days.</p>
              </div>
              <button
                onClick={() => navigate('/supervisor/technician-tracking')}
                className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 sm:inline-flex"
              >
                Open tracking
                <FiArrowRight size={14} />
              </button>
            </div>
            <div className="mt-5 space-y-3">
              {topPerformers.length > 0 ? (
                topPerformers.map((tech) => (
                  <div key={tech.id} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{tech.username}</div>
                        <div className="mt-1 text-sm text-slate-500">
                          {tech.tickets_completed} completed in the last 30 days
                        </div>
                      </div>
                      <div
                        className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                          tech.is_available ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {tech.is_available ? 'Available' : 'Busy'}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  Technician activity will appear here once assignments are active.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h3 className="text-xl font-semibold text-slate-900">Queue Signals</h3>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Team size tracked</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.total_technicians ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Approval queue</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{overview.pending_approvals ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Available right now</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{availableTechnicians}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">Recent Team Tickets</h3>
              <p className="mt-1 text-sm text-slate-500">The latest jobs and schedules under supervisor control.</p>
            </div>
            <button
              onClick={() => navigate('/supervisor/service-tickets')}
              className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 sm:inline-flex"
            >
              Review queue
              <FiArrowRight size={14} />
            </button>
          </div>

          <div className="mt-5 space-y-3">
            {recentTickets.length > 0 ? (
              recentTickets.map((ticket) => (
                <div key={ticket.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{ticket.client}</div>
                      <div className="mt-1 text-sm text-slate-500">
                        {ticket.technician || 'Unassigned'} handling {String(ticket.priority || 'Normal').toLowerCase()} priority work
                      </div>
                    </div>
                    <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                      {ticket.status}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                    <span>Ticket #{ticket.id}</span>
                    <span>{formatDate(ticket.scheduled_date)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                Recent team tickets will show up here once the supervisor has assignments.
              </div>
            )}
          </div>
        </div>
      </section>
    </Layout>
  );
}
