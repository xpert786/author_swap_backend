import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SwapRequest, Notification, Profile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import NotificationSerializer

User = get_user_model()


def _sync_userprofile_to_core(user_profile, core_profile):
    """Copy shared fields from authentication.UserProfile → core.Profile."""
    changed = False

    if user_profile.pen_name and user_profile.pen_name != core_profile.name:
        core_profile.name = user_profile.pen_name
        changed = True
    if user_profile.author_bio and user_profile.author_bio != core_profile.bio:
        core_profile.bio = user_profile.author_bio
        changed = True
    if user_profile.primary_genre and user_profile.primary_genre != core_profile.primary_genre:
        core_profile.primary_genre = user_profile.primary_genre
        changed = True
    if user_profile.profile_photo and user_profile.profile_photo != core_profile.profile_picture:
        core_profile.profile_picture = user_profile.profile_photo
        changed = True

    # Social URLs
    for src, dst in [
        ('website_url', 'website'),
        ('facebook_url', 'facebook_url'),
        ('instagram_url', 'instagram_url'),
        ('tiktok_url', 'tiktok_url'),
    ]:
        val = getattr(user_profile, src, None)
        if val and val != getattr(core_profile, dst, None):
            setattr(core_profile, dst, val)
            changed = True

    if changed:
        core_profile.save()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a core.Profile when a new user registers."""
    if created:
        core_profile, _ = Profile.objects.get_or_create(
            user=instance,
            defaults={
                'name': instance.username,
                'email': instance.email or '',
                'primary_genre': '',
                'bio': '',
            }
        )
        # If UserProfile was already created (by the auth signal), sync its data
        if hasattr(instance, 'profile') and instance.profile:
            _sync_userprofile_to_core(instance.profile, core_profile)


# Import UserProfile here to avoid circular imports
from authentication.models import UserProfile


@receiver(post_save, sender=UserProfile)
def sync_user_profile_to_core_profile(sender, instance, **kwargs):
    """Whenever UserProfile is updated (e.g. via admin), sync to core.Profile."""
    core_profile = Profile.objects.filter(user=instance.user).first()
    if core_profile:
        _sync_userprofile_to_core(instance, core_profile)

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