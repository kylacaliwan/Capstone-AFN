from rest_framework import viewsets, permissions
from .models import DemandForecast
from .serializers import DemandForecastSerializer

class DemandForecastViewSet(viewsets.ModelViewSet):
    queryset = DemandForecast.objects.all()
    serializer_class = DemandForecastSerializer
    permission_classes = [permissions.IsAuthenticated]
