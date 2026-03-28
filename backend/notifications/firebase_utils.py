import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    if not firebase_admin.apps:
        cred = credentials.Certificate({
            'type': 'service_account',
            'project_id': settings.FIREBASE_PROJECT_ID,
            'private_key_id': settings.FIREBASE_PRIVATE_KEY_ID,
            'private_key': settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
            'client_email': settings.FIREBASE_CLIENT_EMAIL,
            'client_id': settings.FIREBASE_CLIENT_ID,
            'auth_uri': settings.FIREBASE_AUTH_URI,
            'token_uri': settings.FIREBASE_TOKEN_URI,
            'auth_provider_x509_cert_url': settings.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
            'client_x509_cert_url': settings.FIREBASE_CLIENT_X509_CERT_URL,
        })
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.warning(f"Firebase initialization failed (development mode): {e}")


def send_push_notification(title, body, fcm_token=None, user_id=None, data=None):
    """
    Send push notification via Firebase Cloud Messaging
    
    Args:
        title: Notification title
        body: Notification body
        fcm_token: Individual FCM token (optional)
        user_id: User ID to get all their tokens (optional)
        data: Additional data payload (optional)
    
    Returns:
        bool: True if sent successfully
    """
    if not fcm_token and not user_id:
        logger.warning("Either fcm_token or user_id must be provided")
        return False

    try:
        tokens = []
        
        if fcm_token:
            tokens = [fcm_token]
        elif user_id:
            # Get all tokens for the user
            from .models import FirebaseToken
            user_tokens = FirebaseToken.objects.filter(user_id=user_id, is_active=True)
            tokens = [token.fcm_token for token in user_tokens]

        if not tokens:
            logger.warning(f"No active FCM tokens found for user_id={user_id}")
            return False

        # Prepare notification
        notification = messaging.Notification(
            title=title,
            body=body,
        )

        # Send to all tokens
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=notification,
                    data=data or {},
                    token=token,
                )
                response = messaging.send(message)
                logger.info(f"Push notification sent successfully: {response}")
            except Exception as e:
                logger.error(f"Failed to send notification to token {token}: {e}")
                # Mark token as inactive if it's invalid
                if "registration token is invalid" in str(e).lower():
                    from .models import FirebaseToken
                    try:
                        FirebaseToken.objects.filter(fcm_token=token).update(is_active=False)
                    except:
                        pass

        return True

    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


def send_low_stock_notification(inventory_item):
    """
    Send push notification for low stock items
    """
    from users.models import User
    
    message = f"Low stock alert for {inventory_item.name}"
    body = f"Current: {inventory_item.available_quantity}, Threshold: {inventory_item.minimum_stock}"
    
    # Send to all admin users
    admin_users = User.objects.filter(role='admin', is_active=True)
    
    for admin in admin_users:
        send_push_notification(
            title=message,
            body=body,
            user_id=admin.id,
            data={
                'type': 'low_stock_alert',
                'inventory_item_id': str(inventory_item.id),
                'action': 'view_inventory'
            }
        )


def send_service_ticket_notification(service_ticket, recipient_user):
    """
    Send push notification for service ticket updates
    """
    message = f"Service Ticket #{service_ticket.id} Update"
    body = str(service_ticket.status or 'Updated')
    
    send_push_notification(
        title=message,
        body=body,
        user_id=recipient_user.id,
        data={
            'type': 'service_ticket_update',
            'ticket_id': str(service_ticket.id),
            'status': service_ticket.status,
            'action': 'view_ticket'
        }
    )
