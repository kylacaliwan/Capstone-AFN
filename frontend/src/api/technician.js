import { api, getApiErrorMessage } from './core';

const normalizeTechnicianJob = (job) => ({
  ...job,
  service: job.service || job.service_type || 'Service',
  ticketId: job.ticketId || job.ticket_id || job.id,
  scheduledDate: job.scheduledDate || job.scheduled_date,
  address: job.address || job.location || '',
  status: String(job.status || '').toLowerCase().replace(/\s+/g, '_')
});

export const fetchTechnicianJobs = async (techName) => {
  try {
    const { data } = await api.get('/technician/jobs', { params: { techName } });
    const jobArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(jobArray) ? jobArray.map(normalizeTechnicianJob) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician jobs.'));
  }
};

export const fetchTechnicianSchedule = async (techName) => {
  try {
    const { data } = await api.get('/technician/schedule/', { params: { techName } });
    const scheduleArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(scheduleArray) ? scheduleArray.map(normalizeTechnicianJob) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician schedule.'));
  }
};

export const fetchTechnicianDashboard = async (techName) => {
  try {
    const { data } = await api.get('/technician/dashboard/', { params: { techName } });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician dashboard.'));
  }
};

export const fetchTechnicianProfile = async (techName) => {
  try {
    const { data } = await api.get('/technician/profile/', { params: { techName } });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician profile.'));
  }
};

export const updateTechnicianProfile = async (techNameOrPayload, updates) => {
  try {
    const resolvedUpdates = typeof techNameOrPayload === 'object' ? techNameOrPayload.updates : updates;
    const { data } = await api.put('/technician/profile/', resolvedUpdates);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update technician profile.'));
  }
};

export const fetchTechnicianHistory = async (techName) => {
  try {
    const { data } = await api.get('/technician/history/', { params: { techName } });
    const historyArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(historyArray) ? historyArray.map(normalizeTechnicianJob) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician history.'));
  }
};

export const updateJobStatus = async (jobId, status) => {
  try {
    const { data } = await api.post(`/technician/jobs/${jobId}/status/`, { status });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update job status.'));
  }
};

export const submitChecklist = async (checklist) => {
  try {
    const { data } = await api.post('/checklist/', checklist);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to submit checklist.'));
  }
};
