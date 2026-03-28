import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import { FiMapPin, FiCalendar, FiUser, FiArrowRight, FiFilter } from 'react-icons/fi';
import { fetchClientRequests } from '../../api/api';

export default function ClientRequestTracking() {
  const [requests, setRequests] = useState([]);
  const [filteredRequests, setFilteredRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    loadRequests();
  }, []);

  useEffect(() => {
    filterRequests();
  }, [requests, statusFilter]);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await fetchClientRequests();
      setRequests(data);
      setError(null);
    } catch (err) {
      setError('Failed to load requests');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filterRequests = () => {
    if (statusFilter === 'all') {
      setFilteredRequests(requests);
    } else {
      setFilteredRequests(requests.filter(req => req.status === statusFilter));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-indigo-100 text-indigo-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      low: 'text-blue-600',
      normal: 'text-gray-600',
      high: 'text-orange-600',
      urgent: 'text-red-600'
    };
    return colors[priority?.toLowerCase()] || 'text-gray-600';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric'
    });
  };

  const handleViewDetail = (requestId) => {
    navigate(`/client/requests/${requestId}`);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Filter Section */}
        <div className="rounded-lg bg-white p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 mb-3">
            <FiFilter className="text-slate-600" />
            <span className="text-sm font-medium text-slate-700">Filter by Status:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'all'
                  ? 'bg-primary text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              All ({requests.length})
            </button>
            <button
              onClick={() => setStatusFilter('pending')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'pending'
                  ? 'bg-yellow-500 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setStatusFilter('approved')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'approved'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Approved
            </button>
            <button
              onClick={() => setStatusFilter('in_progress')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'in_progress'
                  ? 'bg-indigo-500 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              In Progress
            </button>
            <button
              onClick={() => setStatusFilter('completed')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'completed'
                  ? 'bg-green-500 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Completed
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="rounded-lg bg-white p-8 shadow-sm text-center">
            <div className="inline-block">
              <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-primary animate-spin"></div>
            </div>
            <p className="mt-2 text-slate-600">Loading requests...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="rounded-lg bg-red-50 p-4 border border-red-200">
            <p className="text-red-700 font-medium">{error}</p>
            <button
              onClick={loadRequests}
              className="mt-2 text-sm text-red-600 hover:text-red-700 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredRequests.length === 0 && (
          <div className="rounded-lg bg-white p-8 shadow-sm text-center">
            <p className="text-slate-600 mb-4">
              {statusFilter === 'all' 
                ? 'No service requests yet.' 
                : `No ${statusFilter} requests.`}
            </p>
            <button
              onClick={() => navigate('/client/service-requests')}
              className="text-primary hover:underline font-medium"
            >
              Create your first request
            </button>
          </div>
        )}

        {/* Requests Grid */}
        {!loading && filteredRequests.length > 0 && (
          <div className="grid gap-4">
            {filteredRequests.map((request) => (
              <div
                key={request.id}
                className="rounded-lg bg-white p-5 shadow-sm border border-slate-200 hover:shadow-md transition cursor-pointer"
                onClick={() => handleViewDetail(request.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="font-semibold text-slate-800 truncate">
                        Request #{request.id}
                      </h3>
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(request.status)}`}>
                        {request.status?.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className={`inline-block px-2 py-1 text-xs font-medium whitespace-nowrap ${getPriorityColor(request.priority)}`}>
                        {request.priority?.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-sm text-slate-600 mb-3">
                      {request.service_type_name || request.service_type}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      {/* Location */}
                      <div className="flex items-start gap-2">
                        <FiMapPin className="text-slate-400 flex-shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <p className="text-slate-500 text-xs">Location</p>
                          <p className="text-slate-700 truncate">
                            {request.address || 'Not specified'}
                          </p>
                        </div>
                      </div>

                      {/* Request Date */}
                      <div className="flex items-start gap-2">
                        <FiCalendar className="text-slate-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-slate-500 text-xs">Requested</p>
                          <p className="text-slate-700">
                            {formatDate(request.request_date)}
                          </p>
                        </div>
                      </div>

                      {/* Technician (if assigned) */}
                      {request.technician_name && (
                        <div className="flex items-start gap-2">
                          <FiUser className="text-slate-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-slate-500 text-xs">Technician</p>
                            <p className="text-slate-700">
                              {request.technician_name}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Scheduled Date (if available) */}
                      {request.scheduled_date && (
                        <div className="flex items-start gap-2">
                          <FiCalendar className="text-slate-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-slate-500 text-xs">Scheduled</p>
                            <p className="text-slate-700">
                              {formatDate(request.scheduled_date)}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Description Preview */}
                    {request.description && (
                      <p className="mt-3 text-sm text-slate-600 line-clamp-2">
                        {request.description}
                      </p>
                    )}
                  </div>

                  {/* Arrow Icon */}
                  <div className="flex-shrink-0 text-slate-300 mt-1">
                    <FiArrowRight className="w-5 h-5" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
