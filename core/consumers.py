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
        print(f"DEBUG: WebSocket connecting for partner_id={self.scope['url_route']['kwargs'].get('partner_id')}")
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
                print(f"DEBUG: Authenticated user_id={self.user_id}")
            except Exception as e:
                print(f"DEBUG: Token authentication failed: {e}")

        if self.user_id and self.partner_id:
            try:
                # Create a deterministic room name for the two users
                uid1 = min(int(self.user_id), int(self.partner_id))
                uid2 = max(int(self.user_id), int(self.partner_id))
                self.room_group_name = f'chat_{uid1}_{uid2}'
                print(f"DEBUG: Room name: {self.room_group_name}")

                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
                print(f"DEBUG: WebSocket accepted")
            except Exception as e:
                print(f"DEBUG: WebSocket accept error: {e}")
                await self.close()
        else:
            print(f"DEBUG: Connection rejected: user_id={self.user_id}, partner_id={self.partner_id}")
            await self.close()

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    async def disconnect(self, close_code):
        print(f"DEBUG: WebSocket disconnected code={close_code}")
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        print(f"DEBUG: Received WebSocket data: {text_data}")
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
        elif msg_type == 'broadcast_message':
            # Directly format and forward the message created by the REST API
            message_data = data.get('message_data', {})
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data.get('content') or message_data.get('text', ''),
                    'sender_id': self.user_id,
                    'created_at': message_data.get('created_at'),
                    'is_file': message_data.get('is_file', False),
                    'attachment': message_data.get('attachment'),
                    'sender_name': message_data.get('sender_name', ''),
                }
            )
        else:
            message_text = data.get('message')
            if message_text:
                # Save message to database
                message = await self.save_message(self.user_id, self.partner_id, message_text)
                
                if message:
                    print(f"DEBUG: Message saved ID={message.id}")
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
                else:
                    print(f"DEBUG: Failed to save message")

    async def chat_message(self, event):
        print(f"DEBUG: Broadcasting message: {event.get('message', '')}")
        # Build the payload, keeping all fields sent from the views
        payload = {
            'type': 'chat_message', # Must match what CommunicationTools.jsx expects
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'is_file': event.get('is_file', False),
            'attachment': event.get('attachment'),
            'created_at': event.get('created_at')
        }
        await self.send(text_data=json.dumps(payload))


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
        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
            return ChatMessage.objects.create(sender=sender, recipient=receiver, content=text)
        except Exception as e:
            print(f"DEBUG: save_message error: {e}")
            return None
