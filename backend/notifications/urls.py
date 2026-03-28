from django.urls import path, include
from rest_framework import routers
from .views import NotificationViewSet, FirebaseTokenViewSet

router = routers.DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'firebase-tokens', FirebaseTokenViewSet, basename='firebase-token')

urlpatterns = [
    path('', include(router.urls)),
]
