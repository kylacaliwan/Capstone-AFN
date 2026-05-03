from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('superadmin', 'Superadmin'),
        ('admin', 'Admin'),
        ('follow_up', 'Service Follow-Up'),
        ('supervisor', 'Supervisor'),
        ('technician', 'Technician'),
        ('client', 'Client'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    admin_scope = models.CharField(
        max_length=50,
        choices=[
            ('service_follow_up', 'Service Follow-Up'),
            ('task_management', 'Task Management'),
            ('operations', 'Operations Management'),
            ('general', 'General Administration')
        ],
        blank=True,
        null=True,
        default='general'
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Technician-specific fields
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['role', 'is_available', 'status']),
            models.Index(fields=['role', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]
    
    def __str__(self):
        return self.username


class UserCapabilityGrant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='capability_grants',
    )
    capability_code = models.CharField(max_length=100)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_capability_records',
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Capability Grant'
        verbose_name_plural = 'User Capability Grants'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'capability_code'],
                name='unique_user_capability_grant',
            )
        ]
        ordering = ['capability_code', 'id']

    def __str__(self):
        return f"{self.user.username} -> {self.capability_code}"


class AdminSettings(models.Model):
    system_name = models.CharField(max_length=255, default='AFN Service Management')
    support_email = models.EmailField(default='support@afnservice.com')
    enable_notifications = models.BooleanField(default=True)
    auto_dispatch_enabled = models.BooleanField(default=False)
    sms_notifications_enabled = models.BooleanField(default=False)
    default_time_zone = models.CharField(max_length=100, default='UTC')
    max_technician_assignments = models.PositiveSmallIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_settings_updates',
    )

    class Meta:
        verbose_name = 'Admin Settings'
        verbose_name_plural = 'Admin Settings'

    def __str__(self):
        return 'Admin Settings'
