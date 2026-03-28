from django.urls import path, include
from rest_framework import routers
from .views import UserViewSet, AuthViewSet

router = routers.DefaultRouter()
router.register(r'', UserViewSet)
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]
