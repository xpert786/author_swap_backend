from rest_framework import serializers
from .models import NewsletterSlot, SwapRequest, Book, Profile

class AuthorProfileSerializer(serializers.ModelSerializer):
    """Used for nested author representations"""
    swaps_completed = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'name', 'profile_picture', 'swaps_completed', 'reputation_score']

    def get_swaps_completed(self, obj):
        return obj.swaps_completed

class SlotExploreSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 3 - Swap Partner Explorer"""
    author = AuthorProfileSerializer(source='user.profiles.first', read_only=True)
    current_partners_count = serializers.SerializerMethodField()

    class Meta:
        model = NewsletterSlot
        fields = [
            'id', 'send_date', 'send_time', 'audience_size', 'visibility', 
            'status', 'promotion_type', 'price', 'preferred_genre', 
            'current_partners_count', 'max_partners', 'author'
        ]

    def get_current_partners_count(self, obj):
        return obj.swap_requests.filter(status__in=['confirmed', 'verified']).count()

class SlotPartnerSerializer(serializers.ModelSerializer):
    """Used to serialize SwapRequest instances as partners inside a Slot"""
    author = AuthorProfileSerializer(source='requester.profiles.first', read_only=True)
    
    class Meta:
        model = SwapRequest
        fields = ['id', 'author', 'status', 'created_at']

class AuthorDetailedProfileSerializer(serializers.ModelSerializer):
    """Extended author profile with analytics and reputation for details modal"""
    swaps_completed = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'name', 'profile_picture', 'swaps_completed', 'reputation_score',
            'avg_open_rate', 'avg_click_rate', 'monthly_growth', 'send_reliability_percent',
            'confirmed_sends_score', 'timeliness_score', 'missed_sends_penalty', 'communication_score'
        ]

    def get_swaps_completed(self, obj):
        return obj.swaps_completed

class SlotDetailsSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 1 - Slot Details Modal"""
    author = AuthorDetailedProfileSerializer(source='user.profiles.first', read_only=True)
    current_partners_count = serializers.SerializerMethodField()
    swap_partners = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsletterSlot
        fields = [
            'id', 'author', 'send_date', 'send_time', 'audience_size', 'visibility', 
            'status', 'preferred_genre', 'current_partners_count', 'max_partners', 'swap_partners'
        ]

    def get_current_partners_count(self, obj):
        return obj.swap_requests.filter(status__in=['confirmed', 'verified']).count()

    def get_swap_partners(self, obj):
        requests = obj.swap_requests.filter(status__in=['confirmed', 'verified'])
        return SlotPartnerSerializer(requests, many=True).data

class SwapArrangementSerializer(serializers.ModelSerializer):
    """Serializer for Figma Screen 2 - Swap Arrangement Modal"""
    partner = AuthorProfileSerializer(source='slot.user.profiles.first', read_only=True)
    
    you_send_date = serializers.DateField(source='offered_slot.send_date', read_only=True)
    you_send_time = serializers.TimeField(source='offered_slot.send_time', read_only=True)
    you_send_book = serializers.CharField(source='requested_book.title', read_only=True)
    
    partner_sends_date = serializers.DateField(source='slot.send_date', read_only=True)
    partner_sends_time = serializers.TimeField(source='slot.send_time', read_only=True)
    partner_sends_book = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'status', 'partner',
            'you_send_date', 'you_send_time', 'you_send_book',
            'partner_sends_date', 'partner_sends_time', 'partner_sends_book'
        ]
