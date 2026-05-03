from django.urls import path
from .consumers import MessageConsumer

websocket_urlpatterns = [
    path('ws/messages/', MessageConsumer.as_asgi()),
]
