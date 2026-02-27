# core/routing.py
from django.urls import path
from .consumers import NotificationConsumer, ChatConsumer

websocket_urlpatterns = [
    path("authorswap/ws/notifications/", NotificationConsumer.as_asgi()),
    path("authorswap/ws/chat/<int:partner_id>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/chat/<int:partner_id>/", ChatConsumer.as_asgi()),
]
