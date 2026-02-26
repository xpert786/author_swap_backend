from rest_framework import serializers
from .models import NewsletterSlot
from authentication.models import GENRE_SUBGENRE_MAPPING
from .models import (
    Book, Profile, Notification, SwapRequest, 
    SubscriptionTier, UserSubscription, SubscriberVerification,
    SubscriberGrowth, CampaignAnalytic
)

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

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Pull data from authentication.UserProfile to fill empty fields
        try:
            from authentication.models import UserProfile
            user_profile = UserProfile.objects.filter(user=instance.user).first()
            if user_profile:
                # Map: UserProfile field -> core.Profile serializer key
                field_map = {
                    'pen_name': 'name',
                    'author_bio': 'bio',
                    'primary_genre': 'primary_genre',
                    'website_url': 'website',
                    'facebook_url': 'facebook_url',
                    'instagram_url': 'instagram_url',
                    'tiktok_url': 'tiktok_url',
                }
                for src_field, dst_key in field_map.items():
                    src_val = getattr(user_profile, src_field, None)
                    if src_val and not data.get(dst_key):
                        data[dst_key] = src_val

                # Profile photo
                if not data.get('profile_picture') and user_profile.profile_photo:
                    request = self.context.get('request')
                    if request:
                        data['profile_picture'] = request.build_absolute_uri(user_profile.profile_photo.url)
                    else:
                        data['profile_picture'] = user_profile.profile_photo.url

                # Email from User model
                if not data.get('email') and instance.user.email:
                    data['email'] = instance.user.email
        except Exception:
            pass

        return data

