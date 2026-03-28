import { useEffect, useState } from 'react';
import { initializeFirebase, setupMessageHandler } from '../services/firebaseConfig';
import { registerFCMToken, saveFCMTokenLocally, getSavedFCMToken } from '../services/firebaseService';

/**
 * Hook to initialize Firebase and handle push notifications
 */
export function useFirebase() {
  const [firebaseReady, setFirebaseReady] = useState(false);
  const [fcmToken, setFcmToken] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initFirebase = async () => {
      try {
        // Check if already initialized
        const savedToken = getSavedFCMToken();
        if (savedToken) {
          setFcmToken(savedToken);
          const existingSession = await initializeFirebase();
          if (existingSession.success && existingSession.messaging) {
            await setupMessageHandler(existingSession.messaging);
          }
          if (existingSession.success && existingSession.token && existingSession.token !== savedToken) {
            setFcmToken(existingSession.token);
            saveFCMTokenLocally(existingSession.token);
          }
          setFirebaseReady(existingSession.success);
          if (!existingSession.success) {
            setError(existingSession.error || existingSession.reason || null);
          }
          return;
        }

        // Initialize Firebase
        const result = await initializeFirebase();
        
        if (result.success && result.token) {
          setFcmToken(result.token);
          saveFCMTokenLocally(result.token);
          
          // Setup message handler for foreground messages
          if (result.messaging) {
            await setupMessageHandler(result.messaging);
          }
          
          setFirebaseReady(true);
        } else {
          setError(result.error || result.reason);
        }
      } catch (err) {
        console.error('Firebase setup error:', err);
        setError(err.message);
      }
    };

    initFirebase();
  }, []);

  /**
   * Register the FCM token with the backend
   */
  const registerToken = async (userId = null) => {
    if (!fcmToken) {
      console.warn('No FCM token available');
      return false;
    }

    try {
      const result = await registerFCMToken(
        fcmToken,
        `Browser - ${navigator.userAgent.split(' ').pop()}`,
        'web'
      );
      
      return result.success;
    } catch (err) {
      console.error('Error registering FCM token with backend:', err);
      return false;
    }
  };

  return {
    firebaseReady,
    fcmToken,
    error,
    registerToken
  };
}
