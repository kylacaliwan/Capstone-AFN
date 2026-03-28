import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { fetchAdminClients, createAdminClient, updateAdminClient, deleteAdminClient } from '../../api/api';

const emptyForm = {
  username: '',
  name: '',
  email: '',
  phone: '',
  address: '',
  password: '',
  passwordConfirm: ''
};

export default function AdminClients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingClient, setEditingClient] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [message, setMessage] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      setClients(await fetchAdminClients());
      setMessage('');
    } catch (error) {
      setClients([]);
      setMessage(error.message || 'Unable to load clients.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => setFormData(emptyForm);

  const save = async () => {
    try {
      if (editingClient) {
        await updateAdminClient(editingClient.id, formData);
        setMessage('Client updated.');
      } else {
        await createAdminClient(formData);
        setMessage('Client created.');
      }
      resetForm();
      setEditingClient(null);
      await load();
    } catch (error) {
      setMessage(error.message || 'Client save error.');
    }
  };

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap justify-between gap-4 items-end">
        <div>
          <h2 className="text-2xl font-bold">Clients Management</h2>
          <p className="text-slate-600">View and manage client accounts and histories.</p>
        </div>
        <div className="text-sm text-green-700">{message}</div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold mb-3">{editingClient ? 'Edit Client' : 'Add Client'}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            className="border rounded-xl p-2"
            placeholder="Username"
            value={formData.username}
            disabled={!!editingClient}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
          />
          <input className="border rounded-xl p-2" placeholder="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Phone" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Address" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
          {!editingClient && (
            <>
              <input
                type="password"
                className="border rounded-xl p-2"
                placeholder="Password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
              <input
                type="password"
                className="border rounded-xl p-2"
                placeholder="Confirm Password"
                value={formData.passwordConfirm}
                onChange={(e) => setFormData({ ...formData, passwordConfirm: e.target.value })}
              />
            </>
          )}
        </div>
        <div className="mt-4 flex gap-2">
          <button onClick={save} className="bg-primary text-white rounded-xl px-4 py-2">{editingClient ? 'Update' : 'Create'}</button>
          <button className="bg-slate-200 rounded-xl px-4 py-2" onClick={() => { resetForm(); setEditingClient(null); }}>Cancel</button>
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-3">Client list</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="p-3">Username</th>
                <th className="p-3">Name</th>
                <th className="p-3">Email</th>
                <th className="p-3">Phone</th>
                <th className="p-3">Address</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={6} className="p-3">Loading...</td></tr> : clients.length === 0 ? <tr><td colSpan={6} className="p-3">No clients yet.</td></tr> : clients.map((client) => (
                <tr key={client.id} className="border-t">
                  <td className="p-3">{client.username}</td>
                  <td className="p-3">{client.name}</td>
                  <td className="p-3">{client.email}</td>
                  <td className="p-3">{client.phone}</td>
                  <td className="p-3">{client.address}</td>
                  <td className="p-3 flex gap-2">
                    <button
                      className="text-blue-600"
                      onClick={() => {
                        setEditingClient(client);
                        setFormData({
                          username: client.username || '',
                          name: client.name || '',
                          email: client.email || '',
                          phone: client.phone || '',
                          address: client.address || '',
                          password: '',
                          passwordConfirm: ''
                        });
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="text-red-600"
                      onClick={async () => {
                        if (!window.confirm('Delete this client?')) return;
                        try {
                          await deleteAdminClient(client.id);
                          setMessage('Client deleted.');
                          load();
                        } catch (error) {
                          setMessage(error.message || 'Unable to delete client.');
                        }
                      }}
                    >
                      Delete
                    </button>
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
