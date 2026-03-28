import { api, getApiErrorMessage } from './core';

const mapTicketToRequest = (ticket) => ({
  id: ticket.id,
  request_id: ticket.request_details?.id ?? ticket.request,
  service_type: ticket.request_details?.service_type,
  service_type_name: ticket.request_details?.service_type_name,
  description: ticket.request_details?.description,
  status: String(ticket.status || ticket.request_details?.status || '')
    .toLowerCase()
    .replace(/\s+/g, '_'),
  request_status: String(ticket.request_details?.status || '')
    .toLowerCase()
    .replace(/\s+/g, '_'),
  priority: ticket.priority || ticket.request_details?.priority,
  address: ticket.request_details?.location?.address,
  city: ticket.request_details?.location?.city,
  province: ticket.request_details?.location?.province,
  latitude: ticket.request_details?.location?.latitude == null ? null : Number(ticket.request_details.location.latitude),
  longitude: ticket.request_details?.location?.longitude == null ? null : Number(ticket.request_details.location.longitude),
  request_date: ticket.request_details?.request_date,
  preferred_date: ticket.request_details?.preferred_date,
  preferred_time_slot: ticket.request_details?.preferred_time_slot,
  scheduling_notes: ticket.request_details?.scheduling_notes,
  scheduled_date: ticket.scheduled_date,
  scheduled_time: ticket.scheduled_time,
  scheduled_time_slot: ticket.scheduled_time_slot,
  start_time: ticket.start_time,
  end_time: ticket.end_time,
  completed_date: ticket.completed_date,
  technician_name: ticket.technician_name,
  technician_contact: ticket.technician_contact || '',
  client_rating: ticket.client_rating,
  client_feedback: ticket.client_feedback,
  reschedule_requested: Boolean(ticket.reschedule_requested),
  reschedule_reason: ticket.reschedule_reason,
  warranty_status: ticket.warranty_status || 'not_applicable',
  warranty_period_days: ticket.warranty_period_days,
  warranty_start_date: ticket.warranty_start_date,
  warranty_end_date: ticket.warranty_end_date,
  warranty_notes: ticket.warranty_notes,
  proof_media: Array.isArray(ticket.inspection?.proof_media) ? ticket.inspection.proof_media : [],
  progress: ticket.status === 'Completed' ? 100 : ticket.status === 'In Progress' ? 60 : 0
});

export const fetchClientRequests = async () => {
  try {
    const { data } = await api.get('/services/service-tickets/');
    const ticketArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return ticketArray.map(mapTicketToRequest);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load client requests.'));
  }
};

export const updateUserProfile = async (profileData) => {
  try {
    const { data } = await api.patch('/users/me/', profileData);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update user profile.'));
  }
};

export const changePassword = async (passwordData) => {
  try {
    const { data } = await api.post('/users/change_password/', {
      current_password: passwordData.currentPassword,
      new_password: passwordData.newPassword
    });
    return data;
  } catch (error) {
    if (error.response?.data?.error) {
      throw new Error(error.response.data.error);
    }
    throw new Error('Failed to change password');
  }
};

export const fetchRequestDetail = async (requestId) => {
  try {
    const { data } = await api.get(`/services/service-tickets/${requestId}/`);
    return mapTicketToRequest(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load request details.'));
  }
};

export const submitRequestRating = async (requestId, ratingData) => {
  try {
    const { data } = await api.post(`/services/service-tickets/${requestId}/submit_feedback/`, {
      rating: ratingData.rating,
      feedback: ratingData.feedback
    });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to submit request rating.'));
  }
};

export const requestTicketReschedule = async (requestId, schedulingData) => {
  try {
    const { data } = await api.post(`/services/service-tickets/${requestId}/request_reschedule/`, schedulingData);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to request a schedule change.'));
  }
};
