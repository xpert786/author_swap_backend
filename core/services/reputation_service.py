from django.utils import timezone
from django.db.models import Q
from core.models import Profile, SwapRequest

class ReputationService:
    """
    The Automated Reputation Engine.
    Handles automatic score calculation based on platform activity.
    """

    @staticmethod
    def update_confirmed_sends(user):
        """
        Calculates 'Confirmed Sends' score (Max 50 Pts).
        Logic: +5 points for every swap marked as 'completed' or 'verified'.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        # Count all successfully finished swaps for this user
        swaps_completed = user.sent_swap_requests.filter(status__in=['completed', 'verified']).count()
        swaps_completed += SwapRequest.objects.filter(slot__user=user, status__in=['completed', 'verified']).count()
        
        # Award 5 points per swap, capped at 50
        profile.confirmed_sends_score = min(50, swaps_completed * 5)
        
        # Update success rate (%)
        total_swaps = user.sent_swap_requests.exclude(status='rejected').count()
        total_swaps += SwapRequest.objects.filter(slot__user=user).exclude(status='rejected').count()
        
        if total_swaps > 0:
            profile.confirmed_sends_success_rate = round((swaps_completed / total_swaps) * 100, 1)
        
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def update_timeliness(user, is_fast=True):
        """
        Calculates 'Timeliness' score (Max 30 Pts).
        Logic: Reward authors who send their promotions on the scheduled date.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        if is_fast:
            # Add points for a timely send (e.g., +3 per fast send)
            profile.timeliness_score = min(30, profile.timeliness_score + 3)
            # Update moving average of success rate
            profile.timeliness_success_rate = min(100.0, profile.timeliness_success_rate + 10.0)
        else:
            # Optional penalty or decrease for late sends
            profile.timeliness_success_rate = max(0.0, profile.timeliness_success_rate - 5.0)
            
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def record_communication_response(user, request_created_at):
        """
        Calculates 'Communication' score (Max 30 Pts).
        Logic: Reward response times under 2 hours.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        now = timezone.now()
        response_time_hrs = (now - request_created_at).total_seconds() / 3600.0
        
        # Update rolling average of response time
        if profile.avg_response_time_hours == 0:
            profile.avg_response_time_hours = response_time_hrs
        else:
            profile.avg_response_time_hours = (profile.avg_response_time_hours * 0.7) + (response_time_hrs * 0.3)
            
        # Target: Response within 2 hours = 30 pts. Drops to 0 at 24 hours.
        if profile.avg_response_time_hours <= 2.0:
            profile.communication_score = 30
        elif profile.avg_response_time_hours >= 24.0:
            profile.communication_score = 0
        else:
            # Linear decrease between 2h and 24h
            reduction = (profile.avg_response_time_hours - 2.0) / (24.0 - 2.0)
            profile.communication_score = int(30 * (1 - reduction))
            
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def apply_missed_send_penalty(user):
        """
        Calculates 'Missed Sends' penalty (Deducts from 30 Pt base).
        Logic: Penalize users who cancel scheduled swaps late or flake.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        profile.missed_sends_count += 1
        # Penalty: -10 pts per miss
        profile.missed_sends_penalty = max(-30, profile.missed_sends_penalty - 10)
        
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def recalculate_total_score(profile):
        """
        Final 0-100 Score Aggregation.
        """
        # Missed sends starts at a baseline of 30 points and subtracts penalties
        reliability_base = 30 + profile.missed_sends_penalty 
        
        raw_total = (
            profile.confirmed_sends_score + 
            profile.timeliness_score + 
            profile.communication_score + 
            max(0, reliability_base)
        )
        
        # Scale to 100 based on the 140 possible points (50+30+30+30)
        # Higher weight to Confirmed Sends
        profile.reputation_score = min(100.0, round((raw_total / 140.0) * 100.0, 1))
        profile.save()
