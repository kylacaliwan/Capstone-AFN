from rest_framework import viewsets, permissions
from .models import ServiceHistory
from .serializers import ServiceHistorySerializer

class ServiceHistoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceHistory.objects.all()
    serializer_class = ServiceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
