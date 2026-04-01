"""
Management command to check for missed swap sends and apply reputation penalties.
Should be run daily via cron job.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import SwapRequest
from core.services.reputation_service import ReputationService


class Command(BaseCommand):
    help = 'Check for missed swap sends and apply reputation penalties'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # Find swaps that were scheduled but not sent by the slot send date
        # Allow a 24-hour grace period after the scheduled date
        missed_swaps = SwapRequest.objects.filter(
            status__in=['scheduled', 'confirmed'],
            slot__send_date__lt=now.date() - timedelta(days=1)
        )
        
        penalty_count = 0
        
        for swap in missed_swaps:
            # Apply missed send penalty to the slot owner (the one who was supposed to send)
            slot_owner = swap.slot.user
            ReputationService.apply_missed_send_penalty(slot_owner)
            
            # Also mark the swap as missed/flaked in the status
            swap.status = 'rejected'
            swap.rejection_reason = f'Auto-rejected: Newsletter not sent by scheduled date ({swap.slot.send_date}).'
            swap.rejected_at = now
            swap.save()
            
            penalty_count += 1
            
            self.stdout.write(
                self.style.WARNING(
                    f'Applied missed send penalty to {slot_owner.username} for swap {swap.id}'
                )
            )
        
        if penalty_count == 0:
            self.stdout.write(self.style.SUCCESS('No missed swaps found.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Processed {penalty_count} missed swaps with penalties.')
            )
