import { useEffect, useState } from 'react';
import { FiUser, FiClock, FiAlertCircle } from 'react-icons/fi';
import Layout from '../../components/Layout';
import StatusBadge from '../../components/StatusBadge';
import {
  assignTechnician,
  autoAssignTechnician,
  fetchAdminTechnicians,
  fetchServiceTickets
} from '../../api/api';

export default function DispatchBoard() {
  const [tickets, setTickets] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [selectedTech, setSelectedTech] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [assignmentInsight, setAssignmentInsight] = useState('');

  const loadDispatchData = async () => {
    try {
      const [ticketData, technicianData] = await Promise.all([
        fetchServiceTickets(),
        fetchAdminTechnicians()
      ]);
      setTickets(ticketData);
      setTechnicians(technicianData);
      setError('');
    } catch (err) {
      setTickets([]);
      setTechnicians([]);
      setError(err.message || 'Unable to load dispatch board.');
    }
  };

  useEffect(() => {
    loadDispatchData();
  }, []);

  const assignTicket = async () => {
    if (!selectedTicket || !selectedTech) {
      setMessage('Select both a ticket and technician');
      return;
    }

    try {
      await assignTechnician({ ticketId: selectedTicket.id, technicianId: selectedTech.id });
      await loadDispatchData();
      setMessage(`Assigned ${selectedTicket.service} to ${selectedTech.name}`);
      setAssignmentInsight('');
      setSelectedTicket(null);
      setSelectedTech(null);
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage(err.message || 'Assignment failed.');
    }
  };

  const autoAssignTicket = async () => {
    if (!selectedTicket) {
      setMessage('Select a ticket before auto-assigning.');
      return;
    }

    try {
      const result = await autoAssignTechnician({ ticketId: selectedTicket.id });
      await loadDispatchData();
      setMessage(`Smart-assigned ${selectedTicket.service} to ${result.technician?.username || 'technician'}`);
      setAssignmentInsight(result.assignment_summary || '');
      setSelectedTicket(null);
      setSelectedTech(null);
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage(err.message || 'Auto-assignment failed.');
      setAssignmentInsight('');
    }
  };

  const unassignedTickets = tickets.filter((ticket) => !ticket.assignedTech);
  const availableTechnicians = technicians.filter((tech) => tech.isAvailable);
  const pendingTickets = tickets.filter((ticket) => ticket.status === 'not_started' || ticket.status === 'pending');
  const priorityTone = {
    high: 'bg-red-50 text-red-700 ring-red-200',
    medium: 'bg-orange-50 text-orange-700 ring-orange-200',
    low: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    normal: 'bg-slate-100 text-slate-700 ring-slate-200'
  };

  return (
    <Layout>
      <div className="mb-6 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200">Dispatch Workflow</p>
            <h2 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">Dispatch Board</h2>
            <p className="mt-3 text-sm leading-6 text-slate-200 sm:text-base">
              Use this page to actively assign field work. Choose unassigned jobs, compare available technicians,
              and save the dispatch decision.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-sky-100">
            Service Tickets tracks the queue. Dispatch Board handles assignment.
          </div>
        </div>
      </div>

      {message && (
        <div className={`mb-4 rounded-lg border p-3 ${
          message.toLowerCase().includes('failed')
            ? 'border-red-200 bg-red-50 text-red-800'
            : 'border-green-200 bg-green-50 text-green-800'
        }`}>
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
          {error}
        </div>
      )}
      {assignmentInsight && (
        <div className="mb-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800">
          {assignmentInsight}
        </div>
      )}

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <FiAlertCircle className="text-orange-500" />
            Unassigned Jobs ({unassignedTickets.length})
          </h3>
          <div className="max-h-96 space-y-2 overflow-y-auto">
            {unassignedTickets.length > 0 ? (
              unassignedTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={`cursor-pointer rounded-lg p-3 transition ${
                    selectedTicket?.id === ticket.id
                      ? 'border-2 border-blue-500 bg-blue-100'
                      : 'border border-slate-200 bg-slate-50 hover:bg-slate-100'
                  }`}
                >
                  <div className="text-sm font-semibold">#{ticket.id} - {ticket.service}</div>
                  <div className="text-xs text-slate-600">{ticket.client}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <StatusBadge status={ticket.status} size="sm" />
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${
                      priorityTone[ticket.priority] || priorityTone.normal
                    }`}>
                      {String(ticket.priority || 'normal').charAt(0).toUpperCase() + String(ticket.priority || 'normal').slice(1)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">All jobs assigned.</p>
            )}
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <FiUser className="text-green-500" />
            Available Technicians ({availableTechnicians.length})
          </h3>
          <div className="max-h-96 space-y-2 overflow-y-auto">
            {availableTechnicians.length > 0 ? (
              availableTechnicians.map((tech) => (
                <div
                  key={tech.id}
                  onClick={() => setSelectedTech(tech)}
                  className={`cursor-pointer rounded-lg p-3 transition ${
                    selectedTech?.id === tech.id
                      ? 'border-2 border-blue-500 bg-blue-100'
                      : 'border border-slate-200 bg-slate-50 hover:bg-slate-100'
                  }`}
                >
                  <div className="text-sm font-semibold">{tech.name}</div>
                  <div className="text-xs capitalize text-green-600">Status: available</div>
                  <div className="text-xs text-slate-600">
                    Skill: {(tech.skill || 'general').replace('_', ' ')}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No available technicians found.</p>
            )}
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold">Quick Assign</h3>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Selected Job</label>
              <div className="mt-1 rounded bg-slate-100 p-2 text-sm">
                {selectedTicket
                  ? `${selectedTicket.service} (#${selectedTicket.id})`
                  : 'None selected'}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Selected Tech</label>
              <div className="mt-1 rounded bg-slate-100 p-2 text-sm">
                {selectedTech ? selectedTech.name : 'None selected'}
              </div>
            </div>
            <button
              onClick={assignTicket}
              className="w-full rounded-lg bg-blue-600 py-2 font-semibold text-white transition hover:bg-blue-700"
            >
              Confirm Assignment
            </button>
            <button
              onClick={autoAssignTicket}
              className="w-full rounded-lg bg-emerald-500 py-2 font-semibold text-white transition hover:bg-emerald-600"
            >
              Auto-Assign Best Match
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <FiClock className="text-blue-500" />
          Ready for Dispatch ({pendingTickets.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left">ID</th>
                <th className="px-3 py-2 text-left">Client</th>
                <th className="px-3 py-2 text-left">Service</th>
                <th className="px-3 py-2 text-left">Priority</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Technician</th>
              </tr>
            </thead>
            <tbody>
              {pendingTickets.length > 0 ? (
                pendingTickets.map((ticket) => (
                  <tr key={ticket.id} className="border-b border-slate-200 hover:bg-slate-50">
                    <td className="px-3 py-2">#{ticket.id}</td>
                    <td className="px-3 py-2">{ticket.client}</td>
                    <td className="px-3 py-2">{ticket.service}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                        priorityTone[ticket.priority] || priorityTone.normal
                      }`}>
                        {String(ticket.priority || 'normal').charAt(0).toUpperCase() + String(ticket.priority || 'normal').slice(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={ticket.status} size="sm" />
                    </td>
                    <td className="px-3 py-2">{ticket.assignedTech || 'Unassigned'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-3 py-2 text-center text-slate-500">No pending jobs</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
