# Firebase Cloud Messaging Setup Guide

This guide will help you set up Firebase Cloud Messaging (FCM) for push notifications in your AFN Service Management application.

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a new project"
3. Enter your project name: "AFN Service Management"
4. Follow the setup wizard
5. Note your **Project ID** (you'll need this later)

## Step 2: Set Up Firebase Web App

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Click on **"Your apps"** tab
3. Click **"</>Web"** to create a new web app
4. Register your app with a nickname like "AFN Web"
5. Copy the Firebase config (you'll see something like this):
   ```javascript
   {
     apiKey: "YOUR_API_KEY",
     authDomain: "your-project.firebaseapp.com",
     projectId: "your-project-id",
     storageBucket: "your-project.appspot.com",
     messagingSenderId: "YOUR_SENDER_ID",
     appId: "YOUR_APP_ID"
   }
   ```

## Step 3: Set Up Cloud Messaging

6. In Firebase Console, go to **Cloud Messaging** tab
7. Click **"Create Service Account"** (or go to Google Cloud Console)
8. Generate a new **private key** (JSON format)
9. Download the JSON file - you'll need this for the backend

## Step 4: Update .env File (Frontend)

Create/update your `.env` file in the `frontend/` directory:

```env
VITE_FIREBASE_API_KEY=YOUR_API_KEY
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=YOUR_SENDER_ID
VITE_FIREBASE_APP_ID=YOUR_APP_ID
VITE_FIREBASE_VAPID_KEY=YOUR_VAPID_KEY
```

### Getting the VAPID Key:

1. In Firebase Console → Cloud Messaging
2. Click on **"Generate key pair"** (Web Push Certificates)
3. Copy the key pair provided

## Step 5: Update .env File (Backend)

Update your `backend/.env` file with Firebase Server credentials:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=from-your-service-account-json
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...copy the full private key...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=from-service-account-json
```

## Step 6: Install Firebase Admin SDK

```bash
cd backend
pip install firebase-admin
```

## Step 7: Install Firebase Web SDK (Frontend)

```bash
cd frontend
npm install firebase
```

## Step 8: Install/Update Service Worker

The file `public/firebase-messaging-sw.js` is already created. Update it with your Firebase Web config:

```javascript
firebase.initializeApp({
  apiKey: "YOUR_API_KEY",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
});
```

## Step 9: Run the Application

### Backend:
```bash
cd backend
python manage.py runserver
```

### Frontend:
```bash
cd frontend
npm run dev
```

## How It Works

### Frontend Flow:
1. App initializes → Requests notification permission
2. User grants permission → Gets FCM token from Firebase
3. Token is stored locally and sent to backend
4. Backend stores token in `FirebaseToken` model
5. When notification is sent → Firebase sends to stored tokens
6. Browser shows notification (even when app is closed)

### Backend Flow:
1. Admin creates a low-stock inventory alert
2. System calls `send_low_stock_notification(item)`
3. Gets all admin users and their Firebase tokens
4. Uses Firebase Admin SDK to send messages to tokens
5. Notifications appear on user's device

## API Endpoints

### Register FCM Token
```
POST /api/notifications/firebase-tokens/register/
Body: {
  "fcm_token": "your-fcm-token",
  "device_name": "Chrome on Windows",
  "device_type": "web"
}
```

### Deregister FCM Token
```
POST /api/notifications/firebase-tokens/deregister/
Body: {
  "fcm_token": "your-fcm-token"
}
```

### Get All User Tokens
```
GET /api/notifications/firebase-tokens/
```

## Testing Push Notifications

1. **From Firebase Console:**
   - Cloud Messaging → Send test message
   - Select your app
   - Send to a device FCM token

2. **From Backend:**
   ```python
   from notifications.firebase_utils import send_push_notification
   
   send_push_notification(
       title="Test Notification",
       body="This is a test",
       user_id=1
   )
   ```

## Troubleshooting

### "Firebase not initialized"
- Check your `.env` file has all required variables
- Restart the development server

### "Notification permission denied"
- User rejected permissions → App can't send notifications
- User can enable in browser settings

### "Invalid FCM token"
- Token is no longer valid (user uninstalled/cleared data)
- Backend automatically marks it as inactive

### "Service Worker not registering"
- Check `public/firebase-messaging-sw.js` exists
- Update browser → Some browsers require HTTPS for service workers

## Production Notes

- Always use **HTTPS** in production (required for service workers)
- Environment variables must be properly set
- Consider using CI/CD secrets management
- Regularly test notification delivery
- Monitor Firebase quota usage in Google Cloud Console

For more details, visit: [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
