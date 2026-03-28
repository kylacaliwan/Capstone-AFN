from django.db import models
from services.models import ServiceType  # <-- import your ServiceType model

class DemandForecast(models.Model):
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='forecast_demands')
    predicted_demand = models.IntegerField()
    forecast_month = models.CharField(max_length=20)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service_type.name} forecast for {self.forecast_month}"
