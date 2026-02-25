from django.urls import re_path
from .consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'authorswap/ws/notification/$', NotificationConsumer.as_asgi()),
]
