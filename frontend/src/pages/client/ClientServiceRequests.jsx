import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchServiceTickets, fetchServiceTypes, createServiceRequest } from '../../api/api';
import { useAuth } from '../../context/AuthContext';
import { getLocalDateInputValue } from '../../utils/date';
import { useNavigate } from 'react-router-dom';

const TIME_SLOT_OPTIONS = [
  { value: '', label: 'No preference' },
  { value: 'morning', label: 'Morning (8 AM - 11 AM)' },
  { value: 'midday', label: 'Midday (11 AM - 2 PM)' },
  { value: 'afternoon', label: 'Afternoon (2 PM - 5 PM)' },
  { value: 'evening', label: 'Evening (5 PM - 8 PM)' }
];

function LocationPicker({ lat, lng, setLat, setLng, setAddress, setCity, setProvince }) {
  useMapEvents({
    async click(e) {
      const { lat, lng } = e.latlng;
      setLat(lat);
      setLng(lng);

      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`
        );
        const data = await res.json();

        if (data?.address) {
          const addr = data.address;

          setAddress(data.display_name || '');
          setCity(addr.city || addr.town || addr.municipality || '');
          setProvince(addr.state || addr.region || '');
        }
      } catch (err) {
        console.error('Reverse geocoding failed', err);
      }
    }
  });

  return lat != null && lng != null ? <Marker position={[lat, lng]} /> : null;
}

export default function ClientServiceRequests() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [serviceTypes, setServiceTypes] = useState([]);
  const [serviceTypeId, setServiceTypeId] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [province, setProvince] = useState('');
  const [notes, setNotes] = useState('');
  const [preferredDate, setPreferredDate] = useState('');
  const [preferredTimeSlot, setPreferredTimeSlot] = useState('');
  const [schedulingNotes, setSchedulingNotes] = useState('');
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [message, setMessage] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const loadPageData = async () => {
    try {
      const [ticketData, serviceTypeData] = await Promise.all([
        fetchServiceTickets(),
        fetchServiceTypes()
      ]);
      setTickets(ticketData);
      setServiceTypes(serviceTypeData);
      setServiceTypeId((current) => current || String(serviceTypeData[0]?.id || ''));
      setError('');
    } catch (err) {
      setTickets([]);
      setServiceTypes([]);
      setError(err.message || 'Unable to load service tickets.');
    }
  };

  useEffect(() => {
    loadPageData();
  }, []);

  const handleUseMyLocation = () => {
  if (!navigator.geolocation) {
    setSubmitError('Geolocation is not supported by your browser.');
    return;
  }

  setMessage('Getting your location...');
  setSubmitError('');

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;

      setLatitude(lat);
      setLongitude(lng);

      try {
        setMessage('Fetching address...');

        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`
        );

        if (!res.ok) throw new Error('Failed to fetch address');

        const data = await res.json();

        console.log('GEOCODE DATA:', data); // 🔍 DEBUG

        if (data) {
          const addr = data.address || {};

          setAddress(data.display_name || '');
          setCity(addr.city || addr.town || addr.municipality || '');
          setProvince(addr.state || addr.region || '');
        }

        setMessage('Location and address set successfully!');
      } catch (err) {
        console.error(err);
        setSubmitError('Location set but failed to fetch address.');
        setMessage('');
      }
    },
    (err) => {
      console.error(err);
      setSubmitError('Could not get your location. अनुमति denied?');
      setMessage('');
    }
  );
};

  const createRequest = async (e) => {
    e.preventDefault();
    setSubmitError('');

    if (!serviceTypeId) {
      setMessage('');
      setSubmitError('Please choose a service type.');
      return;
    }
    if (!notes.trim()) {
      setMessage('');
      setSubmitError('Please add a short description of the request.');
      return;
    }
    if (latitude == null || longitude == null) {
      setMessage('');
      setSubmitError('Please select location on the map (lat/lng).');
      return;
    }
    if (!address.trim()) {
      setMessage('');
      setSubmitError('Please add a location note (street/landmark).');
      return;
    }

    setIsSubmitting(true);
    setMessage('Submitting service request...');
    try {
      const createdRequest = await createServiceRequest({
        service_type: Number(serviceTypeId),
        description: notes.trim(),
        priority: 'Normal',
        preferred_date: preferredDate || null,
        preferred_time_slot: preferredTimeSlot || null,
        scheduling_notes: schedulingNotes.trim() || null,
        location_address: address.trim(),
        location_city: city.trim(),
        location_province: province.trim(),
        latitude,
        longitude
      });
      setSubmitError('');
      setMessage(`Service request #${createdRequest.id} created successfully.`);
      setAddress('');
      setCity('');
      setProvince('');
      setNotes('');
      setPreferredDate('');
      setPreferredTimeSlot('');
      setSchedulingNotes('');
      setLatitude(null);
      setLongitude(null);
      await loadPageData();
      navigate(`/client/requests`);
    } catch (err) {
      setMessage('');
      setSubmitError(err.message || 'Unable to create service request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const messageToneClassName = message.startsWith('Service request #')
    ? 'text-green-600'
    : 'text-slate-600';

  return (
    <Layout>
      <h2 className="text-2xl font-semibold text-slate-800">Create Service Request</h2>
      {error && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <form onSubmit={createRequest} className="rounded-xl bg-white p-4 shadow-sm space-y-3">
          <div>
            <label className="block text-sm font-medium">Client</label>
            <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {[user?.first_name, user?.last_name].filter(Boolean).join(' ').trim() || user?.username || 'Signed-in client'}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">Service Type</label>
            <select value={serviceTypeId} onChange={(e) => setServiceTypeId(e.target.value)} className="w-full rounded border px-2 py-2">
              {serviceTypes.length > 0 ? (
                serviceTypes.map((serviceType) => (
                  <option key={serviceType.id} value={serviceType.id}>
                    {serviceType.name}
                  </option>
                ))
              ) : (
                <option value="">No service types available</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium">Address / Landmark</label>
            <input value={address} onChange={(e) => setAddress(e.target.value)} className="w-full rounded border px-2 py-2" placeholder="E.g., near SM Mall of Asia" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">City</label>
              <input value={city} onChange={(e) => setCity(e.target.value)} className="w-full rounded border px-2 py-2" placeholder="Optional" />
            </div>
            <div>
              <label className="block text-sm font-medium">Province</label>
              <input value={province} onChange={(e) => setProvince(e.target.value)} className="w-full rounded border px-2 py-2" placeholder="Optional" />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">Preferred Appointment Date</label>
              <input
                type="date"
                value={preferredDate}
                onChange={(e) => setPreferredDate(e.target.value)}
                min={getLocalDateInputValue()}
                className="w-full rounded border px-2 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Preferred Time Slot</label>
              <select
                value={preferredTimeSlot}
                onChange={(e) => setPreferredTimeSlot(e.target.value)}
                className="w-full rounded border px-2 py-2"
              >
                {TIME_SLOT_OPTIONS.map((option) => (
                  <option key={option.value || 'none'} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">Scheduling Notes</label>
            <textarea
              value={schedulingNotes}
              onChange={(e) => setSchedulingNotes(e.target.value)}
              className="w-full rounded border px-2 py-2"
              rows="2"
              placeholder="Gate access, best contact time, building rules, or timing preferences."
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Request Details</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full rounded border px-2 py-2" rows="3" />
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-primary px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Request'}
          </button>
          {submitError && <p className="text-sm text-red-600">{submitError}</p>}
          {message && <p className={`text-sm ${messageToneClassName}`}>{message}</p>}
        </form>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-lg font-semibold">Location Picker</h3>
          <p className="text-sm text-slate-500 mb-2">Tap/click map to set a precise service location.</p>
          <MapContainer center={[12.8797, 121.7740]} zoom={6} className="h-60 w-full">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <LocationPicker
              lat={latitude}
              lng={longitude}
              setLat={setLatitude}
              setLng={setLongitude}
              setAddress={setAddress}
              setCity={setCity}
              setProvince={setProvince}
            />
          </MapContainer>
          <div className="mt-3 text-sm font-medium text-slate-700">
            Selected location: {latitude != null ? latitude.toFixed(6) : 'unset'} , {longitude != null ? longitude.toFixed(6) : 'unset'}
          </div>
          <button
            type="button"
            onClick={handleUseMyLocation}
            className="mt-2 rounded bg-blue-500 px-3 py-2 text-white"
          >
            Use My Location
          </button>

          <h3 className="text-lg font-semibold mt-4">My Service Tickets</h3>
          <ul className="mt-2 space-y-1 text-sm text-slate-600">
            {tickets.slice(0, 5).map((ticket) => (
              <li key={ticket.id} className="border-b border-slate-200 pb-1">#{ticket.id} {ticket.service} - {ticket.status}</li>
            ))}
          </ul>
        </div>
      </div>
    </Layout>
  );
}
