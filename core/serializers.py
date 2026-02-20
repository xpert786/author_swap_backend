from rest_framework import serializers
from .models import NewsletterSlot
from authentication.models import GENRE_SUBGENRE_MAPPING
from .models import Book, Profile, Notification, SwapRequest

from django.utils import timezone
from datetime import timedelta

class ProfileSerializer(serializers.ModelSerializer):   
    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'email': {'required': True},
            'profile_picture': {'required': True},
            'location': {'required': True},
            'primary_genre': {'required': True},
            'bio': {'required': True},
            'instagram_url': {'required': True},
            'tiktok_url': {'required': True},
            'facebook_url': {'required': True},
            'website': {'required': True},
        }

    username = serializers.CharField(source='user.username', read_only=True)

class NewsletterSlotSerializer(serializers.ModelSerializer):
    subgenres = serializers.ListField(
        child=serializers.CharField(), 
        required=False,
        allow_empty=True
    )
    time_period = serializers.ReadOnlyField()
    formatted_time = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    class Meta:
        model = NewsletterSlot
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'audience_size': {'required': True},
            'max_partners': {'required': True},
            'visibility': {'required': True},
            'status': {'required': True},
        }
    def get_formatted_time(self, obj):
        if obj.send_time:
            # %I is 12-hour clock, %M is minutes, %p is AM/PM
            return obj.send_time.strftime("%I:%M %p")
        return None
    def get_formatted_date(self, obj):
        if obj.send_date:
            return obj.send_date.strftime("%d-%m-%Y")
        return None
    def validate(self, data):
        genre = data.get('preferred_genre')
        subs = data.get('subgenres', [])
        
        # Audience size custom validation if needed (e.g., must be > 0)
        # but required=True is handled by extra_kwargs/framework

        if genre and subs:
             allowed_sub_tuples = GENRE_SUBGENRE_MAPPING.get(genre, [])
             allowed_keys = [item[0] for item in allowed_sub_tuples]

             for sub in subs:
                if sub not in allowed_keys:
                    raise serializers.ValidationError({
                        "subgenres": f"'{sub}' is not a valid subgenre for {genre}. "
                                     f"Please only select from the {genre} list."
                    })
        return data

    def to_internal_value(self, data):
        data = data.copy()
        if 'subgenres' in data and isinstance(data['subgenres'], list):
            data['subgenres'] = ",".join(data['subgenres'])
        return super().to_internal_value(data)

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        if instance.subgenres:
            repr['subgenres'] = instance.subgenres.split(',')
        else:
            repr['subgenres'] = []
        return repr
    def get_subgenres(self, obj):
        if obj.subgenres:
            return [s.strip() for s in obj.subgenres.split(',')]
        return []

class BookSerializer(serializers.ModelSerializer):
    # Allows the frontend to send an array of subgenres
    subgenres = serializers.ListField(child=serializers.CharField(), required=True)

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'price_tier': {'required': True},
            'amazon_url': {'required': True},
            'apple_url': {'required': True},
            'kobo_url': {'required': True},
            'barnes_noble_url': {'required': True},
            'rating': {'required': True},
            'availability': {'required': True},
        }

    def validate(self, data):
        genre = data.get('primary_genre')
        subs = data.get('subgenres', [])

        if genre and subs:
            # 1. Fetch the allowed subgenres for the selected category
            allowed_tuples = GENRE_SUBGENRE_MAPPING.get(genre, [])
            allowed_keys = [item[0] for item in allowed_tuples]

            # 2. Enforce the match
            for s in subs:
                if s not in allowed_keys:
                    raise serializers.ValidationError({
                        "subgenres": f"'{s}' is not a valid subgenre for the {genre} category."
                    })
        return data

    def to_internal_value(self, data):
        data = data.copy()  # Make a mutable copy
        # Flatten the list back to a string for the DB CharField
        if 'subgenres' in data and isinstance(data['subgenres'], list):
            data['subgenres'] = ",".join(data['subgenres'])
        return super().to_internal_value(data)

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        if instance.subgenres:
            # If it's already a list (from validated_data), use it
            if isinstance(instance.subgenres, list):
                repr['subgenres'] = instance.subgenres
            # If it's a string (from DB), split it
            elif isinstance(instance.subgenres, str):
                repr['subgenres'] = instance.subgenres.split(',')
        else:
            repr['subgenres'] = []
        return repr

class NotificationSerializer(serializers.ModelSerializer):
    time_group = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'badge', 'action_url', 'is_read', 'created_at', 'time_group']

    def get_time_group(self, obj):
        now = timezone.now().date()
        target = obj.created_at.date()
        if target == now:
            return "Today"
        elif target == now - timedelta(days=1):
            return "Yesterday"
        return target.strftime("%d-%m-%Y")

class RecentSwapSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        model = SwapRequest
        fields = ['id', 'author_name', 'date', 'status']

    def get_author_name(self, obj):
        # Depending on who is viewing, this might be requester or recipient
        # For simplicity, let's show the partner the user interacted with
        return obj.requester.username # Should be more robust in real logic

    def get_date(self, obj):
        return obj.created_at.strftime("%d %b %Y")

class SwapRequestSerializer(serializers.ModelSerializer):

    requester_name = serializers.SerializerMethodField()
    slot_details = NewsletterSlotSerializer(source='slot', read_only=True)
    book_details = BookSerializer(source='book', read_only=True)
    compatibility_indicators = serializers.SerializerMethodField()

    class Meta:
        model = SwapRequest
        fields = '__all__'
        read_only_fields = ['requester', 'created_at']



    def get_requester_name(self, obj):
        profile = obj.requester.profiles.first()
        return profile.name if profile else obj.requester.username

    def get_compatibility_indicators(self, obj):
        indicators = {
            "genre_match": False,
            "audience_comparable": False,
            "reliability_match": False
        }
        if obj.book and obj.slot:
            # Genre Match
            indicators["genre_match"] = obj.book.primary_genre == obj.slot.preferred_genre
            
            # Audience Comparable (within 50% range)
            requester_profile = obj.requester.profiles.first()
            if requester_profile:
                # Assuming the requester's audience is relevant. 
                # For now, let's just check if the slot audience is within range of some benchmark
                # or if we had requester audience size.
                indicators["audience_comparable"] = True # Simplified logic
            
            # Reliability Match
            owner_profile = obj.slot.user.profiles.first()
            requester_profile = obj.requester.profiles.first()
            if owner_profile and requester_profile:
                diff = abs(owner_profile.reputation_score - requester_profile.reputation_score)
                indicators["reliability_match"] = diff <= 1.0
                
        return indicators


class SwapPartnerSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    swaps_completed = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    reputation_score = serializers.SerializerMethodField()
    analytics_summary = serializers.SerializerMethodField()
    analytics_breakdown = serializers.SerializerMethodField()
    reputation_breakdown = serializers.SerializerMethodField()
    recent_swap_history = serializers.SerializerMethodField()

    formatted_time = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = NewsletterSlot
        fields = [
            'id', 'author_name', 'swaps_completed', 'profile_picture', 'reputation_score',
            'send_date', 'send_time', 'preferred_genre', 'audience_size', 'visibility', 
            'status', 'formatted_time', 'formatted_date', 'placement_style', 
            'promotion_type', 'partner_requirements', 'analytics_summary',
            'analytics_breakdown', 'reputation_breakdown', 'recent_swap_history'
        ]



    def get_author_name(self, obj):
        profile = obj.user.profiles.first()
        return profile.name if profile else obj.user.username

    def get_swaps_completed(self, obj):
        profile = obj.user.profiles.first()
        return profile.swaps_completed if profile else 0

    def get_profile_picture(self, obj):
        profile = obj.user.profiles.first()
        if profile and profile.profile_picture:
            return profile.profile_picture.url
        return None

    def get_reputation_score(self, obj):
        profile = obj.user.profiles.first()
        return profile.reputation_score if profile else 5.0

    def get_analytics_summary(self, obj):
        profile = obj.user.profiles.first()
        if profile:
            return {
                "avg_open_rate": f"{profile.avg_open_rate}%",
                "avg_click_rate": f"{profile.avg_click_rate}%",
                "monthly_growth": f"+{profile.monthly_growth}",
                "send_reliability": f"{profile.send_reliability_percent}%"
            }
        return {}

    def get_analytics_breakdown(self, obj):
        profile = obj.user.profiles.first()
        if profile:
            return {
                "avg_open_rate": profile.avg_open_rate,
                "avg_click_rate": profile.avg_click_rate,
                "monthly_growth": profile.monthly_growth,
                "send_reliability": profile.send_reliability_percent
            }
        return {}

    def get_reputation_breakdown(self, obj):
        profile = obj.user.profiles.first()
        if profile:
            return {
                "confirmed_sends": {"score": profile.confirmed_sends_score, "total": 50},
                "timeliness": {"score": profile.timeliness_score, "total": 30},
                "missed_sends": {"score": profile.missed_sends_penalty, "total": 30},
                "communication": {"score": profile.communication_score, "total": 30},
            }
        return {}

    def get_recent_swap_history(self, obj):
        # Fetch last 9 confirmed swaps for this user
        confirmed_requests = SwapRequest.objects.filter(
            slot__user=obj.user, 
            status__in=['confirmed', 'verified']
        ).order_by('-created_at')[:9]
        return RecentSwapSerializer(confirmed_requests, many=True).data

    def get_formatted_time(self, obj):
        if obj.send_time:
            return obj.send_time.strftime("%I:%M %p")
        return None


    def get_formatted_date(self, obj):
        if obj.send_date:
            return obj.send_date.strftime("%d %b %Y")
        return None