import { api } from '../api/api';

/**
 * Register a Firebase Cloud Messaging token with the backend
 */
export const registerFCMToken = async (fcmToken, deviceName = '', deviceType = 'web') => {
  try {
    const response = await api.post(
      '/notifications/firebase-tokens/register/',
      {
        fcm_token: fcmToken,
        device_name: deviceName,
        device_type: deviceType
      }
    );
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Failed to register FCM token:', error);
    return { success: false, error };
  }
};

/**
 * Deregister a Firebase Cloud Messaging token
 */
export const deregisterFCMToken = async (fcmToken, authToken = null) => {
  try {
    const response = await api.post(
      '/notifications/firebase-tokens/deregister/',
      { fcm_token: fcmToken },
      authToken
        ? {
            headers: {
              Authorization: `Token ${authToken}`
            }
          }
        : undefined
    );
    return { success: true };
  } catch (error) {
    console.error('Failed to deregister FCM token:', error);
    return { success: false, error };
  }
};

/**
 * Get all FCM tokens for the current user
 */
export const getUserFCMTokens = async () => {
  try {
    const response = await api.get('/notifications/firebase-tokens/');
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Failed to get FCM tokens:', error);
    return { success: false, error };
  }
};

/**
 * Store FCM token in localStorage
 */
export const saveFCMTokenLocally = (token) => {
  localStorage.setItem('afn_fcm_token', token);
};

/**
 * Get stored FCM token from localStorage
 */
export const getSavedFCMToken = () => {
  return localStorage.getItem('afn_fcm_token');
};

/**
 * Remove stored FCM token
 */
export const removeSavedFCMToken = () => {
  localStorage.removeItem('afn_fcm_token');
};
