from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('ticket_assigned', 'Ticket Assigned'),
        ('status_update', 'Status Update'),
        ('reminder', 'Reminder'),
        ('urgent', 'Urgent Alert'),
        ('task_completed', 'Task Completed'),
        ('customer_inquiry', 'Customer Inquiry'),
        ('message', 'New Message'),
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    ticket = models.ForeignKey(
        'services.ServiceTicket',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    request = models.ForeignKey(
        'services.ServiceRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    message = models.TextField()
    title = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='message')
    status = models.CharField(max_length=50, default="unread")  # unread/read
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Channel preferences
    send_email = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.type} for {self.user.username}"
    
    def mark_as_read(self):
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['-created_at']


class NotificationTemplate(models.Model):
    """Pre-defined notification message templates"""
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    variables = models.JSONField(default=list, help_text="e.g., ['technician_name', 'service_type']")
    
    def __str__(self):
        return self.name


class NotificationLog(models.Model):
    """Track all notification sending attempts"""
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name='log')
    email_status = models.CharField(max_length=50, default='pending')  # pending, sent, failed
    sms_status = models.CharField(max_length=50, default='pending')
    email_response = models.TextField(blank=True, null=True)
    sms_response = models.TextField(blank=True, null=True)
    last_attempt = models.DateTimeField(auto_now=True)
    attempt_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Log for Notification {self.notification.id}"


class FirebaseToken(models.Model):
    """Store Firebase Cloud Messaging tokens for push notifications"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='firebase_tokens'
    )
    fcm_token = models.TextField(unique=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(
        max_length=20,
        choices=[('web', 'Web'), ('ios', 'iOS'), ('android', 'Android')],
        default='web'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_used']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"FCM Token for {self.user.username} ({self.device_type})"