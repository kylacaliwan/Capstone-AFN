import { useEffect, useState } from 'react';
import { FiUser, FiAlertCircle, FiFilter } from 'react-icons/fi';
import Layout from '../../components/Layout';
import {
  assignTechnician,
  autoAssignTechnician,
  fetchAdminTechnicians,
  fetchServiceTickets
} from '../../api/api';

const SKILL_OPTIONS = [
  { value: 'all', label: 'All Skills' },
  { value: 'solar', label: 'Solar Installation' },
  { value: 'cctv', label: 'CCTV Security' },
  { value: 'fire_alarm', label: 'Fire Alarms' },
  { value: 'ac', label: 'AC Services' }
];

export default function AdminDispatchBoard() {
  const [tickets, setTickets] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [filterSkill, setFilterSkill] = useState('all');
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [selectedTech, setSelectedTech] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [assignmentInsight, setAssignmentInsight] = useState('');

  const loadData = async () => {
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
      setError(err.message || 'Unable to load dispatch data.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const assignTicket = async () => {
    if (!selectedTicket || !selectedTech) {
      setMessage('Select both a ticket and technician');
      return;
    }

    try {
      await assignTechnician({ ticketId: selectedTicket.id, technicianId: selectedTech.id });
      await loadData();
      setMessage(`Assigned ${selectedTicket.service} (#${selectedTicket.id}) to ${selectedTech.name}`);
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
      setMessage('Select a job before auto-assigning.');
      return;
    }

    try {
      const result = await autoAssignTechnician({ ticketId: selectedTicket.id });
      await loadData();
      setMessage(`Smart-assigned ticket #${selectedTicket.id} to ${result.technician?.username || 'technician'}.`);
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
  const filteredTechs = filterSkill === 'all'
    ? availableTechnicians
    : availableTechnicians.filter((tech) => (tech.skill || '').toLowerCase() === filterSkill);

  return (
    <Layout>
      <div className="mb-6 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200">Dispatch Workflow</p>
            <h2 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">Dispatch Board</h2>
            <p className="mt-3 text-sm leading-6 text-slate-200 sm:text-base">
              This is the action page for routing work. Pick an unassigned job, match it with an available
              technician, and commit the dispatch decision to the backend.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-sky-100">
            Service Tickets is for queue monitoring. Dispatch Board is for live assignment.
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

      <div className="mb-6 grid gap-4 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-4 shadow-sm lg:col-span-2">
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <FiAlertCircle className="text-red-500" />
            Urgent: Unassigned ({unassignedTickets.length})
          </h3>
          <div className="max-h-96 space-y-2 overflow-y-auto">
            {unassignedTickets.length > 0 ? (
              unassignedTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={`cursor-pointer rounded-lg border-l-4 p-3 transition ${
                    selectedTicket?.id === ticket.id
                      ? 'border-r border-t border-b border-blue-300 border-l-blue-600 bg-blue-100'
                      : 'border-r border-t border-b border-slate-200 border-l-orange-500 bg-slate-50 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-bold">#{ticket.id}</div>
                      <div className="font-semibold">{ticket.service}</div>
                      <div className="text-xs text-slate-600">{ticket.client}</div>
                    </div>
                    <span className={`rounded px-2 py-1 text-xs font-bold ${
                      ticket.priority === 'high' ? 'bg-red-200 text-red-800' :
                      ticket.priority === 'medium' ? 'bg-orange-200 text-orange-800' :
                      'bg-green-200 text-green-800'
                    }`}>
                      {ticket.priority.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="py-8 text-center text-sm text-slate-500">All jobs assigned.</p>
            )}
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm lg:col-span-2">
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <FiUser className="text-green-500" />
            Available Technicians
          </h3>
          <div className="mb-3">
            <label className="mb-1 flex items-center gap-1 text-xs font-medium">
              <FiFilter size={14} /> Filter by Skill
            </label>
            <select
              value={filterSkill}
              onChange={(e) => setFilterSkill(e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
            >
              {SKILL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {filteredTechs.length > 0 ? (
              filteredTechs.map((tech) => (
                <div
                  key={tech.id}
                  onClick={() => setSelectedTech(tech)}
                  className={`cursor-pointer rounded-lg border-l-4 p-3 transition ${
                    selectedTech?.id === tech.id
                      ? 'border-r border-t border-b border-blue-300 border-l-blue-600 bg-blue-100'
                      : 'border-r border-t border-b border-slate-200 border-l-green-500 bg-slate-50 hover:bg-slate-100'
                  }`}
                >
                  <div className="font-semibold">{tech.name}</div>
                  <div className="space-y-1 text-xs">
                    <div className="font-medium capitalize text-green-600">Status: available</div>
                    <div className="text-slate-600">Skill: {(tech.skill || 'general').replace('_', ' ')}</div>
                  </div>
                </div>
              ))
            ) : (
              <p className="py-6 text-center text-sm text-slate-500">No matching available technicians.</p>
            )}
          </div>
        </div>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-slate-50 p-4">
          <h3 className="mb-4 text-lg font-semibold">Assignment Control</h3>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium">Job Selected</label>
              {selectedTicket ? (
                <div className="rounded border-2 border-blue-400 bg-white p-2">
                  <div className="font-bold text-blue-900">#{selectedTicket.id} {selectedTicket.service}</div>
                  <div className="mt-1 text-xs text-slate-600">Client: {selectedTicket.client}</div>
                </div>
              ) : (
                <div className="rounded border border-slate-300 bg-white p-2 text-sm text-slate-500">
                  Select a job from the list
                </div>
              )}
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Technician Selected</label>
              {selectedTech ? (
                <div className="rounded border-2 border-green-400 bg-white p-2">
                  <div className="font-bold text-green-900">{selectedTech.name}</div>
                  <div className="mt-1 text-xs text-slate-600">
                    Skill: {(selectedTech.skill || 'general').replace('_', ' ')}
                  </div>
                </div>
              ) : (
                <div className="rounded border border-slate-300 bg-white p-2 text-sm text-slate-500">
                  Select a technician from the list
                </div>
              )}
            </div>
            <button
              onClick={assignTicket}
              disabled={!selectedTicket || !selectedTech}
              className={`w-full rounded-lg py-2 font-semibold text-white transition ${
                selectedTicket && selectedTech
                  ? 'cursor-pointer bg-blue-600 hover:bg-blue-700'
                  : 'cursor-not-allowed bg-slate-300'
              }`}
            >
              Confirm Dispatch Assignment
            </button>
            <button
              onClick={autoAssignTicket}
              disabled={!selectedTicket}
              className={`w-full rounded-lg py-2 font-semibold transition ${
                selectedTicket
                  ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                  : 'cursor-not-allowed bg-slate-200 text-slate-500'
              }`}
            >
              Auto-Assign Best Match
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-slate-300 bg-gradient-to-r from-slate-50 to-slate-100 p-4">
          <h3 className="mb-4 text-lg font-semibold">Dispatch Stats</h3>
          <div className="space-y-2">
            <div className="flex justify-between rounded border border-slate-200 bg-white p-2">
              <span className="font-medium">Total Jobs</span>
              <span className="text-lg font-bold text-blue-600">{tickets.length}</span>
            </div>
            <div className="flex justify-between rounded border border-slate-200 bg-white p-2">
              <span className="font-medium">Unassigned</span>
              <span className="text-lg font-bold text-red-600">{unassignedTickets.length}</span>
            </div>
            <div className="flex justify-between rounded border border-slate-200 bg-white p-2">
              <span className="font-medium">Available Techs</span>
              <span className="text-lg font-bold text-green-600">{filteredTechs.length}</span>
            </div>
            <div className="mt-3 rounded bg-blue-50 p-2 text-xs text-slate-600">
              Select a job and technician here, then confirm the assignment. Ticket monitoring stays on the
              Service Tickets page.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
