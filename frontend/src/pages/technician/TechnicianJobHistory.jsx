import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { fetchTechnicianHistory } from '../../api/api';
import { FiDownload, FiEye, FiFileText } from 'react-icons/fi';

const formatDate = (dateStr) =>
  new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

const buildHistoryReport = (job) => `AFN Technician Job Report
Ticket: #${job.ticketId}
Client: ${job.client}
Service: ${job.service}
Completed: ${formatDate(job.scheduledDate)}
Priority: ${job.priority || 'Normal'}
Address: ${job.address || 'Not provided'}

Notes:
${job.notes || 'No notes captured for this completed job.'}
`;

export default function TechnicianJobHistory() {
  const { user } = useAuth();
  const techName = user?.username || 'Ade Johnson';
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    const data = await fetchTechnicianHistory(techName);
    setHistory(data);
    setLoading(false);
  };

  const downloadHistoryReport = (job) => {
    const reportBlob = new Blob([buildHistoryReport(job)], { type: 'text/plain;charset=utf-8' });
    const reportUrl = URL.createObjectURL(reportBlob);
    const link = document.createElement('a');
    link.href = reportUrl;
    link.download = `ticket-${job.ticketId}-report.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(reportUrl);
  };

  return (
    <Layout>
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-800">Job History</h2>
        <button
          onClick={loadHistory}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-slate-100 px-6 py-2 text-slate-700 transition hover:bg-slate-200"
        >
          <FiDownload /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="grid place-items-center py-20">
          <div className="mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-slate-400"></div>
          <p className="text-slate-500">Loading history...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50 py-20 text-center">
          <FiFileText className="mx-auto mb-6 h-16 w-16 text-slate-400" />
          <h3 className="mb-3 text-2xl font-bold text-slate-900">No completed jobs yet</h3>
          <p className="mx-auto mb-8 max-w-md text-slate-600">
            Your completed service history will appear here. Check My Jobs for current work.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {history.map((job) => (
            <div
              key={job.id}
              className="rounded-2xl border border-slate-200 bg-white p-8 transition-shadow hover:-translate-y-1 hover:shadow-xl"
            >
              <div className="mb-6 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex-1">
                  <div className="mb-4 flex items-center gap-4">
                    <div className="rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-2 font-semibold text-white">
                      COMPLETED
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-800">
                      {job.service}
                    </span>
                  </div>
                  <h3 className="mb-3 text-2xl font-bold text-slate-900">{job.client}</h3>
                  <div className="mb-4 grid grid-cols-2 gap-6 text-sm">
                    <div>
                      <span className="text-slate-500">Ticket ID</span>
                      <div className="font-semibold text-slate-900">#{job.ticketId}</div>
                    </div>
                    <div>
                      <span className="text-slate-500">Completed</span>
                      <div className="font-semibold">{formatDate(job.scheduledDate)}</div>
                    </div>
                    {job.priority && (
                      <div>
                        <span className="text-slate-500">Priority</span>
                        <div
                          className={`rounded-full px-2 py-1 text-xs font-semibold ${
                            job.priority === 'High'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-green-100 text-green-800'
                          }`}
                        >
                          {job.priority}
                        </div>
                      </div>
                    )}
                  </div>
                  {job.notes && (
                    <div className="mt-4 rounded-r-xl border-l-4 border-green-400 bg-slate-50 p-4">
                      <span className="block text-sm leading-relaxed text-slate-700">{job.notes}</span>
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-3 border-slate-200 pt-4 lg:border-l lg:pl-8 lg:pt-0">
                  <button
                    type="button"
                    onClick={() => setSelectedJob(job)}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-500 px-6 py-3 font-medium text-white shadow-md transition hover:bg-blue-600 lg:w-auto"
                  >
                    <FiEye size={18} /> View Details
                  </button>
                  <button
                    type="button"
                    onClick={() => downloadHistoryReport(job)}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-100 px-6 py-3 font-medium text-slate-700 shadow-md transition hover:bg-slate-200 lg:w-auto"
                  >
                    <FiDownload size={18} /> Download Report
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-12 grid gap-6 md:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100 p-8 md:col-span-2">
          <h4 className="mb-4 text-lg font-semibold text-slate-900">Performance Summary</h4>
          <p className="leading-relaxed text-slate-600">
            {history.length > 0
              ? `Completed ${history.length} jobs across ${new Set(history.map((entry) => entry.service)).size} service types. Your work history demonstrates consistent quality.`
              : 'Your performance metrics will appear here as you complete more jobs.'}
          </p>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg">
          <h4 className="mb-6 text-center text-lg font-semibold">Total Jobs</h4>
          <div className="text-center text-4xl font-bold text-slate-900">{history.length}</div>
        </div>
      </div>

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
                onClick={() => setSelectedJob(null)}
                className="rounded-lg bg-slate-100 px-3 py-2 text-slate-600 hover:bg-slate-200"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Completed Date</div>
                <div className="text-slate-900">{formatDate(selectedJob.scheduledDate)}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium text-slate-500">Priority</div>
                <div className="text-slate-900">{selectedJob.priority || 'Normal'}</div>
              </div>
              <div className="md:col-span-2">
                <div className="mb-1 text-sm font-medium text-slate-500">Address</div>
                <div className="text-slate-900">{selectedJob.address || 'No address recorded.'}</div>
              </div>
            </div>

            <div className="mt-4 rounded-xl bg-slate-50 p-4">
              <div className="mb-1 text-sm font-medium text-slate-500">Completion Notes</div>
              <div className="text-sm text-slate-700">
                {selectedJob.notes || 'No notes were captured for this completed job.'}
              </div>
            </div>

            <div className="mt-6">
              <button
                type="button"
                onClick={() => downloadHistoryReport(selectedJob)}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
              >
                Download This Report
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
