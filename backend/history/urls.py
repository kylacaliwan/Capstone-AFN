from django.urls import path, include
from rest_framework import routers
from .views import ServiceHistoryViewSet

router = routers.DefaultRouter()
router.register(r'history', ServiceHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
