import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SwapRequest, Notification, Profile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import NotificationSerializer

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a core.Profile when a new user registers."""
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'name': instance.username,
                'email': instance.email or '',
                'primary_genre': '',
                'bio': '',
            }
        )

@receiver(post_save, sender=SwapRequest)
def notify_new_swap(sender, instance, created, **kwargs):
    if created: 
        Notification.objects.create(
            recipient=instance.slot.user,
            title="New Swap Request 🎉",
            badge="SWAP",
            message=f"Great news! {instance.requester.username} has requested a swap for your {instance.slot.get_preferred_genre_display()} newsletter slot scheduled on {instance.slot.send_date}.",
            action_url=f"/dashboard/swaps/{instance.id}/"
        )

@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        
        group_name = f'user_{instance.recipient.id}_notifications'
        
        try:
            data = NotificationSerializer(instance).data
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'send_notification',
                    'notification': data
                }
            )
        except Exception:
            pass