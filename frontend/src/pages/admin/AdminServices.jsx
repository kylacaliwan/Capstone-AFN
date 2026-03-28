import { useEffect, useMemo, useState } from 'react';
import Layout from '../../components/Layout';
import {
  createService,
  createServiceInventoryRequirement,
  deleteService,
  deleteServiceInventoryRequirement,
  fetchInventory,
  fetchServiceInventoryRequirements,
  fetchServices,
  updateService,
  updateServiceInventoryRequirement
} from '../../api/api';

const DEFAULT_SERVICE_FORM = {
  name: '',
  description: '',
  estimated_duration: 60
};

const DEFAULT_REQUIREMENT_FORM = {
  service_type: '',
  item: '',
  quantity: 1,
  auto_reserve: true,
  notes: ''
};

const toServiceFormState = (service) => ({
  name: service?.name || '',
  description: service?.description || '',
  estimated_duration: Number(service?.estimated_duration || 60)
});

const toRequirementFormState = (requirement) => ({
  service_type: Number(requirement?.service_type || 0) || '',
  item: Number(requirement?.item || 0) || '',
  quantity: Number(requirement?.quantity || 1),
  auto_reserve: requirement?.auto_reserve !== false,
  notes: requirement?.notes || ''
});

const formatDuration = (minutes) => {
  const safeMinutes = Number(minutes || 0);
  const hours = Math.floor(safeMinutes / 60);
  const remainder = safeMinutes % 60;

  if (hours > 0 && remainder > 0) return `${hours}h ${remainder}m`;
  if (hours > 0) return `${hours}h`;
  return `${safeMinutes}m`;
};

const normalizeRequirement = (requirement) => ({
  ...requirement,
  service_type: Number(requirement?.service_type || 0) || '',
  item: Number(requirement?.item || 0) || '',
  quantity: Number(requirement?.quantity || 0),
  available_quantity: Number(requirement?.available_quantity || 0)
});

