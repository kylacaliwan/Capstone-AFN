import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import { FiMapPin, FiCalendar, FiUser, FiStar, FiDownload, FiEye } from 'react-icons/fi';
import { fetchClientRequests } from '../../api/api';

export default function ClientServiceHistory() {
  const [history, setHistory] = useState([]);
  const [filteredHistory, setFilteredHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState('all'); // all, completed, rated, pending_rating
  const [sortBy, setSortBy] = useState('recent'); // recent, oldest, highest_rating
  const navigate = useNavigate();

  useEffect(() => {
    loadServiceHistory();
  }, []);

  useEffect(() => {
    filterAndSortHistory();
  }, [history, filterType, sortBy]);

  const loadServiceHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchClientRequests();
      // Filter to show completed services
      const completedServices = data.filter(req => req.status === 'completed');
      setHistory(completedServices);
      setError(null);
    } catch (err) {
      setError('Failed to load service history');
      console.error(err);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortHistory = () => {
    let filtered = history;

    // Apply filter
    if (filterType === 'rated') {
      filtered = filtered.filter(h => h.client_rating !== null && h.client_rating !== undefined);
    } else if (filterType === 'pending_rating') {
      filtered = filtered.filter(h => h.client_rating === null || h.client_rating === undefined);
    }

    // Apply sort
    if (sortBy === 'oldest') {
      filtered.sort((a, b) => new Date(a.completed_date) - new Date(b.completed_date));
    } else if (sortBy === 'recent') {
      filtered.sort((a, b) => new Date(b.completed_date) - new Date(a.completed_date));
    } else if (sortBy === 'highest_rating') {
      filtered.sort((a, b) => (b.client_rating || 0) - (a.client_rating || 0));
    }

    setFilteredHistory(filtered);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const renderRating = (rating) => {
    if (rating === null || rating === undefined) {
      return <span className="text-sm text-slate-500">Not yet rated</span>;
    }
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <FiStar
            key={i}
            size={16}
            className={i < rating ? 'fill-yellow-400 text-yellow-400' : 'text-slate-300'}
          />
        ))}
        <span className="ml-2 text-sm font-medium">{rating}/5</span>
      </div>
    );
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-primary"></div>
            <p className="mt-4 text-slate-600">Loading service history...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Service History</h1>
          <p className="mt-2 text-slate-600">View your completed services and manage ratings</p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Filters and Sort */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {/* Filter Type */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Filter</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Services</option>
              <option value="rated">Rated Services</option>
              <option value="pending_rating">Pending Rating</option>
            </select>
          </div>

          {/* Sort */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="recent">Most Recent</option>
              <option value="oldest">Oldest First</option>
              <option value="highest_rating">Highest Rated</option>
            </select>
          </div>

          {/* Stats */}
          <div className="col-span-1 md:col-span-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-blue-50 p-3 text-center">
                <p className="text-2xl font-bold text-blue-600">{history.length}</p>
                <p className="text-xs text-blue-700">Completed Services</p>
              </div>
              <div className="rounded-lg bg-green-50 p-3 text-center">
                <p className="text-2xl font-bold text-green-600">
                  {history.filter(h => h.client_rating).length}
                </p>
                <p className="text-xs text-green-700">Rated Services</p>
              </div>
            </div>
          </div>
        </div>

        {/* Service History List */}
        {filteredHistory.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-slate-300 p-12 text-center">
            <p className="text-slate-500">No completed services yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((service) => (
              <div
                key={service.id}
                className="rounded-lg border border-slate-200 bg-white p-4 hover:shadow-md transition-shadow"
              >
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {/* Service Info */}
                  <div className="md:col-span-2">
                    <h3 className="text-lg font-semibold text-slate-900">{service.service_type}</h3>
                    <p className="mt-1 text-sm text-slate-600">{service.description}</p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="flex items-center gap-1 text-sm text-slate-600">
                        <FiMapPin size={14} />
                        {service.address}
                      </span>
                    </div>
                  </div>

                  {/* Technician & Date */}
                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide">Technician</p>
                      <div className="flex items-center gap-2 mt-1">
                        <FiUser size={16} className="text-slate-400" />
                        <p className="font-medium text-slate-900">{service.technician_name}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide">Completed</p>
                      <div className="flex items-center gap-2 mt-1">
                        <FiCalendar size={16} className="text-slate-400" />
                        <p className="text-sm text-slate-900">{formatDate(service.completed_date)}</p>
                      </div>
                    </div>
                  </div>

                  {/* Rating & Actions */}
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Your Rating</p>
                      <div>{renderRating(service.client_rating)}</div>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => navigate(`/client/requests/${service.id}`)}
                        className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-slate-100 hover:bg-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition"
                      >
                        <FiEye size={14} />
                        View
                      </button>
                      {!service.client_rating && (
                        <button
                          onClick={() => navigate(`/client/requests/${service.id}`)}
                          className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-primary hover:bg-primary/90 px-3 py-2 text-sm font-medium text-white transition"
                        >
                          <FiStar size={14} />
                          Rate
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Feedback Preview */}
                {service.client_feedback && (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Your Feedback</p>
                    <p className="mt-1 text-sm text-slate-700 italic">"{service.client_feedback}"</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
