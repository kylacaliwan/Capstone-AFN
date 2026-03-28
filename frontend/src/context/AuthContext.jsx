import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL, clearStoredAuth } from '../api/core';
import { deregisterFCMToken, getSavedFCMToken, registerFCMToken } from '../services/firebaseService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // Rehydrate from localStorage on mount
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('afn_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => localStorage.getItem('afn_token') || null);

  // Keep Axios default header in sync with token state
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Token ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  /**
   * Authenticate against the Django backend.
   * Returns { success: true } or { success: false, message: string }
   */
  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/users/login/`, { username, password });
      const { user: userData, token: authToken } = response.data;

      localStorage.setItem('afn_token', authToken);
      localStorage.setItem('afn_user', JSON.stringify(userData));

      setToken(authToken);
      setUser(userData);

      // Register FCM token in background (don't block login)
      const fcmToken = localStorage.getItem('afn_fcm_token');
      if (fcmToken) {
        setTimeout(() => {
          registerFCMToken(fcmToken, `Browser - ${navigator.userAgent.split(' ').pop()}`, 'web').catch(() => {});
        }, 500);
      }

      return { success: true };
    } catch (err) {
      const message =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Invalid username or password';
      return { success: false, message };
    }
  };

  const logout = () => {
    const authToken = token;
    const fcmToken = getSavedFCMToken();

    if (authToken && fcmToken) {
      deregisterFCMToken(fcmToken, authToken).catch(() => {});
    }

    // Best-effort server-side token invalidation
    if (authToken) {
      axios.post(
        `${API_BASE_URL}/users/logout/`,
        {},
        {
          headers: {
            Authorization: `Token ${authToken}`
          }
        }
      ).catch(() => {});
    }

    clearStoredAuth();
    setToken(null);
    setUser(null);
  };

  /**
   * Register a new user account.
   * Returns { success: true } or { success: false, message: string }
   */
  const register = async (userData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/users/register/`, userData);
      const { user: newUser, token: authToken } = response.data;

      localStorage.setItem('afn_token', authToken);
      localStorage.setItem('afn_user', JSON.stringify(newUser));

      setToken(authToken);
      setUser(newUser);

      // Register FCM token in background (don't block registration)
      const fcmToken = localStorage.getItem('afn_fcm_token');
      if (fcmToken) {
        setTimeout(() => {
          registerFCMToken(fcmToken, `Browser - ${navigator.userAgent.split(' ').pop()}`, 'web').catch(() => {});
        }, 500);
      }

      return { success: true };
    } catch (err) {
      // Extract error messages from backend validation
      const errorData = err.response?.data;
      let message = 'Registration failed. Please try again.';

      if (typeof errorData === 'object') {
        // Check for specific field errors
        if (errorData.username) {
          message = `Username: ${Array.isArray(errorData.username) ? errorData.username[0] : errorData.username}`;
        } else if (errorData.email) {
          message = `Email: ${Array.isArray(errorData.email) ? errorData.email[0] : errorData.email}`;
        } else if (errorData.password) {
          message = `Password: ${Array.isArray(errorData.password) ? errorData.password[0] : errorData.password}`;
        } else if (errorData.detail) {
          message = errorData.detail;
        }
      }

      return { success: false, message };
    }
  };

  const isAuthenticated = !!user && !!token;

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    // Fallback for cases where hook is called outside provider or during initialization
    return { user: null, token: null, isAuthenticated: false, login: async () => {}, logout: () => {}, register: async () => {} };
  }
  return context;
};
