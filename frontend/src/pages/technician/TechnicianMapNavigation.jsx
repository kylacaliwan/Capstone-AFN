import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { FiNavigation, FiRefreshCw, FiFlag, FiChevronRight } from 'react-icons/fi';
import { fetchNavigationRoute, updateTechnicianLocation } from '../../api/api';
import { useAuth } from '../../context/AuthContext';
import { useGPSTracking } from '../../hooks/useGPSTracking';
import GPSStatusIndicator from '../../components/GPSStatusIndicator';

const techIcon = L.divIcon({
  html: '<div class="w-12 h-12 bg-blue-500 rounded-full shadow-lg border-4 border-white flex items-center justify-center text-white font-bold text-sm">You</div>',
  className: 'leaflet-marker-icon',
  iconSize: [48, 48],
  iconAnchor: [24, 48]
});

const jobIcon = L.divIcon({
  html: '<div class="w-12 h-12 bg-red-500 rounded-full shadow-lg border-4 border-white flex items-center justify-center text-white font-bold text-sm">📍</div>',
  className: 'leaflet-marker-icon',
  iconSize: [48, 48],
  iconAnchor: [24, 48]
});

export default function TechnicianMapNavigation() {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('jobId') || searchParams.get('ticketId');
  const { user } = useAuth();
  const techName = user?.username || 'Technician';
  const [jobLoc, setJobLoc] = useState([14.5547, 121.0337]); // Makati, Philippines (sample job location)
  const [route, setRoute] = useState({ distanceKm: 0, estimatedTimeMin: 0, routeCoords: [], directions: [] });
  const [arrived, setArrived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [mapKey, setMapKey] = useState(0);
  const [watchStarted, setWatchStarted] = useState(false);

  const {
    location: gpsLocation,
    error: gpsError,
    loading: gpsLoading,
    permission: gpsPermission,
    startWatching,
    stopWatching
  } = useGPSTracking({ autoStart: false });

  // Update backend & route whenever GPS location changes
  useEffect(() => {
    if (!gpsLocation) return;

    const { latitude, longitude, accuracy } = gpsLocation;

    const update = async () => {
      try {
        await updateTechnicianLocation({ techName, lat: latitude, lng: longitude, accuracy });
      } catch (e) {
        console.warn('Failed to update technician location', e);
      }

      if (!arrived) {
        loadRoute(latitude, longitude);
      }
    };

    update();
  }, [gpsLocation, arrived, techName]);

  // Start GPS watching and initial route load - only once on mount
  useEffect(() => {
    if (!watchStarted) {
      startWatching();
      setWatchStarted(true);
      // Load the initial route once technician and job coordinates are available
      loadRoute();
    }

    return () => {
      stopWatching();
    };
  }, []);

  // Default to Manila if GPS location unavailable (has routing data in ORS)
  const techLoc = gpsLocation ? [gpsLocation.latitude, gpsLocation.longitude] : [14.5995, 120.9842];

  const loadRoute = async (techLat = techLoc[0], techLng = techLoc[1]) => {
    setLoading(true);
    setCurrentStepIndex(0);
    const data = await fetchNavigationRoute(techLat, techLng, jobLoc[0], jobLoc[1]);
    setRoute(data);
    setMapKey(prev => prev + 1); // Force map rerender
    setLoading(false);
  };

  const markArrived = () => {
    setArrived(true);
  };

  // Auto-advance direction steps based on proximity
  useEffect(() => {
    if (!route.routeCoords || route.routeCoords.length === 0 || !gpsLocation) return;

    const userLatLng = [gpsLocation.latitude, gpsLocation.longitude];
    
    // Calculate distance to next waypoint
    const calculateDistance = (lat1, lng1, lat2, lng2) => {
      const R = 6371; // Earth's radius in km
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLng = (lng2 - lng1) * Math.PI / 180;
      const a = 
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLng / 2) * Math.sin(dLng / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      return R * c;
    };

    const distToJob = calculateDistance(userLatLng[0], userLatLng[1], jobLoc[0], jobLoc[1]);
    if (distToJob < 0.05) { // Within 50 meters
      markArrived();
    }

    // Check progress through route
    if (currentStepIndex < route.directions.length) {
      const nextStep = route.directions[currentStepIndex];
      if (nextStep && nextStep.distance) {
        const distToNextStep = nextStep.distance / 1000; // Convert to km if needed
        if (distToNextStep < 0.1) { // Within 100 meters
          setCurrentStepIndex(Math.min(currentStepIndex + 1, route.directions.length - 1));
        }
      }
    }
  }, [gpsLocation, route]);

  // Fit map bounds to show route
  const fitBounds = (map) => {
    if (!route.routeCoords || route.routeCoords.length < 2) return;
    
    try {
      const bounds = L.latLngBounds(route.routeCoords);
      bounds.extend(techLoc);
      bounds.extend(jobLoc);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    } catch (e) {
      console.error('Error fitting bounds:', e);
    }
  };

  const currentStep = route.directions[currentStepIndex] || null;

  return (
    <Layout>
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-slate-800 flex items-center gap-3 mb-2">
          <FiNavigation className="text-blue-500" size={28} />
          Navigation to Job #{jobId}
        </h2>
        <p className="text-slate-600">Live GPS tracking enabled • {route.directions.length} turns</p>
        <GPSStatusIndicator status={gpsPermission} accuracy={gpsLocation?.accuracy} className="mt-2" />
        {gpsError && (
          <p className="text-sm text-red-600 mt-2">
            GPS error: {gpsError.message}
          </p>
        )}
        {currentStep && (
          <div className="mt-3 p-3 bg-blue-50 border-l-4 border-blue-500 rounded-lg">
            <p className="text-sm font-semibold text-blue-900">Next: {currentStep.instruction}</p>
            <p className="text-xs text-blue-700">
              {currentStep.distance ? `${(currentStep.distance / 1000).toFixed(1)} km` : ''} 
              {currentStep.duration ? ` • ${Math.round(currentStep.duration / 60)} min` : ''}
            </p>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 rounded-2xl bg-white shadow-xl overflow-hidden">
          {loading ? (
            <div className="h-[70vh] flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <MapContainer 
              key={mapKey}
              center={[12.8797, 121.7740]} 
              zoom={7} 
              minZoom={6}
              maxZoom={18}
              maxBounds={[[4.6, 116.9], [20.9, 126.6]]}
              className="h-[70vh]"
              onLoad={(map) => fitBounds(map)}
            >
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              
              {/* Tech location */}
              <Marker position={techLoc} icon={techIcon}>
                <Popup>
                  <div>
                    <strong>Your Location</strong><br />
                    Moving to job site...
                  </div>
                </Popup>
              </Marker>

              {/* Job location */}
              <Marker position={jobLoc} icon={jobIcon}>
                <Popup>
                  <div className="text-center">
                    <strong>Job Site</strong><br />
                    {route.distanceKm} km away<br />
                    ~{route.estimatedTimeMin} min
                  </div>
                </Popup>
              </Marker>

              {/* Route line */}
              {route.routeCoords.length > 1 && (
                <>
                  <Polyline 
                    positions={route.routeCoords} 
                    color="#3b82f6" 
                    weight={5} 
                    opacity={0.8}
                  />
                  {/* Highlight remaining route */}
                  {currentStepIndex < route.routeCoords.length && (
                    <Polyline 
                      positions={route.routeCoords.slice(currentStepIndex)} 
                      color="#10b981" 
                      weight={4} 
                      opacity={0.9}
                    />
                  )}
                </>
              )}
            </MapContainer>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-gradient-to-b from-blue-500 to-blue-600 p-6 text-white rounded-2xl shadow-lg">
            <div className="text-3xl font-bold mb-1">{route.distanceKm} km</div>
            <div className="text-blue-100">Distance</div>
          </div>

          <div className="bg-gradient-to-b from-emerald-500 to-emerald-600 p-6 text-white rounded-2xl shadow-lg">
            <div className="text-3xl font-bold mb-1">{route.estimatedTimeMin} min</div>
            <div className="text-emerald-100">Travel Time</div>
          </div>

          {/* Directions */}
          <div className="p-6 bg-white rounded-2xl shadow-lg border">
            <h4 className="font-semibold mb-4 text-slate-900 flex items-center gap-2">
              Turn-by-Turn Directions ({currentStepIndex + 1}/{route.directions.length})
            </h4>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {route.directions.length > 0 ? route.directions.map((dir, i) => (
                <div 
                  key={i} 
                  className={`flex gap-3 p-3 rounded-lg transition ${
                    i === currentStepIndex 
                      ? 'bg-blue-100 border-2 border-blue-500 shadow-md' 
                      : i < currentStepIndex 
                      ? 'bg-emerald-50 opacity-60'
                      : 'bg-slate-50'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 text-white ${
                    i === currentStepIndex ? 'bg-blue-500' : i < currentStepIndex ? 'bg-emerald-500' : 'bg-slate-300'
                  }`}>
                    {i < currentStepIndex ? '✓' : i + 1}
                  </div>
                  <div className="flex-1">
                    <p className={`font-medium ${i === currentStepIndex ? 'text-blue-900' : 'text-slate-800'}`}>
                      {dir.instruction}
                    </p>
                    <p className="text-xs text-slate-500">
                      {dir.distance ? `${(dir.distance / 1000).toFixed(1)} km` : ''} 
                      {dir.duration ? ` • ${Math.round(dir.duration / 60)} min` : ''}
                    </p>
                  </div>
                  {i === currentStepIndex && <FiChevronRight className="text-blue-500 flex-shrink-0" size={20} />}
                </div>
              )) : (
                <p className="text-slate-500 text-center py-4">No directions available</p>
              )}
            </div>
          </div>

          <div className="p-6 bg-white rounded-2xl shadow-lg border">
            <h4 className="font-semibold mb-4 text-slate-900 flex items-center gap-2">
              Actions
            </h4>
            <div className="space-y-3">
              <button 
                onClick={() => loadRoute()}
                className="w-full flex items-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 rounded-xl transition text-left group"
              >
                <FiRefreshCw className="group-hover:rotate-180 transition-transform" />
                Recalculate Route
              </button>
              {!arrived ? (
                <button 
                  onClick={markArrived}
                  className="w-full flex items-center gap-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-medium shadow-lg transition"
                >
                  <FiFlag />
                  Mark Arrived
                </button>
              ) : (
                <div className="w-full p-4 bg-emerald-100 border-2 border-emerald-400 rounded-xl text-emerald-800 font-medium text-center">
                  ✅ Arrived at site
                </div>
              )}
            </div>
          </div>

          <div className="text-xs text-slate-500 text-center p-3 bg-slate-50 rounded-xl">
            GPS updates in real-time | Route recalculates automatically
          </div>
        </div>
      </div>
    </Layout>
  );
}
