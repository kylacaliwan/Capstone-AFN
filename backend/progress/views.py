from rest_framework import viewsets, permissions
from .models import TicketProgress
from .serializers import TicketProgressSerializer

class TicketProgressViewSet(viewsets.ModelViewSet):
    queryset = TicketProgress.objects.all()
    serializer_class = TicketProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
