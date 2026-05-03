// Firebase Service Worker for handling push notifications
// This file needs to be in the public folder at /firebase-messaging-sw.js

const searchParams = new URL(self.location.href).searchParams;
const firebaseConfig = {
  apiKey: searchParams.get('apiKey') || '',
  authDomain: searchParams.get('authDomain') || '',
  projectId: searchParams.get('projectId') || '',
  storageBucket: searchParams.get('storageBucket') || '',
  messagingSenderId: searchParams.get('messagingSenderId') || '',
  appId: searchParams.get('appId') || '',
};

const isConfigured = Object.values(firebaseConfig).every(Boolean);
const defaultNotificationIcon = '/favicon.svg';

const resolveActionUrl = (data = {}) => {
  if (data.url) {
    return data.url;
  }

  if (data.click_action) {
    return data.click_action;
  }

  if (data.action === 'view_ticket' && data.ticket_id) {
    return '/admin/service-tickets';
  }

  if (data.action === 'view_inventory' && data.inventory_item_id) {
    return '/admin/inventory';
  }

  if (data.action === 'view_job' && data.job_id) {
    return '/technician/my-jobs';
  }

  return '/';
};

if (isConfigured) {
  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');

  firebase.initializeApp(firebaseConfig);

  const messaging = firebase.messaging();

  // Handle background messages
  messaging.onBackgroundMessage((payload) => {
    console.log('Background message received:', payload);

    const payloadData = payload.data || {};
    const notificationTitle = payload.notification?.title || 'AFN Notification';
    const notificationOptions = {
      body: payload.notification?.body || 'You have a new notification',
      icon: payload.notification?.icon || payloadData.icon || defaultNotificationIcon,
      badge: payloadData.badge || payloadData.icon || defaultNotificationIcon,
      tag: payloadData.type || 'default',
      data: payloadData,
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
  });

  // Handle notification clicks
  self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event.notification);

    event.notification.close();

    const data = event.notification.data;
    const actionUrl = new URL(resolveActionUrl(data), self.location.origin);

    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          const clientUrl = new URL(client.url);
          const isSamePath = clientUrl.origin === actionUrl.origin && clientUrl.pathname === actionUrl.pathname;

          if (isSamePath && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(actionUrl.toString());
        }
      })
    );
  });
} else {
  console.warn('Firebase messaging service worker is disabled until real Firebase config is provided.');
}
