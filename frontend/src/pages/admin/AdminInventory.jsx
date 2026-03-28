import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { api } from '../../api/api';
import { FiAlertCircle, FiEdit3, FiPlus, FiRefreshCw, FiTrash2 } from 'react-icons/fi';

const STATUS_OPTIONS = [
  { value: 'available', label: 'Available' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'in_use', label: 'In Use' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'out_of_stock', label: 'Out of Stock' },
  { value: 'retired', label: 'Retired' }
];

const buildDefaultItem = (categoryId = '') => ({
  name: '',
  sku: '',
  category: categoryId,
  quantity: 0,
  minimum_stock: 10,
  status: 'available'
});

const extractList = (data) =>
  Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);

const normalizeCategory = (category) => ({
  id: category.id,
  name: category.name
});

const normalizeInventoryItem = (item) => ({
  ...item,
  category: Number(item?.category || 0) || '',
  category_name: item?.category_name || 'Uncategorized',
  quantity: Number(item?.quantity || 0),
  minimum_stock: Number(item?.minimum_stock || 0),
  available_quantity: Number(item?.available_quantity ?? item?.quantity ?? 0),
  is_low_stock: Boolean(item?.is_low_stock)
});

const statusColor = (status) => {
  switch (status) {
    case 'available':
      return 'bg-green-100 text-green-800';
    case 'reserved':
      return 'bg-blue-100 text-blue-800';
    case 'in_use':
      return 'bg-indigo-100 text-indigo-800';
    case 'maintenance':
      return 'bg-yellow-100 text-yellow-800';
    case 'out_of_stock':
      return 'bg-red-100 text-red-800';
    case 'retired':
      return 'bg-slate-200 text-slate-700';
    default:
      return 'bg-slate-100 text-slate-800';
  }
};

const getApiErrorMessage = (error, fallback) => {
  const data = error?.response?.data;

  if (typeof data === 'string' && data.trim()) {
    return data;
  }

  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat().find(Boolean);
    if (firstError) {
      return Array.isArray(firstError) ? firstError[0] : String(firstError);
    }
  }

  return fallback;
};

