from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SwapRequest, Notification

@receiver(post_save, sender=SwapRequest)
def notify_new_swap(sender, instance, created, **kwargs):
    if created: 
        Notification.objects.create(
            recipient=instance.receiver,
            title="New Swap Request",
            badge="SWAP",
            message=f"{instance.sender.username} requested a swap for {instance.slot_name}.",
            action_url=f"/dashboard/swaps/{instance.id}/"
        )