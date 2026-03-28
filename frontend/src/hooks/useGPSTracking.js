import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * GPS Tracking Hook - Real GPS location tracking for technicians
 * Uses browser Geolocation API with proper error handling and permissions
 */
export const useGPSTracking = (options = {}) => {
  const {
    enableHighAccuracy = true,
    timeout = 10000,
    maximumAge = 30000,
    updateInterval = 10000, // Update every 10 seconds
    onLocationUpdate = null,
    autoStart = false
  } = options;

  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [watching, setWatching] = useState(false);
  const [permission, setPermission] = useState('unknown'); // 'granted', 'denied', 'unknown'
  const watchIdRef = useRef(null);

  // Check geolocation permission
  const checkPermission = useCallback(async () => {
    if ('permissions' in navigator) {
      try {
        const result = await navigator.permissions.query({ name: 'geolocation' });
        setPermission(result.state);
        result.addEventListener('change', () => setPermission(result.state));
      } catch (err) {
        console.warn('Permission API not supported');
      }
    }
  }, []);

  // Get current position once
  const getCurrentPosition = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by this browser'));
        return;
      }

      setLoading(true);
      setError(null);

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const loc = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            altitudeAccuracy: position.coords.altitudeAccuracy,
            heading: position.coords.heading,
            speed: position.coords.speed,
            timestamp: position.timestamp
          };

          setLocation(loc);
          setLoading(false);
          resolve(loc);
        },
        (err) => {
          let errorMessage = 'Unknown GPS error';
          switch (err.code) {
            case err.PERMISSION_DENIED:
              errorMessage = 'GPS access denied by user';
              setPermission('denied');
              break;
            case err.POSITION_UNAVAILABLE:
              errorMessage = 'GPS position unavailable';
              break;
            case err.TIMEOUT:
              errorMessage = 'GPS request timeout';
              break;
          }

          const gpsError = new Error(errorMessage);
          gpsError.code = err.code;
          setError(gpsError);
          setLoading(false);
          reject(gpsError);
        },
        {
          enableHighAccuracy,
          timeout,
          maximumAge
        }
      );
    });
  }, [enableHighAccuracy, timeout, maximumAge]);

  // Start watching position
  const startWatching = useCallback(() => {
    if (!navigator.geolocation) {
      setError(new Error('Geolocation is not supported by this browser'));
      return;
    }

    if (watching) return; // Already watching

    setWatching(true);
    setError(null);

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const loc = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          altitude: position.coords.altitude,
          altitudeAccuracy: position.coords.altitudeAccuracy,
          heading: position.coords.heading,
          speed: position.coords.speed,
          timestamp: position.timestamp
        };

        setLocation(loc);
        setLoading(false);

        // Call callback if provided
        if (onLocationUpdate) {
          onLocationUpdate(loc);
        }
      },
      (err) => {
        let errorMessage = 'GPS tracking error';
        switch (err.code) {
          case err.PERMISSION_DENIED:
            errorMessage = 'GPS access denied';
            setPermission('denied');
            break;
          case err.POSITION_UNAVAILABLE:
            errorMessage = 'GPS position unavailable';
            break;
          case err.TIMEOUT:
            errorMessage = 'GPS request timeout';
            break;
        }

        const gpsError = new Error(errorMessage);
        gpsError.code = err.code;
        setError(gpsError);
        setLoading(false);
        setWatching(false);
      },
      {
        enableHighAccuracy,
        timeout,
        maximumAge
      }
    );

    watchIdRef.current = watchId;
  }, [watching, enableHighAccuracy, timeout, maximumAge, onLocationUpdate]);

  // Stop watching
  const stopWatching = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setWatching(false);
  }, []);

  // Request permission (triggers browser permission prompt)
  const requestPermission = useCallback(async () => {
    try {
      await getCurrentPosition();
      setPermission('granted');
    } catch (err) {
      setPermission('denied');
      throw err;
    }
  }, [getCurrentPosition]);

  // Initialize
  useEffect(() => {
    checkPermission();

    if (autoStart) {
      startWatching();
    }

    // Properly clear the geolocation watcher on unmount to prevent memory/battery leaks
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setWatching(false);
    };
  }, [checkPermission, autoStart]);

  return {
    location,
    error,
    loading,
    watching,
    permission,
    getCurrentPosition,
    startWatching,
    stopWatching,
    requestPermission
  };
};
