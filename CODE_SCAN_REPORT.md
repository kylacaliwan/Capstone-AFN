# Code Scan Report - Critical Issues Found

## 1. 🔴 CRITICAL: API Endpoint Trailing Slash Mismatch
**Location:** frontend/src/api/mockApi.js:84
**Issue:** Missing trailing slash in API endpoint

```javascript
// WRONG (current):
const { data } = await api.get('/services/ors/route', { params: { start, end } });

// CORRECT (should be):
const { data } = await api.get('/services/ors/route/', { params: { start, end } });
```

Django REST Framework ViewSet routes expect trailing slashes. Without it, the request goes through but may cause issues with the router pattern matching, resulting in 502 errors.

**Impact:** HIGH - Causes routing failures

---

## 2. 🔴 CRITICAL: Firebase Configuration Not Loaded in Frontend
**Location:** frontend/src/services/firebaseConfig.js:1-10
**Issue:** All Firebase config keys are placeholders or from environment variables that may not be set

```javascript
export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "YOUR_API_KEY",  // ❌ Fallback is placeholder
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "your-project.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "your-project-id",
  // ... all using placeholder fallbacks
};
```

**Missing .env Configuration:**
- frontend/.env not properly configured with actual Firebase values
- Required vars: VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, etc.
- VITE_FIREBASE_VAPID_KEY not set (needed for push notifications)

**Impact:** HIGH - Firebase notifications won't work

---

## 3. 🔴 CRITICAL: ORS API Key May Not Be Properly Loaded
**Location:** backend/afn_service_management/settings.py:45-46
**Issue:** Potential circular dependency and late loading

```python
OPENROUTESERVICE_API_KEY = os.environ.get('OPENROUTESERVICE_API_KEY', '').strip()
ORS_API_KEY = os.environ.get('ORS_API_KEY', OPENROUTESERVICE_API_KEY).strip()
```

When ors_utils.py imports settings at module load time, if ORS_API_KEY is empty string, the client won't initialize:

```python
if openrouteservice and settings.ORS_API_KEY:  # ❌ Empty string is falsy!
    client = openrouteservice.Client(key=settings.ORS_API_KEY)
else:
    client = None  # Falls back to OSRM
```

**Impact:** MEDIUM - Falls back to OSRM which may have limits

---

## 4. 🟡 WARNING: Missing Error Context Propagation
**Location:** backend/services/views.py:1963-1965
**Issue:** Error details are logged but not always returned to client

```python
except Exception as e:
    logger.error(f"ORS routing error...", exc_info=True)
    return Response({'error': 'routing request failed', 'details': str(e)}, status=502)
```

The frontend improved recently but error details may still not show properly because:
- 502 Bad Gateway is a Django-level error, not always a DRF response
- Exception might be caught elsewhere in middleware

---

## 5. 🟡 WARNING: Frontend Interceptor Not Applied to All Axios Instances
**Location:** frontend/src/services/firebaseService.js:5 and frontend/src/api/mockApi.js:1-20
**Issue:** firebaseService.js creates its own axios instance WITHOUT the auth interceptor

```javascript
// mockApi.js - HAS interceptor ✓
const api = axios.create({ baseURL });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('afn_token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// firebaseService.js - NO interceptor ❌
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';
export const registerFCMToken = async (fcmToken, deviceName = '', deviceType = 'web') => {
  try {
    const response = await axios.post(
      `${API_BASE}/notifications/firebase-tokens/register/`,  // ❌ No auth header!
      { ... }
    );
```

**Impact:** MEDIUM - Firebase token registration fails silently if user is logged in

---

## 6. 🟡 WARNING: Frontend Environment File Not Properly Set Up
**Location:** frontend/.env
**Issue:** File exists but likely missing all values

Missing required vars:
```
VITE_API_BASE_URL=http://localhost:8000/api  ✓ Set
VITE_FIREBASE_API_KEY=  ❌ Empty
VITE_FIREBASE_AUTH_DOMAIN=  ❌ Empty
VITE_FIREBASE_PROJECT_ID=  ❌ Empty
VITE_FIREBASE_STORAGE_BUCKET=  ❌ Empty
VITE_FIREBASE_MESSAGING_SENDER_ID=  ❌ Empty
VITE_FIREBASE_APP_ID=  ❌ Empty
VITE_FIREBASE_VAPID_KEY=  ❌ Empty
```

**Impact:** HIGH - App won't initialize Firebase

---

## 7. 🟡 WARNING: CORS_ALLOW_ALL_ORIGINS=True in Development
**Location:** backend/afn_service_management/settings.py:248
**Issue:** Overly permissive CORS settings

```python
CORS_ALLOW_ALL_ORIGINS = True  # ⚠️  Should be restricted
CORS_ALLOW_CREDENTIALS = True
```

Not immediately causing 502, but security risk. Should be:
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']
```

**Impact:** LOW - Functional but risky

---

## 8. 🟡 WARNING: Mixed Axios Configuration
**Location:** frontend/src/context/AuthContext.jsx:22-28 and frontend/src/api/mockApi.js:10-19
**Issue:** Axios default headers set in AuthContext AND instance interceptor in mockApi

```javascript
// AuthContext.jsx - Sets global defaults
useEffect(() => {
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Token ${token}`;
  }
}, [token]);

// mockApi.js - Also sets via interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('afn_token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
});
```

This isn't wrong, but it's redundant. The interceptor approach in mockApi is better.

**Impact:** LOW - Functional but redundant

---

## Summary of Root Causes for 502 Errors:

1. **Primary:** Missing trailing slash on `/services/ors/route` endpoint
2. **Secondary:** ORS client might not initialize if API key is empty string
3. **Tertiary:** Error details getting lost in middleware

## Immediate Fixes Needed:

1. Add trailing slash to ORS endpoint
2. Verify ORS_API_KEY is set (non-empty)
3. Configure Firebase credentials in both frontend and backend .env files
4. Fix firebaseService.js to use shared authenticated axios instance

