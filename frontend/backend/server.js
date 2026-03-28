import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import nodemailer from 'nodemailer';
dotenv.config();
import {
  getStats,
  getTickets,
  getTechnicians,
  getTracking,
  getClients,
  getInventory,
  assignTechnician,
  updateTicketStatus,
  createServiceRequest,
  // New technician functions
  getTechnicianDashboard,
  getTechnicianJobs,
  updateJobStatus,
  getTechnicianSchedule,
  getNavigationRoute,
  submitChecklist,
  getMessages,
  sendMessage,
  getTechnicianHistory,
  getTechnicianProfile,
  updateTechnicianProfile,
  updateTechnicianLocation
} from './db.js';

const app = express();
app.use(cors());
app.use(express.json());

const requireRole = (requiredRole) => (req, res, next) => {
  const userRole = (req.headers['x-user-role'] || '').toLowerCase();
  if (!userRole) return res.status(401).json({ error: 'Missing x-user-role header.' });
  if (userRole !== requiredRole.toLowerCase()) return res.status(403).json({ error: 'Forbidden. Role mismatch.' });
  next();
};

const sendAssignmentEmail = async (ticket, technicianName) => {
  if (!ticket) return;
  const subject = `Service Ticket #${ticket.id} Assigned`;
  const body = `Ticket ${ticket.id} (${ticket.service}) assigned to ${technicianName}. Status: ${ticket.status}.`;
  // Setup nodemailer
  const transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST,
    port: Number(process.env.EMAIL_PORT),
    secure: false,
    auth: {
      user: process.env.EMAIL_HOST_USER,
      pass: process.env.EMAIL_HOST_PASSWORD
    }
  });
  // Send to client
  if (process.env.EMAIL_HOST_USER && ticket.client) {
    await transporter.sendMail({
      from: process.env.EMAIL_HOST_USER,
      to: ticket.client,
      subject,
      text: body
    });
  }
  // Send to technician (simulate email as username)
  await transporter.sendMail({
    from: process.env.EMAIL_HOST_USER,
    to: technicianName,
    subject,
    text: body
  });
  console.log(`Email sent: ${subject}`);
};

// Existing endpoints
app.get('/api/dashboard/stats', (req, res) => {
  try {
    const stats = getStats();
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: 'Failed to load stats.' });
  }
});

app.get('/api/service-tickets', (req, res) => {
  try {
    res.json(getTickets());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load tickets.' });
  }
});

app.post('/api/service-tickets/assign', requireRole('supervisor'), (req, res) => {
  const { ticketId, technicianName } = req.body;
  try {
    const ticket = getTickets().find(t => Number(t.id) === Number(ticketId));
    const ok = assignTechnician(ticketId, technicianName);
    if (!ok) return res.status(404).json({ error: 'Ticket or technician not found.' });
    sendAssignmentEmail(ticket, technicianName);
    res.json({ success: true });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Assignment failed.' });
  }
});

app.post('/api/tickets/:id/status', (req, res) => {
  const ticketId = Number(req.params.id);
  const { status } = req.body;
  try {
    updateTicketStatus(ticketId, status);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update ticket status.' });
  }
});

app.get('/api/technicians', (req, res) => {
  try {
    res.json(getTechnicians());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load technicians.' });
  }
});

app.get('/api/tracking', (req, res) => {
  try {
    res.json(getTracking());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load tracking data.' });
  }
});

app.get('/api/clients', (req, res) => {
  try {
    res.json(getClients());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load clients.' });
  }
});

app.get('/api/inventory', (req, res) => {
  try {
    res.json(getInventory());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load inventory.' });
  }
});

// Admin CRUD endpoints
app.get('/api/admin/technicians', requireRole('admin'), (req, res) => {
  try {
    res.json(getAdminTechnicians());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load technicians.' });
  }
});

app.post('/api/admin/technicians', (req, res) => {
  try {
    const tech = addAdminTechnician(req.body);
    res.json({ success: true, technician: tech });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create technician.' });
  }
});

app.put('/api/admin/technicians/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    updateAdminTechnician(id, req.body);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update technician.' });
  }
});

app.delete('/api/admin/technicians/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    deleteAdminTechnician(id);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete technician.' });
  }
});

app.get('/api/admin/clients', requireRole('admin'), (req, res) => {
  try {
    res.json(getAdminClients());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load clients.' });
  }
});

app.post('/api/admin/clients', (req, res) => {
  try {
    const client = addAdminClient(req.body);
    res.json({ success: true, client });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create client.' });
  }
});

app.put('/api/admin/clients/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    updateAdminClient(id, req.body);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update client.' });
  }
});

app.delete('/api/admin/clients/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    deleteAdminClient(id);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete client.' });
  }
});

app.get('/api/services', requireRole('admin'), (req, res) => {
  try {
    res.json(getServices());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load services.' });
  }
});

