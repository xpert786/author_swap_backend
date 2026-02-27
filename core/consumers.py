import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        self.user_id = None
        if token:
            try:
                access_token = AccessToken(token)
                self.user_id = access_token['user_id']
            except Exception:
                pass

        if self.user_id:
            self.group_name = f'user_{self.user_id}_notifications'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        notification = event['notification']
        # Send message to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': notification
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat between two users.
    URL: ws://host/authorswap/ws/chat/<partner_id>/?token=<jwt_token>
    
    Creates a shared room for two users based on sorted user IDs:
    chat_<min_id>_<max_id>
    """
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        self.user_id = None
        if token:
            try:
                access_token = AccessToken(token)
                self.user_id = access_token['user_id']
            except Exception:
                pass

        self.partner_id = self.scope['url_route']['kwargs'].get('partner_id')

        if self.user_id and self.partner_id:
            # Create a deterministic room name for the two users
            uid1 = min(int(self.user_id), int(self.partner_id))
            uid2 = max(int(self.user_id), int(self.partner_id))
            self.room_group_name = f'chat_{uid1}_{uid2}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages (for typing indicators, etc.).
        Actual message saving is done via the REST API (SendMessageView).
        """
        data = json.loads(text_data)
        msg_type = data.get('type', 'typing')

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user_id,
                    'is_typing': data.get('is_typing', True),
                }
            )

    async def chat_message(self, event):
        """Receive a chat message from the channel layer (sent by SendMessageView)."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        """Broadcast typing indicator to the chat room."""
        # Don't send typing indicator back to the sender
        if str(event.get('user_id')) != str(self.user_id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
            }))
