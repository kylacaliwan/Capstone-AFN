import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { FiAlertCircle, FiBell, FiCheckCircle, FiInfo, FiTrash2 } from 'react-icons/fi';
import { api } from '../../api/api';

const extractNotifications = (data) => {
  if (Array.isArray(data)) {
    return data;
  }
  if (Array.isArray(data?.results)) {
    return data.results;
  }
  if (Array.isArray(data?.notifications)) {
    return data.notifications;
  }
  return [];
};

export default function ClientNotifications() {
  const { user, token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user && token) {
      loadNotifications();
    }
  }, [user, token]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const response = await api.get('/notifications/');
      const notifArray = extractNotifications(response?.data);
      const sorted = [...notifArray].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      setNotifications(sorted);
      setError('');
    } catch (loadError) {
      setNotifications([]);
      setError(loadError.message || 'Unable to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (notifId) => {
    try {
      await api.post(`/notifications/${notifId}/mark_read/`);
      setNotifications((current) =>
        current.map((notification) =>
          notification.id === notifId ? { ...notification, status: 'read' } : notification
        )
      );
    } catch (markError) {
      setError(markError.message || 'Unable to mark notification as read.');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await api.post('/notifications/mark_all_read/');
      setNotifications((current) => current.map((notification) => ({ ...notification, status: 'read' })));
    } catch (markAllError) {
      setError(markAllError.message || 'Unable to update notifications.');
    }
  };

  const handleDeleteNotification = async (notifId) => {
    try {
      await api.delete(`/notifications/${notifId}/`);
      setNotifications((current) => current.filter((notification) => notification.id !== notifId));
    } catch (deleteError) {
      setError(deleteError.message || 'Unable to delete notification.');
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <FiCheckCircle className="text-green-600" size={20} />;
      case 'warning':
      case 'urgent':
      case 'error':
        return <FiAlertCircle className="text-yellow-600" size={20} />;
      case 'info':
        return <FiInfo className="text-blue-600" size={20} />;
      default:
        return <FiBell className="text-slate-600" size={20} />;
    }
  };

  const getBackgroundColor = (type, status) => {
    const unreadBg = status === 'unread' ? 'bg-blue-50' : '';
    const baseColor = {
      success: 'border-green-200',
      warning: 'border-yellow-200',
      urgent: 'border-yellow-200',
      error: 'border-yellow-200',
      info: 'border-blue-200',
      default: 'border-slate-200'
    };
    return `${unreadBg} border ${baseColor[type] || baseColor.default}`;
  };

  const filteredNotifications = notifications.filter((notification) => {
    if (filter === 'unread') return notification.status === 'unread';
    if (filter === 'success') return notification.type === 'success';
    if (filter === 'warning') return ['warning', 'urgent', 'error'].includes(notification.type);
    if (filter === 'info') return notification.type === 'info';
    return true;
  });

  const unreadCount = notifications.filter((notification) => notification.status === 'unread').length;

  return (
    <Layout>
      <div className="min-h-screen bg-slate-50 p-4">
        <div className="mx-auto max-w-3xl">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Notifications</h1>
              <p className="mt-1 text-slate-600">Stay updated on your service requests and appointments.</p>
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllAsRead}
                className="rounded-lg px-4 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50"
              >
                Mark all as read
              </button>
            )}
          </div>

          {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

          <div className="mb-6 flex flex-wrap gap-2">
            {[
              { label: 'All', value: 'all' },
              { label: 'Unread', value: 'unread', count: unreadCount },
              { label: 'Success', value: 'success' },
              { label: 'Warnings', value: 'warning' },
              { label: 'Info', value: 'info' }
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value)}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 transition-colors ${
                  filter === tab.value
                    ? 'bg-blue-600 text-white'
                    : 'border border-slate-300 bg-white text-slate-700 hover:border-slate-400'
                }`}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {loading ? (
              <div className="py-8 text-center text-slate-500">Loading notifications...</div>
            ) : filteredNotifications.length === 0 ? (
              <div className="py-12 text-center">
                <FiBell size={48} className="mx-auto mb-3 text-slate-300" />
                <p className="text-slate-600">No notifications</p>
              </div>
            ) : (
              filteredNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex items-start gap-4 rounded-lg p-4 transition-shadow hover:shadow-md ${
                    getBackgroundColor(notification.type, notification.status)
                  }`}
                >
                  <div className="mt-1 flex-shrink-0">{getIcon(notification.type)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h3 className={`text-slate-900 ${notification.status === 'unread' ? 'font-bold' : 'font-semibold'}`}>
                          {notification.title || 'Notification'}
                        </h3>
                        <p className="mt-1 text-sm text-slate-700">{notification.message}</p>
                        <p className="mt-2 text-xs text-slate-500">
                          {new Date(notification.created_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteNotification(notification.id)}
                        className="text-slate-400 transition-colors hover:text-slate-600"
                        aria-label="Delete notification"
                      >
                        <FiTrash2 size={18} />
                      </button>
                    </div>
                    {notification.status === 'unread' && (
                      <button
                        onClick={() => handleMarkAsRead(notification.id)}
                        className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700"
                      >
                        Mark as read
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-900">
              <strong>Notification Settings:</strong> You receive updates for request status changes,
              technician assignments, and service completions.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
