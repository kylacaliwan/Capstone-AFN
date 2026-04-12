import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  FiAlertTriangle,
  FiBell,
  FiCalendar,
  FiClipboard,
  FiClock,
  FiFileText,
  FiHome,
  FiLayers,
  FiMap,
  FiMessageSquare,
  FiPackage,
  FiRefreshCw,
  FiSettings,
  FiShield,
  FiTool,
  FiLogOut,
  FiTrendingUp,
  FiUsers
} from 'react-icons/fi';
import { fetchDashboardStats } from '../api/api';

const getFollowUpMenu = (stats) => {
  const overview = stats?.overview || {};
  const caseBreakdown = stats?.case_breakdown || {};
  const hasStats = Boolean(stats);
  const getBadge = (value) => (hasStats ? value ?? 0 : undefined);

  return {
    label: 'After Sales Management',
    description: 'Manage callbacks, complaints, warranties, revisits, and retention work after job completion.',
    sections: [
      {
        title: 'Overview',
        items: [{ label: 'Dashboard', path: '/follow-up/dashboard', icon: FiHome }]
      },
      {
        title: 'Case Queue',
        items: [
          {
            label: 'After Sales Cases',
            path: '/follow-up/cases',
            icon: FiClipboard,
            badge: getBadge(overview.total_cases)
          }
        ]
      },
      {
        title: 'Action Board',
        items: [
          {
            label: 'Open Pipeline',
            path: '/follow-up/cases?status=open_work',
            icon: FiTrendingUp,
            badge: getBadge(overview.open_cases),
            badgeTone: 'bg-sky-100 text-sky-700'
          },
          {
            label: 'Overdue',
            path: '/follow-up/cases?status=overdue',
            icon: FiAlertTriangle,
            badge: getBadge(overview.overdue_cases),
            badgeTone: 'bg-rose-100 text-rose-700'
          },
          {
            label: 'Warranty',
            path: '/follow-up/cases?case_type=warranty',
            icon: FiShield,
            badge: getBadge(caseBreakdown.warranty),
            badgeTone: 'bg-emerald-100 text-emerald-700'
          },
          {
            label: 'Maintenance',
            path: '/follow-up/cases?case_type=maintenance',
            icon: FiClock,
            badge: getBadge(caseBreakdown.maintenance),
            badgeTone: 'bg-amber-100 text-amber-700'
          },
          {
            label: 'Complaints',
            path: '/follow-up/cases?case_type=complaint',
            icon: FiMessageSquare,
            badge: getBadge(caseBreakdown.complaint),
            badgeTone: 'bg-orange-100 text-orange-700'
          },
          {
            label: 'Revisits',
            path: '/follow-up/cases?case_type=revisit',
            icon: FiMap,
            badge: getBadge(caseBreakdown.revisit),
            badgeTone: 'bg-violet-100 text-violet-700'
          },
          {
            label: 'Awaiting Review',
            path: '/follow-up/dashboard#completed-jobs',
            icon: FiRefreshCw,
            badge: getBadge(overview.follow_up_candidates),
            badgeTone: 'bg-slate-100 text-slate-700'
          }
        ]
      }
    ]
  };
};

const roleMenu = {
  admin: {
    label: 'Admin Workspace',
    description: 'Systemwide operations, dispatch, service delivery, and platform controls.',
    sections: [
      {
        title: 'Overview',
        items: [
          { label: 'Dashboard', path: '/admin/dashboard', icon: FiHome },
          { label: 'Analytics', path: '/admin/analytics', icon: FiFileText },
          { label: 'Reports', path: '/admin/reports', icon: FiFileText }
        ]
      },
      {
        title: 'Operations',
        items: [
          { label: 'Service Tickets', path: '/admin/service-tickets', icon: FiClipboard },
          { label: 'Dispatch Board', path: '/admin/dispatch-board', icon: FiLayers },
          { label: 'Technicians', path: '/admin/technicians', icon: FiUsers },
          { label: 'Technician Tracking', path: '/admin/technician-tracking', icon: FiMap },
          { label: 'Clients', path: '/admin/clients', icon: FiUsers },
          { label: 'Services', path: '/admin/services', icon: FiTool },
          { label: 'Inventory', path: '/admin/inventory', icon: FiPackage }
        ]
      },
      {
        title: 'Administration',
        items: [
          { label: 'User Management', path: '/admin/user-management', icon: FiUsers },
          { label: 'Settings', path: '/admin/settings', icon: FiSettings }
        ]
      }
    ]
  },
  supervisor: {
    label: 'Supervisor Workspace',
    description: 'Keep the field team moving with clearer queue, staffing, and dispatch control.',
    sections: [
      {
        title: 'Overview',
        items: [{ label: 'Dashboard', path: '/supervisor/dashboard', icon: FiHome }]
      },
      {
        title: 'Execution',
        items: [
          { label: 'Service Tickets', path: '/supervisor/service-tickets', icon: FiClipboard },
          { label: 'Dispatch Board', path: '/supervisor/dispatch-board', icon: FiLayers },
          { label: 'Technician Monitoring', path: '/supervisor/technician-tracking', icon: FiMap }
        ]
      }
    ]
  },
  technician: {
    label: 'Technician Workspace',
    description: "See today's jobs, routes, checklists, and updates without extra noise.",
    sections: [
      {
        title: 'Overview',
        items: [{ label: 'Dashboard', path: '/technician/dashboard', icon: FiHome }]
      },
      {
        title: 'My Work',
        items: [
          { label: 'My Jobs', path: '/technician/my-jobs', icon: FiClipboard },
          { label: 'Schedule', path: '/technician/schedule', icon: FiCalendar },
          { label: 'Map Navigation', path: '/technician/map-navigation', icon: FiMap },
          { label: 'Digital Checklist', path: '/technician/checklist', icon: FiClipboard },
          { label: 'Job History', path: '/technician/job-history', icon: FiFileText }
        ]
      },
      {
        title: 'Support',
        items: [
          { label: 'Messages', path: '/technician/messages', icon: FiMessageSquare },
          { label: 'Profile', path: '/technician/profile', icon: FiSettings }
        ]
      }
    ]
  },
  client: {
    label: 'Client Workspace',
    description: 'Request service, track progress, and follow outcomes from one simple view.',
    sections: [
      {
        title: 'Overview',
        items: [{ label: 'Dashboard', path: '/client/dashboard', icon: FiHome }]
      },
      {
        title: 'Requests',
        items: [
          { label: 'Create Request', path: '/client/service-requests', icon: FiClipboard },
          { label: 'Track Tickets', path: '/client/requests', icon: FiClipboard },
          { label: 'Service History', path: '/client/service-history', icon: FiFileText }
        ]
      },
      {
        title: 'Support',
        items: [
          { label: 'Messages', path: '/client/messages', icon: FiMessageSquare },
          { label: 'Notifications', path: '/client/notifications', icon: FiBell },
          { label: 'Profile', path: '/client/profile', icon: FiSettings }
        ]
      }
    ]
  }
};