export default function AdminInventory() {
  const [inventory, setInventory] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState(buildDefaultItem());
  const [editingId, setEditingId] = useState(null);
  const [editingItem, setEditingItem] = useState(buildDefaultItem());

  const getDefaultCategoryId = (categoryList = categories) => categoryList[0]?.id || '';

  const resetEditor = (categoryId = getDefaultCategoryId()) => {
    setAdding(false);
    setEditingId(null);
    setNewItem(buildDefaultItem(categoryId));
    setEditingItem(buildDefaultItem(categoryId));
  };

  const loadCategories = async () => {
    const { data } = await api.get('/inventory/categories/');
    let categoryList = extractList(data).map(normalizeCategory);

    if (categoryList.length === 0) {
      const created = await api.post('/inventory/categories/', {
        name: 'General',
        description: 'Default inventory category'
      });
      categoryList = [normalizeCategory(created.data)];
    }

    setCategories(categoryList);
    return categoryList;
  };

  const loadInventory = async () => {
    const { data } = await api.get('/inventory/items/');
    return extractList(data).map(normalizeInventoryItem);
  };

  const loadData = async () => {
    setLoading(true);
    setError('');

    try {
      const categoryList = await loadCategories();
      const items = await loadInventory();
      const defaultCategoryId = getDefaultCategoryId(categoryList);

      setInventory(items);
      setNewItem((current) => (current.category ? current : buildDefaultItem(defaultCategoryId)));
      setEditingItem((current) => (current.category ? current : buildDefaultItem(defaultCategoryId)));
    } catch (loadError) {
      setError(getApiErrorMessage(loadError, 'Failed to load inventory. Please try again.'));
      setInventory([]);
      setCategories([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const buildPayload = (item) => ({
    name: item.name,
    sku: item.sku,
    category: Number(item.category),
    quantity: Number(item.quantity || 0),
    minimum_stock: Number(item.minimum_stock || 0),
    status: item.status
  });

  const addItem = async () => {
    try {
      const { data } = await api.post('/inventory/items/', buildPayload(newItem));
      const defaultCategoryId = getDefaultCategoryId();
      setInventory((current) => [...current, normalizeInventoryItem(data)]);
      setNewItem(buildDefaultItem(defaultCategoryId));
      setAdding(false);
      setError('');
    } catch (addError) {
      setError(getApiErrorMessage(addError, 'Failed to add item. Please try again.'));
    }
  };

  const updateItem = async (id) => {
    try {
      const { data } = await api.patch(`/inventory/items/${id}/`, buildPayload(editingItem));
      setInventory((current) =>
        current.map((item) => (item.id === id ? normalizeInventoryItem({ ...item, ...data }) : item))
      );
      resetEditor();
      setError('');
    } catch (updateError) {
      setError(getApiErrorMessage(updateError, 'Failed to update item. Please try again.'));
    }
  };

  const deleteItem = async (id) => {
    try {
      await api.delete(`/inventory/items/${id}/`);
      setInventory((current) => current.filter((item) => item.id !== id));
      setError('');
    } catch (deleteError) {
      setError(getApiErrorMessage(deleteError, 'Failed to delete item. Please try again.'));
    }
  };

  const lowStockItems = inventory.filter(
    (item) => item.is_low_stock || item.available_quantity <= item.minimum_stock
  );
  const categoryMissing = categories.length === 0;

  return (
    <Layout>
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900">Inventory Management</h2>
          <p className="mt-2 text-slate-600">Track stock levels, item categories, and replenishment risk.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1 rounded-xl p-3 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
          >
            <FiRefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => {
              setEditingId(null);
              setEditingItem(buildDefaultItem(getDefaultCategoryId()));
              setNewItem(buildDefaultItem(getDefaultCategoryId()));
              setAdding(true);
            }}
            disabled={categoryMissing}
            className="rounded-xl bg-emerald-500 px-8 py-3 font-semibold text-white shadow-lg transition hover:bg-emerald-600 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FiPlus size={18} className="ml-1 inline" /> Add Item
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <FiAlertCircle size={16} />
          {error}
          <button onClick={() => setError('')} className="ml-auto font-bold">
            &times;
          </button>
        </div>
      )}

      {categoryMissing && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Inventory categories are required before items can be created.
        </div>
      )}

      {(adding || editingId) && (
        <div className="mb-8 rounded-3xl border bg-white p-8 shadow-xl">
          <h3 className="mb-6 text-xl font-bold">{adding ? 'Add New Item' : 'Edit Item'}</h3>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-6">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Item Name</label>
              <input
                value={adding ? newItem.name : editingItem.name || ''}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, name: e.target.value })
                    : setEditingItem({ ...editingItem, name: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
                placeholder="Solar Panel 345W"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">SKU</label>
              <input
                value={adding ? newItem.sku : editingItem.sku || ''}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, sku: e.target.value })
                    : setEditingItem({ ...editingItem, sku: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
                placeholder="SP345"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Category</label>
              <select
                value={adding ? newItem.category : editingItem.category || ''}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, category: Number(e.target.value) || '' })
                    : setEditingItem({ ...editingItem, category: Number(e.target.value) || '' })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Quantity</label>
              <input
                type="number"
                value={adding ? newItem.quantity : editingItem.quantity || 0}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, quantity: parseInt(e.target.value, 10) || 0 })
                    : setEditingItem({ ...editingItem, quantity: parseInt(e.target.value, 10) || 0 })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Status</label>
              <select
                value={adding ? newItem.status : editingItem.status || 'available'}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, status: e.target.value })
                    : setEditingItem({ ...editingItem, status: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Min Stock</label>
              <input
                type="number"
                value={adding ? newItem.minimum_stock : editingItem.minimum_stock || 10}
                onChange={(e) =>
                  adding
                    ? setNewItem({ ...newItem, minimum_stock: parseInt(e.target.value, 10) || 10 })
                    : setEditingItem({ ...editingItem, minimum_stock: parseInt(e.target.value, 10) || 10 })
                }
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-8 flex gap-4">
            <button
              onClick={adding ? addItem : () => updateItem(editingId)}
              className="flex-1 rounded-2xl bg-emerald-500 px-8 py-4 font-semibold text-white shadow-lg transition-all hover:bg-emerald-600"
            >
              {adding ? 'Add Item' : 'Update Item'}
            </button>
            <button
              onClick={() => resetEditor()}
              className="flex-1 rounded-2xl border border-slate-300 bg-white px-8 py-4 font-semibold transition hover:border-slate-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-3xl border bg-white shadow-xl">
        <div className="border-b border-slate-200 p-8">
          <h3 className="text-2xl font-bold text-slate-900">Stock Overview ({inventory.length} items)</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-8 py-6 text-left text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Item
                </th>
                <th className="px-6 py-6 text-left text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Category
                </th>
                <th className="px-6 py-6 text-left text-sm font-semibold uppercase tracking-wide text-slate-900">
                  SKU
                </th>
                <th className="px-6 py-6 text-right text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Quantity
                </th>
                <th className="px-6 py-6 text-right text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Available
                </th>
                <th className="px-6 py-6 text-center text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Status
                </th>
                <th className="px-6 py-6 text-right text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Min Stock
                </th>
                <th className="px-6 py-6 text-center text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Last Updated
                </th>
                <th className="px-6 py-6 text-right text-sm font-semibold uppercase tracking-wide text-slate-900">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-8 py-6 text-slate-600">
                    Loading inventory...
                  </td>
                </tr>
              ) : inventory.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-8 py-6 text-slate-600">
                    No inventory items found.
                  </td>
                </tr>
              ) : (
                inventory.map((item) => (
                  <tr key={item.id} className="transition hover:bg-slate-50">
                    <td className="px-8 py-6">
                      <div className="font-semibold text-slate-900">{item.name}</div>
                    </td>
                    <td className="px-6 py-6 text-sm text-slate-600">{item.category_name}</td>
                    <td className="px-6 py-6 text-sm text-slate-600">{item.sku || '-'}</td>
                    <td className="px-6 py-6 text-right">
                      <span
                        className={`font-mono text-2xl font-bold ${
                          item.quantity === 0
                            ? 'text-red-600'
                            : item.is_low_stock
                              ? 'text-orange-600'
                              : 'text-emerald-600'
                        }`}
                      >
                        {item.quantity}
                      </span>
                    </td>
                    <td className="px-6 py-6 text-right font-semibold text-slate-900">{item.available_quantity}</td>
                    <td className="px-6 py-6 text-center">
                      <span className={`rounded-full px-4 py-2 text-sm font-semibold ${statusColor(item.status)}`}>
                        {String(item.status || '').replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-6 text-right font-semibold text-slate-900">{item.minimum_stock}</td>
                    <td className="px-6 py-6 text-center text-sm text-slate-500">
                      {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="space-x-2 px-6 py-6 text-right">
                      <button
                        onClick={() => {
                          setAdding(false);
                          setEditingId(item.id);
                          setEditingItem(item);
                        }}
                        className="rounded-lg p-2 text-blue-500 transition hover:bg-blue-50 hover:text-blue-700"
                        title="Edit"
                      >
                        <FiEdit3 size={18} />
                      </button>
                      <button
                        onClick={() => deleteItem(item.id)}
                        className="rounded-lg p-2 text-red-500 transition hover:bg-red-50 hover:text-red-700"
                        title="Delete"
                      >
                        <FiTrash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {lowStockItems.length > 0 && (
        <div className="mt-8 rounded-3xl bg-gradient-to-r from-yellow-500 to-orange-500 p-8 text-white shadow-2xl">
          <h4 className="mb-2 text-xl font-bold">Low Stock Alert</h4>
          <p>{lowStockItems.length} items need replenishment.</p>
        </div>
      )}
    </Layout>
  );
}
