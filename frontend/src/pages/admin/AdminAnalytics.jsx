import { useEffect, useState } from 'react';
import {
  FiActivity,
  FiCalendar,
  FiClock,
  FiMapPin,
  FiRefreshCw,
  FiTrendingUp,
  FiZap
} from 'react-icons/fi';
import { Circle, MapContainer, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import Layout from '../../components/Layout';
import { fetchAdminAnalytics, fetchCoverageHeatmap } from '../../api/api';

const AUTO_REFRESH_MS = 45000;

const riskTone = {
  high: 'border-rose-200 bg-rose-100 text-rose-700',
  medium: 'border-amber-200 bg-amber-100 text-amber-700',
  low: 'border-emerald-200 bg-emerald-100 text-emerald-700'
};

const trendTone = {
  up: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  down: 'border-rose-200 bg-rose-100 text-rose-700',
  flat: 'border-slate-200 bg-slate-100 text-slate-700'
};

const getHeatmapColor = (count, maxDensity) => {
  const safeMax = maxDensity || 1;
  const intensity = count / safeMax;
  if (intensity > 0.8) return '#dc2626';
  if (intensity > 0.6) return '#ea580c';
  if (intensity > 0.4) return '#ca8a04';
  if (intensity > 0.2) return '#16a34a';
  return '#22c55e';
};

const getHeatmapRadius = (count) => Math.max(180, Math.min(700, count * 120));
const formatHours = (value) => `${Number(value || 0).toFixed(1)}h`;
const formatPercent = (value) => `${Number(value || 0).toFixed(1)}%`;

const formatDateTime = (value) => {
  if (!value) return 'Waiting for first snapshot';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const formatShortDate = (value) => {
  if (!value) return 'No date';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric'
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const trendLabel = (item) => {
  if (item.trendDirection === 'up') return `Up ${item.trendDelta}`;
  if (item.trendDirection === 'down') return `Down ${Math.abs(item.trendDelta)}`;
  return 'Flat';
};

export default function AdminAnalytics() {
  const [stats, setStats] = useState(null);
  const [heatmapData, setHeatmapData] = useState([]);
  const [heatmapStats, setHeatmapStats] = useState({ totalPoints: 0, maxDensity: 0 });
  const [error, setError] = useState('');
  const [heatmapError, setHeatmapError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAnalytics = async (background = false) => {
    if (background) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    const [analyticsResult, heatmapResult] = await Promise.allSettled([
      fetchAdminAnalytics(),
      fetchCoverageHeatmap()
    ]);

    if (analyticsResult.status === 'fulfilled') {
      setStats(analyticsResult.value);
      setError('');
    } else {
      setError(analyticsResult.reason?.message || 'Unable to load analytics.');
    }

    if (heatmapResult.status === 'fulfilled') {
      const response = heatmapResult.value || {};
      setHeatmapData(response.heatmap_data || []);
      setHeatmapStats({
        totalPoints: response.total_points || 0,
        maxDensity: response.max_density || 0
      });
      setHeatmapError('');
    } else {
      setHeatmapError(heatmapResult.reason?.message || 'Unable to load service coverage heatmap.');
    }

    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => {
    loadAnalytics(false);
    const intervalId = setInterval(() => {
      loadAnalytics(true);
    }, AUTO_REFRESH_MS);
    return () => clearInterval(intervalId);
  }, []);

  const overview = stats?.overview || {};
  const predictiveSummary = stats?.predictiveSummary || {};
  const serviceForecasts = stats?.serviceForecasts || [];
  const dailyForecast = stats?.dailyForecast || [];
  const topServices = stats?.topRequestedServiceTypes || [];
  const busiestMonths = stats?.busiestMonths || [];
  const busiestWeeks = stats?.busiestWeeks || [];
  const cityTrends = stats?.cityCompletionTrends || [];
  const provinceTrends = stats?.provinceCompletionTrends || [];

  const topMonth = busiestMonths[0];
  const topWeek = busiestWeeks[0];
  const topCity = cityTrends[0];
  const hotspotList = [...heatmapData].sort((a, b) => (b.count || 0) - (a.count || 0)).slice(0, 5);
  const forecastMax = Math.max(1, ...dailyForecast.map((item) => item.predictedRequests || 0));
  const mapCenter = heatmapData.length > 0 ? [heatmapData[0].lat, heatmapData[0].lng] : [6.55, 3.35];

  const renderLocationTrendCard = (title, icon, items, keyName, emptyMessage) => (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-slate-100 p-3 text-slate-700">{icon}</div>
        <div>
          <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm text-slate-500">Completions, rates, and recent momentum.</p>
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={item[keyName]} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-slate-900">{item[keyName]}</div>
                  <div className="mt-1 text-sm text-slate-500">
                    {item.completedCount} completed | {item.totalTickets} total | {formatPercent(item.completionRate)}
                  </div>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${trendTone[item.trendDirection] || trendTone.flat}`}>
                  {trendLabel(item)}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                <span>Last 30d: {item.recentCompleted}</span>
                <span>Prev 30d: {item.previousCompleted}</span>
                <span>Latest: {formatShortDate(item.latestCompletedDate)}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
            {emptyMessage}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <Layout>
      <section className="overflow-hidden rounded-[32px] bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-900 px-6 py-7 text-white shadow-2xl sm:px-7 lg:px-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-300 animate-pulse" />
                Real-Time Analytics
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs text-slate-200">
                Auto-refresh every 45s
              </span>
            </div>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
              Live demand pulse, historical hotspots, and location-driven completion trends.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
              This workspace blends live forecast signals with real historical demand, busiest periods, and
              completion performance by city and province.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:w-[420px]">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-300">
                <FiClock />
                Last Snapshot
              </div>
              <div className="mt-2 text-lg font-semibold text-white">{formatDateTime(stats?.generatedAt)}</div>
            </div>
            <button
              onClick={() => loadAnalytics(true)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-4 py-4 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
            >
              <FiRefreshCw className={refreshing ? 'animate-spin' : ''} />
              {refreshing ? 'Refreshing' : 'Refresh Now'}
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-300">Busiest Month</div>
            <div className="mt-2 text-2xl font-bold text-white">{topMonth?.label || 'No data yet'}</div>
            <div className="mt-1 text-sm text-slate-200">{topMonth?.requestCount || 0} requests</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-300">Busiest Week</div>
            <div className="mt-2 text-xl font-bold text-white">{topWeek?.label || 'No data yet'}</div>
            <div className="mt-1 text-sm text-slate-200">{topWeek?.requestCount || 0} requests</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-300">Leading City</div>
            <div className="mt-2 text-2xl font-bold text-white">{topCity?.city || 'No city data'}</div>
            <div className="mt-1 text-sm text-slate-200">{topCity?.completedCount || 0} completions</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-300">Staffing Pressure</div>
            <div className="mt-2 text-2xl font-bold text-white">{String(predictiveSummary.staffingPressure || 'low').toUpperCase()}</div>
            <div className="mt-1 text-sm text-slate-200">
              {predictiveSummary.recommendedTechnicians || 0} recommended | {predictiveSummary.activeTechnicians || 0} active
            </div>
          </div>
        </div>
      </section>

      {error && <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}

      {loading && !stats ? (
        <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-slate-600">Loading analytics...</p>
        </div>
      ) : null}

      {stats && (
        <>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Requests</div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{overview.totalRequests || 0}</div>
            </div>
            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Completed Jobs</div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{overview.completedRequests || 0}</div>
            </div>
            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Avg Response</div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{formatHours(overview.avgResponseTimeHours)}</div>
            </div>
            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Next 7 Days</div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{predictiveSummary.totalPredictedRequests || 0}</div>
            </div>
            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Mapped Hotspots</div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{heatmapStats.totalPoints}</div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-3xl bg-slate-950 p-6 text-white shadow-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-200">
                    <FiActivity />
                    Demand Pulse
                  </div>
                  <h3 className="mt-3 text-2xl font-semibold">7-Day Live Outlook</h3>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Growth</div>
                  <div className="mt-1 text-2xl font-bold text-white">{Number(predictiveSummary.projectedGrowthRate || 0).toFixed(1)}%</div>
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {dailyForecast.map((day) => (
                  <div key={day.date} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="text-sm font-semibold text-white">{day.label}</div>
                    <div className="mt-4 h-20 overflow-hidden rounded-xl bg-white/5 p-2">
                      <div
                        className="h-full rounded-lg bg-gradient-to-t from-emerald-400 via-cyan-400 to-sky-300"
                        style={{ width: `${Math.max(18, (day.predictedRequests / forecastMax) * 100)}%` }}
                      />
                    </div>
                    <div className="mt-3 text-2xl font-bold text-white">{day.predictedRequests}</div>
                    <div className="mt-2 text-sm text-slate-300">Capacity gap {day.capacityGap}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4">
              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Top Technician</div>
                <div className="mt-3 text-2xl font-bold text-slate-900">{stats.topTech?.techName || 'No completed jobs yet'}</div>
                <div className="mt-1 text-sm text-slate-500">
                  {stats.topTech?.totalCompleted || 0} completed
                  {stats.topTech?.avgRating != null ? ` | ${stats.topTech.avgRating}/5 rating` : ''}
                </div>
              </div>
              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Highest Risk Service</div>
                <div className="mt-3 text-2xl font-bold text-slate-900">{predictiveSummary.topRiskService?.serviceType || 'No risk yet'}</div>
                <div className="mt-1 text-sm text-slate-500">{predictiveSummary.topRiskService?.predictedNext7Days || 0} predicted requests</div>
                <div className="mt-3">
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${riskTone[predictiveSummary.topRiskService?.riskLevel] || riskTone.low}`}>
                    {String(predictiveSummary.topRiskService?.riskLevel || 'low').toUpperCase()} RISK
                  </span>
                </div>
              </div>
              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Fastest Demand Driver</div>
                <div className="mt-3 text-2xl font-bold text-slate-900">{topServices[0]?.serviceType || 'No service data yet'}</div>
                <div className="mt-1 text-sm text-slate-500">
                  {topServices[0]?.requestCount || 0} requests | {formatPercent(topServices[0]?.completionRate || 0)} completion rate
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-3xl bg-white p-6 shadow-sm">
              <h3 className="text-xl font-semibold text-slate-900">Most Requested Service Types</h3>
              <div className="mt-5 space-y-3">
                {topServices.length > 0 ? (
                  topServices.map((service) => (
                    <div key={service.serviceTypeId} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="font-semibold text-slate-900">{service.serviceType}</div>
                          <div className="mt-1 text-sm text-slate-500">
                            {service.recentRequests} recent | {service.completedCount} completed
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-slate-900">{service.requestCount}</div>
                          <div className="text-xs uppercase tracking-wide text-slate-500">Requests</div>
                        </div>
                      </div>
                      <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Completion rate {formatPercent(service.completionRate)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
                    Service demand history will appear here once requests accumulate.
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-6">
              <div className="rounded-3xl bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-amber-100 p-3 text-amber-700"><FiCalendar /></div>
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900">Busiest Months</h3>
                    <p className="mt-1 text-sm text-slate-500">Peak demand by month.</p>
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {busiestMonths.map((month) => (
                    <div key={month.monthStart} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-900">{month.label}</div>
                          <div className="mt-1 text-sm text-slate-500">{month.completedCount} completed | {formatPercent(month.completionRate)}</div>
                        </div>
                        <div className="text-2xl font-bold text-slate-900">{month.requestCount}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-3xl bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-sky-100 p-3 text-sky-700"><FiTrendingUp /></div>
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900">Busiest Weeks</h3>
                    <p className="mt-1 text-sm text-slate-500">Fast-moving weekly surges.</p>
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {busiestWeeks.map((week) => (
                    <div key={week.weekStart} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-900">{week.label}</div>
                          <div className="mt-1 text-sm text-slate-500">{week.completedCount} completed | {formatPercent(week.completionRate)}</div>
                        </div>
                        <div className="text-2xl font-bold text-slate-900">{week.requestCount}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            {renderLocationTrendCard(
              'Completion Trends By City',
              <FiMapPin />,
              cityTrends,
              'city',
              'City-level completion trends will appear once location data is available.'
            )}
            {renderLocationTrendCard(
              'Completion Trends By Province',
              <FiZap />,
              provinceTrends,
              'province',
              'Province-level completion trends will appear once location data is available.'
            )}
          </div>
        </>
      )}

      <div className="mt-6 overflow-hidden rounded-3xl bg-white shadow-xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">Completed Service Coverage Heatmap</h3>
              <p className="mt-1 text-sm text-slate-500">
                Historical delivery hotspots based on completed jobs with saved service locations.
              </p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Live map signal
            </span>
          </div>
        </div>

        {heatmapError ? (
          <div className="p-6 text-sm text-red-800">{heatmapError}</div>
        ) : heatmapData.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">No completed service hotspots are available yet.</div>
        ) : (
          <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="h-[420px] min-h-[420px]">
              <MapContainer center={mapCenter} zoom={11} scrollWheelZoom={true} className="h-full w-full">
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {heatmapData.map((point, index) => (
                  <Circle
                    key={`analytics-heatmap-${index}`}
                    center={[point.lat, point.lng]}
                    radius={getHeatmapRadius(point.count)}
                    pathOptions={{
                      color: getHeatmapColor(point.count, heatmapStats.maxDensity),
                      fillColor: getHeatmapColor(point.count, heatmapStats.maxDensity),
                      fillOpacity: 0.45,
                      weight: 2
                    }}
                  >
                    <Popup>
                      <div className="text-center text-sm">
                        <strong>Service Hotspot</strong>
                        <br />
                        {point.count} completed requests
                        <br />
                        <small>{(point.service_types || []).join(', ')}</small>
                      </div>
                    </Popup>
                  </Circle>
                ))}
              </MapContainer>
            </div>

            <div className="space-y-4 border-t border-slate-200 p-6 lg:border-l lg:border-t-0">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Service Areas</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{heatmapStats.totalPoints}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Peak Density</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{heatmapStats.maxDensity}</div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Top Hotspots</h4>
                <div className="mt-3 space-y-3">
                  {hotspotList.map((point, index) => (
                    <div key={`${point.address}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900">{point.address || 'Service Area'}</div>
                          <div className="mt-1 text-sm text-slate-500">
                            {(point.service_types || []).join(', ') || 'Completed services'}
                          </div>
                        </div>
                        <div className="rounded-full bg-slate-900 px-3 py-1 text-sm font-semibold text-white">
                          {point.count}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
