import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const db = new Database(`${__dirname}/database.sqlite`);

const init = () => {
  // Previous tables...
  db.prepare(`
    CREATE TABLE IF NOT EXISTS technicians (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE,
      status TEXT,
      lat REAL,
      lng REAL,
      currentJob TEXT,
      lastUpdate TEXT,
      skills TEXT
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS tickets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client TEXT,
      service TEXT,
      status TEXT,
      assignedTech TEXT,
      lat REAL,
      lng REAL,
      locationDesc TEXT,
      priority TEXT,
      created TEXT,
      notes TEXT
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS clients (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      email TEXT,
      totalJobs INTEGER,
      phone TEXT,
      address TEXT
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS inventory (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      item TEXT,
      quantity INTEGER,
      status TEXT,
      minStock INTEGER DEFAULT 10,
      lastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS technician_jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ticketId INTEGER,
      techName TEXT,
      status TEXT DEFAULT 'assigned',
      address TEXT,
      scheduledDate TEXT,
      priority TEXT,
      notes TEXT,
      FOREIGN KEY (ticketId) REFERENCES tickets (id)
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS checklists (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jobId INTEGER,
      serviceType TEXT,
      steps TEXT,
      completed JSON,
      techNotes TEXT,
      photos JSON,
      submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (jobId) REFERENCES technician_jobs (id)
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sender TEXT,
      receiverRole TEXT,
      receiverName TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      text TEXT
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS technician_profiles (
      techName TEXT PRIMARY KEY,
      phone TEXT,
      email TEXT,
      skills TEXT,
      totalCompleted INTEGER DEFAULT 0,
      avgCompletionTime TEXT,
      rating REAL DEFAULT 0
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS locations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      techName TEXT,
      lat REAL,
      lng REAL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `).run();

  // NEW for Admin
  db.prepare(`
    CREATE TABLE IF NOT EXISTS services (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE,
      description TEXT,
      price REAL,
      durationHours INTEGER,
      requiresSkills TEXT
    )
  `).run();

  db.prepare(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE,
      role TEXT,
      email TEXT,
      phone TEXT,
      active BOOLEAN DEFAULT 1,
      created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `).run();

  // Seed existing...
  const techCount = db.prepare('SELECT COUNT(*) as count FROM technicians').get().count;
  if (!techCount) {
    const insertTech = db.prepare('INSERT INTO technicians (name, status, lat, lng, currentJob, lastUpdate, skills) VALUES (?, ?, ?, ?, ?, ?, ?)');
    insertTech.run('Ade Johnson', 'available', 6.5244, 3.3792, null, '10 min ago', 'Solar,AC');
    insertTech.run('Aisha Bello', 'on_job', 6.4322, 3.4258, 'Ticket 102', '3 min ago', 'CCTV,Fire');
    insertTech.run('Samuel Peters', 'offline', 6.4655, 3.4064, null, '20 min ago', 'Solar,AC,Fire');
  }

  // Seed users from roles
  ['admin', 'supervisor', 'technician Ade Johnson', 'client'].forEach(u => {
    const exists = db.prepare('SELECT 1 FROM users WHERE username=?').get(u);
    if (!exists) {
      db.prepare('INSERT INTO users (username, role) VALUES (?, ?)').run(u, u.includes(' ') ? 'technician' : u.includes('client') ? 'client' : u);
    }
  });

  // Enhanced clients seed
  const clientCount = db.prepare('SELECT COUNT(*) as count FROM clients').get().count;
  if (clientCount < 3) {
    const insertClient = db.prepare('INSERT INTO clients (name, email, phone, address, totalJobs) VALUES (?, ?, ?, ?, ?)');
    insertClient.run('Greenfields Ltd', 'contact@greenfields.com', '+2348012345678', '12 Marina Lagos', 8);
    insertClient.run('Crest Hotel', 'info@cresthotel.com', '+2348098765432', '45 VI Lagos', 5);
    insertClient.run('Eko Estate', 'maint@eko.com', '+2348076543210', 'Eko Atlantic', 14);
  }

  // Services seed
  const serviceCount = db.prepare('SELECT COUNT(*) as count FROM services').get().count;
  if (!serviceCount) {
    const services = [
      ['Solar Installation', 'Complete rooftop solar system installation', 250000, 8, 'Solar'],
      ['CCTV Installation', '4K camera system with NVR', 150000, 6, 'CCTV'],
      ['Fire Detection Alarm Systems', 'Smoke/heat detectors + panel', 300000, 10, 'Fire'],
      ['Air Conditioning Services', 'Split AC install/service', 120000, 4, 'AC']
    ];
    const insertService = db.prepare('INSERT INTO services (name, description, price, durationHours, requiresSkills) VALUES (?, ?, ?, ?, ?)');
    services.forEach(s => insertService.run(...s));
  }

  // Existing seeds...
};

init();

// Existing functions + previous new...

// Admin new functions
const getAdminTechnicians = () => db.prepare(`
  SELECT t.*, p.totalCompleted, p.rating FROM technicians t 
  LEFT JOIN technician_profiles p ON t.name = p.techName
`).all();

const addAdminTechnician = ({ name, status, lat, lng, currentJob, skills }) => {
  const stmt = db.prepare('INSERT INTO technicians (name, status, lat, lng, currentJob, lastUpdate, skills) VALUES (?, ?, ?, ?, ?, datetime("now"), ?)');
  const info = stmt.run(name, status || 'available', lat || 0, lng || 0, currentJob || '', skills || '');
  return { id: info.lastInsertRowid, name, status, lat, lng, currentJob, skills };
};

const updateAdminTechnician = (id, updates) => {
  const set = Object.keys(updates).map(k => `${k}=?`).join(',');
  const values = [...Object.values(updates), id];
  db.prepare(`UPDATE technicians SET ${set}, lastUpdate=datetime("now") WHERE id=?`).run(...values);
  return true;
};

const deleteAdminTechnician = (id) => {
  db.prepare('DELETE FROM technicians WHERE id=?').run(id);
  return true;
};

const getAdminClients = () => db.prepare('SELECT * FROM clients').all();

const addAdminClient = ({ name, email, phone, address, totalJobs }) => {
  const stmt = db.prepare('INSERT INTO clients (name, email, phone, address, totalJobs) VALUES (?, ?, ?, ?, ?)');
  const info = stmt.run(name, email, phone, address, totalJobs || 0);
  return { id: info.lastInsertRowid, name, email, phone, address, totalJobs: totalJobs || 0 };
};

const updateAdminClient = (id, updates) => {
  const set = Object.keys(updates).map(k => `${k}=?`).join(',');
  const values = [...Object.values(updates), id];
  db.prepare(`UPDATE clients SET ${set} WHERE id=?`).run(...values);
  return true;
};

const deleteAdminClient = (id) => {
  db.prepare('DELETE FROM clients WHERE id=?').run(id);
  return true;
};

const getServices = () => db.prepare('SELECT * FROM services ORDER BY name').all();

const addService = ({ name, description, price, durationHours, requiresSkills }) => {
  const stmt = db.prepare('INSERT INTO services (name, description, price, durationHours, requiresSkills) VALUES (?, ?, ?, ?, ?)');
  const info = stmt.run(name, description, price || 0, durationHours || 0, requiresSkills || '');
  return { id: info.lastInsertRowid, name, description, price, durationHours, requiresSkills };
};

const updateService = (id, updates) => {
  const set = Object.keys(updates).map(k => `${k}=?`).join(',');
  const values = [...Object.values(updates), id];
  db.prepare(`UPDATE services SET ${set} WHERE id=?`).run(...values);
  return true;
};

const deleteService = (id) => {
  db.prepare('DELETE FROM services WHERE id=?').run(id);
  return true;
};

const getStats = () => {
  const totalRequests = db.prepare('SELECT COUNT(*) as count FROM tickets').get().count;
  const pending = db.prepare('SELECT COUNT(*) as count FROM tickets WHERE status="pending"').get().count;
  const activeJobs = db.prepare('SELECT COUNT(*) as count FROM tickets WHERE status IN ("assigned","in_progress")').get().count;
  const completedJobs = db.prepare('SELECT COUNT(*) as count FROM tickets WHERE status="completed"').get().count;
  const activeTechs = db.prepare('SELECT COUNT(*) as count FROM technicians WHERE status="available"').get().count;
  return { totalRequests, pending, activeJobs, completedJobs, activeTechs };
};

const getTickets = () => db.prepare('SELECT * FROM tickets ORDER BY created DESC').all();

const getTechnicians = () => db.prepare('SELECT * FROM technicians').all();

const getTracking = () => {
  const techMarkers = getTechnicians().map((tech) => ({
    id: tech.id,
    name: tech.name,
    status: tech.status,
    lat: tech.lat,
    lng: tech.lng,
    currentJob: tech.currentJob
  }));
  const ticketMarkers = getTickets().filter(t => t.status !== 'completed').map((ticket) => ({
    id: ticket.id,
    client: ticket.client,
    service: ticket.service,
    status: ticket.status,
    lat: ticket.lat,
    lng: ticket.lng,
    locationDesc: ticket.locationDesc
  }));
  return { techMarkers, ticketMarkers };
};

const getClients = () => db.prepare('SELECT * FROM clients').all();

const getInventory = () => db.prepare('SELECT * FROM inventory').all();

const assignTechnician = (ticketId, technicianName) => {
  const ticket = db.prepare('SELECT * FROM tickets WHERE id=?').get(ticketId);
  if (!ticket) return false;
  const tech = db.prepare('SELECT * FROM technicians WHERE name=?').get(technicianName);
  if (!tech) return false;

  db.prepare('UPDATE tickets SET assignedTech=?, status="assigned" WHERE id=?').run(technicianName, ticketId);
  db.prepare('UPDATE technicians SET status="on_job", currentJob=?, lastUpdate=datetime("now") WHERE name=?').run(ticketId, technicianName);
  return true;
};

const updateTicketStatus = (ticketId, status) => {
  db.prepare('UPDATE tickets SET status=? WHERE id=?').run(status, ticketId);
  return true;
};

const createServiceRequest = (client, service, notes, lat = 0, lng = 0, locationDesc = '') => {
  const info = db.prepare('INSERT INTO tickets (client, service, status, assignedTech, lat, lng, locationDesc, priority, created, notes) VALUES (?, ?, "pending", NULL, ?, ?, ?, "medium", datetime("now"), ?)').run(client, service, lat || 0, lng || 0, locationDesc, notes);
  return info.lastInsertRowid;
};

const getTechnicianDashboard = (techName) => {
  const jobs = db.prepare('SELECT status FROM technician_jobs WHERE techName=?').all(techName);
  const total = jobs.length;
  const inProgress = jobs.filter((j) => j.status === 'in_progress').length;
  const completed = jobs.filter((j) => j.status === 'completed').length;
  const pending = jobs.filter((j) => j.status === 'assigned').length;
  return { techName, total, inProgress, completed, pending };
};

const getTechnicianJobs = (techName) => db.prepare('SELECT * FROM technician_jobs WHERE techName=? ORDER BY scheduledDate DESC').all(techName);

const updateJobStatus = (jobId, status) => {
  db.prepare('UPDATE technician_jobs SET status=? WHERE id=?').run(status, jobId);
  return true;
};

const getTechnicianSchedule = (techName) => db.prepare('SELECT * FROM technician_jobs WHERE techName=? AND status IN ("assigned","in_progress") ORDER BY scheduledDate').all(techName);

const getNavigationRoute = (techLat, techLng, jobLat, jobLng) => {
  const distanceKm = Math.sqrt((techLat - jobLat) ** 2 + (techLng - jobLng) ** 2) * 111.195;
  const eta = Math.round((distanceKm / 40) * 60);
  return { start: { lat: techLat, lng: techLng }, end: { lat: jobLat, lng: jobLng }, distanceKm: Number(distanceKm.toFixed(2)), etaMinutes: eta };
};

const submitChecklist = (jobId, serviceType, completed, notes, photos) => {
  db.prepare('INSERT INTO checklists (jobId, serviceType, steps, completed, techNotes, photos) VALUES (?, ?, ?, ?, ?, ?)')
    .run(jobId, serviceType, JSON.stringify(Object.keys(completed)), JSON.stringify(completed), notes, JSON.stringify(photos || []));
  return true;
};

const getMessages = (receiverRole, receiverName) => db.prepare('SELECT * FROM messages WHERE receiverRole=? AND receiverName=? ORDER BY timestamp DESC').all(receiverRole, receiverName);

const sendMessage = (sender, receiverRole, receiverName, text) => {
  db.prepare('INSERT INTO messages (sender, receiverRole, receiverName, text) VALUES (?, ?, ?, ?)').run(sender, receiverRole, receiverName, text);
  return true;
};

const getTechnicianHistory = (techName) => db.prepare('SELECT * FROM technician_jobs WHERE techName=? AND status="completed" ORDER BY scheduledDate DESC').all(techName);

const getTechnicianProfile = (techName) => db.prepare('SELECT * FROM technician_profiles WHERE techName=?').get(techName) || { techName, phone:'', email:'', skills:'', totalCompleted:0, avgCompletionTime:'', rating:0 };

const updateTechnicianProfile = (techName, updates) => {
  const existing = db.prepare('SELECT 1 FROM technician_profiles WHERE techName=?').get(techName);
  const data = { techName, ...updates };
  if (existing) {
    const set = Object.keys(updates).map((k) => `${k}=?`).join(',');
    const values = [...Object.values(updates), techName];
    db.prepare(`UPDATE technician_profiles SET ${set} WHERE techName=?`).run(...values);
  } else {
    db.prepare('INSERT INTO technician_profiles (techName, phone, email, skills, totalCompleted, avgCompletionTime, rating) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .run(techName, data.phone || '', data.email || '', data.skills || '', data.totalCompleted || 0, data.avgCompletionTime || '', data.rating || 0);
  }
  return true;
};

const updateTechnicianLocation = (techName, lat, lng) => {
  db.prepare('INSERT INTO locations (techName, lat, lng) VALUES (?, ?, ?)').run(techName, lat, lng);
  db.prepare('UPDATE technicians SET lat=?, lng=?, lastUpdate=datetime("now") WHERE name=?').run(lat, lng, techName);
  return true;
};

const getAdminAnalytics = () => {
  const totalRevenue = db.prepare('SELECT SUM(price * 1.0) as total FROM services s JOIN tickets t ON s.name = t.service WHERE t.status="completed"').get().total || 0;
  const jobCountByService = db.prepare(`
    SELECT s.name, COUNT(*) as count FROM services s 
    JOIN tickets t ON s.name = t.service 
    GROUP BY s.name ORDER BY count DESC
  `).all();
  const topTech = db.prepare(`
    SELECT techName, totalCompleted FROM technician_profiles 
    ORDER BY totalCompleted DESC LIMIT 1
  `).get();
  return { totalRevenue, jobCountByService, topTech };
};

const getUsers = () => db.prepare('SELECT * FROM users ORDER BY role, username').all();

const createUser = (username, role, email, phone) => {
  db.prepare('INSERT INTO users (username, role, email, phone) VALUES (?, ?, ?, ?)').run(username, role, email, phone);
  return true;
};

const updateUser = (id, updates) => {
  const setClause = Object.keys(updates).map(k => `${k}=?`).join(',');
  const values = [...Object.values(updates), id];
  db.prepare(`UPDATE users SET ${setClause} WHERE id=?`).run(...values);
  return true;
};

const deactivateUser = (id) => {
  db.prepare('UPDATE users SET active=0 WHERE id=?').run(id);
  return true;
};

const getAdminSettings = () => ({ /* mock */ companyName: 'AFN Solar Power Engineering', notificationsEnabled: true });

const updateAdminSettings = (updates) => { /* mock */ return true; };

// Export previous exports + new
export {
  getStats,
  getTickets,
  getTechnicians,
  getTracking,
  getClients,
  getInventory,
  assignTechnician,
  updateTicketStatus,
  createServiceRequest,
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
  updateTechnicianLocation,
  // Admin new
  getAdminTechnicians,
  addAdminTechnician,
  updateAdminTechnician,
  deleteAdminTechnician,
  getAdminClients,
  addAdminClient,
  updateAdminClient,
  deleteAdminClient,
  getServices,
  addService,
  updateService,
  deleteService,
  getAdminAnalytics,
  getUsers,
  createUser,
  updateUser,
  deactivateUser,
  getAdminSettings,
  updateAdminSettings
};