class NewsletterSlotSerializer(serializers.ModelSerializer):
    subgenres = serializers.ListField(
        child=serializers.CharField(), 
        required=False,
        allow_empty=True
    )
    time_period = serializers.ReadOnlyField()
    formatted_time = serializers.SerializerMethodField(required=False)
    formatted_date = serializers.SerializerMethodField()
    class Meta:
        model = NewsletterSlot
        fields = '__all__'
        read_only_fields = ['user', 'audience_size']
        extra_kwargs = {
            'send_time': {'required': False, 'allow_null': True},
            'max_partners': {'required': True},
            'visibility': {'required': True},
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

        # ── Unique date + time check per user ──────────────────────────
        send_date = data.get('send_date')
        send_time = data.get('send_time')
        request = self.context.get('request')

        if send_date and send_time and request:
            user = request.user
            qs = NewsletterSlot.objects.filter(
                user=user,
                send_date=send_date,
                send_time=send_time,
            )
            # If we are updating an existing slot, exclude it from the check
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "send_time": "You already have a newsletter slot scheduled on "
                                 f"{send_date.strftime('%d-%m-%Y')} at "
                                 f"{send_time.strftime('%I:%M %p')}. "
                                 "Please choose a different date or time."
                })

        # ── Subgenre validation ────────────────────────────────────────
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
    subgenres = serializers.ListField(
        child=serializers.CharField(allow_null=True, allow_blank=True, required=False),
        required=False,
        default=list
    )
    rating = serializers.FloatField(allow_null=True, default=0.0)

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
            'availability': {'required': True},
        }

    def validate_subgenres(self, value):
        # Value is already a list due to ListField
        genre = self.initial_data.get('primary_genre')
        if genre and value:
            allowed_tuples = GENRE_SUBGENRE_MAPPING.get(genre, [])
            allowed_keys = [item[0] for item in allowed_tuples]
            for s in value:
                if s not in allowed_keys:
                    raise serializers.ValidationError(
                        f"'{s}' is not a valid subgenre for the {genre} category."
                    )
        return value

    def to_internal_value(self, data):
        # Create a mutable copy if it's a QueryDict (from multipart/form-data)
        if hasattr(data, 'copy'):
            data = data.copy()
        
        # 1. Handle Rating (if empty or non-numeric, just remove it so it falls back to default=0.0)
        if 'rating' in data:
            val = data.get('rating')
            if val is None or (isinstance(val, str) and not val.strip()):
                if hasattr(data, 'pop'):
                    data.pop('rating', None)
                else:
                    del data['rating']
            
        # 2. Handle Subgenres (QueryDict getlist vs dict get)
        if 'subgenres' in data:
            raw_subs = []
            if hasattr(data, 'getlist'):
                raw_subs_list = data.getlist('subgenres')
                if len(raw_subs_list) == 1 and isinstance(raw_subs_list[0], str) and ',' in raw_subs_list[0]:
                    raw_subs = [s.strip() for s in raw_subs_list[0].split(',') if s.strip()]
                else:
                    raw_subs = [s.strip() for s in raw_subs_list if isinstance(s, str) and s.strip()]
            else:
                val = data.get('subgenres')
                if isinstance(val, str):
                    raw_subs = [s.strip() for s in val.split(',') if s.strip()]
                elif isinstance(val, list):
                    raw_subs = [s.strip() for s in val if isinstance(s, str) and s.strip()]
                elif isinstance(val, dict):
                    raw_subs = []
                    for k in sorted(val.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                        item = val[k]
                        if isinstance(item, str) and item.strip():
                            raw_subs.append(item.strip())
            
            if raw_subs:
                if hasattr(data, 'setlist'):
                    data.setlist('subgenres', raw_subs)
                else:
                    data['subgenres'] = raw_subs
            else:
                if hasattr(data, 'pop'):
                    data.pop('subgenres', None)
                else:
                    del data['subgenres']

        validated_data = super().to_internal_value(data)
        
        # Flatten the list back to a string for the DB CharField
        if 'subgenres' in validated_data and isinstance(validated_data['subgenres'], list):
            validated_data['subgenres'] = ",".join(validated_data['subgenres'])
            
        return validated_data

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
                indicators["audience_comparable"] = True # Simplified logic
            
            # Reliability Match
            owner_profile = obj.slot.user.profiles.first()
            requester_profile = obj.requester.profiles.first()
            if owner_profile and requester_profile:
                diff = abs(owner_profile.reputation_score - requester_profile.reputation_score)
                indicators["reliability_match"] = diff <= 1.0
                
        return indicators


class SwapManagementSerializer(serializers.ModelSerializer):
    """
    Serializer for the Swap Management page (Figma).
    Returns all data needed for each swap card.
    """
    # Author info (the person who SENT the request)
    author_name = serializers.SerializerMethodField()
    author_genre_label = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    # Stats
    audience_size = serializers.SerializerMethodField()
    reliability_score = serializers.SerializerMethodField()

    # Book
    requesting_book = serializers.SerializerMethodField()

    # Rejection info
    rejection_info = serializers.SerializerMethodField()

    # Scheduled
    scheduled_label = serializers.SerializerMethodField()

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'status', 'message', 'created_at',
            'author_name', 'author_genre_label', 'profile_picture',
            'audience_size', 'reliability_score',
            'requesting_book',
            'rejection_info', 'rejection_reason', 'rejected_at',
            'scheduled_label', 'scheduled_date',
            'preferred_placement', 'max_partners_acknowledged',
        ]

    def get_partner_user(self, obj):
        request = self.context.get('request')
        if request and request.user == obj.requester:
            return obj.slot.user
        return obj.requester

    def get_author_name(self, obj):
        partner = self.get_partner_user(obj)
        profile = partner.profiles.first()
        return profile.name if profile else partner.username

    def get_author_genre_label(self, obj):
        partner = self.get_partner_user(obj)
        profile = partner.profiles.first()
        if profile:
            return f"{profile.get_primary_genre_display() if hasattr(profile, 'get_primary_genre_display') else profile.primary_genre}"
        return ""

    def get_profile_picture(self, obj):
        partner = self.get_partner_user(obj)
        profile = partner.profiles.first()
        if profile and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None

    def get_audience_size(self, obj):
        # Use the slot's audience_size (synced from MailerLite)
        slot = obj.slot
        return f"{slot.audience_size:,}+" if slot else "0"

    def get_reliability_score(self, obj):
        partner = self.get_partner_user(obj)
        profile = partner.profiles.first()
        if profile:
            return f"{int(profile.send_reliability_percent)}%"
        return "0%"

    def get_requesting_book(self, obj):
        if obj.book:
            return {
                "id": obj.book.id,
                "title": obj.book.title,
                "cover": obj.book.book_cover.url if obj.book.book_cover else None,
            }
        return None

    def get_rejection_info(self, obj):
        if obj.status == 'rejected' and obj.rejection_reason:
            return {
                "reason": obj.rejection_reason,
                "rejected_on": obj.rejected_at.strftime("%B %d, %Y") if obj.rejected_at else None,
            }
        return None

    def get_scheduled_label(self, obj):
        if obj.scheduled_date:
            return f"Scheduled for {obj.scheduled_date.strftime('%B %d %Y')}"
        return None


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


# =====================================================================
# SWAP HISTORY DETAIL (Figma: "Track My Swap" / "View Swap History")
# =====================================================================
from core.models import SwapLinkClick


class SwapLinkClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwapLinkClick
        fields = ['id', 'link_name', 'destination_url', 'clicks', 'ctr', 'ctr_label', 'conversions']


class SwapHistoryDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for the 'View Swap History' detail page (Figma).
    Shows: partner info, request/completed dates, links, promoting book, CTR analysis.
    """
    # Partner info (the OTHER user in this swap)
    partner_name = serializers.SerializerMethodField()
    partner_label = serializers.SerializerMethodField()
    partner_genre = serializers.SerializerMethodField()
    partner_profile_picture = serializers.SerializerMethodField()

    # Dates
    request_date = serializers.SerializerMethodField()
    completed_date = serializers.SerializerMethodField()

    # Status banner
    status_label = serializers.SerializerMethodField()

    # Partner's social links
    partner_links = serializers.SerializerMethodField()

    # Promoting book info
    promoting_book = serializers.SerializerMethodField()

    # Link-Level CTR analysis
    link_ctr_analysis = serializers.SerializerMethodField()

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'status',
            'partner_name', 'partner_label', 'partner_genre', 'partner_profile_picture',
            'request_date', 'completed_date', 'status_label',
            'partner_links',
            'promoting_book',
            'link_ctr_analysis',
            'message',
        ]

    def _get_partner(self, obj):
        """Determine the partner: if I own the slot, partner is the requester. Otherwise, partner is the slot owner."""
        request = self.context.get('request')
        if request and obj.slot.user == request.user:
            return obj.requester
        return obj.slot.user

    def get_partner_name(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        return profile.name if profile else partner.username

    def get_partner_label(self, obj):
        return "Swap Partner"

    def get_partner_genre(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if profile:
            return f"{profile.get_primary_genre_display() if hasattr(profile, 'get_primary_genre_display') else profile.primary_genre} Writer"
        return ""

    def get_partner_profile_picture(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if profile and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None

    def get_request_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d %b, %Y")
        return None

    def get_completed_date(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d %b, %Y")
        return None

    def get_status_label(self, obj):
        labels = {
            'pending': 'Swap Pending',
            'confirmed': 'Swap Confirmed',
            'sending': 'Swap Sending',
            'scheduled': 'Swap Scheduled',
            'completed': 'Swap Completed',
            'verified': 'Swap Verified',
            'rejected': 'Swap Rejected',
        }
        return labels.get(obj.status, obj.get_status_display())

    def get_partner_links(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if not profile:
            return {}
        return {
            "website": profile.website or None,
            "facebook": profile.facebook_url or None,
            "instagram": profile.instagram_url or None,
            "twitter": profile.tiktok_url or None,  # Using tiktok field for now
        }

    def get_promoting_book(self, obj):
        book = obj.book
        if not book:
            return None
        result = {
            "id": book.id,
            "title": book.title,
            "cover": None,
            "status": "Upcoming" if obj.status in ['pending', 'confirmed', 'sending', 'scheduled'] else "Completed",
        }
        if book.book_cover:
            request = self.context.get('request')
            if request:
                result["cover"] = request.build_absolute_uri(book.book_cover.url)
            else:
                result["cover"] = book.book_cover.url
        return result

    def get_link_ctr_analysis(self, obj):
        link_clicks = obj.link_clicks.all()
        return SwapLinkClickSerializer(link_clicks, many=True).data


# =====================================================================
# TRACK MY SWAP MODAL (Figma: "Track My Swap" — active/pending swaps)
# =====================================================================

class TrackMySwapSerializer(serializers.ModelSerializer):
    """
    Serializer for the 'Track My Swap' modal (Figma).
    Shows: partner info, promoting book, countdown deadline, request date, links.
    Used for active swaps (pending/confirmed/sending/scheduled).
    """
    # Swapping With
    partner_name = serializers.SerializerMethodField()
    partner_genre = serializers.SerializerMethodField()
    partner_profile_picture = serializers.SerializerMethodField()

    # Promoting Book
    promoting_book = serializers.SerializerMethodField()

    # Countdown / Deadline
    deadline = serializers.SerializerMethodField()
    request_date = serializers.SerializerMethodField()
    countdown_label = serializers.SerializerMethodField()

    # Status
    status_label = serializers.SerializerMethodField()

    # Partner Links
    partner_links = serializers.SerializerMethodField()

    class Meta:
        model = SwapRequest
        fields = [
            'id', 'status',
            'partner_name', 'partner_genre', 'partner_profile_picture',
            'promoting_book',
            'deadline', 'request_date', 'countdown_label',
            'status_label',
            'partner_links',
            'message',
        ]

    def _get_partner(self, obj):
        request = self.context.get('request')
        if request and obj.slot.user == request.user:
            return obj.requester
        return obj.slot.user

    def get_partner_name(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        return profile.name if profile else partner.username

    def get_partner_genre(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if profile:
            genre = profile.get_primary_genre_display() if hasattr(profile, 'get_primary_genre_display') else profile.primary_genre
            return f"{genre} Writer"
        return ""

    def get_partner_profile_picture(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if profile and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None

    def get_promoting_book(self, obj):
        book = obj.book
        if not book:
            return None
        result = {
            "id": book.id,
            "title": book.title,
            "genre": book.get_primary_genre_display() if hasattr(book, 'get_primary_genre_display') else book.primary_genre,
            "cover": None,
            "badge": "Upcoming" if obj.status in ['pending', 'confirmed', 'sending', 'scheduled'] else "Completed",
        }
        if book.book_cover:
            request = self.context.get('request')
            if request:
                result["cover"] = request.build_absolute_uri(book.book_cover.url)
            else:
                result["cover"] = book.book_cover.url
        return result

    def get_deadline(self, obj):
        """Deadline = slot's send_date + send_time formatted as 'dd MMM, YYYY hh:mmAM/PM'"""
        from datetime import datetime
        slot = obj.slot
        if slot and slot.send_date and slot.send_time:
            dt = datetime.combine(slot.send_date, slot.send_time)
            return dt.strftime("%d %b, %Y %I:%M%p")
        elif slot and slot.send_date:
            return slot.send_date.strftime("%d %b, %Y")
        return None

    def get_request_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d %b, %Y")
        return None

    def get_countdown_label(self, obj):
        """Returns the book title and send_date for the countdown card."""
        book = obj.book
        slot = obj.slot
        return {
            "title": book.title if book else None,
            "date": slot.send_date.strftime("%d %b %Y") if slot and slot.send_date else None,
        }

    def get_status_label(self, obj):
        labels = {
            'pending': 'Waiting for partner response',
            'confirmed': 'Swap Confirmed',
            'sending': 'Sending in progress',
            'scheduled': 'Swap Scheduled',
            'completed': 'Swap Completed',
            'verified': 'Swap Verified',
            'rejected': 'Swap Rejected',
        }
        return labels.get(obj.status, obj.get_status_display())

    def get_partner_links(self, obj):
        partner = self._get_partner(obj)
        profile = partner.profiles.first()
        if not profile:
            return {}
        return {
            "website": profile.website or None,
            "facebook": profile.facebook_url or None,
            "instagram": profile.instagram_url or None,
            "twitter": profile.tiktok_url or None,
        }


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = '__all__'


