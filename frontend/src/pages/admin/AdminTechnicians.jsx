import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { fetchAdminTechnicians, createAdminTechnician, updateAdminTechnician, deleteAdminTechnician } from '../../api/api';

const emptyForm = {
  username: '',
  name: '',
  email: '',
  phone: '',
  status: 'available',
  lat: '',
  lng: '',
  password: '',
  passwordConfirm: ''
};

export default function AdminTechnicians() {
  const [techs, setTechs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingTech, setEditingTech] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [message, setMessage] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchAdminTechnicians();
      setTechs(data);
      setMessage('');
    } catch (error) {
      setTechs([]);
      setMessage(error.message || 'Unable to load technicians.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => setFormData(emptyForm);

  const onSave = async () => {
    try {
      if (editingTech) {
        await updateAdminTechnician(editingTech.id, formData);
        setMessage('Technician updated successfully.');
      } else {
        await createAdminTechnician(formData);
        setMessage('Technician created successfully.');
      }
      resetForm();
      setEditingTech(null);
      await load();
    } catch (error) {
      setMessage(error.message || 'Error saving technician.');
    }
  };

  const onEdit = (tech) => {
    setEditingTech(tech);
    setFormData({
      username: tech.username || '',
      name: tech.name,
      email: tech.email || '',
      phone: tech.phone || '',
      status: tech.status,
      lat: tech.lat,
      lng: tech.lng,
      password: '',
      passwordConfirm: ''
    });
  };

  const onDelete = async (id) => {
    if (!window.confirm('Confirm delete technician?')) return;
    try {
      await deleteAdminTechnician(id);
      setMessage('Technician removed.');
      load();
    } catch (error) {
      setMessage(error.message || 'Unable to remove technician.');
    }
  };

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap justify-between gap-4 items-end">
        <div>
          <h2 className="text-2xl font-bold">Technicians Management</h2>
          <p className="text-slate-600">Manage technicians: add, edit, deactivate and assign skills.</p>
        </div>
        <div className="text-sm text-green-700">{message}</div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold mb-3">{editingTech ? 'Edit Technician' : 'Add Technician'}</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            className="border rounded-xl p-2"
            placeholder="Username"
            value={formData.username}
            disabled={!!editingTech}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
          />
          <input className="border rounded-xl p-2" placeholder="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
          <input className="border rounded-xl p-2" placeholder="Phone" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
          <select className="border rounded-xl p-2" value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}>
            <option value="available">available</option>
            <option value="on_job">on_job</option>
            <option value="offline">offline</option>
          </select>
          <input type="number" className="border rounded-xl p-2" placeholder="Latitude" value={formData.lat} onChange={(e) => setFormData({ ...formData, lat: e.target.value })} />
          <input type="number" className="border rounded-xl p-2" placeholder="Longitude" value={formData.lng} onChange={(e) => setFormData({ ...formData, lng: e.target.value })} />
          {!editingTech && (
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
          <button className="bg-primary text-white rounded-xl px-4 py-2" onClick={onSave}>{editingTech ? 'Update' : 'Create'}</button>
          <button className="bg-slate-200 rounded-xl px-4 py-2" onClick={() => { resetForm(); setEditingTech(null); }}>Cancel</button>
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-3">Technicians</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse">
            <thead>
              <tr className="bg-slate-100 text-left">
                <th className="p-3">Username</th>
                <th className="p-3">Name</th>
                <th className="p-3">Status</th>
                <th className="p-3">Email</th>
                <th className="p-3">Phone</th>
                <th className="p-3">Coordinates</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="p-3">Loading...</td></tr>
              ) : techs.length === 0 ? (
                <tr><td colSpan={7} className="p-3">No technicians found.</td></tr>
              ) : techs.map((tech) => (
                <tr key={tech.id} className="border-t">
                  <td className="p-3">{tech.username}</td>
                  <td className="p-3">{tech.name}</td>
                  <td className="p-3">{tech.status}</td>
                  <td className="p-3">{tech.email || '-'}</td>
                  <td className="p-3">{tech.phone || '-'}</td>
                  <td className="p-3">
                    {tech.lat || tech.lng ? `${tech.lat}, ${tech.lng}` : '-'}
                  </td>
                  <td className="p-3 flex gap-2">
                    <button className="text-blue-600" onClick={() => onEdit(tech)}>Edit</button>
                    <button className="text-red-600" onClick={() => onDelete(tech.id)}>Delete</button>
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
