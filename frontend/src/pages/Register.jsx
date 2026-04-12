import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    phone: '',
    address: '',
    role: 'client',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!formData.username || !formData.email || !formData.password) {
      setError('Username, email, and password are required');
      setLoading(false);
      return;
    }

    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      const result = await register({
        ...formData,
        role: 'client',
      });

      setLoading(false);

      if (!result || !result.success) {
        setError(result?.message || 'Registration failed. Please try again.');
        return;
      }

      navigate('/login', {
        state: { message: 'Registration successful! Please log in.' },
      });
    } catch (err) {
      setLoading(false);
      setError('Something went wrong. Please try again.');
    }
  };

  return (
    <div className="flex h-screen bg-[url('/register-bg.jpg')] bg-cover bg-center text-white">
      
      {/* LEFT SIDE (Overlay Text) */}
      <div className="flex bg-black bg-opacity-65 h-screen w-full font-semibold items-center">
        <h1 className="text-6xl w-[60%] m-32">
          Your Partner in Solar and Smart Home Solutions.
        </h1>
      </div>

      {/* RIGHT SIDE (FORM) */}
      <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white py-14 px-14 text-slate-800 shadow-xl overflow-y-auto">
        
        <h1 className="text-2xl font-bold mb-1 text-center">Create Account</h1>
        <p className="text-sm text-slate-500 mb-6 text-center">
          Create a client account to start requesting service.
        </p>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            placeholder="Username *"
            className="w-full rounded-lg border px-3 py-2"
            required
          />

          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Email *"
            className="w-full rounded-lg border px-3 py-2"
            required
          />

          <input
            type="text"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            placeholder="First Name (Optional)"
            className="w-full rounded-lg border px-3 py-2"
          />

          <input
            type="text"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            placeholder="Last Name (Optional)"
            className="w-full rounded-lg border px-3 py-2"
          />

          <input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            placeholder="Phone (Optional)"
            className="w-full rounded-lg border px-3 py-2"
          />

          <input
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            placeholder="Address (Optional)"
            className="w-full rounded-lg border px-3 py-2"
          />

          <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            Public signup creates a client account.
          </div>

          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Password *"
            className="w-full rounded-lg border px-3 py-2"
            required
          />

          <input
            type="password"
            name="password_confirm"
            value={formData.password_confirm}
            onChange={handleChange}
            placeholder="Confirm Password *"
            className="w-full rounded-lg border px-3 py-2"
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-600 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}