"""Utilities for Smart Routing and Digital Mapping services.

This module implements Smart Routing using OpenRouteService (ORS) for efficient travel paths based on stored service locations.
Supports Geographic Information System (GIS) features with optional ORS client when API key is configured.
Falls back to public OSRM routing API when ORS is unavailable.
"""

import logging
import math

from django.conf import settings

try:
    import openrouteservice
except ImportError:  # pragma: no cover
    openrouteservice = None

logger = logging.getLogger(__name__)

# create ORS client only if available and key provided
if openrouteservice and settings.ORS_API_KEY:
    client = openrouteservice.Client(key=settings.ORS_API_KEY)
else:
    client = None  # will use OSRM fallback


DEFAULT_ROUTE_SPEED_KPH = {
    'driving-car': 35,
    'driving-hgv': 30,
    'cycling-regular': 15,
    'foot-walking': 5,
}


def _calculate_distance_meters(start_coords, end_coords):
    """Approximate point-to-point distance using the Haversine formula."""
    lon1, lat1 = start_coords
    lon2, lat2 = end_coords

    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371000 * c


def _estimate_duration_seconds(distance_meters, profile):
    speed_kph = DEFAULT_ROUTE_SPEED_KPH.get(profile, DEFAULT_ROUTE_SPEED_KPH['driving-car'])
    meters_per_second = max((speed_kph * 1000) / 3600, 1)
    return distance_meters / meters_per_second


def _build_synthetic_route(start_coords, end_coords, profile='driving-car', reason='fallback'):
    """Build a lightweight straight-line route when external routing is unavailable."""
    distance_meters = round(_calculate_distance_meters(start_coords, end_coords), 2)
    duration_seconds = round(_estimate_duration_seconds(distance_meters, profile), 2)

    return {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [list(start_coords), list(end_coords)],
            },
            'properties': {
                'routing_source': 'synthetic',
                'is_fallback': True,
                'fallback_reason': reason,
                'segments': [{
                    'distance': distance_meters,
                    'duration': duration_seconds,
                    'fallback': True,
                    'steps': [{
                        'instruction': 'Head to destination',
                        'distance': distance_meters,
                        'duration': duration_seconds,
                        'type': 'depart',
                        'modifier': 'straight',
                    }],
                }],
            },
        }],
    }


def get_route(start_coords, end_coords, profile='driving-car'):
    """Return a Smart Routing response for efficient travel paths.

    Implements Smart Routing by trying ORS when API key is present, otherwise falls back to OSRM public API.
    Used for Digital Mapping and GIS-based navigation in the Service Management System.
    """
    if getattr(settings, 'IS_TEST', False) or getattr(settings, 'DISABLE_EXTERNAL_ROUTING', False):
        return _build_synthetic_route(
            start_coords,
            end_coords,
            profile,
            reason='external_routing_disabled',
        )

    if client:
        try:
            params = {
                'coordinates': [start_coords, end_coords],
                'profile': profile,
                'format': 'geojson',
                'instructions': True,
            }
            return client.directions(**params)
        except Exception as exc:
            logger.warning("ORS route lookup failed; using synthetic fallback: %s", exc)
            return _build_synthetic_route(start_coords, end_coords, profile, reason='ors_unavailable')

    # OSRM fallback: only supports driving profile and two points
    # Convert OSRM response to ORS GeoJSON format so frontend receives consistent structure
    import requests
    try:
        lon1, lat1 = start_coords
        lon2, lat2 = end_coords
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson&steps=true"
        )
        resp = requests.get(
            url,
            timeout=getattr(settings, 'ROUTING_HTTP_TIMEOUT_SECONDS', 8),
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            geometry = route.get('geometry', {})
            legs = route.get('legs', [])
            distance = sum(leg.get('distance', 0) for leg in legs)
            duration = sum(leg.get('duration', 0) for leg in legs)
            steps = []
            for leg in legs:
                for step in leg.get('steps', []):
                    steps.append({
                        'instruction': step.get('maneuver', {}).get('instruction', 'Continue'),
                        'distance': step.get('distance', 0),
                        'duration': step.get('duration', 0),
                        'type': step.get('maneuver', {}).get('type', 0),
                        'modifier': step.get('maneuver', {}).get('modifier', ''),
                    })
            return {
                'type': 'FeatureCollection',
                'features': [{
                    'type': 'Feature',
                    'geometry': geometry,
                    'properties': {
                        'routing_source': 'osrm',
                        'segments': [{
                            'distance': distance,
                            'duration': duration,
                            'steps': steps,
                        }],
                    },
                }],
            }
    except Exception as exc:
        logger.warning("OSRM route lookup failed; using synthetic fallback: %s", exc)

    return _build_synthetic_route(start_coords, end_coords, profile, reason='osrm_unavailable')


def _require_client():
    """Raise a clear error when the ORS client is not configured."""
    if client is None:
        raise RuntimeError(
            'OpenRouteService client is not configured. '
            'Set the ORS_API_KEY environment variable and install the openrouteservice package.'
        )


def get_directions(coordinates, profile='driving-car', **kwargs):
    """Wrapper for multi-point directions.

    coordinates : list
        List of [lng, lat] pairs (two or more).
    profile : str
    kwargs : additional ORS options (format, instructions, etc.)
    """
    _require_client()
    params = {'coordinates': coordinates, 'profile': profile}
    params.update(kwargs)
    return client.directions(**params)


def get_isochrones(locations, profile='driving-car', ors_range=None, **kwargs):
    """Obtain isochrones for given locations.

    locations : list of [lng, lat]
    ors_range : int or list of ints (seconds or meters)
    """
    _require_client()
    params = {'locations': locations, 'profile': profile}
    if ors_range is not None:
        params['range'] = ors_range
    params.update(kwargs)
    return client.isochrones(**params)


def get_matrix(locations, profile='driving-car', metrics=None, **kwargs):
    """Compute distance/duration matrix."""
    _require_client()
    if metrics is None:
        metrics = ['distance']
    params = {'locations': locations, 'profile': profile, 'metrics': metrics}
    params.update(kwargs)
    return client.distance_matrix(**params)


def snap_points(coordinates, profile='driving-car', **kwargs):
    """Snap a set of coordinates to the road network."""
    _require_client()
    params = {'coordinates': coordinates, 'profile': profile}
    params.update(kwargs)
    return client.snap(**params)
