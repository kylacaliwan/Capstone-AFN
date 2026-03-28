import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import {
  createFollowUpCase,
  fetchFollowUpCases,
  fetchServiceTickets,
  updateFollowUpCase
} from '../../api/api';

const CASE_TYPE_OPTIONS = [
  { value: 'follow_up', label: 'After Sales' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'warranty', label: 'Warranty' },
  { value: 'revisit', label: 'Revisit' },
  { value: 'feedback', label: 'Feedback' }
];

const CASE_TYPE_LABELS = Object.fromEntries(
  CASE_TYPE_OPTIONS.map((option) => [option.value, option.label])
);

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' }
];

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'All cases' },
  { value: 'open_work', label: 'Open work' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'open', label: 'Open only' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' }
];

const DIRECT_STATUS_VALUES = ['open', 'in_progress', 'resolved', 'closed'];
const OPEN_WORK_STATUSES = ['open', 'in_progress'];
const CASE_TYPE_VALUES = CASE_TYPE_OPTIONS.map((option) => option.value);

const emptyForm = {
  service_ticket: '',
  case_type: 'follow_up',
  priority: 'normal',
  summary: '',
  details: '',
  due_date: '',
  requires_revisit: false
};

const formatDate = (value) => {
  if (!value) return 'No date set';

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

const formatCaseType = (value) => CASE_TYPE_LABELS[value] || String(value || '').replace('_', ' ');

const statusTone = {
  open: 'bg-amber-100 text-amber-800',
  in_progress: 'bg-sky-100 text-sky-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-700'
};

const getPreferredCaseType = (caseTypeFilter) => (
  CASE_TYPE_VALUES.includes(caseTypeFilter) ? caseTypeFilter : emptyForm.case_type
);

const isOverdueCase = (caseItem) => {
  if (!OPEN_WORK_STATUSES.includes(caseItem.status) || !caseItem.due_date) {
    return false;
  }

  const dueDate = new Date(caseItem.due_date);
  if (Number.isNaN(dueDate.getTime())) {
    return false;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dueDate < today;
};

const renderClientDetails = (caseItem) => {
  const details = [
    caseItem.client_phone ? `Phone: ${caseItem.client_phone}` : null,
    caseItem.client_email ? `Email: ${caseItem.client_email}` : null,
    caseItem.service_address ? `Address: ${caseItem.service_address}` : null
  ].filter(Boolean);

  if (details.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {details.map((detail) => (
        <span key={detail} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          {detail}
        </span>
      ))}
    </div>
  );
};

export default function FollowUpCases() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [cases, setCases] = useState([]);
  const [completedTickets, setCompletedTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const statusFilter = searchParams.get('status') || 'all';
  const caseTypeFilter = searchParams.get('case_type') || 'all';
  const [form, setForm] = useState({
    ...emptyForm,
    case_type: getPreferredCaseType(searchParams.get('case_type'))
  });

  const activeFilters = [
    statusFilter !== 'all'
      ? STATUS_FILTER_OPTIONS.find((option) => option.value === statusFilter)?.label
      : null,
    caseTypeFilter !== 'all'
      ? CASE_TYPE_OPTIONS.find((option) => option.value === caseTypeFilter)?.label
      : null
  ].filter(Boolean);

  const load = async ({ preserveMessage = false } = {}) => {
    const requestFilters = {};

    if (DIRECT_STATUS_VALUES.includes(statusFilter)) {
      requestFilters.status = statusFilter;
    }
    if (CASE_TYPE_VALUES.includes(caseTypeFilter)) {
      requestFilters.caseType = caseTypeFilter;
    }

    setLoading(true);
    try {
      const [caseList, ticketList] = await Promise.all([
        fetchFollowUpCases(requestFilters),
        fetchServiceTickets()
      ]);

      const eligibleTickets = ticketList.filter((ticket) => ticket.status === 'completed');
      const filteredCases = caseList.filter((caseItem) => {
        if (statusFilter === 'open_work') {
          return OPEN_WORK_STATUSES.includes(caseItem.status);
        }
        if (statusFilter === 'overdue') {
          return isOverdueCase(caseItem);
        }
        return true;
      });

      setCases(filteredCases);
      setCompletedTickets(eligibleTickets);
      setForm((current) => ({
        ...current,
        case_type: CASE_TYPE_VALUES.includes(caseTypeFilter)
          ? getPreferredCaseType(caseTypeFilter)
          : current.case_type,
        service_ticket: current.service_ticket || eligibleTickets[0]?.id || ''
      }));
      if (!preserveMessage) {
        setMessage('');
      }
    } catch (error) {
      setCases([]);
      setCompletedTickets([]);
      setMessage(error.message || 'Unable to load after-sales cases.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter, caseTypeFilter]);

  const createCase = async () => {
    try {
      await createFollowUpCase({
        ...form,
        service_ticket: Number(form.service_ticket),
        due_date: form.due_date || null
      });
      setMessage('After-sales case created.');
      setForm({
        ...emptyForm,
        case_type: getPreferredCaseType(caseTypeFilter),
        service_ticket: completedTickets[0]?.id || ''
      });
      await load({ preserveMessage: true });
    } catch (error) {
      setMessage(error.message || 'Unable to create after-sales case.');
    }
  };

  const updateStatus = async (caseItem, status) => {
    try {
      await updateFollowUpCase(caseItem.id, { status });
      setMessage('After-sales case updated.');
      await load({ preserveMessage: true });
    } catch (error) {
      setMessage(error.message || 'Unable to update after-sales case.');
    }
  };

  const availableTicketOptions = completedTickets;

  const updateFilter = (key, value) => {
    const nextParams = new URLSearchParams(searchParams);
    if (!value || value === 'all') {
      nextParams.delete(key);
    } else {
      nextParams.set(key, value);
    }
    setSearchParams(nextParams);
  };

  const clearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">After Sales Case Queue</h2>
          <p className="text-slate-600">Open and manage after-sales work tied to completed service tickets.</p>
        </div>
        <div className="text-sm text-teal-700">{message}</div>
      </div>

      <div className="mb-6 rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Queue Filters</h3>
            <p className="text-sm text-slate-500">Use the dashboard shortcuts or filter the after-sales queue directly here.</p>
          </div>
          {activeFilters.length > 0 && (
            <button
              onClick={clearFilters}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Clear filters
            </button>
          )}
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1.2fr]">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Status view</label>
            <select
              value={statusFilter}
              onChange={(e) => updateFilter('status', e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              {STATUS_FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Case type</label>
            <select
              value={caseTypeFilter}
              onChange={(e) => updateFilter('case_type', e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              <option value="all">All case types</option>
              {CASE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {activeFilters.length > 0
              ? `Active filters: ${activeFilters.join(' | ')}`
              : 'Showing all after-sales work tied to completed service tickets.'}
          </div>
        </div>
      </div>

      <div className="mb-6 rounded-2xl bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold">Open New After-Sales Case</h3>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Completed Ticket</label>
            <select
              value={form.service_ticket}
              onChange={(e) => setForm({ ...form, service_ticket: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              {availableTicketOptions.length > 0 ? (
                availableTicketOptions.map((ticket) => (
                  <option key={ticket.id} value={ticket.id}>
                    #{ticket.id} {ticket.client} - {ticket.service}
                  </option>
                ))
              ) : (
                <option value="">No completed tickets available</option>
              )}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Case Type</label>
            <select
              value={form.case_type}
              onChange={(e) => setForm({ ...form, case_type: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              {CASE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Priority</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              {PRIORITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2 xl:col-span-3">
            <label className="mb-2 block text-sm font-medium text-slate-700">Summary</label>
            <input
              value={form.summary}
              onChange={(e) => setForm({ ...form, summary: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
              placeholder="Customer requested an after-sales callback on the completed job"
            />
          </div>
          <div className="md:col-span-2 xl:col-span-3">
            <label className="mb-2 block text-sm font-medium text-slate-700">Details</label>
            <textarea
              value={form.details}
              onChange={(e) => setForm({ ...form, details: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
              rows="4"
              placeholder="Capture after-sales notes, complaint details, or warranty context."
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Due Date</label>
            <input
              type="date"
              value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
            />
          </div>
          <label className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.requires_revisit}
              onChange={(e) => setForm({ ...form, requires_revisit: e.target.checked })}
            />
            Requires revisit
          </label>
        </div>
        <button
          onClick={createCase}
          disabled={!form.service_ticket || !form.summary}
          className="mt-4 rounded-xl bg-primary px-4 py-2 text-white disabled:opacity-50"
        >
          Create Case
        </button>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Case Queue</h3>
            <p className="text-sm text-slate-500">
              {activeFilters.length > 0
                ? `Showing ${cases.length} case(s) for ${activeFilters.join(' | ')}.`
                : `Showing ${cases.length} after-sales case(s).`}
            </p>
          </div>
        </div>
        <div className="space-y-4">
          {loading ? (
            <div className="text-slate-600">Loading...</div>
          ) : cases.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
              No after-sales cases yet.
            </div>
          ) : (
            cases.map((caseItem) => (
              <div key={caseItem.id} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{caseItem.summary}</div>
                    <div className="mt-1 text-sm text-slate-500">
                      Ticket #{caseItem.service_ticket} | {caseItem.client_name} | {caseItem.service_type_name}
                    </div>
                  </div>
                  <div className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusTone[caseItem.status] || 'bg-slate-100 text-slate-700'}`}>
                    {String(caseItem.status || '').replace('_', ' ')}
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                  <span>{formatCaseType(caseItem.case_type)}</span>
                  <span>Priority: {caseItem.priority}</span>
                  <span>Due: {formatDate(caseItem.due_date)}</span>
                  <span>{caseItem.requires_revisit ? 'Revisit required' : 'No revisit required'}</span>
                </div>

                {renderClientDetails(caseItem)}
                {caseItem.details && <div className="mt-3 text-sm text-slate-600">{caseItem.details}</div>}

                <div className="mt-4 flex flex-wrap gap-2">
                  {caseItem.status === 'open' && (
                    <button
                      onClick={() => updateStatus(caseItem, 'in_progress')}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Start Work
                    </button>
                  )}
                  {caseItem.status !== 'resolved' && caseItem.status !== 'closed' && (
                    <button
                      onClick={() => updateStatus(caseItem, 'resolved')}
                      className="rounded-xl bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600"
                    >
                      Resolve
                    </button>
                  )}
                  {caseItem.status !== 'closed' && (
                    <button
                      onClick={() => updateStatus(caseItem, 'closed')}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Close
                    </button>
                  )}
                  {(caseItem.status === 'resolved' || caseItem.status === 'closed') && (
                    <button
                      onClick={() => updateStatus(caseItem, 'open')}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Reopen
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}
