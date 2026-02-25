# core/routing.py
from django.urls import path
from .consumers import NotificationConsumer

websocket_urlpatterns = [
    path("authorswap/ws/notification/", NotificationConsumer.as_asgi()),
]
