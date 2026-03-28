import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { fetchTechnicianJobs, updateJobStatus } from '../../api/api';
import { FiClipboard, FiEye, FiMapPin } from 'react-icons/fi';

export default function TechnicianJobs() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const techName = user?.username || 'Ade Johnson';
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [actionMessage, setActionMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadJobs();
  }, []);

  useEffect(() => {
    const requestedTicketId = searchParams.get('ticketId');
    if (!requestedTicketId) {
      setSelectedJob(null);
      return;
    }

    const matchingJob = jobs.find(
      (job) => String(job.ticketId || job.id) === String(requestedTicketId)
    );
    if (matchingJob) {
      setSelectedJob(matchingJob);
    }
  }, [jobs, searchParams]);

  const loadJobs = async () => {
    try {
      const data = await fetchTechnicianJobs(techName);
      setJobs(data);
      setError('');
    } catch (loadError) {
      setJobs([]);
      setError(loadError.message || 'Unable to load jobs.');
    }
  };

  const openJobDetails = (job) => {
    setSelectedJob(job);
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set('ticketId', String(job.ticketId || job.id));
    setSearchParams(nextSearchParams, { replace: true });
  };

  const closeJobDetails = () => {
    setSelectedJob(null);
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.delete('ticketId');
    setSearchParams(nextSearchParams, { replace: true });
  };

  const handleStatusUpdate = async (jobId, status) => {
    try {
      setActionMessage(`Updating job ${jobId} to ${status.toUpperCase()}...`);
      await updateJobStatus(jobId, status);
      await loadJobs();
      setActionMessage(`Job ${jobId} updated to ${status.toUpperCase()}.`);
      setTimeout(() => setActionMessage(''), 4000);
    } catch (updateError) {
      setActionMessage(updateError.message || 'Unable to update job.');
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-slate-800">My Jobs ({jobs.length})</h2>
        <button
          onClick={loadJobs}
          className="rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
        >
          Refresh
        </button>
      </div>

      {actionMessage && (
        <div className="mb-4 rounded border-l-4 border-green-500 bg-green-100 p-3 text-green-800">
          {actionMessage}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-800">{error}</div>
      )}

      {jobs.length === 0 ? (
        <div className="py-12 text-center">
          <FiClipboard className="mx-auto mb-4 h-12 w-12 text-slate-400" />
          <h3 className="mb-2 text-lg font-medium text-slate-900">No jobs assigned</h3>
          <p className="text-slate-500">Check back later for new assignments.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h3 className="text-xl font-bold text-slate-900">{job.service}</h3>
                  <p className="text-slate-600">Ticket #{job.ticketId} | {job.client}</p>
                  <p className="mt-1 text-sm text-slate-500">{job.address}</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    job.status === 'assigned'
                      ? 'bg-yellow-100 text-yellow-800'
                      : job.status === 'accepted'
                        ? 'bg-blue-100 text-blue-800'
                        : job.status === 'in_progress'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-green-100 text-green-800'
                  }`}
                >
                  {job.status.toUpperCase()}
                </span>
              </div>

              <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-500">Priority</label>
                  <span
                    className={`rounded px-2 py-1 text-xs ${
                      job.priority === 'High'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-slate-100 text-slate-800'
                    }`}
                  >
                    {job.priority}
                  </span>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-500">Scheduled</label>
                  <span className="text-sm">{new Date(job.scheduledDate).toLocaleDateString()}</span>
                </div>
                {job.notes && (
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-500">Notes</label>
                    <p className="text-sm text-slate-700">{job.notes}</p>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {job.status === 'assigned' && (
                  <button
                    onClick={() => handleStatusUpdate(job.id, 'accepted')}
                    className="rounded-lg bg-blue-500 px-6 py-2 font-medium text-white transition hover:bg-blue-600"
                  >
                    Accept Job
                  </button>
                )}
                {(job.status === 'assigned' || job.status === 'accepted') && (
                  <button
                    onClick={() => handleStatusUpdate(job.id, 'in_progress')}
                    className="rounded-lg bg-orange-500 px-6 py-2 font-medium text-white transition hover:bg-orange-600"
                  >
                    Start Job
                  </button>
                )}
                {(job.status === 'in_progress' || job.status === 'accepted') && (
                  <button
                    onClick={() => handleStatusUpdate(job.id, 'completed')}
                    className="rounded-lg bg-green-500 px-6 py-2 font-medium text-white transition hover:bg-green-600"
                  >
                    Complete Job
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => openJobDetails(job)}
                  className="flex items-center gap-1 rounded-lg bg-slate-200 px-6 py-2 text-slate-700 hover:bg-slate-300"
                >
                  <FiEye /> Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-2xl font-bold text-slate-900">{selectedJob.service}</h3>
                <p className="text-slate-600">
                  Ticket #{selectedJob.ticketId} for {selectedJob.client}
                </p>
              </div>
              <button
                type="button"
                onClick={closeJobDetails}
                className="rounded-lg bg-slate-100 px-3 py-2 text-slate-600 hover:bg-slate-200"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Status</div>
                <div className="text-slate-900">{selectedJob.status.replace(/_/g, ' ')}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Priority</div>
                <div className="text-slate-900">{selectedJob.priority}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Scheduled Date</div>
                <div className="text-slate-900">
                  {new Date(selectedJob.scheduledDate).toLocaleString()}
                </div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Address</div>
                <div className="text-slate-900">{selectedJob.address || 'Location pending'}</div>
              </div>
            </div>

            {selectedJob.notes && (
              <div className="mt-4 rounded-xl bg-slate-50 p-4">
                <div className="mb-1 text-sm font-medium text-slate-500">Work Notes</div>
                <div className="text-sm text-slate-700">{selectedJob.notes}</div>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to={`/technician/map-navigation?ticketId=${selectedJob.ticketId}`}
                className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-white hover:bg-emerald-600"
              >
                <FiMapPin size={16} /> Open Navigation
              </Link>
              <Link
                to={`/technician/checklist?ticketId=${selectedJob.ticketId}`}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
              >
                Open Checklist
              </Link>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
