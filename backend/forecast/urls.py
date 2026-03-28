from django.urls import path, include
from rest_framework import routers
from .views import DemandForecastViewSet

router = routers.DefaultRouter()
router.register(r'forecasts', DemandForecastViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
