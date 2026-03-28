import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import { FiMapPin, FiCalendar, FiUser, FiArrowLeft, FiStar } from 'react-icons/fi';
import { fetchRequestDetail, requestTicketReschedule, submitRequestRating } from '../../api/api';
import { getLocalDateInputValue } from '../../utils/date';

const TIME_SLOT_LABELS = {
  morning: 'Morning (8 AM - 11 AM)',
  midday: 'Midday (11 AM - 2 PM)',
  afternoon: 'Afternoon (2 PM - 5 PM)',
  evening: 'Evening (5 PM - 8 PM)'
};

export default function ClientRequestDetail() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRatingForm, setShowRatingForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [showRescheduleForm, setShowRescheduleForm] = useState(false);
  const [rescheduleSubmitting, setRescheduleSubmitting] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTimeSlot, setRescheduleTimeSlot] = useState('');
  const [rescheduleReason, setRescheduleReason] = useState('');

  useEffect(() => {
    loadRequest();
  }, [requestId]);

  const loadRequest = async () => {
    setLoading(true);
    try {
      const data = await fetchRequestDetail(requestId);
      setRequest(data);
      setRatingSubmitted(data.client_rating ? true : false);
      setRating(data.client_rating || 0);
      setFeedback(data.client_feedback || '');
      setRescheduleDate(data.preferred_date || data.scheduled_date || '');
      setRescheduleTimeSlot(data.preferred_time_slot || data.scheduled_time_slot || '');
      setRescheduleReason(data.reschedule_reason || data.scheduling_notes || '');
      setError(null);
    } catch (err) {
      setError('Failed to load request details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestReschedule = async () => {
    if (!rescheduleDate || !rescheduleTimeSlot || !rescheduleReason.trim()) {
      alert('Please choose a date, time slot, and reason for the schedule change.');
      return;
    }

    setRescheduleSubmitting(true);
    try {
      await requestTicketReschedule(requestId, {
        preferred_date: rescheduleDate,
        preferred_time_slot: rescheduleTimeSlot,
        reason: rescheduleReason.trim()
      });
      setShowRescheduleForm(false);
      await loadRequest();
    } catch (err) {
      alert('Failed to request reschedule: ' + err.message);
      console.error(err);
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  const handleSubmitRating = async () => {
    if (rating === 0) {
      alert('Please select a rating');
      return;
    }

    setSubmitting(true);
    try {
      await submitRequestRating(requestId, {
        rating,
        feedback
      });
      setRatingSubmitted(true);
      setShowRatingForm(false);
      // Reload to show updated data
      await loadRequest();
    } catch (err) {
      alert('Failed to submit rating: ' + err.message);
      console.error(err);
    } finally {
      setSubmitting(false);
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
      low: 'text-blue-600 bg-blue-50',
      normal: 'text-gray-600 bg-gray-50',
      high: 'text-orange-600 bg-orange-50',
      urgent: 'text-red-600 bg-red-50'
    };
    return colors[priority?.toLowerCase()] || 'text-gray-600 bg-gray-50';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatTime = (dateString) => {
    if (!dateString) return 'TBD';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatTimeSlot = (value) => TIME_SLOT_LABELS[value] || value || 'No specific window';

  if (loading) {
    return (
      <Layout>
        <div className="rounded-lg bg-white p-8 shadow-sm text-center">
          <div className="inline-block">
            <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-primary animate-spin"></div>
          </div>
          <p className="mt-2 text-slate-600">Loading request details...</p>
        </div>
      </Layout>
    );
  }

  if (error || !request) {
    return (
      <Layout>
        <div className="rounded-lg bg-red-50 p-6 border border-red-200">
          <p className="text-red-700 font-medium mb-4">{error || 'Request not found'}</p>
          <button
            onClick={() => navigate('/client/requests')}
            className="text-red-600 hover:text-red-700 underline"
          >
            Back to requests
          </button>
        </div>
      </Layout>
    );
  }

  const isCompleted = request.status === 'completed';
  const canRequestReschedule = request.status !== 'completed' && request.status !== 'cancelled';
  const warrantyStatusTone = {
    active: 'bg-emerald-100 text-emerald-800',
    expired: 'bg-rose-100 text-rose-800',
    void: 'bg-slate-200 text-slate-700',
    not_applicable: 'bg-slate-100 text-slate-700'
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/client/requests')}
            className="p-2 hover:bg-slate-100 rounded text-slate-600 transition"
          >
            <FiArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">
              Service Request #{request.id}
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              {request.service_type_name || request.service_type}
            </p>
          </div>
        </div>

        {/* Status Section */}
        <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-sm text-slate-600 mb-2">Status</p>
              <div className="flex items-center gap-3">
                <span className={`px-4 py-2 rounded-full text-sm font-semibold ${getStatusColor(request.status)}`}>
                  {request.status?.replace('_', ' ').toUpperCase()}
                </span>
                <span className={`px-3 py-1 rounded text-sm font-medium ${getPriorityColor(request.priority)}`}>
                  {request.priority?.toUpperCase()} Priority
                </span>
              </div>
            </div>
            {request.progress && (
              <div>
                <p className="text-sm text-slate-600 mb-2">Progress</p>
                <div className="w-48 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all"
                    style={{ width: `${request.progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-slate-600 mt-1">{request.progress}% Complete</p>
              </div>
            )}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Left Column - Details */}
          <div className="space-y-6">
            {/* Service Details */}
            <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Service Details</h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-600 mb-1">Description</p>
                  <p className="text-slate-800">{request.description || 'No description provided'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">Service Type</p>
                  <p className="text-slate-800">{request.service_type_name || request.service_type}</p>
                </div>
              </div>
            </div>

            {/* Location Details */}
            <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                <FiMapPin className="text-slate-600" />
                Location
              </h3>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-slate-600 mb-1">Address</p>
                  <p className="text-slate-800">{request.address || 'Not specified'}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-600 mb-1">City</p>
                    <p className="text-slate-800">{request.city || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 mb-1">Province</p>
                    <p className="text-slate-800">{request.province || 'N/A'}</p>
                  </div>
                </div>
                {request.latitude && request.longitude && (
                  <div className="text-xs text-slate-600 bg-slate-50 p-2 rounded">
                    Coordinates: {request.latitude.toFixed(4)}, {request.longitude.toFixed(4)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Timeline & Assignment */}
          <div className="space-y-6">
            {/* Timeline */}
            <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                <FiCalendar className="text-slate-600" />
                Timeline
              </h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-600 mb-1">Requested On</p>
                  <p className="text-slate-800">{formatDate(request.request_date)}</p>
                </div>
                {request.scheduled_date && (
                  <div>
                    <p className="text-sm text-slate-600 mb-1">Scheduled Date</p>
                    <p className="text-slate-800">{formatDate(request.scheduled_date)}</p>
                  </div>
                )}
                {request.scheduled_time_slot && (
                  <div>
                    <p className="text-sm text-slate-600 mb-1">Scheduled Time Window</p>
                    <p className="text-slate-800">{formatTimeSlot(request.scheduled_time_slot)}</p>
                  </div>
                )}
                {(request.preferred_date || request.preferred_time_slot) && (
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-sm text-slate-600 mb-1">Preferred Appointment</p>
                    <p className="text-slate-800">
                      {request.preferred_date ? formatDate(request.preferred_date) : 'No date selected'}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">{formatTimeSlot(request.preferred_time_slot)}</p>
                  </div>
                )}
                {request.start_time && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-slate-600 mb-1">Start Time</p>
                      <p className="text-slate-800">{formatTime(request.start_time)}</p>
                    </div>
                    {request.end_time && (
                      <div>
                        <p className="text-sm text-slate-600 mb-1">End Time</p>
                        <p className="text-slate-800">{formatTime(request.end_time)}</p>
                      </div>
                    )}
                  </div>
                )}
                {request.completed_date && (
                  <div>
                    <p className="text-sm text-slate-600 mb-1">Completed On</p>
                    <p className="text-slate-800 ">{formatDate(request.completed_date)}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Technician Assignment */}
            {request.technician_name && (
              <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <FiUser className="text-slate-600" />
                  Assigned Technician
                </h3>
                <p className="text-slate-800 font-medium">{request.technician_name}</p>
                {request.technician_contact && (
                  <p className="text-slate-600 text-sm mt-2">{request.technician_contact}</p>
                )}
              </div>
            )}

            {canRequestReschedule && (
              <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Schedule Changes</h3>
                {request.reschedule_requested ? (
                  <div className="rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                    <p className="font-medium">A schedule change request is already pending.</p>
                    {request.reschedule_reason && <p className="mt-2">{request.reschedule_reason}</p>}
                  </div>
                ) : !showRescheduleForm ? (
                  <button
                    onClick={() => setShowRescheduleForm(true)}
                    className="w-full px-4 py-2 bg-slate-900 text-white rounded hover:bg-slate-800 transition"
                  >
                    Request Reschedule
                  </button>
                ) : (
                  <div className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="block text-sm text-slate-600 mb-2">New Date</label>
                        <input
                          type="date"
                          value={rescheduleDate}
                          min={getLocalDateInputValue()}
                          onChange={(e) => setRescheduleDate(e.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-slate-600 mb-2">Time Window</label>
                        <select
                          value={rescheduleTimeSlot}
                          onChange={(e) => setRescheduleTimeSlot(e.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded"
                        >
                          <option value="">Select time window</option>
                          {Object.entries(TIME_SLOT_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-600 mb-2">Reason</label>
                      <textarea
                        value={rescheduleReason}
                        onChange={(e) => setRescheduleReason(e.target.value)}
                        rows="3"
                        className="w-full px-3 py-2 border border-slate-300 rounded"
                        placeholder="Tell the team why you need another appointment window."
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleRequestReschedule}
                        disabled={rescheduleSubmitting}
                        className="flex-1 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition disabled:opacity-50"
                      >
                        {rescheduleSubmitting ? 'Submitting...' : 'Send Request'}
                      </button>
                      <button
                        onClick={() => setShowRescheduleForm(false)}
                        className="flex-1 px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Warranty Coverage</h3>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${warrantyStatusTone[request.warranty_status] || 'bg-slate-100 text-slate-700'}`}>
                  {String(request.warranty_status || 'not_applicable').replace('_', ' ')}
                </span>
                {request.warranty_end_date && (
                  <span className="text-sm text-slate-600">Ends {formatDate(request.warranty_end_date)}</span>
                )}
              </div>
              {request.warranty_start_date && (
                <p className="mt-3 text-sm text-slate-600">Coverage started {formatDate(request.warranty_start_date)}</p>
              )}
              {request.warranty_notes && (
                <p className="mt-3 text-sm text-slate-700">{request.warranty_notes}</p>
              )}
            </div>

            {/* Rating Section (for completed requests) */}
            {isCompleted && (
              <div className="rounded-lg bg-white p-6 shadow-sm border border-slate-200">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Rate This Service</h3>
                
                {ratingSubmitted ? (
                  <div className="bg-green-50 border border-green-200 rounded p-4">
                    <p className="text-sm text-green-700 font-medium mb-2">Rating submitted</p>
                    <div className="flex items-center gap-1 mb-3">
                      {[...Array(5)].map((_, i) => (
                        <FiStar
                          key={i}
                          className={`w-5 h-5 ${i < rating ? 'fill-yellow-400 text-yellow-400' : 'text-slate-300'}`}
                        />
                      ))}
                    </div>
                    {feedback && (
                      <p className="text-sm text-slate-700 mt-2">{feedback}</p>
                    )}
                    <button
                      onClick={() => setShowRatingForm(true)}
                      className="text-sm text-primary hover:underline mt-2"
                    >
                      Edit Rating
                    </button>
                  </div>
                ) : (
                  <>
                    {!showRatingForm && (
                      <button
                        onClick={() => setShowRatingForm(true)}
                        className="w-full px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition"
                      >
                        Leave Feedback
                      </button>
                    )}

                    {showRatingForm && (
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm text-slate-600 mb-3">How would you rate this service?</p>
                          <div className="flex gap-2">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <button
                                key={star}
                                onClick={() => setRating(star)}
                                className="transition"
                              >
                                <FiStar
                                  className={`w-8 h-8 ${
                                    star <= rating
                                      ? 'fill-yellow-400 text-yellow-400'
                                      : 'text-slate-300 hover:text-yellow-400'
                                  }`}
                                />
                              </button>
                            ))}
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm text-slate-600 mb-2">
                            Additional Feedback (Optional)
                          </label>
                          <textarea
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="Share your experience..."
                            className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
                            rows="3"
                          />
                        </div>

                        <div className="flex gap-2">
                          <button
                            onClick={handleSubmitRating}
                            disabled={submitting || rating === 0}
                            className="flex-1 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {submitting ? 'Submitting...' : 'Submit Rating'}
                          </button>
                          <button
                            onClick={() => {
                              setShowRatingForm(false);
                              setRating(0);
                              setFeedback('');
                            }}
                            className="flex-1 px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