export default function AdminServices() {
  const [services, setServices] = useState([]);
  const [inventoryItems, setInventoryItems] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingService, setEditingService] = useState(null);
  const [editingRequirementId, setEditingRequirementId] = useState(null);
  const [serviceFormData, setServiceFormData] = useState(DEFAULT_SERVICE_FORM);
  const [requirementFormData, setRequirementFormData] = useState(DEFAULT_REQUIREMENT_FORM);
  const [feedback, setFeedback] = useState('');

  const serviceRequirementCounts = useMemo(() => {
    return requirements.reduce((counts, requirement) => {
      const key = Number(requirement.service_type || 0);
      counts[key] = (counts[key] || 0) + 1;
      return counts;
    }, {});
  }, [requirements]);

  const groupedRequirements = useMemo(() => {
    return services.map((service) => ({
      service,
      requirements: requirements.filter((requirement) => Number(requirement.service_type) === Number(service.id))
    }));
  }, [requirements, services]);

  const resetServiceForm = () => setServiceFormData(DEFAULT_SERVICE_FORM);

  const resetRequirementForm = (serviceList = services, itemList = inventoryItems) => {
    setEditingRequirementId(null);
    setRequirementFormData({
      ...DEFAULT_REQUIREMENT_FORM,
      service_type: serviceList[0]?.id || '',
      item: itemList[0]?.id || ''
    });
  };

  const load = async () => {
    setLoading(true);
    try {
      const [serviceList, inventoryList, requirementList] = await Promise.all([
        fetchServices(),
        fetchInventory(),
        fetchServiceInventoryRequirements()
      ]);
      const normalizedRequirements = requirementList.map(normalizeRequirement);

      setServices(serviceList);
      setInventoryItems(inventoryList);
      setRequirements(normalizedRequirements);
      setRequirementFormData((current) => ({
        ...current,
        service_type: current.service_type || serviceList[0]?.id || '',
        item: current.item || inventoryList[0]?.id || ''
      }));
    } catch (error) {
      setServices([]);
      setInventoryItems([]);
      setRequirements([]);
      setFeedback(error.message || 'Unable to load services.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onSaveService = async () => {
    try {
      if (editingService) {
        await updateService(editingService.id, serviceFormData);
        setFeedback('Service updated.');
      } else {
        await createService(serviceFormData);
        setFeedback('Service created.');
      }
      setEditingService(null);
      resetServiceForm();
      await load();
    } catch (error) {
      setFeedback(error.message || 'Error saving service.');
    }
  };

  const onDeleteService = async (id) => {
    if (!window.confirm('Remove this service?')) return;

    try {
      await deleteService(id);
      setFeedback('Service deleted.');
      await load();
    } catch (error) {
      setFeedback(error.message || 'Error deleting service.');
    }
  };

  const onSaveRequirement = async () => {
    try {
      if (editingRequirementId) {
        await updateServiceInventoryRequirement(editingRequirementId, requirementFormData);
        setFeedback('Auto-inventory template updated.');
      } else {
        await createServiceInventoryRequirement(requirementFormData);
        setFeedback('Auto-inventory template created.');
      }
      resetRequirementForm();
      await load();
    } catch (error) {
      setFeedback(error.message || 'Error saving auto-inventory template.');
    }
  };

  const onDeleteRequirement = async (id) => {
    if (!window.confirm('Remove this auto-inventory template?')) return;

    try {
      await deleteServiceInventoryRequirement(id);
      setFeedback('Auto-inventory template deleted.');
      if (editingRequirementId === id) {
        resetRequirementForm();
      }
      await load();
    } catch (error) {
      setFeedback(error.message || 'Error deleting auto-inventory template.');
    }
  };

  const canManageRequirements = services.length > 0 && inventoryItems.length > 0;

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Services Catalog</h2>
          <p className="text-slate-600">
            Manage service types and define the inventory they should reserve automatically when tickets are assigned.
          </p>
        </div>
        <div className="text-sm text-teal-700">{feedback}</div>
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold">{editingService ? 'Edit Service' : 'Add Service'}</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <input
            className="rounded-xl border p-2"
            placeholder="Name"
            value={serviceFormData.name}
            onChange={(e) => setServiceFormData({ ...serviceFormData, name: e.target.value })}
          />
          <input
            type="number"
            min="0"
            className="rounded-xl border p-2"
            placeholder="Estimated Duration (minutes)"
            value={serviceFormData.estimated_duration}
            onChange={(e) =>
              setServiceFormData({ ...serviceFormData, estimated_duration: Number(e.target.value) || 0 })
            }
          />
          <textarea
            className="rounded-xl border p-2 md:col-span-2"
            placeholder="Description"
            value={serviceFormData.description}
            onChange={(e) => setServiceFormData({ ...serviceFormData, description: e.target.value })}
          />
        </div>
        <div className="mt-4 flex gap-2">
          <button className="rounded-xl bg-primary px-4 py-2 text-white" onClick={onSaveService}>
            {editingService ? 'Update' : 'Create'}
          </button>
          <button
            className="rounded-xl bg-slate-200 px-4 py-2"
            onClick={() => {
              resetServiceForm();
              setEditingService(null);
              setFeedback('');
            }}
          >
            Cancel
          </button>
        </div>
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Auto Inventory Templates</h3>
            <p className="text-sm text-slate-600">
              Each template reserves stock automatically when a technician gets a matching ticket.
            </p>
          </div>
          {!canManageRequirements && (
            <div className="text-sm text-amber-700">
              Add at least one service and one inventory item to create templates.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <select
            className="rounded-xl border p-2"
            value={requirementFormData.service_type}
            onChange={(e) => setRequirementFormData({ ...requirementFormData, service_type: Number(e.target.value) || '' })}
            disabled={!canManageRequirements}
          >
            {services.map((service) => (
              <option key={service.id} value={service.id}>
                {service.name}
              </option>
            ))}
          </select>
          <select
            className="rounded-xl border p-2"
            value={requirementFormData.item}
            onChange={(e) => setRequirementFormData({ ...requirementFormData, item: Number(e.target.value) || '' })}
            disabled={!canManageRequirements}
          >
            {inventoryItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.sku || 'No SKU'}) - {item.available_quantity ?? item.quantity ?? 0} available
              </option>
            ))}
          </select>
          <input
            type="number"
            min="1"
            className="rounded-xl border p-2"
            placeholder="Quantity"
            value={requirementFormData.quantity}
            onChange={(e) =>
              setRequirementFormData({ ...requirementFormData, quantity: Number(e.target.value) || 1 })
            }
            disabled={!canManageRequirements}
          />
          <input
            className="rounded-xl border p-2"
            placeholder="Notes (optional)"
            value={requirementFormData.notes}
            onChange={(e) => setRequirementFormData({ ...requirementFormData, notes: e.target.value })}
            disabled={!canManageRequirements}
          />
          <label className="flex items-center gap-3 rounded-xl border px-4 py-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={requirementFormData.auto_reserve}
              onChange={(e) =>
                setRequirementFormData({ ...requirementFormData, auto_reserve: e.target.checked })
              }
              disabled={!canManageRequirements}
            />
            Auto reserve on assignment
          </label>
        </div>

        <div className="mt-4 flex gap-2">
          <button
            className="rounded-xl bg-emerald-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onSaveRequirement}
            disabled={!canManageRequirements}
          >
            {editingRequirementId ? 'Update Template' : 'Add Template'}
          </button>
          <button
            className="rounded-xl bg-slate-200 px-4 py-2"
            onClick={() => resetRequirementForm()}
          >
            Cancel
          </button>
        </div>
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold">Services list</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Description</th>
                <th className="p-3">Estimated Duration</th>
                <th className="p-3">Auto Inventory</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-3">Loading...</td>
                </tr>
              ) : services.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-3">No services found.</td>
                </tr>
              ) : (
                services.map((service) => (
                  <tr key={service.id} className="border-t">
                    <td className="p-3">{service.name}</td>
                    <td className="p-3">{service.description || '-'}</td>
                    <td className="p-3">{formatDuration(service.estimated_duration)}</td>
                    <td className="p-3">{serviceRequirementCounts[service.id] || 0} template(s)</td>
                    <td className="flex gap-2 p-3">
                      <button
                        className="text-blue-600"
                        onClick={() => {
                          setEditingService(service);
                          setServiceFormData(toServiceFormState(service));
                          setFeedback('');
                        }}
                      >
                        Edit
                      </button>
                      <button className="text-red-600" onClick={() => onDeleteService(service.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold">Requirement Matrix</h3>
        {loading ? (
          <div className="text-slate-600">Loading templates...</div>
        ) : groupedRequirements.length === 0 ? (
          <div className="text-slate-600">No services available yet.</div>
        ) : (
          <div className="space-y-6">
            {groupedRequirements.map(({ service, requirements: serviceRequirements }) => (
              <div key={service.id} className="rounded-xl border border-slate-200">
                <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                  <div>
                    <div className="font-semibold text-slate-900">{service.name}</div>
                    <div className="text-sm text-slate-500">
                      {serviceRequirements.length === 0
                        ? 'No auto-inventory templates yet.'
                        : `${serviceRequirements.length} item template(s) configured.`}
                    </div>
                  </div>
                </div>
                {serviceRequirements.length === 0 ? (
                  <div className="px-4 py-4 text-sm text-slate-500">Nothing configured for this service.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead className="bg-slate-50 text-left text-sm text-slate-600">
                        <tr>
                          <th className="p-3">Item</th>
                          <th className="p-3">Quantity</th>
                          <th className="p-3">Available</th>
                          <th className="p-3">Mode</th>
                          <th className="p-3">Notes</th>
                          <th className="p-3">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {serviceRequirements.map((requirement) => (
                          <tr key={requirement.id} className="border-t border-slate-100 text-sm">
                            <td className="p-3">
                              <div className="font-medium text-slate-900">{requirement.item_name}</div>
                              <div className="text-slate-500">{requirement.item_sku || 'No SKU'}</div>
                            </td>
                            <td className="p-3">{requirement.quantity}</td>
                            <td className="p-3">{requirement.available_quantity}</td>
                            <td className="p-3">{requirement.auto_reserve ? 'Auto reserve' : 'Manual only'}</td>
                            <td className="p-3">{requirement.notes || '-'}</td>
                            <td className="flex gap-2 p-3">
                              <button
                                className="text-blue-600"
                                onClick={() => {
                                  setEditingRequirementId(requirement.id);
                                  setRequirementFormData(toRequirementFormState(requirement));
                                  setFeedback('');
                                }}
                              >
                                Edit
                              </button>
                              <button
                                className="text-red-600"
                                onClick={() => onDeleteRequirement(requirement.id)}
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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
