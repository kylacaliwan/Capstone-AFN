import { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { useFirebase } from './hooks/useFirebase';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const SupervisorDashboard = lazy(() => import('./pages/supervisor/SupervisorDashboard'));
const TechnicianDashboard = lazy(() => import('./pages/technician/TechnicianDashboard'));
const ClientDashboard = lazy(() => import('./pages/client/ClientDashboard'));
const FollowUpDashboard = lazy(() => import('./pages/follow_up/FollowUpDashboard'));
const FollowUpCases = lazy(() => import('./pages/follow_up/FollowUpCases'));
const ClientRequestTracking = lazy(() => import('./pages/client/ClientRequestTracking'));
const ClientRequestDetail = lazy(() => import('./pages/client/ClientRequestDetail'));
const ClientServiceHistory = lazy(() => import('./pages/client/ClientServiceHistory'));
const ClientMessages = lazy(() => import('./pages/client/ClientMessages'));
const ClientNotifications = lazy(() => import('./pages/client/ClientNotifications'));
const ClientProfile = lazy(() => import('./pages/client/ClientProfile'));
const AdminServiceTickets = lazy(() => import('./pages/admin/AdminServiceTickets'));
const AdminTechnicianTracking = lazy(() => import('./pages/admin/AdminTechnicianTracking'));
const AdminTechnicians = lazy(() => import('./pages/admin/AdminTechnicians'));
const AdminClients = lazy(() => import('./pages/admin/AdminClients'));
const AdminServices = lazy(() => import('./pages/admin/AdminServices'));
const AdminAnalytics = lazy(() => import('./pages/admin/AdminAnalytics'));
const AdminReports = lazy(() => import('./pages/admin/AdminReports'));
const AdminUserManagement = lazy(() => import('./pages/admin/AdminUserManagement'));
const AdminSettings = lazy(() => import('./pages/admin/AdminSettings'));
const CoverageHeatmap = lazy(() => import('./pages/admin/CoverageHeatmap'));
const AdminDispatchBoard = lazy(() => import('./pages/admin/AdminDispatchBoard'));
const SupervisorTracking = lazy(() => import('./pages/supervisor/SupervisorTracking'));
const DispatchBoard = lazy(() => import('./pages/supervisor/DispatchBoard'));
const TechnicianJobs = lazy(() => import('./pages/technician/TechnicianJobs'));
const ClientServiceRequests = lazy(() => import('./pages/client/ClientServiceRequests'));
const TechnicianSchedule = lazy(() => import('./pages/technician/TechnicianSchedule'));
const TechnicianMapNavigation = lazy(() => import('./pages/technician/TechnicianMapNavigation'));
const TechnicianChecklist = lazy(() => import('./pages/technician/TechnicianChecklist'));
const TechnicianMessages = lazy(() => import('./pages/technician/TechnicianMessages'));
const TechnicianJobHistory = lazy(() => import('./pages/technician/TechnicianJobHistory'));
const TechnicianProfile = lazy(() => import('./pages/technician/TechnicianProfile'));
const AdminInventory = lazy(() => import('./pages/admin/AdminInventory'));

const getDashboardPath = (role) => {
  switch (role) {
    case 'admin':
      return '/admin/dashboard';
    case 'follow_up':
      return '/follow-up/dashboard';
    case 'supervisor':
      return '/supervisor/dashboard';
    case 'technician':
      return '/technician/dashboard';
    case 'client':
      return '/client/dashboard';
    default:
      return '/login';
  }
};

const RoleRedirect = ({ role }) => <Navigate to={getDashboardPath(role)} replace />;

const ProtectedRoute = ({ role, children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to={getDashboardPath(user.role)} replace />;
  return children;
};

function FirebaseBootstrap() {
  const { fcmToken, registerToken } = useFirebase();

  useEffect(() => {
    if (!fcmToken) {
      return;
    }

    registerToken().catch(() => {});
  }, [fcmToken]);

  return null;
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <>
      {user ? <FirebaseBootstrap /> : null}
      <Suspense fallback={<div className="grid min-h-screen place-items-center text-slate-600">Loading...</div>}>
        <Routes>
          <Route path="/" element={<RoleRedirect role={user?.role} />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/admin/dashboard" element={<ProtectedRoute role="admin"><AdminDashboard /></ProtectedRoute>} />
          <Route path="/admin/service-tickets" element={<ProtectedRoute role="admin"><AdminServiceTickets /></ProtectedRoute>} />
          <Route path="/admin/dispatch-board" element={<ProtectedRoute role="admin"><AdminDispatchBoard /></ProtectedRoute>} />
          <Route path="/admin/technician-tracking" element={<ProtectedRoute role="admin"><AdminTechnicianTracking /></ProtectedRoute>} />
          <Route path="/admin/technicians" element={<ProtectedRoute role="admin"><AdminTechnicians /></ProtectedRoute>} />
          <Route path="/admin/clients" element={<ProtectedRoute role="admin"><AdminClients /></ProtectedRoute>} />
          <Route path="/admin/services" element={<ProtectedRoute role="admin"><AdminServices /></ProtectedRoute>} />
          <Route path="/admin/inventory" element={<ProtectedRoute role="admin"><AdminInventory /></ProtectedRoute>} />
          <Route path="/admin/analytics" element={<ProtectedRoute role="admin"><AdminAnalytics /></ProtectedRoute>} />
          <Route path="/admin/reports" element={<ProtectedRoute role="admin"><AdminReports /></ProtectedRoute>} />
          <Route path="/admin/user-management" element={<ProtectedRoute role="admin"><AdminUserManagement /></ProtectedRoute>} />
          <Route path="/admin/settings" element={<ProtectedRoute role="admin"><AdminSettings /></ProtectedRoute>} />
          <Route path="/admin/coverage-heatmap" element={<ProtectedRoute role="admin"><CoverageHeatmap /></ProtectedRoute>} />

          <Route path="/follow-up/dashboard" element={<ProtectedRoute role="follow_up"><FollowUpDashboard /></ProtectedRoute>} />
          <Route path="/follow-up/cases" element={<ProtectedRoute role="follow_up"><FollowUpCases /></ProtectedRoute>} />

          <Route path="/supervisor/dashboard" element={<ProtectedRoute role="supervisor"><SupervisorDashboard /></ProtectedRoute>} />
          <Route path="/supervisor/dispatch-board" element={<ProtectedRoute role="supervisor"><DispatchBoard /></ProtectedRoute>} />
          <Route path="/supervisor/service-tickets" element={<ProtectedRoute role="supervisor"><AdminServiceTickets /></ProtectedRoute>} />
          <Route path="/supervisor/technician-tracking" element={<ProtectedRoute role="supervisor"><SupervisorTracking /></ProtectedRoute>} />

          <Route path="/technician/dashboard" element={<ProtectedRoute role="technician"><TechnicianDashboard /></ProtectedRoute>} />
          <Route path="/technician/my-jobs" element={<ProtectedRoute role="technician"><TechnicianJobs /></ProtectedRoute>} />
          <Route path="/technician/schedule" element={<ProtectedRoute role="technician"><TechnicianSchedule /></ProtectedRoute>} />
          <Route path="/technician/map-navigation" element={<ProtectedRoute role="technician"><TechnicianMapNavigation /></ProtectedRoute>} />
          <Route path="/technician/checklist" element={<ProtectedRoute role="technician"><TechnicianChecklist /></ProtectedRoute>} />
          <Route path="/technician/messages" element={<ProtectedRoute role="technician"><TechnicianMessages /></ProtectedRoute>} />
          <Route path="/technician/job-history" element={<ProtectedRoute role="technician"><TechnicianJobHistory /></ProtectedRoute>} />
          <Route path="/technician/profile" element={<ProtectedRoute role="technician"><TechnicianProfile /></ProtectedRoute>} />

          <Route path="/client/dashboard" element={<ProtectedRoute role="client"><ClientDashboard /></ProtectedRoute>} />
          <Route path="/client/service-requests" element={<ProtectedRoute role="client"><ClientServiceRequests /></ProtectedRoute>} />
          <Route path="/client/requests" element={<ProtectedRoute role="client"><ClientRequestTracking /></ProtectedRoute>} />
          <Route path="/client/requests/:requestId" element={<ProtectedRoute role="client"><ClientRequestDetail /></ProtectedRoute>} />
          <Route path="/client/service-history" element={<ProtectedRoute role="client"><ClientServiceHistory /></ProtectedRoute>} />
          <Route path="/client/messages" element={<ProtectedRoute role="client"><ClientMessages /></ProtectedRoute>} />
          <Route path="/client/notifications" element={<ProtectedRoute role="client"><ClientNotifications /></ProtectedRoute>} />
          <Route path="/client/profile" element={<ProtectedRoute role="client"><ClientProfile /></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
