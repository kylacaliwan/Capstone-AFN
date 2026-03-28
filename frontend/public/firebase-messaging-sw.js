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

if (isConfigured) {
  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');

  firebase.initializeApp(firebaseConfig);

  const messaging = firebase.messaging();

  // Handle background messages
  messaging.onBackgroundMessage((payload) => {
    console.log('Background message received:', payload);

    const notificationTitle = payload.notification?.title || 'AFN Notification';
    const notificationOptions = {
      body: payload.notification?.body || 'You have a new notification',
      icon: '/logo.png',
      badge: '/badge.png',
      tag: payload.data?.type || 'default',
      data: payload.data || {},
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
  });

  // Handle notification clicks
  self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event.notification);

    event.notification.close();

    const data = event.notification.data;
    let actionUrl = '/';

    if (data.action === 'view_ticket' && data.ticket_id) {
      actionUrl = `/admin/service-tickets`;
    } else if (data.action === 'view_inventory' && data.inventory_item_id) {
      actionUrl = `/admin/inventory`;
    } else if (data.action === 'view_job' && data.job_id) {
      actionUrl = `/technician/my-jobs`;
    }

    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((clientList) => {
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url === actionUrl && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(actionUrl);
        }
      })
    );
  });
} else {
  console.warn('Firebase messaging service worker is disabled until real Firebase config is provided.');
}