export default function Sidebar({ role, isOpen, onClose }) {
  const { user, logout } = useAuth();

  const navigate = useNavigate();
  const handleLogout = async () => {
    await logout();
    navigate('../client/hero.jsx'); // 👈 your landing page route
  };
  const displayName =
  user?.first_name?.trim() || user?.username || user?.email || 'Team member';

const roleLabelMap = {
  admin: 'Admin',
  follow_up: 'After Sales',
  supervisor: 'Supervisor',
  technician: 'Technician',
  client: 'Client'
};

const roleLabel = roleLabelMap[user?.role] || 'User';
  const location = useLocation();
  const [afterSalesStats, setAfterSalesStats] = useState(null);

  useEffect(() => {
    let isMounted = true;

    if (role !== 'follow_up') {
      setAfterSalesStats(null);
      return () => {
        isMounted = false;
      };
    }

    fetchDashboardStats('follow_up')
      .then((data) => {
        if (isMounted) {
          setAfterSalesStats(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setAfterSalesStats(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [role, location.pathname, location.search]);

  if (!role) return null;

  const menu = role === 'follow_up' ? getFollowUpMenu(afterSalesStats) : roleMenu[role];

  if (!menu) return null;

  const isItemActive = (item) => {
    const [pathWithSearch, hashFragment = ''] = item.path.split('#');
    const [pathname, searchFragment = ''] = pathWithSearch.split('?');

    if (searchFragment || hashFragment) {
      const currentSearch = location.search.startsWith('?') ? location.search.slice(1) : location.search;
      const currentHash = location.hash.startsWith('#') ? location.hash.slice(1) : location.hash;

      return location.pathname === pathname && currentSearch === searchFragment && currentHash === hashFragment;
    }

    return location.pathname === pathname;
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-20 bg-black/30 transition-opacity md:hidden ${
          isOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-[85vw] max-w-72 overflow-y-auto border-r border-slate-200 bg-white p-3 transition-transform md:translate-x-2 md:w-64 md:max-w-none md:p-4 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="hidden mb-5 rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-sky-900 p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-200">AFN Portal</p>
              <h2 className="mt-2 text-lg font-bold sm:text-xl">{menu.label}</h2>
              <p className="mt-1 text-xs leading-5 text-slate-200">{menu.description}</p>
            </div>
            <button className="rounded-md p-1 text-xl leading-none text-white md:hidden" onClick={onClose}>
              x
            </button>
          </div>
        </div>

        <div className='w-full flex items-center justify-center mb-10 '>
          <img className='h-20 w-30' src="/logo.png"  alt="logo" />
        </div>

        <nav className="space-y-5">
          {menu.sections.map((section) => (
            <div key={section.title}>
              <div className="px-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                {section.title}
              </div>
              <div className="mt-2 space-y-1.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const itemIsActive = isItemActive(item);

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={onClose}
                      className={() =>
                        `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all ${
                          itemIsActive ? 'bg-primary text-white shadow-md' : 'text-slate-700 hover:bg-slate-100'
                        }`
                      }
                    >
                      <Icon size={16} className="shrink-0" />
                      <span className="min-w-0 break-words">{item.label}</span>
                      {item.badge !== undefined && item.badge !== null && (
                        <span
                          className={`ml-auto inline-flex min-w-7 items-center justify-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                            itemIsActive ? 'bg-white/20 text-white' : item.badgeTone || 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                      
                    </NavLink>
                  );
                })}
              </div>
              
            </div>
          ))}
        </nav>

        <div className='mt-8 -mx-3 md:-mx-4'>
          <div className='w-full bg-blue-300 p-4 flex flex-col gap-4'>
            
            {/* USER INFO */}
            <div className='flex items-center gap-3'>
              <img className='h-10 w-10 rounded-full' src="/user-icon.png" alt="user" />
              
              <div className='flex flex-col'>
                <span className='text-sm font-semibold text-slate-800'>
                  {displayName}
                </span>
                <span className='text-xs text-slate-500'>
                  {roleLabel}
                </span>
              </div>
            </div>

            {/* LOGOUT BUTTON */}
            <button
              onClick={handleLogout}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-red-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-red-600"
            >
              <FiLogOut />
              <span>Logout</span>
            </button>

          </div>
        </div>
      </aside>
    </>
  );
}
