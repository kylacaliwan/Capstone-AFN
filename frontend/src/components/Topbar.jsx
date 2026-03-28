import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FiArrowRight, FiLogOut, FiMenu } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';

const routeMeta = [
  {
    prefix: '/admin/dashboard',
    title: 'Operations Dashboard',
    subtitle: 'Watch service health, queue pressure, and field readiness.'
  },
  {
    prefix: '/admin/service-tickets',
    title: 'Service Tickets',
    subtitle: 'Review the queue, triage new work, and assign next steps.'
  },
  {
    prefix: '/admin/dispatch-board',
    title: 'Dispatch Board',
    subtitle: 'Balance assignments, coverage, and technician workload.'
  },
  {
    prefix: '/admin/analytics',
    title: 'Predictive Analytics',
    subtitle: 'Track live trends, forecast demand, and spot risk early.'
  },
  {
    prefix: '/follow-up/dashboard',
    title: 'After Sales Management Dashboard',
    subtitle: 'Manage callbacks, complaints, warranties, revisits, and retention risk after service completion.'
  },
  {
    prefix: '/follow-up/cases',
    title: 'After Sales Case Queue',
    subtitle: 'Track callbacks, warranty issues, complaints, revisits, and post-service care.'
  },
  {
    prefix: '/supervisor/dashboard',
    title: 'Team Control Center',
    subtitle: 'Focus the team on the jobs, queues, and technicians that need attention.'
  },
  {
    prefix: '/supervisor/dispatch-board',
    title: 'Supervisor Dispatch',
    subtitle: 'Route active work and keep appointments moving.'
  },
  {
    prefix: '/supervisor/service-tickets',
    title: 'Team Ticket Queue',
    subtitle: 'See which tickets need action from the field team.'
  },
  {
    prefix: '/supervisor/technician-tracking',
    title: 'Technician Monitoring',
    subtitle: 'Check technician availability and live field coverage.'
  },
  {
    prefix: '/technician/dashboard',
    title: 'Technician Dashboard',
    subtitle: 'Start the day with your jobs, route, and readiness.'
  },
  {
    prefix: '/technician/my-jobs',
    title: 'My Jobs',
    subtitle: 'See assigned jobs and move through the queue with less friction.'
  },
  {
    prefix: '/technician/schedule',
    title: "Today's Schedule",
    subtitle: 'Keep your appointments and timing in view.'
  },
  {
    prefix: '/client/dashboard',
    title: 'Service Overview',
    subtitle: 'Track requests, open tickets, and recent service outcomes.'
  },
  {
    prefix: '/client/service-requests',
    title: 'Create Service Request',
    subtitle: 'Submit a new issue or maintenance request with the right details.'
  },
  {
    prefix: '/client/requests',
    title: 'Track Service Tickets',
    subtitle: 'Follow active requests and ticket progress in one place.'
  },
  {
    prefix: '/client/service-history',
    title: 'Service History',
    subtitle: 'Review recently completed work and feedback.'
  }
];

const roleMeta = {
  admin: {
    workspace: 'Admin workspace',
    action: { label: 'Open analytics', path: '/admin/analytics' }
  },
  follow_up: {
    workspace: 'After sales management',
    action: { label: 'Open case queue', path: '/follow-up/cases' }
  },
  supervisor: {
    workspace: 'Supervisor workspace',
    action: { label: 'Open dispatch board', path: '/supervisor/dispatch-board' }
  },
  technician: {
    workspace: 'Technician workspace',
    action: { label: 'View my jobs', path: '/technician/my-jobs' }
  },
  client: {
    workspace: 'Client workspace',
    action: { label: 'Create request', path: '/client/service-requests' }
  }
};

export default function Topbar({ toggleSidebar }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const activeRoute = useMemo(
    () => routeMeta.find((item) => location.pathname.startsWith(item.prefix)),
    [location.pathname]
  );

  const activeRole = roleMeta[user?.role] || null;
  const primaryAction =
    activeRole && activeRole.action.path !== location.pathname ? activeRole.action : null;
  const displayName =
    user?.first_name?.trim() || user?.username || user?.email || 'Team member';

  return (
    <div className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/95 px-3 py-3 shadow-sm backdrop-blur sm:px-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <button
            onClick={toggleSidebar}
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-700 transition hover:bg-slate-50 md:hidden"
          >
            <FiMenu size={18} />
          </button>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-sky-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                {activeRole?.workspace || 'AFN portal'}
              </span>
              <span className="text-xs text-slate-400">{displayName}</span>
            </div>
            <h1 className="mt-2 truncate text-lg font-semibold text-slate-900 sm:text-xl">
              {activeRoute?.title || 'AFN Service Management'}
            </h1>
            <p className="text-sm text-slate-500">
              {activeRoute?.subtitle || 'Role-based service operations workspace.'}
            </p>
          </div>
        </div>

        <div className="hidden ml-auto  items-center gap-2">
          <button
            onClick={logout}
            className="inline-flex items-center gap-1 rounded-xl bg-red-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-red-600 sm:px-3 sm:py-2"
          >
            <FiLogOut />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </div>
  );
}
