// Centralized config for client-safe environment keys.
// IMPORTANT: Only expose keys that are safe to be public (non-secret).
// Never put passwords, server keys, or private tokens here — they will
// be visible in the browser after build. Keep those in the Django backend only.

// Safe: public-facing map/routing API keys
export const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
export const OPENROUTESERVICE_API_KEY =
  import.meta.env.VITE_OPENROUTESERVICE_API_KEY || import.meta.env.VITE_ORS_API_KEY;
export const OPENWEATHER_API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY;

// All email settings and Firebase server keys have been removed from this file.
// Email sending is handled exclusively by Django. Firebase server key stays on the backend.