class UserSubscriptionSerializer(serializers.ModelSerializer):
    tier_details = SubscriptionTierSerializer(source='tier', read_only=True)

    class Meta:
        model = UserSubscription
        fields = '__all__'


class SubscriberVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriberVerification
        fields = '__all__'


class AuthorReputationSerializer(serializers.ModelSerializer):
    reputation_score = serializers.SerializerMethodField()
    platform_ranking = serializers.SerializerMethodField()
    reputation_badges = serializers.SerializerMethodField()
    reputation_score_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'reputation_score',
            'is_webhook_verified',
            'platform_ranking',
            'reputation_badges',
            'reputation_score_breakdown',
        ]

    def get_reputation_score(self, obj):
        return {
            "score": int(obj.reputation_score),
            "max": 100
        }

    def get_platform_ranking(self, obj):
        return {
            "rank": obj.platform_ranking_position,
            "percentile": obj.platform_ranking_percentile
        }

    def get_reputation_badges(self, obj):
        return [
            {
                "name": "Verified Sender",
                "description": "Complete 10+ swaps with verification",
                "status": "Earned"
            },
            {
                "name": "100% Reliability",
                "description": "Perfect send record for 30 days",
                "status": "Active"
            },
            {
                "name": "Top Swap Partner",
                "description": "Top 10% of all authors in reliability",
                "status": "Earned"
            },
            {
                "name": "Fast Communicator",
                "description": "Average response time under 2 hours",
                "status": "Locked"
            }
        ]

    def get_reputation_score_breakdown(self, obj):
        return {
            "confirmed_sends": {
                "score": obj.confirmed_sends_score,
                "max": 50,
                "description": f"{int(obj.confirmed_sends_success_rate)}% success rate",
                "points": f"+{obj.confirmed_sends_score} points"
            },
            "timeliness": {
                "score": obj.timeliness_score,
                "max": 30,
                "description": f"{int(obj.timeliness_success_rate)} % success rate",
                "points": f"+{obj.timeliness_score} points"
            },
            "missed_sends": {
                "score": abs(obj.missed_sends_penalty),
                "max": 30,
                "description": f"{obj.missed_sends_count} missed sends",
                "points": f"{obj.missed_sends_penalty} points"
            },
            "communication": {
                "score": obj.communication_score,
                "max": 30,
                "description": f"{obj.avg_response_time_hours}h avg response",
                "points": f"+{obj.communication_score} points"
            }
        }


class SubscriberGrowthSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriberGrowth
        fields = '__all__'


class CampaignAnalyticSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = CampaignAnalytic
        fields = '__all__'

    def get_formatted_date(self, obj):
        return obj.date.strftime("%B %d, %Y")