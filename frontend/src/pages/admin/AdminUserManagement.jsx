import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { fetchAdminUsers, createAdminUser, updateAdminUser, deactivateAdminUser } from '../../api/api';

const emptyForm = {
  username: '',
  role: 'technician',
  email: '',
  phone: '',
  password: '',
  passwordConfirm: ''
};

export default function AdminUserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = async ({ preserveFeedback = false } = {}) => {
    setLoading(true);
    try {
      const fetchedUsers = await fetchAdminUsers();
      const sortedUsers = [...fetchedUsers].sort((left, right) => Number(right.id || 0) - Number(left.id || 0));
      setUsers(sortedUsers);
      if (!preserveFeedback) {
        setMessage('');
        setError('');
      }
    } catch (error) {
      setUsers([]);
      if (!preserveFeedback) {
        setMessage('');
      }
      setError(error.message || 'Unable to load users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createNew = async (event) => {
    event.preventDefault();
    setMessage('');
    setError('');

    if (!form.username.trim()) {
      setError('Username is required.');
      return;
    }

    if (!form.password) {
      setError('Password is required.');
      return;
    }

    if (form.password !== form.passwordConfirm) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await createAdminUser(form);
      setMessage('User created.');
      setForm(emptyForm);
      await load({ preserveFeedback: true });
    } catch (error) {
      setError(error.message || 'Failed to create user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap justify-between gap-4 items-end">
        <div>
          <h2 className="text-2xl font-bold">User Management</h2>
          <p className="text-slate-600">Manage system users, roles, and access rights.</p>
        </div>
        {message && <div className="text-sm text-green-700">{message}</div>}
      </div>

      <form onSubmit={createNew} className="rounded-xl bg-white p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold mb-3">Create new user</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input className="border rounded-xl p-2" placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <select className="border rounded-xl p-2" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="admin">admin</option>
            <option value="follow_up">After Sales Management</option>
            <option value="supervisor">supervisor</option>
            <option value="technician">technician</option>
            <option value="client">client</option>
          </select>
          <input className="border rounded-xl p-2" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input
            type="password"
            className="border rounded-xl p-2"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <input
            type="password"
            className="border rounded-xl p-2"
            placeholder="Confirm Password"
            value={form.passwordConfirm}
            onChange={(e) => setForm({ ...form, passwordConfirm: e.target.value })}
          />
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-3 bg-primary text-white rounded-xl px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? 'Creating...' : 'Create'}
        </button>
      </form>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-3">All users</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="p-3">Username</th>
                <th className="p-3">Role</th>
                <th className="p-3">Email</th>
                <th className="p-3">Phone</th>
                <th className="p-3">Active</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={6} className="p-3">Loading...</td></tr> : users.map(u => (
                <tr key={u.id} className="border-t">
                  <td className="p-3">{u.username}</td>
                  <td className="p-3">{u.role}</td>
                  <td className="p-3">{u.email || '-'}</td>
                  <td className="p-3">{u.phone || '-'}</td>
                  <td className="p-3">{u.active ? 'Yes' : 'No'}</td>
                  <td className="p-3">
                    {u.active ? (
                      <button
                        className="text-red-600"
                        onClick={async () => {
                          try {
                            await deactivateAdminUser(u.id);
                            setMessage('User deactivated');
                            load();
                          } catch (error) {
                            setMessage(error.message || 'Unable to deactivate user.');
                          }
                        }}
                      >
                        Deactivate
                      </button>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}

