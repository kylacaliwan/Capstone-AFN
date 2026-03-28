// Firebase Web SDK configuration
// This is the public configuration from Firebase Console
const firebaseEnv = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
  vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY || '',
};

export const firebaseConfig = {
  apiKey: firebaseEnv.apiKey,
  authDomain: firebaseEnv.authDomain,
  projectId: firebaseEnv.projectId,
  storageBucket: firebaseEnv.storageBucket,
  messagingSenderId: firebaseEnv.messagingSenderId,
  appId: firebaseEnv.appId,
};

export const isFirebaseMessagingConfigured = Object.values(firebaseEnv).every(Boolean);

let firebaseInitPromise = null;
let foregroundHandlerAttached = false;

const buildFirebaseServiceWorkerUrl = () => {
  const serviceWorkerUrl = new URL('/firebase-messaging-sw.js', window.location.origin);
  Object.entries(firebaseEnv).forEach(([key, value]) => {
    if (value) {
      serviceWorkerUrl.searchParams.set(key, value);
    }
  });
  return serviceWorkerUrl.toString();
};

async function registerFirebaseServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    return null;
  }

  const registration = await navigator.serviceWorker.register(
    buildFirebaseServiceWorkerUrl(),
    { scope: '/' }
  );

  await navigator.serviceWorker.ready;
  return registration;
}

async function initializeFirebaseInternal() {
  if (!isFirebaseMessagingConfigured) {
    return { success: false, reason: 'not_configured' };
  }

  if (typeof window === 'undefined' || typeof Notification === 'undefined') {
    return { success: false, reason: 'unsupported' };
  }

  try {
    // Import dynamically to avoid bundling Firebase if not needed
    const { initializeApp, getApp, getApps } = await import('firebase/app');
    const { getMessaging, getToken, isSupported } = await import('firebase/messaging');

    if (!(await isSupported())) {
      return { success: false, reason: 'unsupported' };
    }

    const serviceWorkerRegistration = await registerFirebaseServiceWorker();

    // Initialize Firebase once and reuse it across re-renders.
    const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
    const messaging = getMessaging(app);

    try {
      const permission = await Notification.requestPermission();

      if (permission === 'granted') {
        const token = await getToken(messaging, {
          vapidKey: firebaseEnv.vapidKey,
          serviceWorkerRegistration: serviceWorkerRegistration || undefined,
        });

        if (token) {
          console.log('Firebase token obtained:', token);
          return { success: true, token, messaging };
        }
        return { success: false, reason: 'token_unavailable' };
      }

      if (permission === 'denied') {
        console.warn('Notification permission denied by user');
        return { success: false, reason: 'permission_denied' };
      }

      return { success: false, reason: 'permission_dismissed' };
    } catch (error) {
      console.error('Error getting Firebase token:', error);
      return { success: false, error };
    }
  } catch (error) {
    console.error('Firebase initialization failed:', error);
    return { success: false, error };
  }
}

/**
 * Initialize Firebase Cloud Messaging
 * Call this once when the app starts
 */
export async function initializeFirebase() {
  if (!firebaseInitPromise) {
    firebaseInitPromise = initializeFirebaseInternal();
  }
  return firebaseInitPromise;
}

/**
 * Handle incoming messages when the app is in foreground
 */
export async function setupMessageHandler(messaging) {
  if (!isFirebaseMessagingConfigured || foregroundHandlerAttached) {
    return;
  }

  if (typeof window === 'undefined' || typeof Notification === 'undefined') {
    return;
  }

  try {
    const { onMessage } = await import('firebase/messaging');
    
    foregroundHandlerAttached = true;
    onMessage(messaging, (payload) => {
      console.log('Message received in foreground:', payload);
      
      const notificationTitle = payload.notification?.title || 'Notification';
      const notificationOptions = {
        body: payload.notification?.body || '',
        icon: '/logo.png',
        badge: '/badge.png',
        tag: payload.data?.type || 'default',
        data: payload.data || {}
      };

      // Show notification
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then(() => {
          new Notification(notificationTitle, notificationOptions);
        });
      }

      // You can also dispatch a custom event or trigger Redux to update UI
      window.dispatchEvent(new CustomEvent('firebase-notification', {
        detail: payload
      }));
    });
  } catch (error) {
    foregroundHandlerAttached = false;
    console.error('Error setting up message handler:', error);
  }
}
