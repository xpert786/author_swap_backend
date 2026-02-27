import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser


from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from core.models import ChatMessage, Profile, SwapRequest
from django.db.models import Q

User = get_user_model()

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
                self.user = await self.get_user(self.user_id)
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

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

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
    """
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        self.partner_id = self.scope['url_route']['kwargs'].get('partner_id')
        self.user_id = None

        if token:
            try:
                access_token = AccessToken(token)
                self.user_id = access_token['user_id']
                self.user = await self.get_user(self.user_id)
            except Exception:
                pass

        if self.user_id and self.partner_id:
            # Check if user can chat with partner
            can_chat = await self.check_can_chat(self.user_id, self.partner_id)
            if not can_chat:
                await self.close()
                return

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

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def check_can_chat(self, user1_id, user2_id):
        try:
            user1 = User.objects.get(id=user1_id)
            user2 = User.objects.get(id=user2_id)
            
            # Check if they are friends
            profile1 = Profile.objects.filter(user=user1).first()
            profile2 = Profile.objects.filter(user=user2).first()
            if profile1 and profile2 and profile1.friends.filter(id=profile2.id).exists():
                return True
            
            # Check if they are swap partners (any swap relationship, excluding rejected)
            is_partner = SwapRequest.objects.filter(
                (Q(requester=user1) & Q(slot__user=user2)) |
                (Q(requester=user2) & Q(slot__user=user1))
            ).exclude(status='rejected').exists()
            
            return is_partner
        except Exception:
            return False

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'chat')

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user_id,
                    'is_typing': data.get('is_typing', True),
                }
            )
        else:
            message_text = data.get('message')
            if message_text:
                # Save message to database
                message = await self.save_message(self.user_id, self.partner_id, message_text)
                
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_text,
                        'sender_id': self.user_id,
                        'created_at': message.created_at.isoformat()
                    }
                )

    async def chat_message(self, event):
        # Format for frontend: type 'chat' as expected by CommunicationTools.jsx
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'created_at': event['created_at']
        }))

    async def typing_indicator(self, event):
        # Don't send typing indicator back to the sender
        if str(event.get('user_id')) != str(self.user_id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
            }))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, text):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        return ChatMessage.objects.create(sender=sender, recipient=receiver, content=text)
