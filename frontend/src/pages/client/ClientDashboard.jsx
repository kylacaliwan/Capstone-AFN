import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiAlertCircle,
  FiArrowRight,
  FiCheckCircle,
  FiClipboard,
  FiClock,
  FiMessageSquare,
  FiPlusSquare
} from 'react-icons/fi';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import QuickNavGrid from '../../components/QuickNavGrid';
import { fetchDashboardStats } from '../../api/api';

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

export default function ClientDashboard() {
  const [stats, setStats] = useState({});
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardStats('client')
      .then((data) => {
        setStats(data);
        setError('');
      })
      .catch((err) => {
        setStats({});
        setError(err.message || 'Unable to load client dashboard.');
      });
  }, []);

  const overview = stats?.overview || {};
  const statusBreakdown = stats?.status_breakdown || {};
  const alerts = stats?.alerts || [];
  const recommendations = stats?.recommendations || [];
  const activeRequests = stats?.active_requests || [];
  const activeTickets = stats?.active_tickets || [];
  const recentHistory = stats?.recent_history || [];
  const performance = stats?.performance || {};

  const quickLinks = [
    {
      label: 'Create Service Request',
      path: '/client/service-requests',
      description: 'Start a new request in a few steps.',
      icon: <FiPlusSquare />
    },
    {
      label: 'Track My Tickets',
      path: '/client/requests',
      description: 'See what is active, approved, or in progress.',
      icon: <FiClipboard />
    },
    {
      label: 'Service History',
      path: '/client/service-history',
      description: 'Review completed jobs and recent outcomes.',
      icon: <FiClock />
    },
    {
      label: 'Messages',
      path: '/client/messages',
      description: 'Reach support without leaving the portal.',
      icon: <FiMessageSquare />
    }
  ];

  return (
    <Layout>
      <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="All requests" value={overview.total_requests ?? 0} />
        <StatsCard title="Active requests" value={overview.active_requests ?? 0} color="text-amber-600" />
        <StatsCard title="Open tickets" value={overview.active_tickets ?? 0} color="text-sky-600" />
        <StatsCard title="Completed services" value={overview.completed_services ?? 0} color="text-emerald-600" />
      </section>

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      {alerts.length > 0 && (
        <section className="mt-6 grid gap-3">
          {alerts.map((alert) => (
            <div
              key={alert.message}
              className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              <FiAlertCircle className="mt-0.5 shrink-0" />
              <span>{alert.message}</span>
            </div>
          ))}
        </section>
      )}

      <section className="mt-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-slate-900">Quick Actions</h3>
            <p className="text-sm text-slate-500">The most common client tasks stay one tap away.</p>
          </div>
        </div>
        <QuickNavGrid items={quickLinks} />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-semibold text-slate-900">Active Requests</h3>
                <p className="mt-1 text-sm text-slate-500">Requests still waiting for approval or assignment.</p>
              </div>
              <button
                onClick={() => navigate('/client/requests')}
                className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 sm:inline-flex"
              >
                View all
                <FiArrowRight size={14} />
              </button>
            </div>
            <div className="mt-5 space-y-3">
              {activeRequests.length > 0 ? (
                activeRequests.map((request) => (
                  <div key={request.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900">{request.service_type}</div>
                        <div className="mt-1 text-sm text-slate-500">{request.description}</div>
                      </div>
                      <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                        {request.status}
                      </div>
                    </div>
                    <div className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-400">
                      Submitted {formatDate(request.created_at)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  No active requests right now.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-700">
                <FiCheckCircle />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-slate-900">Recent Service History</h3>
                <p className="mt-1 text-sm text-slate-500">Your latest completed services and feedback snapshots.</p>
              </div>
            </div>
            <div className="mt-5 space-y-3">
              {recentHistory.length > 0 ? (
                recentHistory.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{item.service_type}</div>
                        <div className="mt-1 text-sm text-slate-500">Technician: {item.technician}</div>
                      </div>
                      <div className="text-right text-sm text-slate-500">
                        <div>{formatDate(item.completed_date)}</div>
                        <div>{item.rating != null ? `${item.rating}/5 rating` : 'No rating yet'}</div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  Completed services will appear here once work is finished.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h3 className="text-xl font-semibold text-slate-900">Ticket Snapshot</h3>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Pending approval</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{statusBreakdown.pending ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Approved</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{statusBreakdown.approved ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">In progress</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{statusBreakdown.in_progress ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">On hold</div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{statusBreakdown.on_hold ?? 0}</div>
              </div>
            </div>
            <div className="mt-5 rounded-2xl border border-slate-200 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Service rating</div>
              <div className="mt-2 text-2xl font-bold text-slate-900">
                {performance.avg_rating != null ? `${performance.avg_rating}/5` : 'No ratings yet'}
              </div>
              <div className="mt-1 text-sm text-slate-500">{performance.total_rated ?? 0} rated services</div>
            </div>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h3 className="text-xl font-semibold text-slate-900">Live Tickets</h3>
            <p className="mt-1 text-sm text-slate-500">Current tickets already in the service pipeline.</p>
            <div className="mt-5 space-y-3">
              {activeTickets.length > 0 ? (
                activeTickets.map((ticket) => (
                  <div key={ticket.id} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{ticket.service_type}</div>
                        <div className="mt-1 text-sm text-slate-500">Technician: {ticket.technician}</div>
                      </div>
                      <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                        {ticket.status}
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-slate-500">
                      {ticket.scheduled_date ? `Scheduled ${formatDate(ticket.scheduled_date)}` : 'Schedule pending'}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  No active tickets at the moment.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h3 className="text-xl font-semibold text-slate-900">Next Best Actions</h3>
            <div className="mt-5 space-y-3">
              {recommendations.length > 0 ? (
                recommendations.map((item) => (
                  <div key={item.message} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="font-semibold text-slate-900">{item.action}</div>
                    <div className="mt-1 text-sm text-slate-500">{item.message}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  You are up to date. New recommendations will appear when the system spots them.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
