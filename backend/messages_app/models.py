from django.db import models
from django.conf import settings  # <-- for custom User
from services.models import ServiceTicket  # <-- import ServiceTicket from services app

class Message(models.Model):
    ticket = models.ForeignKey(
        ServiceTicket, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # use custom user model
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # use custom user model
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='received_messages'
    )
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver} for Ticket {self.ticket.id}"