import {
  api,
  buildUserCreatePayload,
  buildUserUpdatePayload,
  getApiErrorMessage,
  normalizeTechnicianStatus,
  normalizeUser
} from './core';

export const fetchAdminUsers = async () => {
  try {
    const { data } = await api.get('/admin/users/');
    const userArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(userArray) ? userArray.map(normalizeUser) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load admin users.'));
  }
};

export const createAdminUser = async (userData) => {
  try {
    const payload = buildUserCreatePayload(userData);
    const { data } = await api.post('/admin/users/', payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create user.'));
  }
};

export const updateAdminUser = async (userId, updates) => {
  try {
    const payload = buildUserUpdatePayload(updates);
    const { data } = await api.put(`/admin/users/${userId}/`, payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update user.'));
  }
};

export const deactivateAdminUser = async (userId) => {
  try {
    const { data } = await api.delete(`/admin/users/${userId}/`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to deactivate user.'));
  }
};

export const fetchAdminClients = async () => {
  try {
    const { data } = await api.get('/admin/clients/');
    const clientArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(clientArray) ? clientArray.map(normalizeUser) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load admin clients.'));
  }
};

export const createAdminClient = async (client) => {
  try {
    const payload = {
      ...buildUserCreatePayload(client),
      role: 'client'
    };
    const { data } = await api.post('/admin/clients/', payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create client.'));
  }
};

export const updateAdminClient = async (id, updates) => {
  try {
    const payload = buildUserUpdatePayload(updates);
    const { data } = await api.put(`/admin/clients/${id}/`, payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update client.'));
  }
};

export const deleteAdminClient = async (id) => {
  try {
    const { data } = await api.delete(`/admin/clients/${id}/`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to delete client.'));
  }
};

export const fetchAdminTechnicians = async () => {
  try {
    const { data } = await api.get('/admin/technicians/');
    const techArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(techArray)
      ? techArray.map((tech) => ({
          ...normalizeUser(tech),
          status: normalizeTechnicianStatus(tech),
          skills: Array.isArray(tech.skills) ? tech.skills : [],
          skill: tech.skill
            ? String(tech.skill).toLowerCase().replace(/\s+/g, '_')
            : (Array.isArray(tech.skills) && tech.skills.length > 0
                ? String(tech.skills[0]).toLowerCase().replace(/\s+/g, '_')
                : '')
        }))
      : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load technicians.'));
  }
};

export const createAdminTechnician = async (tech) => {
  try {
    const payload = {
      ...buildUserCreatePayload(tech),
      role: 'technician',
      status: tech.status === 'offline' ? 'inactive' : 'active',
      is_available: tech.status === 'available',
      current_latitude: tech.lat === '' ? null : tech.lat,
      current_longitude: tech.lng === '' ? null : tech.lng
    };
    const { data } = await api.post('/admin/technicians/', payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create technician.'));
  }
};

export const updateAdminTechnician = async (id, updates) => {
  try {
    const payload = buildUserUpdatePayload({
      ...updates,
      technicianStatus: updates.status
    });
    const { data } = await api.put(`/admin/technicians/${id}/`, payload);
    return normalizeUser(data);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update technician.'));
  }
};

export const deleteAdminTechnician = async (id) => {
  try {
    const { data } = await api.delete(`/admin/technicians/${id}/`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to delete technician.'));
  }
};

export const assignTechnician = async ({ ticketId, technicianId, technicianName }) => {
  try {
    let resolvedTechnicianId = technicianId;
    if (!resolvedTechnicianId && technicianName) {
      const technicians = await fetchAdminTechnicians();
      resolvedTechnicianId = technicians.find((tech) => tech.name === technicianName)?.id;
    }
    if (!resolvedTechnicianId) {
      throw new Error('Please select a valid technician.');
    }
    const { data } = await api.post(`/services/service-tickets/${ticketId}/assign/`, {
      technician_id: resolvedTechnicianId
    });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to assign technician.'));
  }
};

export const autoAssignTechnician = async ({ ticketId }) => {
  try {
    const { data } = await api.post(`/services/service-tickets/${ticketId}/auto_assign/`, {});
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to auto-assign technician.'));
  }
};

export const fetchAdminSettings = async () => {
  try {
    const { data } = await api.get('/admin/settings/');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load admin settings.'));
  }
};

export const updateAdminSettings = async (settings) => {
  try {
    const { data } = await api.put('/admin/settings/', settings);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update admin settings.'));
  }
};

export const fetchServices = async () => {
  try {
    const { data } = await api.get('/admin/services/');
    const serviceArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(serviceArray)
      ? serviceArray.map((service) => ({
          ...service,
          estimated_duration: Number(service?.estimated_duration || 0)
        }))
      : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load services.'));
  }
};

export const createService = async (service) => {
  try {
    const payload = {
      name: service.name,
      description: service.description,
      estimated_duration: Number(service.estimated_duration || 0)
    };
    const { data } = await api.post('/admin/services/', payload);
    return {
      ...data,
      estimated_duration: Number(data?.estimated_duration || 0)
    };
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create service.'));
  }
};

export const updateService = async (id, updates) => {
  try {
    const payload = {
      name: updates.name,
      description: updates.description,
      estimated_duration: Number(updates.estimated_duration || 0)
    };
    const { data } = await api.put(`/admin/services/${id}/`, payload);
    return {
      ...data,
      estimated_duration: Number(data?.estimated_duration || 0)
    };
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update service.'));
  }
};

export const deleteService = async (id) => {
  try {
    const { data } = await api.delete(`/admin/services/${id}/`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to delete service.'));
  }
};

export const fetchAdminAnalytics = async () => {
  try {
    const { data } = await api.get('/admin/analytics/');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load admin analytics.'));
  }
};

export const fetchInventory = async () => {
  try {
    const { data } = await api.get('/inventory/items/');
    const inventoryArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(inventoryArray) ? inventoryArray : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load inventory.'));
  }
};

export const fetchServiceInventoryRequirements = async () => {
  try {
    const { data } = await api.get('/inventory/service-type-requirements/');
    const requirementArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(requirementArray) ? requirementArray : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load service inventory requirements.'));
  }
};

export const createServiceInventoryRequirement = async (requirement) => {
  try {
    const payload = {
      service_type: Number(requirement.service_type),
      item: Number(requirement.item),
      quantity: Number(requirement.quantity || 0),
      auto_reserve: requirement.auto_reserve !== false,
      notes: requirement.notes || ''
    };
    const { data } = await api.post('/inventory/service-type-requirements/', payload);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to create inventory requirement.'));
  }
};

export const updateServiceInventoryRequirement = async (id, requirement) => {
  try {
    const payload = {
      service_type: Number(requirement.service_type),
      item: Number(requirement.item),
      quantity: Number(requirement.quantity || 0),
      auto_reserve: requirement.auto_reserve !== false,
      notes: requirement.notes || ''
    };
    const { data } = await api.put(`/inventory/service-type-requirements/${id}/`, payload);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to update inventory requirement.'));
  }
};

export const deleteServiceInventoryRequirement = async (id) => {
  try {
    await api.delete(`/inventory/service-type-requirements/${id}/`);
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to delete inventory requirement.'));
  }
};
