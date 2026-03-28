import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { fetchTechnicianProfile, updateTechnicianProfile } from '../../api/api';

export default function TechnicianProfile() {
  const { user } = useAuth();
  const techName = user?.username || 'Ade Johnson';
  const [profile, setProfile] = useState({
    phone: '',
    email: '',
    skills: '',
    totalCompleted: 0,
    avgCompletionTime: '',
    rating: 0
  });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    const data = await fetchTechnicianProfile(techName);
    setProfile(data);
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('Saving profile...');
    try {
      await updateTechnicianProfile({ techName, updates: { phone: profile.phone } });
      setEditing(false);
      setMessage('Profile updated successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to save profile.');
    }
    setSaving(false);
  };

  const skillsList = profile.skills ? profile.skills.split(',').map(s => s.trim()) : [];

  return (
    <Layout>
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-900 mb-2">Profile</h2>
        <p className="text-slate-600">Manage your account and view performance metrics.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Profile Card */}
        <div className="lg:col-span-2 bg-white rounded-3xl shadow-xl border border-slate-200 p-10">
          <div className="flex items-center gap-6 mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shadow-lg flex-shrink-0">
              {techName.slice(0,2).toUpperCase()}
            </div>
            <div>
              <h3 className="text-2xl font-bold text-slate-900">{techName}</h3>
              <p className="text-slate-600">{profile.status || 'Active'}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-8 mb-10">
            <div>
              <label className="block text-sm font-semibold text-slate-900 mb-3">Phone Number</label>
              {editing ? (
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({...profile, phone: e.target.value})}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="Enter phone number"
                />
              ) : (
                <div className="text-2xl font-semibold text-slate-900">{profile.phone || 'Not set'}</div>
              )}
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-900 mb-3">Email</label>
              <div className="text-lg text-slate-700">{profile.email || 'Not set'}</div>
            </div>
          </div>

          <div className="mb-10">
            <label className="block text-sm font-semibold text-slate-900 mb-4">Skills</label>
            <div className="flex flex-wrap gap-2">
              {skillsList.map((skill, i) => (
                <span key={i} className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {skill}
                </span>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6 pt-8 border-t border-slate-200">
            <div className="text-center p-6 bg-slate-50 rounded-2xl">
              <div className="text-3xl font-bold text-emerald-600 mb-2">{profile.totalCompleted || 0}</div>
              <div className="text-sm text-slate-600 uppercase tracking-wide">Total Jobs</div>
            </div>
            <div className="text-center p-6 bg-slate-50 rounded-2xl">
              <div className="text-3xl font-bold text-blue-600 mb-2">{profile.avgCompletionTime || 'N/A'}</div>
              <div className="text-sm text-slate-600 uppercase tracking-wide">Avg Time</div>
            </div>
            <div className="text-center p-6 bg-slate-50 rounded-2xl">
              <div className={`text-3xl font-bold mb-2 ${profile.rating >= 4 ? 'text-amber-500' : 'text-slate-400'}`}>
                {profile.rating ? profile.rating.toFixed(1) : 'N/A'}
              </div>
              <div className="text-sm text-slate-600 uppercase tracking-wide">Rating</div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 mt-10 pt-8 border-t border-slate-200">
            <button
              onClick={() => setEditing(!editing)}
              className="flex-1 px-8 py-4 border-2 border-slate-300 hover:border-slate-400 bg-white rounded-2xl font-semibold text-slate-900 transition hover:shadow-md disabled:opacity-50"
              disabled={saving}
            >
              {editing ? 'Cancel' : 'Edit Phone'}
            </button>
            {editing && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-8 py-4 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-semibold rounded-2xl shadow-lg transition-all hover:shadow-xl disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </button>
            )}
          </div>

          {message && (
            <div className={`mt-6 p-4 rounded-2xl text-center font-semibold ${
              message.includes('success') 
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                : 'bg-red-100 text-red-800 border border-red-300'
            }`}>
              {message}
            </div>
          )}
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-purple-500 to-indigo-600 p-8 text-white rounded-3xl shadow-2xl">
            <h4 className="text-xl font-bold mb-4">Last 30 Days</h4>
            <div className="space-y-3">
              <div className="flex justify-between text-lg">
                <span>Jobs Completed</span>
                <span className="font-black text-2xl">{profile.totalCompleted || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Avg Rating</span>
                <span>{profile.rating ? `${profile.rating.toFixed(1)}/5` : 'N/A'}</span>
              </div>
            </div>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg border">
            <h4 className="font-bold mb-6 text-slate-900 text-center">Certified Skills</h4>
            <div className="grid grid-cols-2 gap-3">
              {['Solar Installation', 'CCTV', 'Fire Detection', 'AC Services'].map(skill => (
                <div key={skill} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                  <span className="text-sm">{skill}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
