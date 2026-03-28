import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiActivity, FiAlertCircle, FiClipboard, FiMap, FiRefreshCw } from 'react-icons/fi';
import Layout from '../../components/Layout';
import StatusBadge, { formatStatusLabel } from '../../components/StatusBadge';
import { fetchServiceTickets } from '../../api/api';

const priorityTone = {
  high: 'bg-red-50 text-red-700 ring-red-200',
  medium: 'bg-orange-50 text-orange-700 ring-orange-200',
  low: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  normal: 'bg-slate-100 text-slate-700 ring-slate-200'
};

const queueActionLabel = (ticket) => {
  if (!ticket.assignedTech) return 'Dispatch technician';
  if (ticket.status === 'not_started' || ticket.status === 'assigned') return 'Confirm arrival window';
  if (ticket.status === 'in_progress') return 'Monitor field progress';
  if (ticket.status === 'completed') return 'Review completion notes';
  if (ticket.status === 'on_hold') return 'Resolve blocker';
  return 'Monitor queue';
};

export default function AdminServiceTickets() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      const ticketData = await fetchServiceTickets();
      setTickets(ticketData);
      setError('');
    } catch (loadError) {
      setTickets([]);
      setError(loadError.message || 'Unable to load service tickets.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const normalizedStatus = (status) => String(status || '').toLowerCase().replace(/\s+/g, '_');
  const unassignedTickets = tickets.filter((ticket) => !ticket.assignedTech);
  const pendingTickets = tickets.filter((ticket) => ['pending', 'not_started'].includes(normalizedStatus(ticket.status)));
  const activeTickets = tickets.filter((ticket) => ['in_progress', 'assigned'].includes(normalizedStatus(ticket.status)));
  const completedTickets = tickets.filter((ticket) => normalizedStatus(ticket.status) === 'completed');

  return (
    <Layout>
      <section className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-200">Queue Oversight</p>
            <h1 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">Service Tickets</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
              Review ticket volume, service status, priorities, and assignment gaps in one place. Use the
              dispatch board when you are ready to actively route jobs to technicians.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap lg:max-w-md lg:justify-end">
            <button
              onClick={() => navigate('/admin/dispatch-board')}
              className="inline-flex items-center justify-center rounded-xl bg-sky-400 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-sky-300"
            >
              <FiMap className="mr-2" />
              Open Dispatch Board
            </button>
            <button
              onClick={loadData}
              className="inline-flex items-center justify-center rounded-xl bg-white/15 px-4 py-3 text-sm font-medium text-white backdrop-blur transition hover:bg-white/20"
            >
              <FiRefreshCw className="mr-2" />
              Refresh Queue
            </button>
          </div>
        </div>
      </section>

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-500">Total Tickets</p>
          <p className="mt-2 text-3xl font-bold text-slate-800">{tickets.length}</p>
        </div>
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-500">Pending Queue</p>
          <p className="mt-2 text-3xl font-bold text-amber-600">{pendingTickets.length}</p>
        </div>
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-500">Active Work</p>
          <p className="mt-2 text-3xl font-bold text-blue-600">{activeTickets.length}</p>
        </div>
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-500">Unassigned</p>
          <p className="mt-2 text-3xl font-bold text-red-600">{unassignedTickets.length}</p>
        </div>
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-[1.45fr_0.85fr]">
        <div className="rounded-2xl bg-white p-4 shadow-sm sm:p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 sm:text-xl">
                <FiClipboard className="text-blue-600" />
                Ticket Queue
              </h2>
              <p className="text-sm text-slate-500">Monitor service demand, ownership, and progress across all tickets.</p>
            </div>
            <div className="text-sm text-slate-500">Dispatch actions live on the dispatch board.</div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <StatusBadge status="not_started" size="sm" />
            <StatusBadge status="assigned" size="sm" />
            <StatusBadge status="in_progress" size="sm" />
            <StatusBadge status="completed" size="sm" />
            <StatusBadge status="on_hold" size="sm" />
          </div>

          <div className="mt-4 space-y-3 md:hidden">
            {tickets.map((ticket) => (
              <div key={ticket.id} className="rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-bold text-blue-600">#{ticket.id}</div>
                    <div className="font-semibold text-slate-900">{ticket.service}</div>
                    <div className="text-sm text-slate-600">{ticket.client}</div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                      priorityTone[ticket.priority] || priorityTone.normal
                    }`}
                  >
                    {String(ticket.priority || 'low').charAt(0).toUpperCase() + String(ticket.priority || 'low').slice(1)}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <StatusBadge status={ticket.status} />
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                    {ticket.assignedTech || 'Unassigned'}
                  </span>
                </div>

                <div className="mt-3 grid gap-2 text-sm text-slate-700">
                  <div>
                    <span className="font-medium text-slate-900">Queue Step:</span>{' '}
                    {queueActionLabel(ticket)}
                  </div>
                  <div>
                    <span className="font-medium text-slate-900">Display Status:</span>{' '}
                    {formatStatusLabel(ticket.status)}
                  </div>
                </div>

                {!ticket.assignedTech && (
                  <button
                    onClick={() => navigate('/admin/dispatch-board')}
                    className="mt-4 inline-flex items-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    <FiMap className="mr-2" />
                    Assign in Dispatch
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="mt-4 hidden overflow-x-auto md:block">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-3 py-2 text-left">ID</th>
                  <th className="px-3 py-2 text-left">Client</th>
                  <th className="px-3 py-2 text-left">Service</th>
                  <th className="px-3 py-2 text-left">Priority</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Technician</th>
                  <th className="px-3 py-2 text-left">Next Step</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id} className="border-b border-slate-200 hover:bg-slate-50">
                    <td className="px-3 py-2 font-bold text-blue-600">#{ticket.id}</td>
                    <td className="px-3 py-2">{ticket.client}</td>
                    <td className="px-3 py-2">{ticket.service}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                          priorityTone[ticket.priority] || priorityTone.normal
                        }`}
                      >
                        {String(ticket.priority || 'low').charAt(0).toUpperCase() + String(ticket.priority || 'low').slice(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={ticket.status} size="sm" />
                    </td>
                    <td className="px-3 py-2 font-medium">{ticket.assignedTech || 'Unassigned'}</td>
                    <td className="px-3 py-2">
                      {ticket.assignedTech ? (
                        <span className="text-xs font-medium text-slate-500">{queueActionLabel(ticket)}</span>
                      ) : (
                        <button
                          onClick={() => navigate('/admin/dispatch-board')}
                          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                        >
                          Send to Dispatch
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-blue-200 bg-gradient-to-b from-blue-50 to-slate-50 p-5">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <FiAlertCircle className="text-blue-600" />
              Queue Focus
            </h2>
            <div className="mt-4 space-y-3 text-sm text-slate-700">
              <div className="rounded-xl border border-white/70 bg-white/80 p-3">
                <div className="font-semibold text-slate-900">Unassigned tickets</div>
                <div className="mt-1">{unassignedTickets.length} tickets still need dispatch attention.</div>
              </div>
              <div className="rounded-xl border border-white/70 bg-white/80 p-3">
                <div className="font-semibold text-slate-900">Work in progress</div>
                <div className="mt-1">{activeTickets.length} tickets are already moving through field execution.</div>
              </div>
              <div className="rounded-xl border border-white/70 bg-white/80 p-3">
                <div className="font-semibold text-slate-900">Completed today</div>
                <div className="mt-1">{completedTickets.length} tickets are marked complete in the current data set.</div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <FiActivity className="text-amber-600" />
              Page Role
            </h2>
            <div className="mt-4 space-y-3 text-sm text-slate-700">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="font-semibold text-slate-900">Service Tickets</div>
                <div className="mt-1">Best for reviewing queue health, priorities, and who owns each job.</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="font-semibold text-slate-900">Dispatch Board</div>
                <div className="mt-1">Best for actively matching unassigned work to available technicians.</div>
              </div>
              <button
                onClick={() => navigate('/admin/dispatch-board')}
                className="mt-1 inline-flex items-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
              >
                <FiMap className="mr-2" />
                Go to Dispatch Workflow
              </button>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
