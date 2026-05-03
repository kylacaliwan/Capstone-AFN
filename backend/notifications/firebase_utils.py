import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ModuleNotFoundError:
    firebase_admin = None
    credentials = None
    messaging = None
    logger.warning("firebase_admin is not installed; push notifications are disabled.")

# Initialize Firebase Admin SDK
try:
    if firebase_admin and not firebase_admin.apps:
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


def _normalize_firebase_data(data=None):
    normalized = {}
    for key, value in (data or {}).items():
        if value is None:
            continue
        normalized[str(key)] = str(value)
    return normalized


def create_in_app_notification(*, user, title, body, notification_type='info', ticket=None, request=None):
    from .models import Notification

    return Notification.objects.create(
        user=user,
        ticket=ticket,
        request=request,
        title=title,
        message=body,
        type=notification_type,
    )


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

    if messaging is None:
        logger.warning("Push notification skipped because firebase_admin is unavailable")
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
                    data=_normalize_firebase_data(data),
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


def send_user_notification(
    *,
    user,
    title,
    body,
    notification_type='info',
    data=None,
    ticket=None,
    request=None,
    send_push=True,
):
    """
    Create an in-app notification for one user and optionally push it to all of
    the user's active Firebase devices.
    """
    notification = create_in_app_notification(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        ticket=ticket,
        request=request,
    )

    if send_push:
        payload = _normalize_firebase_data(data)
        payload.setdefault('notification_id', str(notification.id))
        if ticket is not None:
            payload.setdefault('ticket_id', str(ticket.id))
        if request is not None:
            payload.setdefault('request_id', str(request.id))

        send_push_notification(
            title=title,
            body=body,
            user_id=user.id,
            data=payload,
        )

    return notification


def send_team_notification(
    title,
    body,
    *,
    users=None,
    role=None,
    supervisor=None,
    user_ids=None,
    notification_type='info',
    data=None,
    ticket=None,
    request=None,
    send_push=True,
):
    """
    Broadcast a notification to a group of users.

    At least one selector must be provided so we do not accidentally notify
    every active account in the system.
    """
    from users.models import User

    if users is None and role is None and supervisor is None and user_ids is None:
        raise ValueError("send_team_notification requires users, role, supervisor, or user_ids")

    recipients = users if users is not None else User.objects.filter(is_active=True)

    if role is not None:
        recipients = recipients.filter(role=role)

    if user_ids is not None:
        recipients = recipients.filter(id__in=user_ids)

    if supervisor is not None:
        from services.models import ServiceTicket

        supervisor_id = getattr(supervisor, 'id', supervisor)
        technician_ids = (
            ServiceTicket.objects.filter(
                supervisor_id=supervisor_id,
                technician__isnull=False,
            )
            .values_list('technician_id', flat=True)
            .distinct()
        )
        recipients = recipients.filter(id__in=technician_ids)

    recipients = list(recipients.distinct())

    notifications = [
        send_user_notification(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            data=data,
            ticket=ticket,
            request=request,
            send_push=send_push,
        )
        for user in recipients
    ]

    return {
        'success': True,
        'recipient_count': len(recipients),
        'user_ids': [user.id for user in recipients],
        'notifications': notifications,
    }


def send_low_stock_notification(inventory_item):
    """
    Send push notification for low stock items
    """
    from users.models import User
    
    message = f"Low stock alert for {inventory_item.name}"
    body = f"Current: {inventory_item.available_quantity}, Threshold: {inventory_item.minimum_stock}"
    
    # Send to all admin users
    admin_users = User.objects.filter(role__in=['superadmin', 'admin'], is_active=True)

    send_team_notification(
        message,
        body,
        users=admin_users,
        notification_type='warning',
        data={
            'type': 'low_stock_alert',
            'inventory_item_id': str(inventory_item.id),
            'action': 'view_inventory',
        },
    )


def send_service_ticket_notification(service_ticket, recipient_user):
    """
    Send push notification for service ticket updates
    """
    message = f"Service Ticket #{service_ticket.id} Update"
    body = str(service_ticket.status or 'Updated')

    send_user_notification(
        user=recipient_user,
        title=message,
        body=body,
        notification_type='status_update',
        ticket=service_ticket,
        request=service_ticket.request,
        data={
            'type': 'service_ticket_update',
            'ticket_id': str(service_ticket.id),
            'status': service_ticket.status,
            'action': 'view_ticket',
        },
    )
