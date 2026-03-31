from rest_framework import serializers
from .models import NewsletterSlot, SwapRequest, Book, Profile

class AuthorProfileSerializer(serializers.ModelSerializer):
    """Used for nested author representations"""
    swaps_completed = serializers.SerializerMethodField()
    rating = serializers.FloatField(source='reputation_score', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # Add user ID for chat

    class Meta:
        model = Profile
        fields = [
            'id', 'user_id', 'name', 'profile_picture', 'swaps_completed', 'reputation_score', 'rating',
            'primary_genre', 'send_reliability_percent'
        ]

    def get_swaps_completed(self, obj):
        return obj.swaps_completed

class SlotExploreSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 3 - Swap Partner Explorer"""
    author = AuthorProfileSerializer(source='user.profiles.first', read_only=True)
    current_partners_count = serializers.SerializerMethodField()
    audience_size = serializers.SerializerMethodField()  # Override to use active subscribers

    formatted_send_date_time = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsletterSlot
        fields = [
            'id', 'send_date', 'send_time', 'formatted_send_date_time', 'share_url', 'audience_size', 'visibility', 
            'status', 'promotion_type', 'price', 'preferred_genre', 'placement_style', 
            'current_partners_count', 'max_partners', 'author'
        ]

    def get_audience_size(self, obj):
        """Return active subscribers count instead of total audience size"""
        from core.models import SubscriberVerification
        try:
            verification = SubscriberVerification.objects.get(user=obj.user)
            return verification.active_subscribers
        except SubscriberVerification.DoesNotExist:
            return 0

    def get_current_partners_count(self, obj):
        return obj.swap_requests.filter(status__in=['confirmed', 'verified', 'scheduled', 'completed']).count()

    def get_formatted_send_date_time(self, obj):
        """Returns formatted date and time like 'Wednesday, May 15 at 10:00 AM EST'"""
        if not obj.send_date:
            return None
        
        # Format the date: Wednesday, May 15
        date_str = obj.send_date.strftime('%A, %B %d')
        
        if obj.send_time:
            # Format the time: 10:00 AM
            time_str = obj.send_time.strftime('%I:%M %p').lstrip('0')
            return f"{date_str} at {time_str} EST"
        
        # Fallback if no time is specified
        return f"{date_str} (Flexible)"

    def get_share_url(self, obj):
        return f"http://72.61.251.114/authorswap-frontend/slot-detail/{obj.id}/"

class SlotPartnerSerializer(serializers.ModelSerializer):
    """Used to serialize SwapRequest instances as partners inside a Slot"""
    author = AuthorProfileSerializer(source='requester.profiles.first', read_only=True)
    rating = serializers.FloatField(source='requester.profiles.first.reputation_score', read_only=True)
    status = serializers.SerializerMethodField()
    
    # "You" is the owner of the slot. You are sending the partner's book in your slot.
    you_send_date = serializers.DateField(source='slot.send_date', read_only=True)
    you_send_time = serializers.TimeField(source='slot.send_time', read_only=True)
    you_send_book = serializers.SerializerMethodField()
    you_send_date_formatted = serializers.SerializerMethodField()
    you_send_time_formatted = serializers.SerializerMethodField()
    
    # "Partner" is the requester. The partner sends your book in their offered slot.
    partner_sends_date = serializers.SerializerMethodField()
    partner_sends_time = serializers.SerializerMethodField()
    partner_sends_book = serializers.SerializerMethodField()
    partner_sends_date_formatted = serializers.SerializerMethodField()
    partner_sends_time_formatted = serializers.SerializerMethodField()
    
    # Partner's audience size from offered slot
    partner_audience_size = serializers.SerializerMethodField()

    def get_status(self, obj):
        # For free slots with completed status, show as completed
        if obj.status == 'completed':
            return 'completed'
        # For confirmed or other statuses, show as scheduled
        if obj.status in ['confirmed']:
            return 'scheduled'
        return obj.status

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'author', 'status', 'created_at', 'rating',
            'you_send_date', 'you_send_time', 'you_send_book', 'you_send_date_formatted', 'you_send_time_formatted',
            'partner_sends_date', 'partner_sends_time', 'partner_sends_book', 'partner_sends_date_formatted', 'partner_sends_time_formatted',
            'partner_audience_size'
        ]

    def get_you_send_book(self, obj):
        return obj.book.title if obj.book else None

    def get_partner_sends_date(self, obj):
        return obj.offered_slot.send_date if obj.offered_slot else None

    def get_partner_sends_time(self, obj):
        return obj.offered_slot.send_time if obj.offered_slot else None

    def get_partner_sends_book(self, obj):
        return obj.requested_book.title if obj.requested_book else None

    def get_partner_audience_size(self, obj):
        """Return active subscribers count from partner's offered slot"""
        from core.models import SubscriberVerification
        if obj.offered_slot:
            try:
                verification = SubscriberVerification.objects.get(user=obj.offered_slot.user)
                return verification.active_subscribers
            except SubscriberVerification.DoesNotExist:
                return 0
        return 0

    def get_you_send_date_formatted(self, obj):
        """Returns formatted date like 'Wednesday, May 15'"""
        if obj.slot and obj.slot.send_date:
            return obj.slot.send_date.strftime('%A, %B %d')
        return None

    def get_you_send_time_formatted(self, obj):
        """Returns formatted time like '10:00 AM'"""
        if obj.slot and obj.slot.send_time:
            # Drop the leading zero if there is one using format string
            return obj.slot.send_time.strftime('%I:%M %p').lstrip('0')
        return None

    def get_partner_sends_date_formatted(self, obj):
        """Returns formatted date like 'Friday, May 17'"""
        if obj.offered_slot and obj.offered_slot.send_date:
            return obj.offered_slot.send_date.strftime('%A, %B %d')
        return None

    def get_partner_sends_time_formatted(self, obj):
        """Returns formatted time like '02:00 PM'"""
        if obj.offered_slot and obj.offered_slot.send_time:
            return obj.offered_slot.send_time.strftime('%I:%M %p').lstrip('0')
        return None

class AuthorDetailedProfileSerializer(serializers.ModelSerializer):
    """Extended author profile with analytics and reputation for details modal"""
    swaps_completed = serializers.SerializerMethodField()
    rating = serializers.FloatField(source='reputation_score', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'name', 'profile_picture', 'swaps_completed', 'reputation_score', 'rating',
            'avg_open_rate', 'avg_click_rate', 'monthly_growth', 'send_reliability_percent',
            'confirmed_sends_score', 'timeliness_score', 'missed_sends_penalty', 'communication_score',
            'bio'
        ]

    def get_swaps_completed(self, obj):
        return obj.swaps_completed

class SlotDetailsSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 1 - Slot Details Modal"""
    author = AuthorDetailedProfileSerializer(source='user.profiles.first', read_only=True)
    current_partners_count = serializers.SerializerMethodField()
    swap_partners = serializers.SerializerMethodField()
    audience_size = serializers.SerializerMethodField()  # Override to use active subscribers
    
    formatted_send_date_time = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsletterSlot
        fields = [
            'id', 'author', 'send_date', 'send_time', 'formatted_send_date_time', 'share_url', 'audience_size', 'visibility', 
            'status', 'preferred_genre', 'placement_style', 'current_partners_count', 'max_partners', 'swap_partners'
        ]

    def get_audience_size(self, obj):
        """Return active subscribers count instead of total audience size"""
        from core.models import SubscriberVerification
        try:
            verification = SubscriberVerification.objects.get(user=obj.user)
            return verification.active_subscribers
        except SubscriberVerification.DoesNotExist:
            return 0

    def get_current_partners_count(self, obj):
        return obj.swap_requests.filter(status__in=['confirmed', 'verified', 'completed', 'sending', 'scheduled']).count()

    def get_swap_partners(self, obj):
        requests = obj.swap_requests.filter(status__in=['confirmed', 'verified', 'completed', 'sending', 'scheduled'])
        return SlotPartnerSerializer(requests, many=True, context=self.context).data

    def get_share_url(self, obj):
        return f"http://72.61.251.114/authorswap-frontend/slot-detail/{obj.id}/"

    def get_formatted_send_date_time(self, obj):
        """Returns formatted date and time like 'Wednesday, May 15 at 10:00 AM EST'"""
        if not obj.send_date:
            return None
        
        # Format the date: Wednesday, May 15
        date_str = obj.send_date.strftime('%A, %B %d')
        
        if obj.send_time:
            # Format the time: 10:00 AM
            time_str = obj.send_time.strftime('%I:%M %p').lstrip('0')
            return f"{date_str} at {time_str} EST"
        
        # Fallback if no time is specified
        return f"{date_str} (Flexible)"

class SwapArrangementSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 2 - Swap Arrangement Modal"""
    partner = AuthorProfileSerializer(source='slot.user.profiles.first', read_only=True)
    
    you_send_date = serializers.DateField(source='offered_slot.send_date', read_only=True)
    you_send_time = serializers.TimeField(source='offered_slot.send_time', read_only=True)
    you_send_book = serializers.CharField(source='requested_book.title', read_only=True)
    
    partner_sends_date = serializers.DateField(source='slot.send_date', read_only=True)
    partner_sends_time = serializers.TimeField(source='slot.send_time', read_only=True)
    partner_sends_book = serializers.CharField(source='book.title', read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        if obj.status in ['confirmed', 'completed']:
            return 'scheduled'
        return obj.status

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'status', 'partner',
            'you_send_date', 'you_send_time', 'you_send_book',
            'partner_sends_date', 'partner_sends_time', 'partner_sends_book'
        ]
