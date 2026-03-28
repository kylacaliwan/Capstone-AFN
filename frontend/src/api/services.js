import { api, getApiErrorMessage, normalizeTicket } from './core';

const normalizeCoordinateValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return value;
  }

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return value;
  }

  return numericValue.toFixed(6);
};

const normalizeCoordinatePayload = (payload) => ({
  ...payload,
  latitude: normalizeCoordinateValue(payload.latitude),
  longitude: normalizeCoordinateValue(payload.longitude),
  lat: normalizeCoordinateValue(payload.lat),
  lng: normalizeCoordinateValue(payload.lng),
});

export const fetchNavigationRoute = async (techLat, techLng, jobLat, jobLng) => {
  try {
    const start = `${techLng},${techLat}`;
    const end = `${jobLng},${jobLat}`;
    const { data } = await api.get('/services/ors/route/', { params: { start, end } });

    if (!data?.features || data.features.length === 0) {
      throw new Error('No route found');
    }

    const feature = data.features[0];
    const geometry = feature?.geometry;
    const properties = feature?.properties;
    const coords = geometry?.coordinates || [];
    const routeCoords = coords.map(([lng, lat]) => [lat, lng]);

    const segments = properties?.segments || [{}];
    const primarySegment = segments[0];

    let directions = [];
    if (primarySegment.steps) {
      directions = primarySegment.steps.map((step) => ({
        instruction: step.instruction || 'Continue',
        distance: step.distance || 0,
        duration: step.duration || 0,
        type: step.type || 0,
        modifier: step.modifier || ''
      }));
    }

    const distanceKm = primarySegment.distance
      ? Number((primarySegment.distance / 1000).toFixed(1))
      : 0;
    const estimatedTimeMin = primarySegment.duration
      ? Math.round(primarySegment.duration / 60)
      : 0;

    return {
      distanceKm,
      estimatedTimeMin,
      routeCoords,
      directions
    };
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load navigation route.'));
  }
};

export const fetchDashboardStats = async (role) => {
  try {
    const { data } = await api.get('/dashboard/stats/', { params: { role } });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load dashboard statistics.'));
  }
};

export const updateTechnicianLocation = async ({ techName, lat, lng, accuracy }) => {
  try {
    const { data } = await api.post('/services/technician/location/', {
      latitude: lat,
      longitude: lng,
      accuracy
    });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update technician location.'));
  }
};

export const fetchServiceTickets = async () => {
  try {
    const { data } = await api.get('/services/service-tickets/');
    const ticketArray = Array.isArray(data) ? data : (data.results || []);
    return ticketArray.map(normalizeTicket);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load service tickets.'));
  }
};

export const fetchServiceTypes = async () => {
  try {
    const { data } = await api.get('/services/service-types/');
    const serviceTypes = Array.isArray(data) ? data : (data.results || []);
    return Array.isArray(serviceTypes) ? serviceTypes : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load service types.'));
  }
};

export const createServiceRequest = async (requestData) => {
  try {
    const payload = normalizeCoordinatePayload(requestData);
    const { data } = await api.post('/services/service-requests/', payload);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create service request.'));
  }
};

export const fetchCoverageHeatmap = async () => {
  try {
    const { data } = await api.get('/services/coverage-heatmap/service_density/');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load coverage heatmap.'));
  }
};

export const fetchFollowUpCases = async (filters = {}) => {
  try {
    const params = {};

    if (filters.status) {
      params.status = filters.status;
    }
    if (filters.caseType) {
      params.case_type = filters.caseType;
    }
    if (filters.assignedOnly) {
      params.assigned_only = 'true';
    }

    const { data } = await api.get('/services/follow-up-cases/', { params });
    const caseArray = Array.isArray(data) ? data : (data.results || []);
    return Array.isArray(caseArray) ? caseArray : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load follow-up cases.'));
  }
};

export const createFollowUpCase = async (caseData) => {
  try {
    const { data } = await api.post('/services/follow-up-cases/', caseData);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create follow-up case.'));
  }
};

export const updateFollowUpCase = async (caseId, updates) => {
  try {
    const { data } = await api.patch(`/services/follow-up-cases/${caseId}/`, updates);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update follow-up case.'));
  }
};

export const fetchTechnicianCoverage = async () => {
  try {
    const { data } = await api.get('/services/coverage-heatmap/technician_coverage/');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technician coverage.'));
  }
};

export const fetchTrackingData = async () => {
  try {
    const { data } = await api.get('/tracking');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load tracking data.'));
  }
};

export const getGoogleMapsUrl = ({ lat, lng, zoom = 14 }) =>
  `https://www.google.com/maps/search/?api=1&query=${lat},${lng}&zoom=${zoom}`;
