import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { fetchServiceTickets } from '../../api/api';

const convertToCSV = (rows) => {
  if (!rows.length) return '';
  const headers = Object.keys(rows[0]);
  const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const csv = [headers.join(','), ...rows.map(row => headers.map(h => escape(row[h])).join(','))].join('\n');
  return csv;
};

export default function AdminReports() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchServiceTickets()
      .then((res) => {
        setTickets(res || []);
        setError('');
      })
      .catch((err) => {
        setTickets([]);
        setError(err.message || 'Unable to load reports.');
      })
      .finally(() => setLoading(false));
  }, []);

  const downloadCSV = () => {
    const csv = convertToCSV(tickets);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `service-tickets-${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Layout>
      <h2 className="text-2xl font-bold mb-4">Reports</h2>
      <p className="text-slate-600">Generate and download operational reports.</p>

      <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="rounded-xl bg-white p-4 shadow-sm flex-1">
          <h3 className="text-lg font-semibold">Service Ticket Report</h3>
          <p className="text-sm text-slate-500">Contains ticket-level details for analysis and compliance.</p>
        </div>
        <button onClick={downloadCSV} className="rounded-xl bg-primary px-5 py-2 text-white shadow-lg hover:bg-blue-700 transition">
          Export Tickets CSV
        </button>
      </div>

      <div className="mt-6 rounded-xl bg-white p-4 shadow-sm overflow-x-auto">
        {error && <p className="mb-4 text-sm text-red-700">{error}</p>}
        {loading ? (
          <p>Loading tickets...</p>
        ) : tickets.length === 0 ? (
          <p>No service tickets to display.</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="p-2">ID</th>
                <th className="p-2">Client</th>
                <th className="p-2">Service</th>
                <th className="p-2">Status</th>
                <th className="p-2">Assigned</th>
                <th className="p-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id} className="border-t">
                  <td className="p-2">{ticket.id}</td>
                  <td className="p-2">{ticket.client}</td>
                  <td className="p-2">{ticket.service}</td>
                  <td className="p-2">{ticket.status}</td>
                  <td className="p-2">{ticket.assignedTech || '-'}</td>
                  <td className="p-2">{new Date(ticket.created).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
