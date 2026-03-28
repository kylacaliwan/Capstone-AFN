from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
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
    status = models.CharField(max_length=20, default='active')  # active, inactive
    
    # Technician-specific fields
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return self.username
