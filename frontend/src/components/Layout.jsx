import { useState } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="min-h-screen md:flex md:ml-64">
        <Sidebar role={user?.role} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="min-w-0 flex-1">
          <Topbar toggleSidebar={() => setSidebarOpen((value) => !value)} />
          <main className="mx-auto w-full max-w-[1600px] px-3 py-4 sm:px-4 md:px-4 lg:px-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
