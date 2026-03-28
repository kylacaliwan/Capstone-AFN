import os
import logging
from twilio.rest import Client
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms_notification(message, to_phone_numbers=None):
    """
    Send SMS notification using Twilio
    """
    if not all([
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
        settings.TWILIO_PHONE_NUMBER
    ]):
        logger.warning("Twilio credentials not configured. SMS notification skipped.")
        return False

    if not to_phone_numbers:
        to_phone_numbers = settings.ADMIN_PHONE_NUMBERS

    if not to_phone_numbers:
        logger.warning("No phone numbers configured for SMS notifications.")
        return False

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        for phone_number in to_phone_numbers:
            if phone_number.strip():
                message_obj = client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone_number.strip()
                )
                logger.info(f"SMS sent successfully to {phone_number}: {message_obj.sid}")

        return True

    except Exception as e:
        logger.error(f"Failed to send SMS notification: {str(e)}")
        return False

def send_low_stock_alert(inventory_item):
    """
    Send SMS alert for low stock items
    """
    message = f"ALERT: Low stock for {inventory_item.name} (ID: {inventory_item.id}). Current: {inventory_item.available_quantity}, Threshold: {inventory_item.minimum_stock}"

    return send_sms_notification(message)

def send_inventory_update_alert(inventory_item, action, quantity, user=None):
    """
    Send SMS alert for inventory updates
    """
    user_info = f" by {user.username}" if user else ""
    message = f"INVENTORY UPDATE: {action} {quantity} units of {inventory_item.name} (ID: {inventory_item.id}){user_info}. New quantity: {inventory_item.available_quantity}"

    return send_sms_notification(message)