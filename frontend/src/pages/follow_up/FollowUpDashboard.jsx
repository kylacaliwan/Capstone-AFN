import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiArrowRight,
  FiCheckCircle,
  FiClipboard,
  FiClock,
} from 'react-icons/fi';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import { fetchDashboardStats } from '../../api/api';

const CASE_TYPE_LABELS = {
  follow_up: 'After Sales',
  maintenance: 'Maintenance',
  complaint: 'Complaint',
  warranty: 'Warranty',
  revisit: 'Revisit',
  feedback: 'Feedback'
};

const CASE_TYPE_TONES = {
  follow_up: 'bg-slate-900 text-white',
  maintenance: 'bg-amber-100 text-amber-800',
  complaint: 'bg-orange-100 text-orange-800',
  warranty: 'bg-emerald-100 text-emerald-800',
  revisit: 'bg-violet-100 text-violet-800',
  feedback: 'bg-sky-100 text-sky-800'
};

const STATUS_TONES = {
  open: 'bg-rose-100 text-rose-800',
  in_progress: 'bg-sky-100 text-sky-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-700'
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

const renderClientDetails = (item) => {
  const details = [
    item.client_phone ? `Phone: ${item.client_phone}` : null,
    item.client_email ? `Email: ${item.client_email}` : null,
    item.service_address || item.location ? `Address: ${item.service_address || item.location}` : null
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

export default function FollowUpDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardStats('follow_up')
      .then((data) => {
        setStats(data);
        setError('');
      })
      .catch((err) => {
        setStats(null);
        setError(err.message || 'Unable to load after sales management dashboard.');
      });
  }, []);

  const overview = stats?.overview || {};
  const recentCases = stats?.recent_cases || [];
  const followUpCandidates = stats?.follow_up_candidates || [];
  const caseBreakdown = stats?.case_breakdown || {};
  const maintenanceQueue = stats?.maintenance_queue || [];
  const complaintCaseCount = caseBreakdown.complaint ?? 0;
  const revisitCaseCount = caseBreakdown.revisit ?? 0;
  const customerRecoveryCount = complaintCaseCount + revisitCaseCount;
  const maintenanceWatchCount = (overview.maintenance_due_soon ?? 0) + (overview.maintenance_due ?? 0);
  const caseMixEntries = Object.entries(caseBreakdown).sort(([, left], [, right]) => right - left);
  const totalCaseMix = caseMixEntries.reduce((sum, [, count]) => sum + count, 0);

  const heroMetrics = [
    {
      label: 'Active Casework',
      value: overview.open_cases ?? 0,
      note: 'Open or in progress',
      tone: 'border-sky-400/30 bg-sky-400/10 text-sky-100'
    },
    {
      label: 'Customer Recovery',
      value: customerRecoveryCount,
      note: 'Complaints + revisits',
      tone: 'border-orange-300/30 bg-orange-300/10 text-orange-100'
    },
    {
      label: 'Maintenance Watch',
      value: maintenanceWatchCount,
      note: 'Due now or due soon',
      tone: 'border-emerald-300/30 bg-emerald-300/10 text-emerald-100'
    }
  ];

  return (
    <Layout>
      <section className="relative overflow-hidden rounded-[30px] bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-900 px-5 py-6 text-white shadow-xl sm:px-6 sm:py-7 lg:px-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(251,191,36,0.18),_transparent_34%),radial-gradient(circle_at_bottom_left,_rgba(16,185,129,0.14),_transparent_32%)]" />
        <div className="relative">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">After Sales Management</p>
              <h2 className="mt-2 text-2xl font-semibold sm:text-3xl lg:text-4xl">
                Close the loop after every completed service visit.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
                Keep callbacks, warranties, complaints, revisits, and maintenance reminders visible so customer
                promises stay owned after the technician leaves the site.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  onClick={() => navigate('/follow-up/cases')}
                  className="inline-flex items-center justify-center rounded-2xl bg-amber-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-200"
                >
                  <FiClipboard className="mr-2" />
                  Open Case Queue
                </button>
                <button
                  onClick={() => navigate('/follow-up/dashboard#completed-jobs')}
                  className="inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/8 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/12"
                >
                  Review Completed Jobs
                  <FiArrowRight className="ml-2" />
                </button>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 xl:w-[480px] xl:grid-cols-1">
              {heroMetrics.map((item) => (
                <div key={item.label} className={`rounded-2xl border px-4 py-4 backdrop-blur-sm ${item.tone}`}>
                  <div className="text-xs font-semibold uppercase tracking-[0.2em]">{item.label}</div>
                  <div className="mt-2 text-3xl font-bold">{item.value}</div>
                  <div className="mt-1 text-sm opacity-90">{item.note}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mt-5">
        <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-900 shadow-sm">
          Queue shortcuts now live in the left sidebar so this dashboard can stay focused on case health and recent
          customer activity.
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatsCard title="Total cases" value={overview.total_cases ?? 0} />
          <StatsCard title="Open pipeline" value={overview.open_cases ?? 0} color="text-sky-600" />
          <StatsCard title="Overdue recoveries" value={overview.overdue_cases ?? 0} color="text-rose-600" />
          <StatsCard title="Resolved this week" value={overview.resolved_this_week ?? 0} color="text-emerald-600" />
          <StatsCard title="Awaiting review" value={overview.follow_up_candidates ?? 0} color="text-amber-600" />
          <StatsCard title="Maintenance watch" value={maintenanceWatchCount} color="text-emerald-700" />
        </div>
      </section>

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="rounded-[28px] bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Recovery Pipeline</p>
              <h3 className="mt-2 text-xl font-semibold text-slate-900">Recent After-Sales Cases</h3>
              <p className="mt-1 text-sm text-slate-500">
                The latest customer care, warranty, and revisit work entering the queue.
              </p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {recentCases.length > 0 ? (
              recentCases.map((item) => (
                <div key={item.id} className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${CASE_TYPE_TONES[item.case_type] || 'bg-slate-200 text-slate-700'}`}>
                          {formatCaseType(item.case_type)}
                        </span>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_TONES[item.status] || 'bg-slate-200 text-slate-700'}`}>
                          {String(item.status || '').replace('_', ' ')}
                        </span>
                      </div>
                      <div className="mt-3 text-base font-semibold text-slate-900">{item.summary}</div>
                      <div className="mt-1 text-sm text-slate-500">
                        {item.client} | {item.service_type}
                      </div>
                    </div>
                    <div className="text-right text-sm text-slate-500">
                      <div>Priority: {item.priority}</div>
                      <div className="mt-1">Due: {formatDate(item.due_date)}</div>
                    </div>
                  </div>
                  {renderClientDetails(item)}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                No after-sales cases have entered the queue yet.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[28px] bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
                <FiClock />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Maintenance Watch</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-900">Upcoming Service Care</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Clients nearing their planned maintenance window and requiring outreach.
                </p>
              </div>
            </div>
            <div className="mt-5 space-y-3">
              {maintenanceQueue.length > 0 ? (
                maintenanceQueue.map((item) => (
                  <div key={item.id} className="rounded-3xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{item.client}</div>
                        <div className="mt-1 text-sm text-slate-500">
                          {item.service_type} | {item.maintenance_profile_label}
                        </div>
                      </div>
                      <div className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
                        {String(item.status || '').replace('_', ' ')}
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                      <span>Due: {formatDate(item.next_due_date)}</span>
                      <span>Alert from: {formatDate(item.notify_on_date)}</span>
                      <span>Risk: {String(item.risk_level || 'normal').replace('_', ' ')}</span>
                    </div>
                    {renderClientDetails(item)}
                    {item.prediction_notes && <div className="mt-3 text-sm text-slate-500">{item.prediction_notes}</div>}
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  No maintenance reminders are inside the after-sales watch window yet.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[28px] bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-sky-100 p-3 text-sky-700">
                <FiCheckCircle />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Case Distribution</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-900">What The Queue Looks Like</h3>
                <p className="mt-1 text-sm text-slate-500">
                  See where the after-sales workload is concentrating right now.
                </p>
              </div>
            </div>
            <div className="mt-5 space-y-3">
              {caseMixEntries.length > 0 ? (
                caseMixEntries.map(([type, count]) => {
                  const share = totalCaseMix > 0 ? Math.max((count / totalCaseMix) * 100, 8) : 0;
                  const tone = CASE_TYPE_TONES[type] || 'bg-slate-200 text-slate-700';
                  const barTone = tone.split(' ')[0];

                  return (
                    <div key={type} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-semibold text-slate-900">{formatCaseType(type)}</div>
                        <div className="text-lg font-bold text-slate-900">{count}</div>
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                        <div className={`h-full rounded-full ${barTone}`} style={{ width: `${share}%` }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  Case categories will appear here after the first after-sales cases are opened.
                </div>
              )}
            </div>
          </div>

          <div id="completed-jobs" className="scroll-mt-24 rounded-[28px] bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Awaiting Triage</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-900">Completed Jobs Awaiting Review</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Recently completed tickets that still need an after-sales decision.
                </p>
              </div>
              <button
                onClick={() => navigate('/follow-up/cases')}
                className="inline-flex items-center rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Open queue
                <FiArrowRight className="ml-2" />
              </button>
            </div>
            <div className="mt-5 space-y-3">
              {followUpCandidates.length > 0 ? (
                followUpCandidates.map((item) => (
                  <div key={item.ticket_id} className="rounded-3xl border border-slate-200 p-4">
                    <div className="font-semibold text-slate-900">{item.client}</div>
                    <div className="mt-1 text-sm text-slate-500">{item.service_type}</div>
                    <div className="mt-3 text-sm text-slate-500">Completed {formatDate(item.completed_date)}</div>
                    {renderClientDetails(item)}
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                  No completed jobs are waiting for after-sales review right now.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
