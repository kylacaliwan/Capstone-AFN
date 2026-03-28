from django.urls import path, include
from rest_framework import routers
from .views import TicketProgressViewSet

router = routers.DefaultRouter()
router.register(r'progress', TicketProgressViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
