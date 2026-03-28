import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';
import { MapContainer, TileLayer, Circle, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { FiMap, FiUsers, FiTrendingUp } from 'react-icons/fi';
import { fetchCoverageHeatmap, fetchTechnicianCoverage } from '../../api/api';

export default function CoverageHeatmap() {
  const [heatmapData, setHeatmapData] = useState([]);
  const [technicianCoverage, setTechnicianCoverage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalPoints: 0, maxDensity: 0, totalTechnicians: 0 });
  const [error, setError] = useState('');
  const mapCenter = heatmapData.length > 0
    ? [heatmapData[0].lat, heatmapData[0].lng]
    : technicianCoverage.length > 0
      ? technicianCoverage[0].center
      : [6.55, 3.35];

  useEffect(() => {
    loadHeatmapData();
  }, []);

  const loadHeatmapData = async () => {
    setLoading(true);
    try {
      const [heatmapResponse, coverageResponse] = await Promise.all([
        fetchCoverageHeatmap(),
        fetchTechnicianCoverage()
      ]);

      setHeatmapData(heatmapResponse.heatmap_data || []);
      setTechnicianCoverage(coverageResponse.coverage_areas || []);
      setStats({
        totalPoints: heatmapResponse.total_points || 0,
        maxDensity: heatmapResponse.max_density || 0,
        totalTechnicians: coverageResponse.total_technicians || 0
      });
      setError('');
    } catch (error) {
      setHeatmapData([]);
      setTechnicianCoverage([]);
      setStats({ totalPoints: 0, maxDensity: 0, totalTechnicians: 0 });
      setError(error.message || 'Unable to load coverage heatmap.');
    }
    setLoading(false);
  };

  const getHeatmapColor = (count, maxDensity) => {
    const intensity = count / maxDensity;
    if (intensity > 0.8) return '#dc2626'; // Red for high density
    if (intensity > 0.6) return '#ea580c'; // Orange
    if (intensity > 0.4) return '#ca8a04'; // Yellow
    if (intensity > 0.2) return '#16a34a'; // Green
    return '#22c55e'; // Light green for low density
  };

  const getHeatmapRadius = (count) => {
    return Math.max(20, Math.min(50, count * 2)); // Scale radius based on count
  };

  return (
    <Layout>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-800 flex items-center gap-3 mb-2">
          <FiMap className="text-blue-500" size={28} />
          Coverage Heatmap
        </h2>
        <p className="text-slate-600">GIS-based visualization of service request concentrations and technician coverage areas</p>
      </div>
      {error && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}

      {/* Stats Cards */}
      <div className="grid gap-6 mb-8 sm:grid-cols-2 lg:grid-cols-3">
        <div className="bg-gradient-to-b from-blue-500 to-blue-600 p-6 text-white rounded-2xl shadow-lg">
          <div className="text-3xl font-bold mb-1">{stats.totalPoints}</div>
          <div className="text-blue-100">Service Areas</div>
        </div>
        <div className="bg-gradient-to-b from-emerald-500 to-emerald-600 p-6 text-white rounded-2xl shadow-lg">
          <div className="text-3xl font-bold mb-1">{stats.maxDensity}</div>
          <div className="text-emerald-100">Max Density</div>
        </div>
        <div className="bg-gradient-to-b from-purple-500 to-purple-600 p-6 text-white rounded-2xl shadow-lg">
          <div className="text-3xl font-bold mb-1">{stats.totalTechnicians}</div>
          <div className="text-purple-100">Active Technicians</div>
        </div>
      </div>

      {/* Map */}
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="h-[70vh] flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <MapContainer center={mapCenter} zoom={11} className="h-[70vh]">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

            {/* Heatmap Circles */}
            {heatmapData.map((point, index) => (
              <Circle
                key={`heatmap-${index}`}
                center={[point.lat, point.lng]}
                radius={getHeatmapRadius(point.count) * 10} // Scale for visibility
                pathOptions={{
                  color: getHeatmapColor(point.count, stats.maxDensity),
                  fillColor: getHeatmapColor(point.count, stats.maxDensity),
                  fillOpacity: 0.6,
                  weight: 2
                }}
              >
                <Popup>
                  <div className="text-center">
                    <strong>Service Hotspot</strong><br />
                    {point.count} completed requests<br />
                    <small>Services: {point.service_types.join(', ')}</small>
                  </div>
                </Popup>
              </Circle>
            ))}

            {/* Technician Coverage Areas */}
            {technicianCoverage.map((tech, index) => (
              <Circle
                key={`coverage-${index}`}
                center={tech.center}
                radius={tech.radius_km * 1000} // Convert km to meters
                pathOptions={{
                  color: '#3b82f6',
                  fillColor: '#3b82f6',
                  fillOpacity: 0.1,
                  weight: 2,
                  dashArray: '5, 5'
                }}
              >
                <Popup>
                  <div className="text-center">
                    <strong>{tech.name}</strong><br />
                    Coverage Area: {tech.radius_km} km radius
                  </div>
                </Popup>
              </Circle>
            ))}
          </MapContainer>
        )}
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-slate-50 rounded-xl">
        <h4 className="font-semibold mb-3 text-slate-800">Map Legend</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-red-600"></div>
            <span>High Density (80%+)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-orange-600"></div>
            <span>Medium-High (60-80%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-yellow-600"></div>
            <span>Medium (40-60%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-green-600"></div>
            <span>Low Density (20-40%)</span>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-200">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-4 h-4 border-2 border-blue-500 border-dashed rounded-full bg-blue-50"></div>
            <span>Technician Coverage Areas</span>
          </div>
        </div>
      </div>
    </Layout>
  );
}