app.post('/api/services', (req, res) => {
  try {
    const service = addService(req.body);
    res.json({ success: true, service });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create service.' });
  }
});

app.put('/api/services/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    updateService(id, req.body);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update service.' });
  }
});

app.delete('/api/services/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    deleteService(id);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete service.' });
  }
});

app.get('/api/admin/analytics', requireRole('admin'), (req, res) => {
  try {
    res.json(getAdminAnalytics());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load analytics.' });
  }
});

app.get('/api/admin/users', requireRole('admin'), (req, res) => {
  try {
    res.json(getUsers());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load users.' });
  }
});

app.post('/api/admin/users', (req, res) => {
  try {
    const { username, role, email, phone } = req.body;
    createUser(username, role, email, phone);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create user.' });
  }
});

app.put('/api/admin/users/:id', (req, res) => {
  const id = Number(req.params.id);
  try {
    updateUser(id, req.body);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update user.' });
  }
});

app.post('/api/admin/users/:id/deactivate', (req, res) => {
  const id = Number(req.params.id);
  try {
    deactivateUser(id);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to deactivate user.' });
  }
});

app.get('/api/admin/settings', requireRole('admin'), (req, res) => {
  try {
    res.json(getAdminSettings());
  } catch (error) {
    res.status(500).json({ error: 'Failed to load settings.' });
  }
});

app.put('/api/admin/settings', requireRole('admin'), (req, res) => {
  try {
    updateAdminSettings(req.body);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update settings.' });
  }
});

app.post('/api/service-requests', (req, res) => {
  const { client, service, notes, lat, lng, locationDesc } = req.body;
  try {
    const ticketId = createServiceRequest(client, service, notes, lat, lng, locationDesc);
    res.json({ success: true, ticketId });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create service request.' });
  }
});

// New Technician Dashboard endpoints
app.get('/api/technician/dashboard', (req, res) => {
  const { techName } = req.query;
  try {
    const stats = getTechnicianDashboard(techName || 'Ade Johnson');
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: 'Failed to load dashboard.' });
  }
});

app.get('/api/technician/jobs', (req, res) => {
  const { techName } = req.query;
  try {
    res.json(getTechnicianJobs(techName || 'Ade Johnson'));
  } catch (error) {
    res.status(500).json({ error: 'Failed to load jobs.' });
  }
});

app.put('/api/jobs/update-status', (req, res) => {
  const { jobId, status } = req.body;
  try {
    updateJobStatus(jobId, status);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update job status.' });
  }
});

app.get('/api/technician/schedule', (req, res) => {
  const { techName } = req.query;
  try {
    res.json(getTechnicianSchedule(techName || 'Ade Johnson'));
  } catch (error) {
    res.status(500).json({ error: 'Failed to load schedule.' });
  }
});

app.get('/api/navigation/route', (req, res) => {
  const { techLat, techLng, jobLat, jobLng } = req.query;
  try {
    const route = getNavigationRoute(parseFloat(techLat), parseFloat(techLng), parseFloat(jobLat), parseFloat(jobLng));
    res.json(route);
  } catch (error) {
    res.status(500).json({ error: 'Failed to calculate route.' });
  }
});

app.post('/api/jobs/checklist', (req, res) => {
  const { jobId, serviceType, completed, notes, photos } = req.body;
  try {
    submitChecklist(jobId, serviceType, completed, notes, photos);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to submit checklist.' });
  }
});

app.get('/api/messages', (req, res) => {
  const { receiverRole, receiverName } = req.query;
  try {
    res.json(getMessages(receiverRole, receiverName || 'Ade Johnson'));
  } catch (error) {
    res.status(500).json({ error: 'Failed to load messages.' });
  }
});

app.post('/api/messages/send', (req, res) => {
  const { sender, receiverRole, receiverName, text } = req.body;
  try {
    sendMessage(sender, receiverRole, receiverName, text);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to send message.' });
  }
});

app.get('/api/technician/history', (req, res) => {
  const { techName } = req.query;
  try {
    res.json(getTechnicianHistory(techName || 'Ade Johnson'));
  } catch (error) {
    res.status(500).json({ error: 'Failed to load history.' });
  }
});

app.get('/api/technician/profile', (req, res) => {
  const { techName } = req.query;
  try {
    res.json(getTechnicianProfile(techName || 'Ade Johnson'));
  } catch (error) {
    res.status(500).json({ error: 'Failed to load profile.' });
  }
});

app.put('/api/technician/update-profile', (req, res) => {
  const { techName, updates } = req.body;
  try {
    updateTechnicianProfile(techName || 'Ade Johnson', updates);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update profile.' });
  }
});

app.post('/api/technician/location', (req, res) => {
  const { techName, lat, lng } = req.body;
  try {
    updateTechnicianLocation(techName, parseFloat(lat), parseFloat(lng));
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update location.' });
  }
});

app.listen(4000, () => {
  console.log('Backend API server running at http://localhost:4000');
});

