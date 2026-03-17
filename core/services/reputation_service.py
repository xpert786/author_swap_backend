from django.utils import timezone
from django.db.models import Q
from core.models import Profile, SwapRequest

class ReputationService:
    @staticmethod
    def update_confirmed_sends(user):
        """
        Awards points based on the number of completed/verified swaps.
        Max Points: 50 (10 swaps x 5 points each).
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        # Count swaps where the user was a partner and status is completed or verified
        swaps_completed = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user),
            status__in=['completed', 'verified']
        ).count()
        
        # Calculate points (5 per swap, cap at 50)
        profile.confirmed_sends_score = min(50, swaps_completed * 5)
        
        # Calculate success rate
        total_involvement = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user)
        ).exclude(status='rejected').count()
        
        if total_involvement > 0:
            profile.confirmed_sends_success_rate = (swaps_completed / total_involvement) * 100.0
        
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def update_timeliness(user, is_ontime=True):
        """
        Awards points for sending promotions on the scheduled date.
        Max Points: 30.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        if is_ontime:
            # Add 3 points per timely send, max 30
            profile.timeliness_score = min(30, profile.timeliness_score + 3)
            # Impact on success rate (moving average)
            profile.timeliness_success_rate = min(100.0, (profile.timeliness_success_rate * 0.8) + 20.0)
        else:
            profile.timeliness_success_rate = profile.timeliness_success_rate * 0.8
            
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def record_communication_response(user, request_created_at):
        """
        Updates communication score based on response time.
        Target: < 2 hours response for 30 points.
        """
        profile = user.profiles.first()
        if not profile:
            return
        
        now = timezone.now()
        response_time_hrs = (now - request_created_at).total_seconds() / 3600.0
        
        # Update moving average
        if profile.avg_response_time_hours == 0:
            profile.avg_response_time_hours = response_time_hrs
        else:
            profile.avg_response_time_hours = (profile.avg_response_time_hours * 0.7) + (response_time_hrs * 0.3)
            
        # Points calculation (linear scale: 2h = 30pts, 24h = 0pts)
        if profile.avg_response_time_hours <= 2.0:
            profile.communication_score = 30
        elif profile.avg_response_time_hours >= 24.0:
            profile.communication_score = 0
        else:
            penalty_range = 24.0 - 2.0
            excess = profile.avg_response_time_hours - 2.0
            profile.communication_score = int(30 * (1 - (excess / penalty_range)))
            
        profile.save()
        ReputationService.recalculate_total_score(profile)

    @staticmethod
    def apply_missed_send_penalty(user):
        """
        Deducts points for missed or flaked swaps.
        Starts with a 30 point maintenance score.
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
        Sums up all breakdown scores to update the main 0-100 reputation score.
        """
        # Base reliability starts at 30 points
        reliability_base = 30 + profile.missed_sends_penalty
        
        total_raw = (
            profile.confirmed_sends_score + 
            profile.timeliness_score + 
            profile.communication_score + 
            max(0, reliability_base)
        )
        
        # Scale 130 max points down to 100
        profile.reputation_score = min(100, int((total_raw / 130.0) * 100.0))
        profile.save()
