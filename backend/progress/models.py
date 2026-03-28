from django.db import models
from django.conf import settings  # for custom User model
from services.models import ServiceTicket  # import ServiceTicket from its app

class TicketProgress(models.Model):
    ticket = models.ForeignKey(
        ServiceTicket, 
        on_delete=models.CASCADE, 
        related_name='progress_updates'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # use custom User model
        on_delete=models.SET_NULL, 
        null=True
    )
    progress_status = models.CharField(max_length=100)  # Assigned, On Site, Work Started, Work Completed
    comment = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.progress_status} for Ticket {self.ticket.id} by {self.updated_by}"