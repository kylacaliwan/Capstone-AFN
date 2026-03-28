import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { fetchAdminSettings, updateAdminSettings } from '../../api/api';

export default function AdminSettings() {
  const [settings, setSettings] = useState({
    systemName: '',
    supportEmail: '',
    enableNotifications: false,
    autoDispatchEnabled: false,
    smsNotificationsEnabled: false,
    defaultTimeZone: 'Africa/Lagos',
    maxTechnicianAssignments: 5
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAdminSettings()
      .then((data) => {
        setSettings(prev => ({ ...prev, ...data }));
        setError('');
      })
      .catch((err) => {
        setError(err.message || 'Unable to load settings.');
      });
  }, []);

  const save = async () => {
    try {
      await updateAdminSettings(settings);
      setMessage('Settings updated.');
      setError('');
    } catch (err) {
      setMessage('');
      setError(err.message || 'Unable to update settings.');
    }
  };

  return (
    <Layout>
      <h2 className="text-2xl font-bold mb-4">Settings</h2>
      <p className="text-slate-600">System configuration and global preferences.</p>
      {error && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}

      <div className="mt-4 rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">System Name</span>
            <input value={settings.systemName || ''} onChange={(e) => setSettings({ ...settings, systemName: e.target.value })} className="mt-1 block w-full border px-3 py-2 rounded-lg" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Support Email</span>
            <input value={settings.supportEmail || ''} onChange={(e) => setSettings({ ...settings, supportEmail: e.target.value })} className="mt-1 block w-full border px-3 py-2 rounded-lg" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Default TimeZone</span>
            <input value={settings.defaultTimeZone || 'Africa/Lagos'} onChange={(e) => setSettings({ ...settings, defaultTimeZone: e.target.value })} className="mt-1 block w-full border px-3 py-2 rounded-lg" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Max Technician Assignments</span>
            <input type="number" value={settings.maxTechnicianAssignments || 5} onChange={(e) => setSettings({ ...settings, maxTechnicianAssignments: parseInt(e.target.value) })} className="mt-1 block w-full border px-3 py-2 rounded-lg" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Enable Notifications</span>
            <input type="checkbox" checked={settings.enableNotifications || false} onChange={(e) => setSettings({ ...settings, enableNotifications: e.target.checked })} className="mt-2" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Enable Auto Dispatch</span>
            <input type="checkbox" checked={settings.autoDispatchEnabled || false} onChange={(e) => setSettings({ ...settings, autoDispatchEnabled: e.target.checked })} className="mt-2" />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Enable SMS Notifications</span>
            <input type="checkbox" checked={settings.smsNotificationsEnabled || false} onChange={(e) => setSettings({ ...settings, smsNotificationsEnabled: e.target.checked })} className="mt-2" />
          </label>
        </div>
        <button className="px-5 py-2 rounded-xl bg-primary text-white" onClick={save}>Save</button>
        <div className="mt-2 text-green-700">{message}</div>
      </div>
    </Layout>
  );
}

