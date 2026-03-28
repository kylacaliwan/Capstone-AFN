from django.db import models
from django.conf import settings  # for custom User model
from services.models import ServiceTicket, ServiceType  # adjust import path as needed

class ServiceHistory(models.Model):
    ticket = models.ForeignKey(ServiceTicket, on_delete=models.CASCADE, related_name='history')
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # safer for custom User
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'technician'},
        related_name='service_histories'
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='service_histories'
    )
    completion_date = models.DateTimeField()
    service_duration = models.IntegerField(help_text="Duration in minutes")
    customer_rating = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"History for Ticket #{self.ticket.id} - {self.service_type.name if self.service_type else 'Unknown'}"