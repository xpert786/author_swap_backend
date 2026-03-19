from django.contrib.auth import get_user_model
User = get_user_model()
from rest_framework.views import APIView
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal, InvalidOperation
from .serializers import (
    NewsletterSlotSerializer, NotificationSerializer, SwapPartnerSerializer, 
    SwapRequestSerializer, SwapManagementSerializer, BookSerializer, ProfileSerializer, RecentSwapSerializer,
    SubscriptionTierSerializer, UserSubscriptionSerializer, SubscriberVerificationSerializer,
    SubscriberGrowthSerializer, CampaignAnalyticSerializer, ChatMessageSerializer,
    ConversationListSerializer, ConversationPartnerSerializer,
    EmailListSerializer, EmailDetailSerializer, ComposeEmailSerializer,
    WalletSerializer, PaymentTransactionSerializer
)
from .ui_serializers import SlotExploreSerializer, SlotDetailsSerializer
from authentication.constants import GENRE_SUBGENRE_MAPPING


from .models import (
    Book, NewsletterSlot, Profile, SwapRequest, Notification, 
    SubscriptionTier, UserSubscription, SubscriberVerification,
    SubscriberGrowth, CampaignAnalytic, Email, ChatMessage, SwapPayment,
    UserWallet, PaymentTransaction
)
import calendar
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.db.models.functions import ExtractMonth
import pytz
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView

from urllib.parse import urlencode
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, NumberFilter, CharFilter, DateFilter
import requests



class CreateNewsletterSlotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NewsletterSlotSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Auto-populate audience_size from verification if it exists
            audience_size = 0
            verification = getattr(request.user, 'verification', None)
            if verification:
                audience_size = verification.audience_size

            slot = serializer.save(user=request.user, audience_size=audience_size)
            
            # Auto-create CampaignAnalytic entry for this slot
            from core.models import CampaignAnalytic
            from datetime import datetime
            
            # Format campaign name: "Newsletter: Genre (Date)" or "Swap: Genre (Date)"
            genre_display = slot.get_preferred_genre_display()
            date_str = slot.send_date.strftime("%b %-d, %Y") if slot.send_date else "TBD"
            
            # Check if slot has any confirmed swaps to determine type
            has_swaps = slot.swap_requests.filter(
                status__in=['completed', 'verified', 'confirmed', 'sending', 'scheduled']
            ).exists()
            campaign_type = "Swap" if has_swaps else "Newsletter"
            campaign_name = f"{campaign_type}: {genre_display} ({date_str})"
            
            # Get active subscribers count for subscribers field
            active_subscribers = 0
            if verification:
                active_subscribers = getattr(verification, 'active_subscribers', 0) or 0
            
            CampaignAnalytic.objects.create(
                user=request.user,
                name=campaign_name,
                date=slot.send_date or datetime.now().date(),
                subscribers=active_subscribers,
                open_rate=0.0,
                click_rate=0.0,
                type='Recent'
            )
            
            return Response({
                "message": "Newsletter slot created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        slots = request.user.newsletter_slots.all()

        # Apply filters from query params
        genre = request.query_params.get('genre', None)
        visibility = request.query_params.get('visibility', None)
        slot_status = request.query_params.get('status', None)
        month = request.query_params.get('month', None)
        year = request.query_params.get('year', None)

        if genre and genre.lower() != 'all':
            slots = slots.filter(preferred_genre=genre)
        if visibility and visibility.lower() not in ('all', 'all visibility'):
            slots = slots.filter(visibility=visibility.lower().replace(' ', '_'))
        if slot_status and slot_status.lower() not in ('all', 'all status'):
            slots = slots.filter(status=slot_status.lower())
        if month:
            slots = slots.filter(send_date__month=int(month))
        if year:
            slots = slots.filter(send_date__year=int(year))

        serializer = NewsletterSlotSerializer(slots.order_by('send_date', 'send_time'), many=True, context={'request': request})
        return Response({
            "message": "Newsletter slots retrieved successfully.",
            "count": slots.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class AudienceSizeView(APIView):
    """
    GET /api/audience-size/
    Returns the user's verified audience size from MailerLite.
    Used by the frontend to pre-fill or display audience size when creating slots.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        verification, _ = SubscriberVerification.objects.get_or_create(user=request.user)
        return Response({
            "audience_size": verification.active_subscribers,
            "is_connected": verification.is_connected_mailerlite,
            "last_verified": verification.last_verified_at
        }, status=status.HTTP_200_OK)


class NewsletterSlotDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = NewsletterSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NewsletterSlot.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Newsletter slot deleted successfully."}, status=status.HTTP_200_OK)


class GenreSubgenreMappingView(APIView):
    """
    Returns the mapping of primary genres to their subgenres.
    Used by the frontend to dynamically populate subgenre dropdowns.
    """
    def get(self, request):
        data = {}
        for genre, subgenres in GENRE_SUBGENRE_MAPPING.items():
            data[genre] = [
                {"value": val, "label": label} 
                for val, label in subgenres
            ]
            
        return Response(data, status=status.HTTP_200_OK)

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView


class BookDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Book.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # If this book is being set as primary, demote others
        if serializer.validated_data.get('is_primary_promo'):
             # Exclude current instance to avoid self-update issues
            Book.objects.filter(user=self.request.user).exclude(pk=self.get_object().pk).update(is_primary_promo=False)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Book deleted successfully."}, status=status.HTTP_200_OK)

class AddBookView(ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Book.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # If this is set as the primary book, demote others
        if serializer.validated_data.get('is_primary_promo'):
            Book.objects.filter(user=self.request.user).update(is_primary_promo=False)
        serializer.save(user=self.request.user)

    def _get_book(self, request):
        book_id = request.data.get('book_id')
        if not book_id:
            return None, Response({"book_id": "This field is required for updates."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            book = Book.objects.get(pk=book_id, user=request.user)
            return book, None
        except Book.DoesNotExist:
            return None, Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        book, error = self._get_book(request)
        if error:
            return error
        serializer = BookSerializer(book, data=request.data, context={'request': request})
        if serializer.is_valid():
            if serializer.validated_data.get('is_primary_promo'):
                Book.objects.filter(user=request.user).exclude(pk=book.pk).update(is_primary_promo=False)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        book, error = self._get_book(request)
        if error:
            return error
        serializer = BookSerializer(book, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            if serializer.validated_data.get('is_primary_promo'):
                Book.objects.filter(user=request.user).exclude(pk=book.pk).update(is_primary_promo=False)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        book, error = self._get_book(request)
        if error:
            return error
        book.delete()
        return Response({"message": "Book deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class ProfileDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        if Profile.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Profile already exists."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.first()
        if obj is None:
            from rest_framework.exceptions import NotFound
            raise NotFound({
                "detail": "Profile not found. Please create your profile first.",
                "has_profile": False
            })
        self.check_object_permissions(self.request, obj)
        return obj
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Profile deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class BookManagementStatsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_books = Book.objects.filter(user=request.user)
        
        # Calculate stats
        total_books = user_books.count()
        # Assuming you have an 'is_active' or 'is_promoted' flag
        active_promos = user_books.filter(is_active=True).count() 
        primary_promo = user_books.filter(is_primary_promo=True).count()
        
        # Example static data for logic, replace with actual calculation
        avg_open_rate = 0

        return Response({
            "total_books": total_books,
            "active_promotions": active_promos,
            "primary_promo": primary_promo,
            "avg_open_rate": f"{avg_open_rate}%"
        })

class NewsletterStatsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        # Get month/year from query params or default to current
        month = int(request.query_params.get('month', datetime.now().month))
        year = int(request.query_params.get('year', datetime.now().year))

        # Get filter params
        genre_filter = request.query_params.get('genre', None)
        visibility_filter = request.query_params.get('visibility', None)
        status_filter = request.query_params.get('status', None)

        # --- Base queryset with filters ---
        all_slots = NewsletterSlot.objects.filter(user=user)
        if genre_filter and genre_filter.lower() != 'all':
            all_slots = all_slots.filter(preferred_genre=genre_filter)
        if visibility_filter and visibility_filter.lower() not in ('all', 'all visibility'):
            all_slots = all_slots.filter(visibility=visibility_filter.lower().replace(' ', '_'))
        if status_filter and status_filter.lower() not in ('all', 'all status'):
            all_slots = all_slots.filter(status=status_filter.lower())

        # --- 1. TOP STATS CARDS DATA (filtered) ---
        # Confirmed = agreed & scheduled (but not yet sent): confirmed, scheduled, accepted
        confirmed_statuses = ['confirmed', 'scheduled', 'accepted', 'active']
        # Verified = sent & proven via ESP: verified, completed, sent
        verified_statuses = ['verified', 'completed', 'sent']
        
        stats = {
            "total": all_slots.count(),
            "published_slots": all_slots.filter(visibility='public').count(),
            "pending_swaps": SwapRequest.objects.filter(
                slot__in=all_slots, status='pending'
            ).count(),
            "confirmed_swaps": SwapRequest.objects.filter(
                slot__in=all_slots, status__in=confirmed_statuses
            ).count(),
            "verified_sent": SwapRequest.objects.filter(
                slot__in=all_slots, status__in=verified_statuses
            ).count()
        }

        # --- 2. CALENDAR DATA (filtered) ---
        calendar_data = []
        num_days = calendar.monthrange(year, month)[1]
        
        # Status definitions for swap lifecycle
        confirmed_statuses = ['confirmed', 'scheduled', 'accepted', 'active']
        verified_statuses = ['verified', 'completed', 'sent']

        slots_in_month = all_slots.filter(
            send_date__year=year, 
            send_date__month=month
        ).values('send_date', 'visibility', 'status').annotate(
            total=Count('id'),
            pending=Count('swap_requests', filter=Q(swap_requests__status='pending')),
            confirmed=Count('swap_requests', filter=Q(swap_requests__status__in=confirmed_statuses)),
            verified=Count('swap_requests', filter=Q(swap_requests__status__in=verified_statuses))
        )

        # Build lookup: one date can have multiple slots, so aggregate
        date_map = {}
        for s in slots_in_month:
            d = s['send_date']
            if d not in date_map:
                date_map[d] = {
                    'total': 0, 'pending': 0, 'confirmed': 0, 'verified': 0,
                    'has_public': False, 'has_available': False, 'has_booked': False, 'has_pending_slot': False,
                    'slots': []
                }
            date_map[d]['total'] += s['total']
            date_map[d]['pending'] += s['pending']
            date_map[d]['confirmed'] += s['confirmed']
            date_map[d]['verified'] += s['verified']
            if s.get('visibility') == 'public':
                date_map[d]['has_public'] = True
            if s.get('status') == 'available':
                date_map[d]['has_available'] = True
            elif s.get('status') == 'booked':
                date_map[d]['has_booked'] = True
            elif s.get('status') == 'pending':
                date_map[d]['has_pending_slot'] = True

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            day_stats = date_map.get(current_date, {})
            
            calendar_data.append({
                "date": current_date.isoformat(),
                "day": day,
                "slot_count": day_stats.get('total', 0),
                "has_slots": day_stats.get('total', 0) > 0,
                "has_published": day_stats.get('has_public', False),
                "has_available": day_stats.get('has_available', False),
                "has_booked": day_stats.get('has_booked', False),
                "has_confirmed": day_stats.get('confirmed', 0) > 0,
                "has_pending": day_stats.get('pending', 0) > 0 or day_stats.get('has_pending_slot', False),
                "has_verified": day_stats.get('verified', 0) > 0,
            })

        # --- 3. Active filters echo (for frontend state) ---
        active_filters = {
            "genre": genre_filter or "all",
            "visibility": visibility_filter or "all",
            "status": status_filter or "all",
        }

        return Response({
            "stats_cards": stats,
            "active_filters": active_filters,
            "calendar": {
                "month_name": calendar.month_name[month],
                "year": year,
                "days": calendar_data
            }
        })
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch notifications for current user
        notifications = Notification.objects.filter(recipient=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        
        # Grouping logic for the frontend "Today/Yesterday" view
        grouped_data = {}
        for item in serializer.data:
            group = item['time_group']
            if group not in grouped_data:
                grouped_data[group] = []
            grouped_data[group].append(item)
            
        return Response(grouped_data)

class TestWebSocketNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import Notification
        
        # Create a notification for the user making the request
        notification = Notification.objects.create(
            recipient=request.user,
            title="API Triggered Notification!",
            badge="TEST",
            message="You successfully hit the test endpoint and triggered a WebSocket message.",
            action_url="/"
        )
        return Response({"detail": "Notification sent."})

class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        notification_unread = Notification.objects.filter(recipient=user, is_read=False).count()
        chat_unread = ChatMessage.objects.filter(recipient=user, is_read=False).count()
        from core.models import Email
        email_unread = Email.objects.filter(recipient=user, is_read=False, folder='inbox').count()
        
        return Response({
            "notifications": notification_unread,
            "chat": chat_unread,
            "email": email_unread,
            "total": notification_unread + chat_unread + email_unread
        })
        
        return Response({"message": "WebSocket notification triggered!"})

class NewsletterSlotExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')

        try:
            slot = NewsletterSlot.objects.get(pk=pk, user=request.user)
        except NewsletterSlot.DoesNotExist:
            return Response({"detail": "Newsletter slot not found."}, status=status.HTTP_404_NOT_FOUND)

        export_format = request.query_params.get('format', 'ics').lower()
        
        # Calculate start and end times
        start_dt = datetime.combine(slot.send_date, slot.send_time)
        end_dt = start_dt + timedelta(hours=1) # Default duration of 1 hour

        title = f"Newsletter Slot: {slot.preferred_genre}"
        description = f"Audience Size: {slot.audience_size}\nSubgenres: {slot.subgenres}\nVisibility: {slot.visibility}"

        if export_format == 'google':
            base_url = "https://www.google.com/calendar/render"
            params = {
                'action': 'TEMPLATE',
                'text': title,
                'dates': f"{start_dt.strftime('%Y%m%dT%H%M%SZ')}/{end_dt.strftime('%Y%m%dT%H%M%SZ')}",
                'details': description,
            }
            return Response({"url": f"{base_url}?{urlencode(params)}"})

        elif export_format == 'outlook':
            base_url = "https://outlook.office.com/calendar/0/deeplink/compose"
            params = {
                'path': '/calendar/action/compose',
                'rru': 'addevent',
                'subject': title,
                'startdt': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'enddt': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'body': description,
            }
            return Response({"url": f"{base_url}?{urlencode(params)}"})

        elif export_format == 'ics':
            uid = f"slot-{slot.id}@{request.get_host()}"
            ics_content = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Author Swap//Newsletter Slot//EN",
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{title}",
                f"DESCRIPTION:{description.replace('\\n', '\\\\n')}",
                "END:VEVENT",
                "END:VCALENDAR"
            ]
            response = HttpResponse("\n".join(ics_content), content_type='text/calendar')
            response['Content-Disposition'] = f'attachment; filename="newsletter_slot_{slot.id}.ics"'
            return response

        elif export_format == 'json':
            return Response({
                "uid": f"slot-{slot.id}@{request.get_host()}",
                "dtstamp": datetime.now().strftime('%Y%m%dT%H%M%SZ'),
                "dtstart": start_dt.strftime('%Y%m%dT%H%M%SZ'),
                "dtend": end_dt.strftime('%Y%m%dT%H%M%SZ'),
                "summary": title,
                "description": description,
                "metadata": {
                    "id": slot.id,
                    "preferred_genre": slot.preferred_genre,
                    "audience_size": slot.audience_size,
                    "subgenres": slot.subgenres,
                    "visibility": slot.visibility,
                    "send_date": slot.send_date.isoformat(),
                    "send_time": slot.send_time.isoformat(),
                }
            })

        return Response({"detail": "Invalid export format. Supported: google, outlook, ics, json."}, status=status.HTTP_400_BAD_REQUEST)

class NewsletterSlotFilter(FilterSet):
    min_audience = NumberFilter(field_name="audience_size", lookup_expr='gte')
    max_audience = NumberFilter(field_name="audience_size", lookup_expr='lte')
    min_reputation = NumberFilter(field_name="user__profiles__reputation_score", lookup_expr='gte')
    genre = CharFilter(field_name="preferred_genre")
    promotion = CharFilter(field_name="promotion_type")
    start_date = DateFilter(field_name="send_date", lookup_expr='gte')
    end_date = DateFilter(field_name="send_date", lookup_expr='lte')

    class Meta:
        model = NewsletterSlot
        fields = ['genre', 'min_audience', 'max_audience', 'min_reputation', 'promotion', 'status', 'start_date', 'end_date']

class SwapPartnerDiscoveryView(ListCreateAPIView):
    """
    Discovery view to find slots from other authors with advanced filtering.
    """
    serializer_class = SwapPartnerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = NewsletterSlotFilter

    def get_queryset(self):
        return NewsletterSlot.objects.filter(
            visibility='public', 
            status='available'
        ).exclude(user=self.request.user).order_by('-created_at')


class SwapRequestListView(APIView):
    """
    Handles listing and creating swap requests.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slot_id=None):
        # Check if user has at least one book to promote
        user_books_count = Book.objects.filter(user=request.user).count()
        if user_books_count == 0:
            return Response(
                {"detail": "You must have at least one book to send a swap request. Please add a book first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data.copy()
        
        # Handle slot_id from URL keyword argument
        if slot_id and 'slot' not in data:
            data['slot'] = slot_id
            
        # Handle cases where 'slot_id' is passed in body instead of 'slot'
        if 'slot_id' in data and 'slot' not in data:
            data['slot'] = data['slot_id']
            
        # Handle cases where slot ID is passed as a query param
        if 'slot' not in data and request.query_params.get('slot_id'):
            data['slot'] = request.query_params.get('slot_id')

        serializer = SwapRequestSerializer(data=data)
        if serializer.is_valid():
            slot = serializer.validated_data['slot']
            book = serializer.validated_data.get('book')
            offered_slot = serializer.validated_data.get('offered_slot')
            requested_book = serializer.validated_data.get('requested_book')
            
            # Auto-pick the requester's book to promote if none provided
            if not book:
                primary_book = Book.objects.filter(user=request.user, is_primary_promo=True).first()
                if primary_book:
                    book = primary_book
                else:
                    # Fallback to the latest active book
                    book = Book.objects.filter(user=request.user, is_active=True).order_by('-created_at').first()
            
            # Auto-pick the slot the requester is offering in return ("Partner Sends Date/Time")
            if not offered_slot:
                offered_slot = NewsletterSlot.objects.filter(user=request.user, status='available').order_by('send_date').first()
                
            # Auto-pick the book the slot owner wants to promote ("Partner Sends Book")
            if not requested_book:
                primary_target = Book.objects.filter(user=slot.user, is_primary_promo=True).first()
                if primary_target:
                    requested_book = primary_target
                else:
                    requested_book = Book.objects.filter(user=slot.user, is_active=True).order_by('-created_at').first()
                    
            # Check if a request already exists
            if SwapRequest.objects.filter(slot=slot, requester=request.user).exists():
                return Response({"detail": "You have already sent a request for this slot."}, status=status.HTTP_400_BAD_REQUEST)

            # Link validation (Resilient for mock/test links)
            if book:
                links = [book.amazon_url, book.apple_url, book.kobo_url, book.barnes_noble_url]
                for link in links:
                    if link and 'test' not in link and 'localhost' not in link: # Skip check for test/local links
                        try:
                            r = requests.head(link, timeout=3, allow_redirects=True)
                            # We still check for hard 404s on real links, but won't block the whole request
                            # if it's just a connection glitch or mock link
                        except requests.RequestException:
                            pass # For now, we skip blocking on connectivity issues to avoid UX friction

            initial_status = 'pending'
            target_profile = slot.user.profiles.first()
            requester_profile = request.user.profiles.first()

            if target_profile and requester_profile:
                is_friend = target_profile.friends.filter(id=requester_profile.id).exists()
                meets_rep = (target_profile.auto_approve_min_reputation > 0 and 
                             requester_profile.reputation_score >= target_profile.auto_approve_min_reputation)
                
                if (target_profile.auto_approve_friends and is_friend) or meets_rep:
                    initial_status = 'confirmed'

            swap_req = serializer.save(
                requester=request.user, 
                status=initial_status, 
                book=book,
                offered_slot=offered_slot,
                requested_book=requested_book
            )
            
            # MailerLite Notification
            if initial_status == 'pending':
                from core.services.mailerlite_service import send_swap_request_notification
                try:
                    # Notify the receiving author (slot owner)
                    send_swap_request_notification(slot.user.email)
                except Exception:
                    pass
                    

            response_data = SwapRequestSerializer(swap_req).data
            response_data['detail'] = f"Swap request sent successfully! {request.user.username} has requested the {slot.send_date} slot."
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        slot_id = kwargs.get('slot_id')
        if slot_id:
            try:
                slot = NewsletterSlot.objects.get(id=slot_id)
                serializer = SlotExploreSerializer(slot, context={'request': request})
                response_data = dict(serializer.data)
                
                # Fetch the current user's active books to allow them to pick one to promote
                from core.models import Book
                from core.serializers import BookSerializer
                user_books = Book.objects.filter(user=request.user)
                
                # Use the exact same serializer as the AddBookView to reuse the structure
                books_data = list(BookSerializer(user_books, many=True, context={'request': request}).data)
                
                # Check if the user has already requested this slot
                from core.models import SwapRequest
                sent_request = SwapRequest.objects.filter(slot=slot, requester=request.user).exists()
                response_data['sent_request'] = sent_request
                
                # Compute global Compatibility Indicators
                indicators = {
                    "genre_match": False,
                    "audience_comparable": False,
                    "reliability_match": False
                }
                
                owner_profile = slot.user.profiles.first()
                requester_profile = request.user.profiles.first()
                
                if owner_profile and requester_profile:
                    # Audience Comparable: Simplified logic
                    indicators["audience_comparable"] = True
                    
                    # Reliability Match: reputation score difference <= 1.0
                    owner_rep = owner_profile.reputation_score or 0.0
                    req_rep = requester_profile.reputation_score or 0.0
                    indicators["reliability_match"] = abs(owner_rep - req_rep) <= 1.0

                # Genre Match: True if specific book matches, else verify if any book matches
                book_id = request.query_params.get('book_id')
                if book_id:
                    selected_book = user_books.filter(id=book_id).first()
                    if selected_book:
                        indicators["genre_match"] = selected_book.primary_genre == slot.preferred_genre
                elif any(b.primary_genre == slot.preferred_genre for b in user_books):
                    indicators["genre_match"] = True
                
                response_data['compatibility'] = indicators

                # Inject compatibility indicators into each book in my_books for instant frontend updates
                for book_item in books_data:
                    book_obj = user_books.filter(id=book_item['id']).first()
                    if book_obj:
                        book_item['compatibility'] = {
                            "genre_match": book_obj.primary_genre == slot.preferred_genre,
                            "audience_comparable": indicators["audience_comparable"],
                            "reliability_match": indicators["reliability_match"]
                        }
                
                response_data['my_books'] = books_data
                
                return Response(response_data)
            except NewsletterSlot.DoesNotExist:
                return Response({"detail": "Slot not found."}, status=status.HTTP_404_NOT_FOUND)
                
        # Requested to return data from NewsletterSlot table instead of SwapRequest
        slots = NewsletterSlot.objects.all().order_by('-created_at')
        serializer = SlotExploreSerializer(slots, many=True)
        return Response(serializer.data)

class SwapRequestDetailView(RetrieveAPIView):
    """
    Requested to fetch from NewsletterSlot table.
    Endpoint: /api/swap-requests/<id>/
    """
    queryset = NewsletterSlot.objects.all()
    serializer_class = SlotDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NewsletterSlot.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Creates a swap request for this specific slot.
        """
        slot_id = kwargs.get('pk')
        return SwapRequestListView().post(request, slot_id=slot_id)

class RequestSwapPlacementView(APIView):
    """
    POST /api/slots/<slot_id>/request-placement/
    Handles the Figma "Request Swap Placement" modal submission.
    Expects: book (ID), preferred_placement, max_partners_acknowledged, 
             amazon_url, apple_url, kobo_url, barnes_noble_url, message
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slot_id):
        # Check if user has at least one book to promote
        user_books_count = Book.objects.filter(user=request.user).count()
        if user_books_count == 0:
            return Response(
                {"detail": "You must have at least one book to send a swap request. Please add a book first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            slot = NewsletterSlot.objects.get(id=slot_id)
        except NewsletterSlot.DoesNotExist:
            all_slots = list(NewsletterSlot.objects.values_list('id', flat=True)[:20])
            return Response({"detail": f"Slot {slot_id} not found. Available slots: {all_slots}"}, status=status.HTTP_404_NOT_FOUND)

        #if slot.user == request.user:
        #    return Response({"detail": "You cannot request a swap for your own slot."}, status=status.HTTP_400_BAD_REQUEST)

        if SwapRequest.objects.filter(slot=slot, requester=request.user).exists():
            return Response({"detail": "You have already sent a request for this slot."}, status=status.HTTP_400_BAD_REQUEST)

        book_id = request.data.get('book')
        if not book_id:
            return Response({"detail": "Please select a book to promote."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(id=book_id, user=request.user)
        except Book.DoesNotExist:
            return Response({"detail": "Invalid book selected."}, status=status.HTTP_400_BAD_REQUEST)

        # Update retailer links directly from the Swap Request form (Figma)
        updated_links = False
        link_fields = ['amazon_url', 'apple_url', 'kobo_url', 'barnes_noble_url']
        for field in link_fields:
            if field in request.data:
                setattr(book, field, request.data[field])
                updated_links = True
        if updated_links:
            book.save()

        # Resilient Link validation
        links = [book.amazon_url, book.apple_url, book.kobo_url, book.barnes_noble_url]
        for link in links:
            if link and 'test' not in link and 'localhost' not in link:
                try:
                    r = requests.head(link, timeout=3, allow_redirects=True)
                except requests.RequestException:
                    pass

        # Parse UI fields
        preferred_placement = request.data.get('preferred_placement', 'middle').lower()
        max_partners_acknowledged = int(request.data.get('max_partners_acknowledged', 5))
        message = request.data.get('message', '')

        initial_status = 'pending'
        target_profile = slot.user.profiles.first()
        requester_profile = request.user.profiles.first()

        if target_profile and requester_profile:
            is_friend = target_profile.friends.filter(id=requester_profile.id).exists()
            meets_rep = (target_profile.auto_approve_min_reputation > 0 and 
                         requester_profile.reputation_score >= target_profile.auto_approve_min_reputation)
            
            if (target_profile.auto_approve_friends and is_friend) or meets_rep:
                initial_status = 'confirmed'

        swap_req = SwapRequest.objects.create(
            slot=slot,
            requester=request.user,
            book=book,
            status=initial_status,
            preferred_placement=preferred_placement,
            max_partners_acknowledged=max_partners_acknowledged,
            message=message
        )
        
        # If auto-approved, check if slot should be marked as booked
        # Check if slot should be booked based on current accepted swaps
        accepted_count = SwapRequest.objects.filter(
            slot=slot,
            status__in=['completed', 'confirmed', 'verified', 'scheduled']
        ).count()

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[SLOT_STATUS DirectPayment] Slot {slot.id}: accepted_count={accepted_count}, max_partners={slot.max_partners}, current_status={slot.status}")

        if accepted_count >= slot.max_partners:
            slot.status = 'booked'
            slot.save(update_fields=['status'])
            logger.warning(f"[SLOT_STATUS DirectPayment] Slot {slot.id} set to BOOKED")
        
        # MailerLite Notification
        if initial_status == 'pending':
            from core.services.mailerlite_service import send_swap_request_notification
            try:
                # Notify the receiving author (slot owner)
                send_swap_request_notification(slot.user.email)
            except Exception:
                pass

        
        response_data = SwapRequestSerializer(swap_req).data
        response_data['detail'] = f"Swap request sent successfully! You have requested the {slot.send_date} slot."
        return Response(response_data, status=status.HTTP_201_CREATED)

    def patch(self, request, slot_id):
        try:
            slot = NewsletterSlot.objects.get(id=slot_id)
        except NewsletterSlot.DoesNotExist:
            return Response({"detail": f"Slot {slot_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            swap_req = SwapRequest.objects.get(slot=slot, requester=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found for this slot."}, status=status.HTTP_404_NOT_FOUND)

        book_id = request.data.get('book')
        if book_id:
            try:
                book = Book.objects.get(id=book_id, user=request.user)
                swap_req.book = book
            except Book.DoesNotExist:
                return Response({"detail": "Invalid book selected."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            book = swap_req.book

        # Update retailer links from the Swap Request form
        updated_links = False
        link_fields = ['amazon_url', 'apple_url', 'kobo_url', 'barnes_noble_url']
        for field in link_fields:
            if field in request.data:
                setattr(book, field, request.data[field])
                updated_links = True
        
        if updated_links:
            book.save()

            # Resilient Link validation
            links = [book.amazon_url, book.apple_url, book.kobo_url, book.barnes_noble_url]
            for link in links:
                if link and 'test' not in link and 'localhost' not in link:
                    try:
                        requests.head(link, timeout=3, allow_redirects=True)
                    except requests.RequestException:
                        pass

        if 'preferred_placement' in request.data:
            swap_req.preferred_placement = request.data.get('preferred_placement').lower()
        if 'max_partners_acknowledged' in request.data:
            swap_req.max_partners_acknowledged = int(request.data.get('max_partners_acknowledged'))
        if 'message' in request.data:
            swap_req.message = request.data.get('message')

        swap_req.save()

        response_data = SwapRequestSerializer(swap_req).data
        response_data['detail'] = "Swap request updated successfully!"
        return Response(response_data, status=status.HTTP_200_OK)

class MyPotentialBooksView(ListAPIView):
    """
    Lists the current user's books to choose from when initiating a swap.
    """
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Book.objects.filter(user=self.request.user)

class SwapPartnerDetailView(RetrieveAPIView):
    """
    Detailed information for a specific slot/partner opportunity.
    """
    queryset = NewsletterSlot.objects.all()
    serializer_class = SwapPartnerSerializer
    permission_classes = [IsAuthenticated]

class RecentSwapHistoryView(ListAPIView):
    """
    Returns recent swap history for a specific author.
    """
    serializer_class = RecentSwapSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        author_id = self.kwargs.get('author_id')
        return SwapRequest.objects.filter(
            slot__user_id=author_id, 
            status__in=['confirmed', 'verified', 'scheduled', 'completed']
        ).order_by('-created_at')


# =====================================================================
# SWAP MANAGEMENT PAGE (Figma: "Swap Management")
# =====================================================================
from django.utils import timezone as tz
from core.services.mailerlite_service import (
    send_swap_request_notification,
    approve_swap_notification,
    reject_swap_notification,
    sync_profile_audience,
)


class SwapManagementListView(APIView):
    """
    GET /api/swaps/
    Returns swap requests grouped/filtered by tab.
    Tabs: all, pending, sending, rejected, scheduled, completed
    Also supports ?search=<query> for searching by author, book, or date.
    """
    permission_classes = [IsAuthenticated]

    TAB_STATUS_MAP = {
        'all': None,
        'pending': ['pending'],
        'sending': ['sending'],
        'rejected': ['rejected'],
        'scheduled': ['scheduled', 'completed', 'confirmed'],
        'completed': ['verified'],
    }

    def get(self, request):
        user = request.user
        tab = request.query_params.get('tab', 'all').lower()
        status_filter = request.query_params.get('status', '').lower()
        search = request.query_params.get('search', '').strip()

        # Auto-expire pending swaps older than 7 days
        from datetime import timedelta
        expired_cutoff = tz.now() - timedelta(days=7)
        expired_swaps = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user),
            status='pending',
            created_at__lt=expired_cutoff
        )
        if expired_swaps.exists():
            expired_swaps.update(
                status='rejected',
                rejection_reason='Auto-rejected: 7-day acceptance window expired.',
                rejected_at=tz.now()
            )

        # Base queryset: swaps where the current user is either the requester (sent) or owns the slot (received)
        qs = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user)
        ).select_related(
            'requester', 'slot', 'book'
        ).order_by('-created_at')

        # Status filtering (takes priority over tab filtering)
        if status_filter:
            if tab == 'pending':
                qs = qs.filter(slot__user=user, status='pending')
            elif tab == 'sending':
                qs = qs.filter(requester=user, status='pending')
            elif tab == 'rejected':
                qs = qs.filter(status='rejected')
            elif tab == 'scheduled':
                qs = qs.filter(status='scheduled')
            elif tab == 'completed':
                qs = qs.filter(status__in=['completed', 'verified'])
        else:
            # Tab filtering (only if no explicit status filter)
            if tab == 'pending':
                qs = qs.filter(slot__user=user, status='pending')
            elif tab == 'sending':
                qs = qs.filter(requester=user, status='pending')
            elif tab == 'rejected':
                qs = qs.filter(status='rejected')
            elif tab == 'scheduled':
                qs = qs.filter(status='scheduled')
            elif tab == 'completed':
                qs = qs.filter(status__in=['completed', 'verified'])

        # Search by author name, book title, or date
        if search:
            qs = qs.filter(
                Q(requester__profiles__name__icontains=search) |
                Q(requester__username__icontains=search) |
                Q(book__title__icontains=search) |
                Q(slot__send_date__icontains=search)
            ).distinct()

        # Removed blocking sync_profile_audience loop to prevent API cancellation/timeout.
        # This should be handled by a background task or a separate endpoint.

        serializer = SwapManagementSerializer(qs, many=True, context={'request': request})

        # Tab counts for the badge numbers on each tab
        all_qs = SwapRequest.objects.filter(Q(slot__user=user) | Q(requester=user))
        
        # If status filter is provided, use it for counts
        if status_filter:
            tab_counts = {
                'all': all_qs.count(),
                'filtered': all_qs.filter(status=status_filter).count(),
            }
        else:
            tab_counts = {
                'all': all_qs.count(),
                'pending': all_qs.filter(slot__user=user, status='pending').count(),
                'sending': all_qs.filter(requester=user, status='pending').count(),
                'rejected': all_qs.filter(status='rejected').count(),
                'scheduled': all_qs.filter(status='scheduled').count(),
                'completed': all_qs.filter(status__in=['completed', 'verified']).count(),
            }

        return Response({
            'tab': tab,
            'status_filter': status_filter if status_filter else None,
            'tab_counts': tab_counts,
            'results': serializer.data,
        })


class AcceptSwapView(APIView):
    """
    POST /api/accept-swap/<id>/
    Slot owner accepts a swap request.
    Moves subscriber from Pending → Approved in MailerLite.
    """ 
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            swap = SwapRequest.objects.get(pk=pk, slot__user=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found."}, status=status.HTTP_404_NOT_FOUND)

        if swap.status not in ['pending']:
            return Response({"detail": f"Cannot accept a swap in '{swap.status}' state."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if slot is free (no payment required)
        slot = swap.slot
        is_free_slot = slot.promotion_type == 'free' or (slot.price is None or slot.price == 0)
        
        # Update status: if free, mark as completed; otherwise scheduled
        if is_free_slot:
            swap.status = 'completed'
        else:
            swap.status = 'scheduled'
        swap.save()

        # Check if slot should be booked based on current accepted swaps
        accepted_count = SwapRequest.objects.filter(
            slot=slot,
            status__in=['completed', 'confirmed', 'verified', 'scheduled']
        ).count()

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[SLOT_STATUS] Slot {slot.id}: accepted_count={accepted_count}, max_partners={slot.max_partners}, current_status={slot.status}")

        if accepted_count >= slot.max_partners:
            slot.status = 'booked'
            slot.save(update_fields=['status'])
            logger.warning(f"[SLOT_STATUS] Slot {slot.id} set to BOOKED")
        elif accepted_count < slot.max_partners and slot.status == 'booked':
            # Revert to available if it was booked but now has room
            slot.status = 'available'
            slot.save(update_fields=['status'])
            logger.warning(f"[SLOT_STATUS] Slot {slot.id} reverted to AVAILABLE")

        # Update CampaignAnalytic entry to change from Newsletter to Swap type
        from core.models import CampaignAnalytic
        from datetime import datetime
        
        genre_display = slot.get_preferred_genre_display()
        date_str = slot.send_date.strftime("%b %-d, %Y") if slot.send_date else "TBD"
        old_campaign_name = f"Newsletter: {genre_display} ({date_str})"
        new_campaign_name = f"Swap: {genre_display} ({date_str})"
        
        # Try to update existing Newsletter campaign to Swap
        try:
            campaign = CampaignAnalytic.objects.filter(
                user=slot.user,
                name=old_campaign_name
            ).first()
            
            if campaign:
                campaign.name = new_campaign_name
                campaign.save(update_fields=['name'])
                print(f"[DEBUG] Updated campaign: {old_campaign_name} → {new_campaign_name}")
            else:
                # If no existing campaign found, create a new Swap campaign
                CampaignAnalytic.objects.create(
                    user=slot.user,
                    name=new_campaign_name,
                    date=slot.send_date or datetime.now().date(),
                    subscribers=0,
                    open_rate=0.0,
                    click_rate=0.0,
                    type='Recent'
                )
                print(f"[DEBUG] Created new Swap campaign: {new_campaign_name}")
        except Exception as e:
            print(f"[DEBUG] Error updating campaign: {e}")

        # MailerLite: move from Pending → Approved group
        requester_email = swap.requester.email
        try:
            approve_swap_notification(requester_email)
        except Exception:
            pass  # Non-critical; log internally

        # Notification for requester - different message for free vs paid
        if is_free_slot:
            notification_title = "Swap Request Completed! ✅"
            notification_message = f"Great news! {request.user.username} has accepted your swap request for their free {swap.slot.get_preferred_genre_display()} slot. The swap is now completed!"
        else:
            notification_title = "Swap Request Accepted! ✅"
            notification_message = f"Good news! {request.user.username} has accepted your swap request for their {swap.slot.get_preferred_genre_display()} slot. Payment required to confirm."
        
        Notification.objects.create(
            recipient=swap.requester,
            title=notification_title,
            badge="SWAP",
            message=notification_message,
            action_url=f"/dashboard/swaps/track/{swap.id}/"
        )

        return Response({
            "detail": f"Swap request accepted. Status: {swap.status}.",
            "swap": SwapManagementSerializer(swap, context={'request': request}).data
        })


class RejectSwapView(APIView):
    """
    POST /api/reject-swap/<id>/
    Slot owner declines a swap request with an optional reason.
    Body: { "reason": "Audience size too small for current campaign goals." }
    Moves subscriber from Pending → Rejected group in MailerLite.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            swap = SwapRequest.objects.get(pk=pk, slot__user=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found."}, status=status.HTTP_404_NOT_FOUND)

        if swap.status not in ['pending', 'confirmed']:
            return Response({"detail": f"Cannot reject a swap in '{swap.status}' state."}, status=status.HTTP_400_BAD_REQUEST)

        swap.status = 'rejected'
        swap.rejection_reason = request.data.get('rejection_reason', request.data.get('reason', ''))
        swap.rejected_at = tz.now()
        swap.save()
        
        # Revert slot status to available if it was booked and now has room
        slot = swap.slot
        if slot.status == 'booked':
            accepted_count = SwapRequest.objects.filter(
                slot=slot, 
                status__in=['completed', 'confirmed', 'verified', 'scheduled']
            ).count()
            if accepted_count < slot.max_partners:
                slot.status = 'available'
                slot.save(update_fields=['status'])

        # MailerLite: move to Rejected group
        requester_email = swap.requester.email
        try:
            reject_swap_notification(requester_email)
        except Exception:
            pass

        # Notification for requester
        Notification.objects.create(
            recipient=swap.requester,
            title="Swap Request Update",
            badge="SWAP",
            message=f"Your swap request with {request.user.username} was not accepted at this time.",
            action_url=f"/dashboard/swaps/"
        )

        return Response({
            "detail": "Swap request declined.",
            "swap": SwapManagementSerializer(swap, context={'request': request}).data
        })


class RestoreSwapView(APIView):
    """
    POST /api/restore-swap/<id>/
    Restores a previously rejected swap request back to pending.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            swap = SwapRequest.objects.get(pk=pk, slot__user=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found."}, status=status.HTTP_404_NOT_FOUND)

        if swap.status != 'rejected':
            return Response({"detail": "Only rejected swaps can be restored."}, status=status.HTTP_400_BAD_REQUEST)

        swap.status = 'pending'
        swap.rejection_reason = None
        swap.rejected_at = None
        swap.save()

        # MailerLite: move back to Pending group
        requester_email = swap.requester.email
        try:
            send_swap_request_notification(requester_email)
        except Exception:
            pass

        # Notification for requester
        Notification.objects.create(
            recipient=swap.requester,
            title="Swap Request Restored 🔄",
            badge="SWAP",
            message=f"{request.user.username} has restored your rejected swap request back to pending.",
            action_url=f"/dashboard/swaps/manage/"
        )

        return Response({
            "detail": "Swap request restored to pending.",
            "swap": SwapManagementSerializer(swap, context={'request': request}).data
        })


class SwapHistoryDetailView(APIView):
    """
    GET /api/swap-history/<id>/
    Returns detailed swap history for the 'Track My Swap' / 'View Swap History' page (Figma).
    Includes: partner info, dates, social links, promoting book, CTR analysis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from core.serializers import SwapHistoryDetailSerializer

        try:
            # User can view if they are the slot owner OR the requester
            swap = SwapRequest.objects.select_related(
                'requester', 'slot', 'book'
            ).prefetch_related('link_clicks').get(
                Q(slot__user=request.user) | Q(requester=request.user),
                pk=pk,
            )
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SwapHistoryDetailSerializer(swap, context={'request': request})
        return Response(serializer.data)


class TrackMySwapView(APIView):
    """
    GET /api/track-swap/<id>/
    Returns data for the 'Track My Swap' modal (Figma).
    Shows: partner info, promoting book, countdown, deadline, links.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from core.serializers import TrackMySwapSerializer

        try:
            swap = SwapRequest.objects.select_related(
                'requester', 'slot', 'book'
            ).get(
                Q(slot__user=request.user) | Q(requester=request.user),
                pk=pk,
            )
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap not found."}, status=status.HTTP_404_NOT_FOUND)

        # Auto-expire if pending for > 7 days
        from datetime import timedelta
        from django.utils import timezone as tz
        if swap.status == 'pending':
            cutoff = tz.now() - timedelta(days=7)
            if swap.created_at < cutoff:
                swap.status = 'rejected'
                swap.rejection_reason = 'Auto-rejected: 7-day acceptance window expired.'
                swap.rejected_at = tz.now()
                swap.save()

        serializer = TrackMySwapSerializer(swap, context={'request': request})
        
        # Ensure link click tracking exists for this swap
        from core.models import SwapLinkClick
        if not swap.link_clicks.exists() and swap.book:
            # Create default tracking link for the swap
            destination_url = getattr(swap.book, 'amazon_url', None) or getattr(swap.book, 'website_url', None) or "#"
            SwapLinkClick.objects.get_or_create(
                swap=swap,
                link_name=f"Swap Promo - {swap.book.title}",
                destination_url=destination_url,
                defaults={'clicks': 0}
            )
            # Refresh serializer to include the new link
            serializer = TrackMySwapSerializer(swap, context={'request': request})
        
        return Response(serializer.data)


class CancelSwapView(APIView):
    """
    POST /api/cancel-swap/<id>/
    Cancels an active swap request (from the Track My Swap modal).
    Only the requester (who sent the swap request) can cancel it.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            swap = SwapRequest.objects.get(pk=pk, requester=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found."}, status=status.HTTP_404_NOT_FOUND)

        if swap.status in ['completed', 'verified']:
            return Response(
                {"detail": f"Cannot cancel a swap in '{swap.status}' state."},
                status=status.HTTP_400_BAD_REQUEST
            )

        swap.status = 'rejected'
        swap.rejection_reason = 'Cancelled by requester.'
        swap.rejected_at = tz.now()
        swap.save()
        
        # Revert slot status to available if it was booked and now has room
        slot = swap.slot
        if slot.status == 'booked':
            accepted_count = SwapRequest.objects.filter(
                slot=slot, 
                status__in=['completed', 'confirmed', 'verified', 'scheduled']
            ).count()

            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[SLOT_STATUS CancelSwap] Slot {slot.id}: accepted_count={accepted_count}, max_partners={slot.max_partners}, current_status={slot.status}")

            if accepted_count < slot.max_partners:
                slot.status = 'available'
                slot.save(update_fields=['status'])
                logger.warning(f"[SLOT_STATUS CancelSwap] Slot {slot.id} reverted to AVAILABLE")

        # Notification for slot owner
        from core.models import Notification
        Notification.objects.create(
            recipient=swap.slot.user,
            title="Swap Cancelled 🛑",
            badge="SWAP",
            message=f"{request.user.username} has cancelled their swap request for your {swap.slot.send_date} slot.",
            action_url=f"/dashboard/swaps/manage/"
        )

        return Response({
            "detail": "Swap request cancelled successfully.",
            "swap_id": swap.id,
            "status": swap.status,
        })



class AuthorReputationView(APIView):
    """
    GET /api/author-reputation/
    Returns the current user's reputation score, badges, and breakdown
    based on the Author Reputation System UI.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.serializers import AuthorReputationSerializer
        profile = request.user.profiles.first()
        if not profile:
            return Response({"detail": "Profile not found. Please create a profile first."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AuthorReputationSerializer(profile, context={'request': request})
        return Response(serializer.data)


class SubscriberVerificationView(APIView):
    """
    GET /api/subscriber-verification/
    Returns user's verification status, current subscription, and available tiers.
    
    POST /api/subscriber-verification/
    Select a subscription plan.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        verification, _ = SubscriberVerification.objects.get_or_create(user=request.user)
        subscription = UserSubscription.objects.filter(user=request.user, is_active=True).first()

        # ── Proactively sync from Stripe to catch any recent Checkout completions ──
        # This ensures that upgrades (which create NEW subscriptions) are caught immediately.
        subscription = _sync_user_subscription_from_stripe(request.user) or subscription

        tiers = SubscriptionTier.objects.all().order_by('price')

        sub_data = UserSubscriptionSerializer(subscription).data if subscription else None
        
        # 🔗 Add Stripe Customer Portal URL for billing management
        if subscription and subscription.stripe_customer_id:
            try:
                portal_session = stripe.billing_portal.Session.create(
                    customer=subscription.stripe_customer_id,
                    return_url="http://72.61.251.114/authorswap-frontend/subscription",
                    flow_data={
                        'type': 'payment_method_update'
                    }
                )
                if sub_data:
                    sub_data['portal_url'] = portal_session.url
            except Exception:
                pass

        return Response({
            "verification": SubscriberVerificationSerializer(verification).data,
            "subscription": sub_data,
            "available_tiers": SubscriptionTierSerializer(tiers, many=True).data,
        })


    def post(self, request):
        """
        Legacy mock endpoint.
        Returns an error indicating that plan selection must go through Stripe.
        """
        return Response(
            {"error": "This endpoint is deprecated. Use /api/stripe/create-checkout-session/ to select or upgrade a plan."},
            status=status.HTTP_400_BAD_REQUEST
        )


class ConnectMailerLiteView(APIView):
    """
    POST /api/connect-mailerlite/
    Connects user's account to MailerLite using an API key.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        api_key = request.data.get('api_key')
        if not api_key:
            return Response({"error": "API Key is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate API key with MailerLite before saving
        try:
            import requests
            import logging
            logger = logging.getLogger(__name__)
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            # Test API by fetching account info
            logger.info(f"Testing MailerLite API with key: {api_key[:8]}...")
            response = requests.get('https://connect.mailerlite.com/api/account', headers=headers, timeout=10)
            logger.info(f"MailerLite API response status: {response.status_code}")
            logger.info(f"MailerLite API response body: {response.text[:200]}...")
            
            if response.status_code != 200:
                return Response({
                    "error": "Invalid MailerLite API Key",
                    "details": f"API returned status {response.status_code}: {response.text[:100]}"
                }, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.RequestException as e:
            logger.error(f"MailerLite API request failed: {str(e)}")
            return Response({
                "error": "Failed to validate API Key",
                "details": f"Connection error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from core.services.mailerlite_service import sync_profile_audience
        from django.utils import timezone
        
        profile = request.user.profiles.first()
        if profile:
            # We must save the key FIRST so sync_profile_audience can use it correctly
            verification, _ = SubscriberVerification.objects.get_or_create(user=request.user)
            verification.mailerlite_api_key = api_key
            verification.save()

            audience = sync_profile_audience(profile, api_key=api_key)
            
            verification.is_connected_mailerlite = True
            verification.mailerlite_api_key_last_4 = api_key[-4:]
            verification.audience_size = audience
            verification.last_verified_at = timezone.now()
            verification.save()
            
            # Notification for MailerLite connection
            Notification.objects.create(
                recipient=request.user,
                title="MailerLite Connected! 🔗",
                badge="VERIFIED",
                message=f"Success! Your MailerLite account is connected. We found {audience:,} subscribers.",
                action_url="/dashboard/subscriber-verification/"
            )
            
            return Response({
                "message": "Successfully connected to MailerLite", 
                "audience_size": audience,
                "status": "active" if audience > 0 else "empty"
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)


class SubscriberAnalyticsView(APIView):
    """
    GET /api/subscriber-analytics/
    Returns comprehensive analytics for the Subscriber Verification & Analytics page.
    Triggers a real-time sync with MailerLite if connected.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.services.mailerlite_service import sync_subscriber_analytics, get_subscriber_counts_by_status
        
        # DEBUG: Force refresh from database
        from core.models import SubscriberVerification
        verification, created = SubscriberVerification.objects.get_or_create(user=request.user)
        print(f"[DEBUG] Before sync - active_subscribers: {verification.active_subscribers}, audience_size: {verification.audience_size}")
        
        # Check if user wants to skip sync (for faster loading)
        skip_sync = request.GET.get('skip_sync', '').lower() in ['true', '1', 'yes']
        
        if skip_sync:
            # Use cached data without syncing
            from core.models import SubscriberVerification
            verification, _ = SubscriberVerification.objects.get_or_create(user=request.user)
            print(f"[DEBUG] Skip sync - using cached data for user {request.user.username}")
        else:
            # Trigger real-time sync (this calls get_subscriber_counts_by_status and updates the model)
            verification = sync_subscriber_analytics(request.user)
            print(f"[DEBUG] After sync - active_subscribers: {verification.active_subscribers}, audience_size: {verification.audience_size}")
            
            # After sync, ensure we have the latest data
            verification.refresh_from_db()
        
        growth_data = SubscriberGrowth.objects.filter(user=request.user)
        
        # Get campaign filter parameter for tabs (recent, top, swap)
        campaign_tab = request.GET.get('campaign_tab', 'recent')
        
        # Base query - all campaigns for user
        campaigns_qs = CampaignAnalytic.objects.filter(user=request.user)
        
        # Apply filtering based on tab
        if campaign_tab == 'top':
            # Top performing: highest open rate + click rate
            campaigns = campaigns_qs.order_by('-open_rate', '-click_rate')[:10]
        elif campaign_tab == 'swap':
            # Swap campaigns: filter by name containing swap-related keywords
            campaigns = campaigns_qs.filter(
                name__icontains='swap'
            ).order_by('-date')[:10]
        else:
            # Recent (default): most recent by date
            campaigns = campaigns_qs.order_by('-date')[:10]
        
        # DEBUG: Log campaign count
        print(f"[DEBUG] Campaigns query for user {request.user.username} (ID: {request.user.id}): {campaigns.count()} campaigns")
        for c in campaigns:
            print(f"[DEBUG]   - {c.name} (ID: {c.id}, User: {c.user_id})")
        
        # 1. Historical Trends aggregation & Metrics Calculation
        
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        now = timezone.now()
        current_year = now.year
        
        growth_records = {g.month: g.count for g in growth_data if g.year == current_year}
        # Use all campaigns for stats, not just current year
        monthly_stats = campaigns.annotate(
            m=ExtractMonth('date')
        ).values('m').annotate(
            avg_open=Avg('open_rate'),
            avg_click=Avg('click_rate')
        )
        stats_map = {item['m']: item for item in monthly_stats}
        
        historical_trends = []
        for i, m_name in enumerate(month_names, 1):
            s = stats_map.get(i, {})
            historical_trends.append({
                "month": m_name,
                "open_rate": round(s.get('avg_open', 0.0), 1),
                "click_rate": round(s.get('avg_click', 0.0), 1),
                "subscriber_growth": growth_records.get(m_name, 0)
            })

        # 2. Calculate Stats Deltas
        # Subscriber Delta (vs previous month)
        sub_delta = 0
        prev_month_idx = now.month - 2
        if prev_month_idx >= 0:
            prev_month_name = month_names[prev_month_idx]
            prev_sub_count = growth_records.get(prev_month_name)
            if prev_sub_count is not None:
                sub_delta = verification.active_subscribers - prev_sub_count
        sub_delta_str = f"+{sub_delta}" if sub_delta >= 0 else str(sub_delta)

        # Open Rate Delta
        curr_month_open = stats_map.get(now.month, {}).get('avg_open', verification.avg_open_rate)
        prev_month_open = stats_map.get(now.month - 1, {}).get('avg_open', verification.avg_open_rate)
        open_delta = curr_month_open - prev_month_open
        open_delta_str = f"+{open_delta:.1f}%" if open_delta >= 0 else f"{open_delta:.1f}%"

        # Click Rate Delta
        curr_month_click = stats_map.get(now.month, {}).get('avg_click', verification.avg_click_rate)
        prev_month_click = stats_map.get(now.month - 1, {}).get('avg_click', verification.avg_click_rate)
        click_delta = curr_month_click - prev_month_click
        click_delta_str = f"+{click_delta:.1f}%" if click_delta >= 0 else f"{click_delta:.1f}%"

        # 3. Dynamic Sync Time
        last_synced = "Never"
        if verification.last_verified_at:
            ist = pytz.timezone('Asia/Kolkata')
            local_dt = verification.last_verified_at.astimezone(ist)
            if local_dt.date() == now.astimezone(ist).date():
                last_synced = local_dt.strftime("%I:%M %p Today")
            else:
                last_synced = local_dt.strftime("%b %d, %Y")

        # 4. Link-level analysis from User Slots & Swaps
        link_level_ctr = []
        slots = NewsletterSlot.objects.filter(user=request.user).prefetch_related(
            'swap_requests__requester__profiles', 
            'swap_requests__book',
            'swap_requests__link_clicks'
        ).order_by('-send_date')

        # Apply campaign_name filter if provided
        campaign_filter = request.GET.get('campaign_name', None)
        if campaign_filter:
            # Filter slots based on campaign name pattern
            # Campaign name format: "Newsletter: {genre} ({date})" or "Swap: {genre} ({date})"
            if 'Newsletter:' in campaign_filter:
                genre_part = campaign_filter.replace('Newsletter:', '').strip()
                # Extract genre from "Children's Books (Mar 17, 2026)" format
                if '(' in genre_part:
                    genre = genre_part.split('(')[0].strip()
                    slots = slots.filter(preferred_genre__icontains=genre)
            elif 'Swap:' in campaign_filter:
                genre_part = campaign_filter.replace('Swap:', '').strip()
                if '(' in genre_part:
                    genre = genre_part.split('(')[0].strip()
                    slots = slots.filter(preferred_genre__icontains=genre)

        # Apply pagination - show only 5 campaigns
        page = int(request.GET.get('link_page', 1))
        page_size = 5
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_slots = slots[start_idx:end_idx]

        for slot in paginated_slots:
            links = []
            has_swaps = False
            for swap in slot.swap_requests.filter(status__in=['completed', 'verified', 'confirmed', 'sending', 'scheduled']):
                has_swaps = True
                for lc in swap.link_clicks.all():
                    links.append({
                        "id": lc.id,
                        "name": lc.link_name,
                        "url": lc.destination_url,
                        "clicks": lc.clicks,
                        "ctr": f"{lc.ctr}%",
                        "ctr_label": lc.ctr_label,
                        "conversion": lc.conversions or "0 sales"
                    })
                if not swap.link_clicks.exists() and swap.book:
                    partner_name = swap.requester.username
                    if swap.requester.profiles.first():
                        partner_name = swap.requester.profiles.first().name
                    
                    # Get book URL and add tracking parameter
                    book_url = getattr(swap.book, 'amazon_url', '#') or "#"
                    if '?' in book_url and book_url != '#':
                        tracked_url = f"{book_url}&swap_track={swap.id}"
                    else:
                        tracked_url = f"{book_url}?swap_track={swap.id}" if book_url != '#' else '#'
                    
                    links.append({
                        "id": f"swap_{swap.id}",
                        "name": f"Swap Promo - {swap.book.title} ({partner_name})",
                        "url": tracked_url,
                        "destination_url": book_url,
                        "clicks": 0,
                        "ctr": "0.0%",
                        "ctr_label": "Pending Data",
                        "conversion": "-"
                    })
            if not links:
                links.append({
                    "id": f"slot_{slot.id}",
                    "name": f"Primary Newsletter Link",
                    "url": "#",
                    "clicks": 0,
                    "ctr": "0.0%",
                    "ctr_label": "Pending",
                    "conversion": "-"
                })
            campaign_type = "Swap" if has_swaps else "Newsletter"
            date_str = slot.send_date.strftime("%b %-d, %Y") if slot.send_date else "TBD"
            campaign_name = f"{campaign_type}: {slot.get_preferred_genre_display()} ({date_str})"
            link_level_ctr.append({"campaign_id": slot.id, "campaign_name": campaign_name, "links": links})

        # Calculate pagination info
        total_campaigns = slots.count()
        total_pages = (total_campaigns + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        return Response({
            "connection_status": {
                "connected": verification.is_connected_mailerlite,
                "provider": "MailerLite",
                "verified": verification.is_connected_mailerlite,
                "last_synced": last_synced
            },
            "summary_stats": {
                "active_subscribers": {
                    "value": verification.audience_size,
                    "active": verification.active_subscribers,
                    "delta": sub_delta_str,
                    "delta_text": "this month",
                    "is_positive": sub_delta >= 0
                },
                "avg_open_rate": {
                    "value": f"{verification.avg_open_rate}%",
                    "delta": open_delta_str,
                    "delta_text": "vs last month",
                    "is_positive": open_delta >= 0
                },
                "avg_click_rate": {
                    "value": f"{verification.avg_click_rate}%",
                    "delta": click_delta_str,
                    "delta_text": "vs last month",
                    "is_positive": click_delta >= 0
                },
                "list_health_score": {
                    "value": f"{verification.list_health_score}/100",
                    "delta": "+0",
                    "delta_text": "points improvement",
                    "is_positive": True
                },
            },
            "growth_chart": SubscriberGrowthSerializer(growth_data, many=True).data,
            "subscriber_status_breakdown": {
                "active": verification.active_subscribers,
                "unsubscribed": verification.unsubscribed_subscribers,
                "unconfirmed": verification.unconfirmed_subscribers,
                "bounced": verification.bounced_subscribers,
                "junk": verification.junk_subscribers,
                "total": verification.audience_size,
                "dashboard_comparison_note": "Dashboard total may include 'unconfirmed' subscribers. API 'active' count only includes confirmed subscribers."
            },
            "list_health_metrics": {
                "bounce_rate": f"{verification.bounce_rate}%",
                "unsubscribe_rate": f"{verification.unsubscribe_rate}%",
                "active_rate": f"{verification.active_rate}%",
                "avg_engagement": verification.avg_engagement,
            },
            "campaign_analytics": CampaignAnalyticSerializer(campaigns, many=True).data,
            "link_level_ctr": {
                "results": link_level_ctr,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_campaigns": total_campaigns,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "page_size": page_size,
                    "filters": {
                        "campaign_name": campaign_filter
                    } if campaign_filter else None
                }
            },
            "historical_trends": historical_trends
        })


class CampaignDatesView(APIView):
    """
    GET /api/campaign-dates/
    Returns list of campaign dates for dropdown filter
    Format: "Science Fiction (Apr 1, 2026)" instead of full "Newsletter: Science Fiction (Apr 1, 2026)"
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.models import NewsletterSlot
        
        # Get all slots for the user
        slots = NewsletterSlot.objects.filter(user=request.user).order_by('-send_date')
        
        campaign_dates = []
        for slot in slots:
            # Determine campaign type
            has_swaps = slot.swap_requests.filter(status__in=['completed', 'verified', 'confirmed', 'sending', 'scheduled']).exists()
            campaign_type = "Swap" if has_swaps else "Newsletter"
            
            # Format date
            date_str = slot.send_date.strftime("%b %-d, %Y") if slot.send_date else "TBD"
            
            # Create campaign name
            campaign_name = f"{campaign_type}: {slot.get_preferred_genre_display()} ({date_str})"
            
            # Create display name (without "Newsletter:" or "Swap:" prefix)
            display_name = f"{slot.get_preferred_genre_display()} ({date_str})"
            
            campaign_dates.append({
                "value": campaign_name,  # Full name for filtering
                "label": display_name,   # Short name for display
                "campaign_id": slot.id,
                "date": date_str,
                "genre": slot.get_preferred_genre_display(),
                "type": campaign_type
            })
        
        return Response({
            "campaign_dates": campaign_dates,
            "total": len(campaign_dates)
        })


class CampaignAnalyticCreateView(APIView):
    """
    POST /api/campaign-analytics/create/
    Creates a new CampaignAnalytic entry for the authenticated user.
    Body: {
        "name": "Campaign Name",
        "date": "2026-03-19",
        "subscribers": 7251,
        "open_rate": 42.5,
        "click_rate": 8.7,
        "type": "Recent"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from core.models import CampaignAnalytic
        
        # Get data from request
        name = request.data.get('name')
        date_str = request.data.get('date')
        subscribers = request.data.get('subscribers', 0)
        open_rate = request.data.get('open_rate', 0.0)
        click_rate = request.data.get('click_rate', 0.0)
        campaign_type = request.data.get('type', 'Recent')
        
        # Validate required fields
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not date_str:
            return Response({"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse date
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "date must be in YYYY-MM-DD format"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create campaign analytic
        campaign = CampaignAnalytic.objects.create(
            user=request.user,
            name=name,
            date=date_obj,
            subscribers=int(subscribers),
            open_rate=float(open_rate),
            click_rate=float(click_rate),
            type=campaign_type
        )
        
        return Response({
            "message": "Campaign analytic created successfully",
            "campaign": {
                "id": campaign.id,
                "name": campaign.name,
                "date": campaign.date.isoformat(),
                "subscribers": campaign.subscribers,
                "open_rate": campaign.open_rate,
                "click_rate": campaign.click_rate,
                "type": campaign.type
            }
        }, status=status.HTTP_201_CREATED)


# =====================================================================
# AUTHOR DASHBOARD (Figma: "Author Dashboard" — main landing page)
# =====================================================================

class AuthorDashboardView(APIView):
    """
    GET /api/dashboard/
    Returns all data needed for the Author Dashboard page:
    - Stats cards (Books, Newsletter Slots, Completed Swaps, Reliability)
    - Calendar (monthly view with slot/swap indicators)
    - Recent Activity (notifications + swap events)
    - Campaign Analytics (open rate, click rate, performance comparison)
    Supports query params: ?month=2&year=2026&genre=romance
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = datetime.now()
        month = int(request.query_params.get('month', now.month))
        year = int(request.query_params.get('year', now.year))
        genre_filter = request.query_params.get('genre', None)

        # ─── 1. STATS CARDS ──────────────────────────────────────────
        total_books = Book.objects.filter(user=user).count()
        total_slots = NewsletterSlot.objects.filter(user=user).count()

        completed_swaps = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user),
            status__in=['completed', 'verified', 'confirmed', 'scheduled']
        ).count()

        profile = user.profiles.first()
        reliability_score = 0
        if profile:
            reliability_score = int(profile.send_reliability_percent) if profile.send_reliability_percent else 0

        stats_cards = {
            "book": total_books,
            "newsletter_slots": total_slots,
            "completed_swaps": completed_swaps,
            "reliability": reliability_score,
        }

        # ─── 2. CALENDAR ─────────────────────────────────────────────
        num_days = calendar.monthrange(year, month)[1]

        slots_qs = NewsletterSlot.objects.filter(
            user=user,
            send_date__year=year,
            send_date__month=month
        )
        if genre_filter:
            slots_qs = slots_qs.filter(preferred_genre=genre_filter)

        slots_in_month = slots_qs.values('send_date').annotate(
            total_slots=Count('id'),
            pending_swaps=Count('swap_requests', filter=Q(swap_requests__status='pending')),
            confirmed_swaps=Count('swap_requests', filter=Q(swap_requests__status__in=['confirmed', 'verified', 'completed', 'scheduled'])),
            scheduled_swaps=Count('swap_requests', filter=Q(swap_requests__status='scheduled')),
        )

        date_map = {s['send_date']: s for s in slots_in_month}

        calendar_days = []
        today = date.today()
        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            day_stats = date_map.get(current_date, {})

            calendar_days.append({
                "date": current_date.isoformat(),
                "day": day,
                "is_today": current_date == today,
                "has_slots": day_stats.get('total_slots', 0) > 0,
                "has_pending": day_stats.get('pending_swaps', 0) > 0,
                "has_confirmed": day_stats.get('confirmed_swaps', 0) > 0,
                "has_scheduled": day_stats.get('scheduled_swaps', 0) > 0,
                "slot_count": day_stats.get('total_slots', 0),
            })

        calendar_data = {
            "month_name": calendar.month_name[month],
            "year": year,
            "month": month,
            "days": calendar_days,
        }

        # ─── 3. RECENT ACTIVITY ──────────────────────────────────────
        # Combine notifications and swap events into a unified feed
        recent_activities = []

        # Fetch recent notifications
        from django.utils import timezone
        now_aware = timezone.now()
        
        notifications = Notification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:10]

        for notif in notifications:
            time_diff = now_aware - notif.created_at
            days = time_diff.days
            seconds = time_diff.seconds
            
            if days == 0:
                if seconds < 3600:
                    mins = max(1, seconds // 60)
                    time_ago = f"{mins} min{'s' if mins != 1 else ''} ago"
                else:
                    hours = seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif days == 1:
                time_ago = "1 day ago"
            else:
                time_ago = f"{days} days ago"

            recent_activities.append({
                "id": notif.id,
                "type": "notification",
                "title": notif.title,
                "message": notif.message,
                "badge": notif.badge,
                "time_ago": time_ago,
                "action_url": notif.action_url,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
            })

        # If not enough notifications, also pull recent swap events
        if len(recent_activities) < 6:
            recent_swaps = SwapRequest.objects.filter(
                Q(slot__user=user) | Q(requester=user)
            ).select_related('requester', 'slot', 'book').order_by('-created_at')[:6]

            for swap in recent_swaps:
                partner = swap.slot.user if swap.requester == user else swap.requester
                partner_profile = partner.profiles.first()
                partner_name = partner_profile.name if partner_profile else partner.username

                status_messages = {
                    'pending': f"Swap request pending with {partner_name}",
                    'confirmed': f"Completed swap with {partner_name}",
                    'sending': f"Sending swap with {partner_name}",
                    'scheduled': f"Scheduled swap with {partner_name}",
                    'completed': f"Completed swap with {partner_name}",
                    'verified': f"Verified swap with {partner_name}",
                    'rejected': f"Swap request declined by {partner_name}",
                }

                time_diff = now_aware - swap.created_at
                days = time_diff.days
                seconds = time_diff.seconds
                
                if days == 0:
                    if seconds < 3600:
                        mins = max(1, seconds // 60)
                        time_ago = f"{mins} min{'s' if mins != 1 else ''} ago"
                    else:
                        hours = seconds // 3600
                        time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
                elif days == 1:
                    time_ago = "1 day ago"
                else:
                    time_ago = f"{days} days ago"

                recent_activities.append({
                    "id": f"swap_{swap.id}",
                    "type": "swap_event",
                    "title": status_messages.get(swap.status, f"Swap update with {partner_name}"),
                    "message": swap.message or "",
                    "badge": "SWAP",
                    "time_ago": time_ago,
                    "action_url": f"/dashboard/swaps/track/{swap.id}/",
                    "is_read": True,
                    "created_at": swap.created_at.isoformat(),
                })

        # Sort by created_at descending and limit to 6
        recent_activities.sort(key=lambda x: x['created_at'], reverse=True)
        recent_activities = recent_activities[:6]

        # ─── 4. CAMPAIGN ANALYTICS ───────────────────────────────────
        campaigns = CampaignAnalytic.objects.filter(user=user).order_by('-date')

        # Calculate averages for the analytics cards
        total_campaigns = campaigns.count()
        if total_campaigns > 0:
            from django.db.models import Avg
            avg_stats = campaigns.aggregate(
                avg_open_rate=Avg('open_rate'),
                avg_click_rate=Avg('click_rate'),
            )
            avg_open_rate = round(avg_stats['avg_open_rate'] or 0, 1)
            avg_click_rate = round(avg_stats['avg_click_rate'] or 0, 1)
        else:
            avg_open_rate = 0.0
            avg_click_rate = 0.0

        # Previous period comparison (last 30 days vs 30 days before that)
        thirty_days_ago = today - timedelta(days=30)
        sixty_days_ago = today - timedelta(days=60)

        current_period = campaigns.filter(date__gte=thirty_days_ago)
        previous_period = campaigns.filter(date__gte=sixty_days_ago, date__lt=thirty_days_ago)

        current_avg_open = 0.0
        current_avg_click = 0.0
        if current_period.exists():
            from django.db.models import Avg
            current_stats = current_period.aggregate(
                avg_open=Avg('open_rate'),
                avg_click=Avg('click_rate'),
            )
            current_avg_open = round(current_stats['avg_open'] or 0, 1)
            current_avg_click = round(current_stats['avg_click'] or 0, 1)

        prev_avg_open = 0.0
        prev_avg_click = 0.0
        if previous_period.exists():
            prev_stats = previous_period.aggregate(
                avg_open=Avg('open_rate'),
                avg_click=Avg('click_rate'),
            )
            prev_avg_open = round(prev_stats['avg_open'] or 0, 1)
            prev_avg_click = round(prev_stats['avg_click'] or 0, 1)

        open_rate_change = round(current_avg_open - prev_avg_open, 1)
        click_rate_change = round(current_avg_click - prev_avg_click, 1)

        campaign_analytics = {
            "avg_open_rate": avg_open_rate,
            "avg_click_rate": avg_click_rate,
            "current_period": {
                "open_rate": current_avg_open,
                "click_rate": current_avg_click,
            },
            "previous_period": {
                "open_rate": prev_avg_open,
                "click_rate": prev_avg_click,
            },
            "open_rate_change": open_rate_change,
            "click_rate_change": click_rate_change,
            "improvement_label": f"+{open_rate_change}% improvement" if open_rate_change > 0 else f"{open_rate_change}% change",
            "recent_campaigns": CampaignAnalyticSerializer(campaigns[:5], many=True).data,
        }

        # ─── 5. QUICK ACTIONS ────────────────────────────────────────
        quick_actions = [
            {"label": "Add New Book", "url": "/dashboard/books/add/", "icon": "book"},
            {"label": "Add Newsletter Slot", "url": "/dashboard/newsletter-slot/add/", "icon": "calendar"},
        ]

        # ─── 6. USER INFO (Welcome Banner) ───────────────────────────
        user_profile = None
        try:
            user_profile = user.profile  # from authentication.UserProfile
        except Exception:
            pass

        pen_name = None
        if profile and profile.name:
            pen_name = profile.name
        elif user_profile and user_profile.pen_name:
            pen_name = user_profile.pen_name
        else:
            pen_name = user.username
            
        profile_photo = None
        if profile and profile.profile_picture:
            profile_photo = request.build_absolute_uri(profile.profile_picture.url)
        elif user_profile and user_profile.profile_photo:
            profile_photo = request.build_absolute_uri(user_profile.profile_photo.url)

        welcome = {
            "name": pen_name,
            "profile_photo": profile_photo,
            "greeting": f"Welcome back, {pen_name}!",
            "subtitle": "Here's what's happening with your swaps and books",
        }

        return Response({
            "welcome": welcome,
            "stats_cards": stats_cards,
            "calendar": calendar_data,
            "recent_activity": recent_activities,
            "campaign_analytics": campaign_analytics,
            "quick_actions": quick_actions,
        })


class AllSwapRequestsView(ListAPIView):
    """
    GET /api/all-swap-requests/
    Returns all swap requests in the platform.
    Can be filtered by status using ?status=pending,etc.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = SwapRequest.objects.all().order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)
        return qs

    def list(self, request, *args, **kwargs):
        # We can reuse the SwapManagementSerializer or create a specialized one.
        # But since the user wants just "all swap requests", we'll just serialize it directly.
        from core.serializers import SwapManagementSerializer
        queryset = self.get_queryset()
        
        # simple pagination could be used here but returning all if small
        # For a full platform we should use pagination.
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SwapManagementSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = SwapManagementSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


# =====================================================================
# EMAIL / COMMUNICATION TOOLS
# =====================================================================
from core.models import Email
from core.serializers import EmailListSerializer, EmailDetailSerializer, ComposeEmailSerializer


class EmailListView(APIView):
    """
    GET /api/emails/?folder=inbox&search=query
    Returns emails for the current user grouped by folder.
    Also returns folder counts for badge numbers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        folder = request.query_params.get('folder', 'inbox').lower()
        search = request.query_params.get('search', '').strip()

        # Build base queryset based on folder
        if folder == 'sent':
            qs = Email.objects.filter(sender=user, folder='sent', is_draft=False)
        elif folder == 'drafts':
            qs = Email.objects.filter(sender=user, is_draft=True)
        else:
            qs = Email.objects.filter(recipient=user, folder=folder)

        # Search filter
        if search:
            qs = qs.filter(
                Q(subject__icontains=search) |
                Q(body__icontains=search) |
                Q(sender__profiles__name__icontains=search) |
                Q(sender__username__icontains=search) |
                Q(recipient__profiles__name__icontains=search) |
                Q(recipient__username__icontains=search)
            ).distinct()

        qs = qs.select_related('sender', 'recipient').order_by('-created_at')

        serializer = EmailListSerializer(qs, many=True, context={'request': request})

        # Folder counts
        inbox_count = Email.objects.filter(recipient=user, folder='inbox', is_read=False).count()
        snoozed_count = Email.objects.filter(recipient=user, folder='snoozed').count()
        sent_count = Email.objects.filter(sender=user, folder='sent', is_draft=False).count()
        drafts_count = Email.objects.filter(sender=user, is_draft=True).count()
        spam_count = Email.objects.filter(recipient=user, folder='spam').count()
        trash_count = Email.objects.filter(recipient=user, folder='trash').count()

        return Response({
            'folder': folder,
            'folder_counts': {
                'inbox': inbox_count,
                'snoozed': snoozed_count,
                'sent': sent_count,
                'drafts': drafts_count,
                'spam': spam_count,
                'trash': trash_count,
            },
            'results': serializer.data,
        })


class ComposeEmailView(APIView):
    """
    POST /api/emails/compose/
    Compose and send an email (or save as draft).
    Also sends a real email via SMTP if not a draft.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ComposeEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        User = request.user.__class__

        # Resolve recipient
        recipient = None
        if data.get('recipient_id'):
            try:
                recipient = User.objects.get(id=data['recipient_id'])
            except User.DoesNotExist:
                return Response({"detail": "Recipient not found."}, status=status.HTTP_404_NOT_FOUND)
        elif data.get('recipient_username'):
            try:
                recipient = User.objects.get(username=data['recipient_username'])
            except User.DoesNotExist:
                return Response({"detail": f"User '{data['recipient_username']}' not found."}, status=status.HTTP_404_NOT_FOUND)

        is_draft = data.get('is_draft', False)
        parent_email = None
        if data.get('parent_email_id'):
            parent_email = Email.objects.filter(id=data['parent_email_id']).first()

        from django.utils import timezone

        email_obj = Email.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=data['subject'],
            body=data['body'],
            is_draft=is_draft,
            folder='drafts' if is_draft else 'sent',
            parent_email=parent_email,
            sent_at=None if is_draft else timezone.now(),
        )

        # Handle file attachment
        if request.FILES.get('attachment'):
            email_obj.attachment = request.FILES['attachment']
            email_obj.save()

        # If not draft, also create an inbox copy for the recipient
        if not is_draft:
            Email.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=data['subject'],
                body=data['body'],
                folder='inbox',
                is_draft=False,
                parent_email=parent_email,
                sent_at=email_obj.sent_at,
                attachment=email_obj.attachment,
            )

            email_sent = False
            # Send real email via SMTP
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                import logging
                logger = logging.getLogger(__name__)

                sender_profile = request.user.profiles.first()
                sender_name = sender_profile.name if sender_profile else request.user.username

                logger.info(f"Attempting to send email from {settings.DEFAULT_FROM_EMAIL} to {recipient.email}")
                logger.info(f"Using EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not Set')} as user {getattr(settings, 'EMAIL_HOST_USER', 'Not Set')}")

                send_mail(
                    subject=data['subject'],
                    message=data['body'],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                    html_message=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: #2D6A4F; padding: 20px; color: white; border-radius: 8px 8px 0 0;">
                            <h2 style="margin: 0;">AuthorSwap Message</h2>
                        </div>
                        <div style="padding: 20px; background: #f9f9f9; border: 1px solid #e0e0e0;">
                            <p style="color: #666; margin-bottom: 5px;">From: <strong>{sender_name}</strong></p>
                            <h3 style="margin-top: 0;">{data['subject']}</h3>
                            <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #eee;">
                                {data['body']}
                            </div>
                            <p style="color: #999; font-size: 12px; margin-top: 20px;">
                                This message was sent through AuthorSwap Communication Tools.
                                Log in to your dashboard to reply.
                            </p>
                        </div>
                    </div>
                    """,
                )
                logger.info(f"Successfully sent email to {recipient.email}")
                email_sent = True
            except Exception as e:
                import traceback
                logger.error(f"Failed to send email to {recipient.email}: {str(e)}\n{traceback.format_exc()}")
                print(f"FAILED TO SEND EMAIL: {e}")
                pass  # Email sending is non-critical, we handle the alert in response

            # Create a notification for the recipient
            try:
                sender_profile = request.user.profiles.first()
                sender_name = sender_profile.name if sender_profile else request.user.username
                # Use only the first word/name for cleaner notifications
                sender_first_name = sender_name.split()[0] if sender_name else request.user.username
                Notification.objects.create(
                    recipient=recipient,
                    title=f"New Email from {sender_first_name}",
                    message=f"{sender_first_name} sent you a message: \"{data['subject']}\"",
                    badge='NEW',
                    action_url=f'/communication-tools/email/{email_obj.id}/',
                )
            except Exception:
                pass

        result = EmailDetailSerializer(email_obj, context={'request': request}).data
        
        if is_draft:
            result['detail'] = "Draft saved successfully."
        else:
            if email_sent:
                result['detail'] = "Email sent successfully."
            else:
                result['detail'] = "Message saved, but failed to deliver the external email notification due to server configuration."
                
        return Response(result, status=status.HTTP_201_CREATED)


class EmailDetailView(APIView):
    """
    GET    /api/emails/<id>/     — Read a single email (marks as read)
    PATCH  /api/emails/<id>/     — Update (star, move folder, mark read/unread)
    DELETE /api/emails/<id>/     — Move to trash or permanently delete
    """
    permission_classes = [IsAuthenticated]

    def get_email(self, pk, user):
        try:
            return Email.objects.get(
                Q(pk=pk),
                Q(sender=user) | Q(recipient=user)
            )
        except Email.DoesNotExist:
            return None

    def get(self, request, pk):
        email = self.get_email(pk, request.user)
        if not email:
            return Response({"detail": "Email not found."}, status=status.HTTP_404_NOT_FOUND)

        # Mark as read if recipient is viewing
        if email.recipient_id == request.user.id and not email.is_read:
            email.is_read = True
            email.save(update_fields=['is_read'])

        serializer = EmailDetailSerializer(email, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        email = self.get_email(pk, request.user)
        if not email:
            return Response({"detail": "Email not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update allowed fields
        if 'is_starred' in request.data:
            email.is_starred = request.data['is_starred']
        if 'is_read' in request.data:
            email.is_read = request.data['is_read']
        if 'folder' in request.data:
            email.folder = request.data['folder']
        if 'snoozed_until' in request.data:
            email.snoozed_until = request.data.get('snoozed_until')
            if email.snoozed_until:
                email.folder = 'snoozed'

        email.save()
        serializer = EmailDetailSerializer(email, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, pk):
        email = self.get_email(pk, request.user)
        if not email:
            return Response({"detail": "Email not found."}, status=status.HTTP_404_NOT_FOUND)

        if email.folder == 'trash':
            # Already in trash → permanently delete
            email.delete()
            return Response({"detail": "Email permanently deleted."}, status=status.HTTP_204_NO_CONTENT)
        else:
            # Move to trash
            email.folder = 'trash'
            email.save(update_fields=['folder'])
            return Response({"detail": "Email moved to trash."})


class EmailActionView(APIView):
    """
    POST /api/emails/action/
    Bulk actions: move to folder, mark as read/unread, star/unstar, delete.
    Body: { "email_ids": [1,2,3], "action": "move_to_trash" | "mark_read" | "mark_unread" | "star" | "unstar" | "move_to_inbox" | "move_to_spam" | "delete" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        email_ids = request.data.get('email_ids', [])
        action = request.data.get('action', '')

        if not email_ids or not action:
            return Response({"detail": "email_ids and action are required."}, status=status.HTTP_400_BAD_REQUEST)

        emails = Email.objects.filter(
            Q(id__in=email_ids),
            Q(sender=request.user) | Q(recipient=request.user)
        )

        if action == 'mark_read':
            emails.update(is_read=True)
        elif action == 'mark_unread':
            emails.update(is_read=False)
        elif action == 'star':
            emails.update(is_starred=True)
        elif action == 'unstar':
            emails.update(is_starred=False)
        elif action == 'move_to_trash':
            emails.update(folder='trash')
        elif action == 'move_to_inbox':
            emails.update(folder='inbox')
        elif action == 'move_to_spam':
            emails.update(folder='spam')
        elif action == 'delete':
            count = emails.count()
            emails.delete()
            return Response({"detail": f"{count} email(s) permanently deleted."})
        else:
            return Response({"detail": f"Unknown action: '{action}'."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": f"Action '{action}' applied to {emails.count()} email(s)."})


# =====================================================================
# CHAT / MESSAGING SYSTEM
# =====================================================================
from core.models import ChatMessage
from core.serializers import ChatMessageSerializer, ConversationListSerializer


class ChatAuthorListView(APIView):
    """
    GET /api/chat/authors/
    Returns list of authors from slots/explore that the current user can chat with.
    Each author includes their profile info.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search', '').strip()

        # Get unique user IDs from all newsletter slots (same as slots/explore)
        slot_user_ids = NewsletterSlot.objects.values_list('user_id', flat=True).distinct()

        # Exclude current user
        profiles = Profile.objects.filter(
            user_id__in=slot_user_ids
        ).exclude(user=request.user).select_related('user')

        if search:
            profiles = profiles.filter(
                Q(name__icontains=search) |
                Q(user__username__icontains=search)
            )

        # For each author, include unread message count
        result = []
        for profile in profiles:
            unread = ChatMessage.objects.filter(
                sender=profile.user, recipient=request.user, is_read=False
            ).count()

            # Get last message (if any)
            last_msg = ChatMessage.objects.filter(
                Q(sender=profile.user, recipient=request.user) |
                Q(sender=request.user, recipient=profile.user)
            ).order_by('-created_at').first()

            profile_pic = None
            if profile.profile_picture:
                if hasattr(request, 'build_absolute_uri'):
                    profile_pic = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    profile_pic = profile.profile_picture.url

            result.append({
                'user_id': profile.user.id,
                'username': profile.user.username,
                'name': profile.name,
                'profile_picture': profile_pic,
                'location': profile.location,
                'unread_count': unread,
                'last_message': last_msg.content[:60] if last_msg else None,
                'last_message_time': last_msg.created_at if last_msg else None,
            })

        # Sort by last_message_time (most recent first), then by name
        result.sort(key=lambda x: x.get('last_message_time') or datetime.min, reverse=True)

        return Response(result)


class ConversationListView(APIView):
    """
    GET /api/chat/conversations/?search=query
    Returns list of all swap partners the current user can communicate with.
    Includes both users with existing chats and all swap partners.
    Each has: last message, unread count, profile info, and swap status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        search = request.query_params.get('search', '').strip()

        # 1. Find all swap partners (users from swap requests)
        swap_requests = SwapRequest.objects.filter(
            (Q(requester=user) | Q(slot__user=user))
        ).exclude(status='rejected')
        
        swap_partner_ids = set()
        for sr in swap_requests:
            if sr.requester == user:
                swap_partner_ids.add(sr.slot.user_id)
            else:
                swap_partner_ids.add(sr.requester_id)

        # 2. Find all users the current user has chatted with
        sent_to_ids = ChatMessage.objects.filter(sender=user).values_list('recipient_id', flat=True).distinct()
        received_from_ids = ChatMessage.objects.filter(recipient=user).values_list('sender_id', flat=True).distinct()
        chat_partner_ids = set(sent_to_ids) | set(received_from_ids)

        # 3. Combine both sets (all swap partners + all chat partners)
        all_partner_ids = swap_partner_ids | chat_partner_ids

        if not all_partner_ids:
            return Response([])

        profiles = Profile.objects.filter(user_id__in=all_partner_ids).select_related('user')

        if search:
            profiles = profiles.filter(
                Q(name__icontains=search) |
                Q(user__username__icontains=search)
            )

        from django.utils import timezone
        from core.serializers import ConversationListSerializer

        conversations = []
        for profile in profiles:
            partner = profile.user

            # Last message between the two users
            last_msg = ChatMessage.objects.filter(
                Q(sender=user, recipient=partner) |
                Q(sender=partner, recipient=user)
            ).order_by('-created_at').first()

            # Unread count (messages FROM this partner that I haven't read)
            unread = ChatMessage.objects.filter(
                sender=partner, recipient=user, is_read=False
            ).count()

            profile_pic = None
            if profile.profile_picture:
                profile_pic = request.build_absolute_uri(profile.profile_picture.url)

            # Format time
            formatted_time = ""
            if last_msg:
                now = timezone.now().date()
                msg_date = last_msg.created_at.date()
                if msg_date == now:
                    formatted_time = "Today"
                elif (now - msg_date).days == 1:
                    formatted_time = "Yesterday"
                else:
                    formatted_time = msg_date.strftime("%m/%d/%Y")

            # Swap status logic
            swap = SwapRequest.objects.filter(
                (Q(requester=user) & Q(slot__user=partner)) |
                (Q(requester=partner) & Q(slot__user=user))
            ).exclude(status='rejected').order_by('-created_at').first()
            
            swap_status = swap.status if swap else None

            conversations.append({
                'id': partner.id,
                'user_id': partner.id,
                'username': partner.username,
                'name': profile.name,
                'avatar': profile_pic,
                'profile_picture': profile_pic,
                'location': profile.location,
                'lastMessage': last_msg.content if last_msg else "",
                'last_message': last_msg.content[:80] if last_msg else "",
                'last_message_time': last_msg.created_at if last_msg else None,
                'time': formatted_time,
                'formatted_time': formatted_time,
                'unread_count': unread,
                'swap_status': swap_status,
            })

        # Sort: most recent conversation first, then alphabetically for new partners
        conversations.sort(key=lambda x: (x.get('last_message_time') or datetime.min, x.get('name', '')), reverse=True)

        return Response(conversations)

class ComposePartnerListView(APIView):
    """
    GET /api/chat/compose/?search=query
    Returns list of unique swap partners (authors) with their latest slot info.
    Supports search by author name, username, or genre.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        search = request.query_params.get('search', '').strip()
        
        # Get all users who have slots (exclude current user)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = User.objects.exclude(id=user.id).filter(newsletter_slots__isnull=False).distinct()
        
        # Apply search filter if provided
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(profiles__name__icontains=search) |
                Q(newsletter_slots__preferred_genre__icontains=search)
            )
        
        # Serialize unique authors with their latest slot info
        result = []
        for u in users:
            profile = u.profiles.first()
            profile_pic = None
            if profile and profile.profile_picture:
                profile_pic = request.build_absolute_uri(profile.profile_picture.url)
            
            # Get latest slot for this user
            latest_slot = NewsletterSlot.objects.filter(user=u).order_by('-created_at').first()
            
            # Count current partners across all slots
            from django.db.models import Count, Q
            current_partners = NewsletterSlot.objects.filter(user=u).aggregate(
                total_partners=Count('swap_requests', filter=Q(swap_requests__status__in=['confirmed', 'verified', 'scheduled', 'completed']))
            )['total_partners'] or 0
            
            # Check if already chatted
            has_chat = ChatMessage.objects.filter(
                Q(sender=user, recipient=u) | Q(sender=u, recipient=user)
            ).exists()
            
            # Check if swap partner
            is_swap_partner = SwapRequest.objects.filter(
                (Q(requester=user) & Q(slot__user=u)) |
                (Q(requester=u) & Q(slot__user=user))
            ).exclude(status='rejected').exists()
            
            result.append({
                'id': u.id,
                'user_id': u.id,
                'username': u.username,
                'name': profile.name if profile else u.username,
                'profile_picture': profile_pic,
                'latest_slot': {
                    'id': latest_slot.id if latest_slot else None,
                    'send_date': latest_slot.send_date if latest_slot else None,
                    'send_time': latest_slot.send_time if latest_slot else None,
                    'audience_size': latest_slot.audience_size if latest_slot else '0',
                    'visibility': latest_slot.visibility if latest_slot else 'public',
                    'status': latest_slot.status if latest_slot else 'active',
                    'promotion_type': latest_slot.promotion_type if latest_slot else 'swap',
                    'price': float(latest_slot.price) if latest_slot and latest_slot.price else 0.00,
                    'preferred_genre': latest_slot.preferred_genre if latest_slot else (profile.primary_genre if profile else None),
                    'max_partners': latest_slot.max_partners if latest_slot else 1,
                },
                'author': {
                    'id': u.id,  # User ID for chat functionality
                    'user_id': u.id,  # Explicit user_id field
                    'profile_id': profile.id if profile else None,  # Profile ID for reference
                    'name': profile.name if profile else u.username,
                    'profile_picture': profile_pic,
                    'swaps_completed': profile.swaps_completed if profile else 0,
                    'reputation_score': profile.reputation_score if profile else 5.0,
                    'rating': profile.reputation_score if profile else 5.0,
                    'primary_genre': profile.primary_genre if profile else (latest_slot.preferred_genre if latest_slot else None),
                    'send_reliability_percent': profile.send_reliability_percent if profile else 0,
                },
                'total_partners_count': current_partners,
                'available_slots': NewsletterSlot.objects.filter(user=u).count(),
                'has_chat_history': has_chat,
                'is_swap_partner': is_swap_partner,
                'eligible_to_chat': True,
            })
        
        return Response(result)

class MySwapPartnersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get all users who have created newsletters
        newsletter_users = User.objects.filter(
            newsletter_slots__isnull=False
        ).distinct()
        
        # Exclude current user
        newsletter_users = newsletter_users.exclude(id=user.id)
        
        from core.serializers import ConversationPartnerSerializer
        serializer = ConversationPartnerSerializer(newsletter_users, many=True, context={'request': request})
        return Response(serializer.data)
        search = request.query_params.get('search', '').strip()

        # Find all unique users the current user has chatted with
        sent_to_ids = ChatMessage.objects.filter(sender=user).values_list('recipient_id', flat=True).distinct()
        received_from_ids = ChatMessage.objects.filter(recipient=user).values_list('sender_id', flat=True).distinct()
        chat_partner_ids = set(sent_to_ids) | set(received_from_ids)

        if not chat_partner_ids:
            return Response([])

        profiles = Profile.objects.filter(user_id__in=chat_partner_ids).select_related('user')

        if search:
            profiles = profiles.filter(
                Q(name__icontains=search) |
                Q(user__username__icontains=search)
            )

        from django.utils import timezone

        conversations = []
        for profile in profiles:
            partner = profile.user

            # Last message between the two users
            last_msg = ChatMessage.objects.filter(
                Q(sender=user, recipient=partner) |
                Q(sender=partner, recipient=user)
            ).order_by('-created_at').first()

            # Unread count (messages FROM this partner that I haven't read)
            unread = ChatMessage.objects.filter(
                sender=partner, recipient=user, is_read=False
            ).count()

            profile_pic = None
            if profile.profile_picture:
                profile_pic = request.build_absolute_uri(profile.profile_picture.url)

            # Format time
            formatted_time = ""
            if last_msg:
                now = timezone.now().date()
                msg_date = last_msg.created_at.date()
                if msg_date == now:
                    formatted_time = "Today"
                elif (now - msg_date).days == 1:
                    formatted_time = "Yesterday"
                else:
                    formatted_time = msg_date.strftime("%m/%d/%Y")

            conversations.append({
                'user_id': partner.id,
                'username': partner.username,
                'name': profile.name,
                'profile_picture': profile_pic,
                'location': profile.location,
                'last_message': last_msg.content[:80] if last_msg else "",
                'last_message_time': last_msg.created_at if last_msg else None,
                'formatted_time': formatted_time,
                'unread_count': unread,
            })

        # Sort: most recent conversation first
        conversations.sort(key=lambda x: x.get('last_message_time') or datetime.min, reverse=True)

        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)


class ChatHistoryView(APIView):
    """
    GET /api/chat/history/<receiver_id>/
    Returns chat message history between the current user and the specified user.
    Messages grouped by date with "Yesterday", "Today" labels.
    Also marks all unread messages from the other user as read.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, receiver_id):
        user = request.user

        # Try to find user by ID first, then by profile ID
        other_user = None
        try:
            # First try as User ID
            other_user = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            try:
                # If not found, try as Profile ID
                profile = Profile.objects.get(id=receiver_id)
                other_user = profile.user
            except Profile.DoesNotExist:
                pass

        if not other_user:
            # Provide more helpful error message with available users
            available_users = list(User.objects.values_list('id', flat=True))
            user_details = []
            for uid in available_users[:5]:  # Show first 5 users for context
                try:
                    u = User.objects.get(id=uid)
                    profile = u.profiles.first()
                    user_details.append(f"{uid}: {profile.name if profile else u.username}")
                except:
                    user_details.append(f"{uid}: (error loading user)")
            
            return Response({
                "detail": f"User with ID {receiver_id} not found.",
                "available_user_ids": available_users,
                "user_details": user_details,
                "message": f"Please check the user ID. Available user IDs are: {available_users[:10]}{'...' if len(available_users) > 10 else ''}"
            }, status=status.HTTP_404_NOT_FOUND)

        # Fetch all messages between the two users
        messages = ChatMessage.objects.filter(
            Q(sender=user, recipient=other_user) |
            Q(sender=other_user, recipient=user)
        ).select_related('sender', 'recipient').order_by('created_at')

        # Mark unread messages from the other user as read
        ChatMessage.objects.filter(
            sender=other_user, recipient=user, is_read=False
        ).update(is_read=True)

        # Group messages by date
        from django.utils import timezone
        now = timezone.now().date()
        grouped = {}
        for msg in messages:
            msg_date = msg.created_at.date()
            if msg_date == now:
                label = "Today"
            elif (now - msg_date).days == 1:
                label = "Yesterday"
            else:
                label = msg_date.strftime("%B %d, %Y")

            if label not in grouped:
                grouped[label] = []
            grouped[label].append(msg)

        # Build response
        result = []
        for date_label, msgs in grouped.items():
            result.append({
                'date_label': date_label,
                'messages': ChatMessageSerializer(msgs, many=True, context={'request': request}).data,
            })

        # Other user profile info
        other_profile = other_user.profiles.first()
        other_info = {
            'id': other_user.id, # Added for frontend compatibility
            'user_id': other_user.id,
            'username': other_user.username,
            'name': other_profile.name if other_profile else other_user.username,
            'avatar': request.build_absolute_uri(other_profile.profile_picture.url) if other_profile and other_profile.profile_picture else None, # Added for frontend compatibility
            'profile_picture': request.build_absolute_uri(other_profile.profile_picture.url) if other_profile and other_profile.profile_picture else None,
            'location': other_profile.location if other_profile else None,
        }

        # Flat list for the frontend's current implementation if it doesn't support grouping
        # Wait, the frontend expects a flat list: data.map(...)
        messages_flat = ChatMessageSerializer(messages, many=True, context={'request': request}).data
        
        # If the frontend expects a flat list, we should probably return that for now
        # but the ad6737 version returns grouped. Let's provide BOTH or choose.
        # CommunicationTools.jsx: const data = await getChatHistory(activeConv); const formattedMessages = data.map(...)
        # So it expects a FLAT ARRAY.
        return Response(messages_flat)


class SendMessageView(APIView):
    """
    POST /api/chat/<user_id>/send/
    Send a message to another user.
    Body: { "content": "Hello!", "attachment": <file> (optional) }
    Also pushes the message via WebSocket channel layer for real-time delivery.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        user = request.user
        
        # Try to find user by ID first, then by profile ID
        recipient = None
        try:
            # First try as User ID
            recipient = User.objects.get(id=user_id)
        except User.DoesNotExist:
            try:
                # If not found, try as Profile ID
                profile = Profile.objects.get(id=user_id)
                recipient = profile.user
            except Profile.DoesNotExist:
                pass

        if not recipient:
            # Provide more helpful error message with available users
            available_users = list(User.objects.values_list('id', flat=True))
            user_details = []
            for uid in available_users[:5]:  # Show first 5 users for context
                try:
                    u = User.objects.get(id=uid)
                    profile = u.profiles.first()
                    user_details.append(f"{uid}: {profile.name if profile else u.username}")
                except:
                    user_details.append(f"{uid}: (error loading user)")
            
            return Response({
                "detail": f"Recipient with ID {user_id} not found.",
                "available_user_ids": available_users,
                "user_details": user_details,
                "message": f"Please check the recipient ID. Available user IDs are: {available_users[:10]}{'...' if len(available_users) > 10 else ''}"
            }, status=status.HTTP_404_NOT_FOUND)

        if recipient.id == user.id:
            return Response({"detail": "You cannot send a message to yourself."}, status=status.HTTP_400_BAD_REQUEST)
        
        content = request.data.get('content', '')
        attachment = request.FILES.get('attachment')
        
        # If no text message, use the filename as the content
        if not content and attachment:
            content = attachment.name
        elif not content and not attachment: # If neither content nor attachment, it's an invalid message
            return Response({"detail": "Message content or an attachment is required."}, status=status.HTTP_400_BAD_REQUEST)

        msg = ChatMessage.objects.create(
            sender=user,
            recipient=recipient,
            content=content,
            attachment=attachment,
            is_file=True if attachment else False
        )

        # Create persistent notification and push real-time updates
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            sender_profile = user.profiles.first()
            sender_name = sender_profile.name if sender_profile else user.username

            # Create persistent notification (Once)
            Notification.objects.create(
                recipient=recipient,
                title='New Message 💬',
                message=f'You have a new message from {sender_name}',
                badge='NEW',
                action_url=f"/communication?conv={user.id}"
            )

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{min(user.id, recipient.id)}_{max(user.id, recipient.id)}',
                    {
                        'type': 'chat_message',
                        'message': msg.content,
                        'is_file': msg.is_file,
                        'attachment': request.build_absolute_uri(msg.attachment.url) if msg.attachment else None,
                        'sender_id': user.id,
                        'sender_name': sender_name,
                        'created_at': msg.created_at.isoformat(),
                    }
                )
        except Exception as e:
            print(f"Error in chat notifications: {e}")
            pass

        return Response(ChatMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ChatMessageDetailView(APIView):
    """
    PATCH /api/chat/message/<message_id>/  — Edit your own message content.
    DELETE /api/chat/message/<message_id>/ — Delete your own message.

    Only the original sender can edit or delete a message.
    """
    permission_classes = [IsAuthenticated]

    def get_message(self, pk, user):
        try:
            return ChatMessage.objects.get(pk=pk, sender=user)
        except ChatMessage.DoesNotExist:
            return None

    def patch(self, request, message_id):
        msg = self.get_message(message_id, request.user)
        if not msg:
            return Response(
                {"detail": "Message not found or you are not the sender."},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_content = request.data.get('content', '').strip()
        if not new_content:
            return Response(
                {"detail": "Content cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg.content = new_content
        msg.is_edited = True
        msg.save(update_fields=['content', 'is_edited', 'updated_at'])

        return Response(
            ChatMessageSerializer(msg, context={'request': request}).data
        )

    def delete(self, request, message_id):
        msg = self.get_message(message_id, request.user)
        if not msg:
            return Response(
                {"detail": "Message not found or you are not the sender."},
                status=status.HTTP_404_NOT_FOUND,
            )

        msg.delete()
        return Response({"detail": "Message deleted."}, status=status.HTTP_204_NO_CONTENT)


import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

stripe.api_key = settings.STRIPE_SECRET_KEY

# ─────────────────────────────────────────────────────────────────────────────
# Stripe shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_period_end(stripe_obj):
    """
    Safely extract current_period_end from a Stripe subscription object.
    Works whether the object is a StripeObject, plain dict, or partially
    expanded (e.g. from a Checkout Session expand). Falls back to 30 days
    from today if the field is missing or None.
    """
    from datetime import date as _d, timedelta as _td
    import time as _t

    ts = None
    # Try attribute access first (StripeObject), then key access
    try:
        ts = stripe_obj.current_period_end
    except AttributeError:
        pass
    if ts is None:
        try:
            ts = stripe_obj.get('current_period_end')
        except (AttributeError, TypeError):
            pass
    if ts is None:
        try:
            ts = stripe_obj['current_period_end']
        except (KeyError, TypeError):
            pass

    if ts:
        try:
            return _d.fromtimestamp(int(ts))
        except (OSError, OverflowError, ValueError):
            pass

    # Fallback: 30 days from today
    return _d.today() + _td(days=30)


def _get_or_create_stripe_customer(user, user_sub):
    """
    Ensure the user has a valid Stripe Customer on the current Stripe account.
    Creates a new one if missing or stale (from a different account).
    Persists the customer ID back to user_sub if provided.
    Returns: stripe_customer_id (str)
    """
    # 1. Try to get existing ID from UserSubscription or UserProfile
    customer_id = user_sub.stripe_customer_id if user_sub else None
    
    if not customer_id:
        try:
            # Check authentication.models.UserProfile
            if hasattr(user, 'profile') and user.profile.stripe_customer_id:
                customer_id = user.profile.stripe_customer_id
        except Exception:
            pass

    # 2. If an ID exists, verify it's still valid in Stripe
    if customer_id:
        try:
            stripe.Customer.retrieve(customer_id)
            # Valid case - Sync it across both models for consistency
            if user_sub and not user_sub.stripe_customer_id:
                user_sub.stripe_customer_id = customer_id
                user_sub.save(update_fields=['stripe_customer_id'])
            
            try:
                if hasattr(user, 'profile') and not user.profile.stripe_customer_id:
                    user.profile.stripe_customer_id = customer_id
                    user.profile.save(update_fields=['stripe_customer_id'])
            except Exception:
                pass
                
            return customer_id
        except stripe.error.InvalidRequestError:
            customer_id = None          # stale ID from a different account

    # 3. No valid customer found anywhere, create a new one
    customer = stripe.Customer.create(
        email=user.email,
        name=user.get_full_name() or user.username,
        metadata={'user_id': str(user.id)},
    )
    customer_id = customer.id

    # 4. Save the new ID in both locations
    if user_sub:
        user_sub.stripe_customer_id = customer_id
        user_sub.save(update_fields=['stripe_customer_id'])
    
    try:
        if hasattr(user, 'profile'):
            user.profile.stripe_customer_id = customer_id
            user.profile.save(update_fields=['stripe_customer_id'])
    except Exception:
        pass

    return customer_id


def _apply_unused_credit(user_sub, stripe_customer_id):
    """
    Calculate the prorated credit owed to the user from unused days on their
    current plan and post it as a Customer Balance Transaction in Stripe.
    """
    from datetime import date as _d
    import math

    def _clear_balance():
        try:
            stripe.Customer.modify(stripe_customer_id, balance=0)
        except Exception:
            pass

    if not user_sub or not user_sub.active_until or not user_sub.tier:
        _clear_balance()
        return 0

    # IMPORTANT GUARD: Only give credit if they actually have a paid Stripe subscription!
    if not user_sub.stripe_subscription_id:
        _clear_balance()
        return 0

    today = _d.today()
    active_until = user_sub.active_until

    if active_until <= today:
        _clear_balance()
        return 0           # subscription already expired — no credit

    remaining_days = (active_until - today).days
    
    # Use 30-day billing period as the base (standard monthly billing)
    tier_price_cents = int(float(user_sub.tier.price) * 100)
    daily_rate_cents = tier_price_cents / 30.0
    credit_cents = math.floor(remaining_days * daily_rate_cents)

    if credit_cents <= 0:
        _clear_balance()
        return 0

    # the amount shown and charged — so the user sees only what they actually owe.
    # Set the absolute balance (instead of adding a transaction) so it doesn't duplicate
    # if the user abandons checkout and tries again.
    try:
        stripe.Customer.modify(
            stripe_customer_id,
            balance=-credit_cents,           # negative = credit toward next charge
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not apply credit balance in Stripe: {str(e)}")
        
    return credit_cents


def _sync_user_subscription_from_stripe(user):
    """
    Proactively checks Stripe for active/trialing subscriptions and syncs DB.
    Returns the UserSubscription object if found/created, else None.
    """
    try:
        user_sub = getattr(user, 'subscription', None)
        stripe_customer_id = user_sub.stripe_customer_id if user_sub else None

        # 1. Validate stored ID or search by email
        if stripe_customer_id:
            try:
                stripe.Customer.retrieve(stripe_customer_id)
            except stripe.error.InvalidRequestError:
                stripe_customer_id = None

        if not stripe_customer_id:
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                stripe_customer_id = customers.data[0].id

        if not stripe_customer_id:
            return None

        # 2. Look for ALL active or trialing subscriptions
        subs = stripe.Subscription.list(
            customer=stripe_customer_id, 
            status='all', 
            limit=10,
            expand=['data.items.data.price']
        )
        
        candidates = []
        for s in subs.data:
            if s.status in ('active', 'trialing'):
                # Match price to Tier
                price_id = s['items']['data'][0]['price']['id']
                tier = SubscriptionTier.objects.filter(stripe_price_id=price_id).first()
                if not tier:
                    # Fallback by amount
                    p_obj = s['items']['data'][0]['price']
                    tier = SubscriptionTier.objects.filter(price=round(p_obj.unit_amount/100, 2)).first()
                
                if tier:
                    candidates.append((tier, s))

        if not candidates:
            return None

        # 3. Aggressive Logic: Pick the HIGHEST tier among active ones
        # This handles the case where user paid for an upgrade but old sub is still active.
        candidates.sort(key=lambda x: x[0].price, reverse=True)
        winner_tier, winner_sub = candidates[0]

        # 4. Clean up: Cancel any other active subscriptions to prevent double-billing
        for tier, sub in candidates[1:]:
            try:
                stripe.Subscription.delete(sub.id) # Immediate cancel
                import logging
                logging.getLogger(__name__).info(f"Sync: Cancelled duplicate lower-tier sub {sub.id} for user {user.id}")
            except Exception:
                pass

        # 5. Sync DB
        period_end = _safe_period_end(winner_sub)
        obj, _ = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                'tier': winner_tier,
                'active_until': period_end,
                'renew_date': period_end,
                'is_active': True,
                'stripe_customer_id': stripe_customer_id,
                'stripe_subscription_id': winner_sub.id,
            }
        )
        return obj

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync from Stripe Error for user {user.id}: {str(e)}")
        return None


class UpgradeSubscriptionView(APIView):
    """
    POST /api/subscription/upgrade
    Upgrades a user's subscription.
    - If user has a saved card: charges it directly (in-place subscription modify).
    - If no saved card: returns a Stripe Checkout URL to add a card first.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        user_id = request.data.get('user_id')
        tier_id = request.data.get('tier_id')

        if not tier_id:
            return Response({"error": "tier_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({"error": "Invalid subscription tier."}, status=status.HTTP_404_NOT_FOUND)
            
        new_price_id = tier.stripe_price_id
        if not new_price_id:
             return Response({"error": "The selected tier does not have a valid Stripe price."}, status=status.HTTP_400_BAD_REQUEST)

        if user_id and str(user_id) != str(request.user.id) and not request.user.is_staff:
            return Response({"error": "You do not have permission to upgrade this subscription."}, status=status.HTTP_403_FORBIDDEN)

        user_sub = getattr(request.user, 'subscription', None)
        
        if not user_sub or not user_sub.stripe_subscription_id or not user_sub.stripe_customer_id:
            return Response({"error": "No active subscription found. Please subscribe first."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cust_id = user_sub.stripe_customer_id

            # ── Step 1: Detect saved payment method ──
            # Priority: customer invoice default → subscription default → any attached card
            stripe_customer = stripe.Customer.retrieve(cust_id)
            default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')

            if not default_pm_id:
                # Check the subscription's own stored default
                stripe_sub_peek = stripe.Subscription.retrieve(user_sub.stripe_subscription_id)
                default_pm_id = stripe_sub_peek.get('default_payment_method')

            if not default_pm_id:
                # Last resort: list any card payment methods attached to the customer
                payment_methods = stripe.PaymentMethod.list(customer=cust_id, type='card')
                if payment_methods.data:
                    default_pm_id = payment_methods.data[0].id

            # ── Step 2: No saved card → redirect to Stripe Checkout ──
            if not default_pm_id:
                _apply_unused_credit(user_sub, cust_id)

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{'price': new_price_id, 'quantity': 1}],
                    mode='subscription',
                    client_reference_id=str(request.user.id),
                    customer=cust_id,
                    success_url="http://72.61.251.114/authorswap-frontend/subscription",
                    cancel_url="http://72.61.251.114/authorswap-frontend/subscription",
                )
                return Response({
                    "requires_checkout": True,
                    "url": checkout_session.url,
                    "detail": "No saved payment method found. Please add a card via the checkout link.",
                }, status=status.HTTP_200_OK)

            # ── Step 3: Saved card found → pin it, then upgrade in-place ──
            # Set the card as default on both the customer and the subscription so
            # the proration invoice generated by always_invoice is charged immediately.
            stripe.Customer.modify(cust_id, invoice_settings={'default_payment_method': default_pm_id})

            stripe_sub = stripe.Subscription.retrieve(user_sub.stripe_subscription_id)
            if not stripe_sub.get('items') or not stripe_sub['items']['data']:
                return Response({"error": "Invalid subscription state in Stripe."}, status=status.HTTP_400_BAD_REQUEST)

            subscription_item_id = stripe_sub['items']['data'][0]['id']

            try:
                updated_sub = stripe.Subscription.modify(
                    user_sub.stripe_subscription_id,
                    items=[{"id": subscription_item_id, "price": new_price_id}],
                    default_payment_method=default_pm_id,
                    proration_behavior="always_invoice",  # immediately charges the prorated difference
                )
            except stripe.error.CardError:
                # If direct charge fails, fall back to returning a checkout URL
                _apply_unused_credit(user_sub, cust_id)
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{'price': new_price_id, 'quantity': 1}],
                    mode='subscription',
                    client_reference_id=str(request.user.id),
                    customer=cust_id,
                    success_url="http://72.61.251.114/authorswap-frontend/subscription",
                    cancel_url="http://72.61.251.114/authorswap-frontend/subscription",
                )
                return Response({
                    "requires_checkout": True,
                    "url": checkout_session.url,
                    "detail": "Your saved card was declined. Please use a different card via the checkout link.",
                }, status=status.HTTP_200_OK)

            period_end = _safe_period_end(updated_sub)
            user_sub.tier = tier
            user_sub.active_until = period_end
            user_sub.renew_date = period_end
            user_sub.is_active = True
            user_sub.save(update_fields=['tier', 'active_until', 'renew_date', 'is_active'])

            return Response({
                "status": "success",
                "message": "Subscription upgraded successfully",
                "new_plan": tier.name.lower(),
                "requires_checkout": False,
            }, status=status.HTTP_200_OK)

        except stripe.error.CardError as e:
            return Response({"error": f"Payment failed: {e.user_message}"}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"UpgradeSubscription error: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateStripeCheckoutSessionView(APIView):
    """    POST /api/stripe/create-checkout-session/
    Expects {'tier_id': 1}
    Generates a Stripe Checkout Session URL for the specified subscription tier.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe API configuration is missing. Please add STRIPE_SECRET_KEY to your backend .env file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Ensure it's set for this thread/process and strip any whitespace
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        tier_id = request.data.get('tier_id')
        if not tier_id:
            return Response({"detail": "tier_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({"detail": "Invalid subscription tier."}, status=status.HTTP_404_NOT_FOUND)

        try:
            price_id = tier.stripe_price_id

            def _ensure_valid_price(t):
                """Create a new Stripe Product+Price for the tier and persist it."""
                product = stripe.Product.create(
                    name=f"Author Swap - {t.name}",
                    description=t.best_for or t.name,
                )
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(t.price * 100),
                    currency="usd",
                    recurring={"interval": "month"},
                )
                t.stripe_price_id = price.id
                t.save(update_fields=['stripe_price_id'])
                return price.id

            if not price_id:
                price_id = _ensure_valid_price(tier)
            else:
                try:
                    stripe.Price.retrieve(price_id)
                except stripe.error.InvalidRequestError:
                    price_id = _ensure_valid_price(tier)

            # ── If user already has an active subscription, use ChangePlanView logic ──
            existing_sub = getattr(request.user, 'subscription', None)
            if existing_sub and existing_sub.stripe_subscription_id and existing_sub.is_active:
                # Try to modify the existing subscription in-place.
                # If the stored subscription ID is stale (wrong account/deleted),
                # fall through silently to create a fresh Checkout Session.
                try:
                    stripe_sub = stripe.Subscription.retrieve(existing_sub.stripe_subscription_id)
                    item_id = stripe_sub['items']['data'][0]['id']

                    # 'always_invoice' immediately charges/credits the prorated difference
                    # instead of deferring it to the next billing cycle.
                    updated_sub = stripe.Subscription.modify(
                        existing_sub.stripe_subscription_id,
                        items=[{'id': item_id, 'price': price_id}],
                        proration_behavior='always_invoice',
                    )

                    # Use Stripe's real billing cycle end (not a hardcoded +30 days)
                    from datetime import date as _date
                    period_end = _safe_period_end(updated_sub)
                    existing_sub.tier = tier
                    existing_sub.active_until = period_end
                    existing_sub.renew_date = period_end
                    existing_sub.is_active = True
                    existing_sub.save(update_fields=['tier', 'active_until', 'renew_date', 'is_active'])

                    return Response({
                        "detail": f"Plan updated to {tier.label} successfully.",
                        "tier": tier.name,
                        "label": tier.label,
                        "active_until": str(period_end),
                    })

                except stripe.error.InvalidRequestError:
                    # Stale subscription ID (different Stripe account or deleted).
                    # Clear it so a fresh checkout session creates a new subscription.
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Stale stripe_subscription_id '{existing_sub.stripe_subscription_id}' "
                        f"for user {request.user.id}. Clearing and falling back to new checkout."
                    )
                    existing_sub.stripe_subscription_id = None
                    existing_sub.stripe_customer_id = None
                    existing_sub.save(update_fields=['stripe_subscription_id', 'stripe_customer_id'])

            # ── New subscription — create a Checkout Session ──
            # Always get or create a Stripe Customer so:
            #  (a) saved payment methods are remembered
            #  (b) any proration credit is tied to the customer
            from datetime import date as _d
            existing_sub = existing_sub  # already retrieved above

            cust_id = _get_or_create_stripe_customer(request.user, existing_sub)

            # If the user had an active subscription (even if stale), apply the
            # unused-days credit to the customer balance so Stripe Checkout
            # shows and charges only the net amount owed.
            if existing_sub and existing_sub.is_active:
                _apply_unused_credit(existing_sub, cust_id)

            # ── Check for saved card and charge directly if available ──
            stripe_customer = stripe.Customer.retrieve(cust_id)
            default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')

            if not default_pm_id:
                # Fallback: check all card payment methods
                pms = stripe.PaymentMethod.list(customer=cust_id, type='card', limit=1)
                if pms.data:
                    default_pm_id = pms.data[0].id

            if default_pm_id:
                try:
                    # Attempt to create the subscription directly
                    subscription = stripe.Subscription.create(
                        customer=cust_id,
                        items=[{'price': price_id}],
                        default_payment_method=default_pm_id,
                        off_session=True,
                        # 'error_if_incomplete' ensures we don't create half-baked subscriptions
                        # if payment fails or authentication (SCA) is required.
                        payment_behavior='error_if_incomplete', 
                    )

                    period_end = _safe_period_end(subscription)
                    
                    # Update or create local subscription
                    sub_obj, created = UserSubscription.objects.update_or_create(
                        user=request.user,
                        defaults={
                            'tier': tier,
                            'active_until': period_end,
                            'renew_date': period_end,
                            'is_active': True,
                            'stripe_customer_id': cust_id,
                            'stripe_subscription_id': subscription.id,
                        }
                    )

                    return Response({
                        "detail": f"Subscribed to {tier.label} successfully using your saved card.",
                        "tier": tier.name,
                        "label": tier.label,
                        "active_until": str(period_end),
                        "charged_directly": True,
                    })
                except stripe.error.CardError:
                    # Payment failed or authentication required - fall through to Checkout Session
                    pass
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Direct subscription creation failed for user {request.user.id}: {str(e)}")
                    # Fall through to Checkout Session
                    pass

            checkout_kwargs = dict(
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                client_reference_id=str(request.user.id),
                customer=cust_id,       # customer balance (credit) auto-applied
                success_url="http://72.61.251.114/authorswap-frontend/subscription",
                cancel_url="http://72.61.251.114/authorswap-frontend/subscription",
            )

            checkout_session = stripe.checkout.Session.create(**checkout_kwargs)
            return Response({'url': checkout_session.url})

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Stripe Checkout Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateSwapCheckoutSessionView(APIView):
    """
    POST /api/stripe/create-swap-checkout-session/
    Expects {'swap_request_id': 1}
    Generates a Stripe Checkout Session URL for paying for a swap request.
    
    This is used when a user requests a swap in a paid slot (promotion_type='paid').
    The user must complete payment before the swap request is fully submitted.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe API configuration is missing. Please add STRIPE_SECRET_KEY to your backend .env file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        swap_request_id = request.data.get('swap_request_id')
        if not swap_request_id:
            return Response({"detail": "swap_request_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            swap_request = SwapRequest.objects.get(id=swap_request_id, requester=request.user)
        except SwapRequest.DoesNotExist:
            return Response({"detail": "Swap request not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get the slot and check if it's a paid slot
        slot = swap_request.slot
        prom_type = str(slot.promotion_type).lower() if slot.promotion_type else ''
        slot_price = slot.price or 0
        
        # A slot requires payment if promotion_type is 'paid' OR price > 0
        if prom_type != 'paid' and slot_price <= 0:
            return Response(
                {"detail": "This slot does not require payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if price is set
        if slot_price <= 0:
            return Response(
                {"detail": "This slot has no price set."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if payment already exists
        existing_payment = getattr(swap_request, 'payment', None)
        if existing_payment and existing_payment.status == 'completed':
            return Response(
                {"detail": "Payment has already been completed for this swap request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get or create Stripe customer
            user_sub = getattr(request.user, 'subscription', None)
            cust_id = _get_or_create_stripe_customer(request.user, user_sub)

            # ── Check if user already has a saved card ──
            # Retrieve the Stripe Customer to look for a default payment method.
            stripe_customer = stripe.Customer.retrieve(cust_id)
            default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')

            # Also check payment_methods list in case default isn't set via invoice_settings
            if not default_pm_id:
                payment_methods = stripe.PaymentMethod.list(customer=cust_id, type='card')
                if payment_methods.data:
                    default_pm_id = payment_methods.data[0].id

            metadata = {
                'swap_request_id': str(swap_request.id),
                'user_id': str(request.user.id),
                'slot_id': str(slot.id),
                'payment_type': 'swap',
            }

            if default_pm_id:
                try:
                    # ── User has a saved card → charge it directly ──
                    payment_intent = stripe.PaymentIntent.create(
                        amount=int(slot_price * 100),  # Convert to cents
                        currency='usd',
                        customer=cust_id,
                        payment_method=default_pm_id,
                        confirm=True,
                        off_session=True,  # Charge without user interaction
                        metadata=metadata,
                        description=f"Swap Request {swap_request.id} - {slot.preferred_genre} slot on {slot.send_date}",
                    )

                    # Mark payment as completed
                    SwapPayment.objects.update_or_create(
                        swap_request=swap_request,
                        defaults={
                            'payer': request.user,
                            'amount': slot_price,
                            'currency': 'USD',
                            'stripe_payment_intent_id': payment_intent.id,
                            'status': 'completed',
                            'paid_at': timezone.now(),
                        }
                    )

                    return Response({
                        'charged': True,
                        'payment_done': True,
                        'detail': 'Payment charged successfully using your saved card.',
                        'payment_intent_id': payment_intent.id,
                    })
                except stripe.error.CardError:
                    # Saved card failed or requires authentication → fall through to Checkout Session
                    pass
                except Exception as e:
                    # Other errors (e.g. stale PM) → fall through to Checkout
                    pass

            # ── No saved card → redirect user to Stripe Checkout to add one ──
            # Create Stripe Product and Price for this swap payment
            product = stripe.Product.create(
                name=f"Swap Request - {slot.preferred_genre} slot on {slot.send_date}",
                description=f"Newsletter swap promotion slot from {slot.user.username}",
            )

            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(slot_price * 100),  # Convert to cents
                currency="usd",
            )

            # Create Checkout Session for one-time payment
            checkout_kwargs = dict(
                payment_method_types=['card'],
                line_items=[{'price': price.id, 'quantity': 1}],
                mode='payment',  # One-time payment, not subscription
                client_reference_id=str(request.user.id),
                customer=cust_id,
                success_url=f"http://72.61.251.114/authorswap-frontend/swap-management",
                cancel_url=f"http://72.61.251.114/authorswap-frontend/swap-management",
                metadata=metadata,
                payment_intent_data={
                    'setup_future_usage': 'off_session',  # Save card for future charges
                },
            )

            checkout_session = stripe.checkout.Session.create(**checkout_kwargs)

            # Create or update SwapPayment record
            SwapPayment.objects.update_or_create(
                swap_request=swap_request,
                defaults={
                    'payer': request.user,
                    'amount': slot_price,
                    'currency': 'USD',
                    'stripe_checkout_session_id': checkout_session.id,
                    'status': 'pending',
                }
            )

            return Response({
                'charged': False,
                'payment_done': False,
                'url': checkout_session.url,
                'session_id': checkout_session.id,
                'detail': 'No saved card found. Please complete payment via the checkout link.',
            })

        except stripe.error.CardError as e:
            # Saved card was declined — tell the frontend to redirect user to add a new card
            import logging
            logging.getLogger(__name__).warning(f"Swap payment card declined for user {request.user.id}: {str(e)}")
            return Response(
                {
                    'error': e.user_message or 'Your saved card was declined.',
                    'charged': False,
                    'payment_done': False,
                    'requires_action': True,
                    'detail': 'Your saved card was declined. Please update your payment method.',
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Swap Checkout Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncSwapPaymentView(APIView):
    """
    POST /api/stripe/sync-swap-payment/

    Queries Stripe directly for a swap payment's checkout session status
    and updates the local SwapPayment record.

    Call this endpoint right after the user returns from Stripe's checkout
    success URL so the DB is updated even if the webhook hasn't fired yet.

    Body: { "session_id": "cs_test_xxx", "swap_request_id": 1 }

    Response (success):
        {
            "detail": "Payment synced.",
            "status": "completed",
            "payment_done": true
        }

    Response (pending):
        { "detail": "Payment not completed yet.", "status": "pending", "payment_done": false }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        swap_request_id = request.data.get('swap_request_id')
        session_id = request.data.get('session_id')

        if not swap_request_id:
            return Response(
                {'detail': 'swap_request_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            swap_request = SwapRequest.objects.get(id=swap_request_id, requester=request.user)
        except SwapRequest.DoesNotExist:
            return Response(
                {'detail': 'Swap request not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get or create the payment record
        payment = getattr(swap_request, 'payment', None)

        try:
            # If we have a session_id, verify with Stripe
            if session_id:
                try:
                    session = stripe.checkout.Session.retrieve(session_id)
                    payment_status = session.get('payment_status')
                    
                    if payment_status == 'paid':
                        payment_intent = session.get('payment_intent')
                        
                        if not payment:
                            # Create payment record if it doesn't exist
                            slot = swap_request.slot
                            payment = SwapPayment.objects.create(
                                swap_request=swap_request,
                                payer=request.user,
                                amount=slot.price or 0,
                                currency='USD',
                                stripe_checkout_session_id=session_id,
                                stripe_payment_intent_id=payment_intent,
                                status='completed',
                                paid_at=timezone.now()
                            )
                        else:
                            # Update existing payment
                            if payment.status != 'completed':
                                payment.status = 'completed'
                                payment.stripe_payment_intent_id = payment_intent
                                payment.paid_at = timezone.now()
                                payment.save(update_fields=['status', 'stripe_payment_intent_id', 'paid_at'])
                        
                        # Notify the receiver (slot owner)
                        from core.models import Notification
                        Notification.objects.create(
                            recipient=swap_request.slot.user,
                            title="Payment Received! 💰",
                            badge="WALLET",
                            message=f"{request.user.username} has sent you ${payment.amount}. Your account is credited. Please confirm receipt on the swap management page.",
                            action_url=f"/dashboard/swaps/manage/"
                        )
                        
                        return Response({
                            'detail': 'Payment synced.',
                            'status': 'completed',
                            'payment_done': True
                        })
                    
                except stripe.error.InvalidRequestError:
                    pass  # Invalid session ID

            # Check local payment status
            if payment and payment.status == 'completed':
                return Response({
                    'detail': 'Payment completed.',
                    'status': 'completed',
                    'payment_done': True
                })

            return Response({
                'detail': 'Payment not completed yet.',
                'status': payment.status if payment else 'pending',
                'payment_done': False
            })

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SyncSwapPayment Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmSwapPaymentView(APIView):
    """
    POST /api/stripe/confirm-swap-payment/<swap_request_id>/

    Allows the RECEIVER (slot owner) to confirm they received the payment.
    This updates the payment status to show as 'completed' in the swap status.

    Body: { "confirm": true }  (optional, defaults to true)

    Response (success):
        {
            "detail": "Payment confirmed.",
            "status": "completed",
            "receiver_confirmed": true,
            "confirmed_at": "2026-03-16T12:00:00Z"
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, swap_request_id):
        try:
            swap_request = SwapRequest.objects.get(
                id=swap_request_id,
                slot__user=request.user  # Only the slot owner (receiver) can confirm
            )
        except SwapRequest.DoesNotExist:
            return Response(
                {'detail': 'Swap request not found or you are not authorized to confirm this payment.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the payment record
        payment = getattr(swap_request, 'payment', None)
        if not payment:
            # If no payment record exists, but the receiver is manually confirming, 
            # we create a 'placeholder' completed payment so the swap can finish.
            from core.models import SwapPayment
            from django.utils import timezone
            payment = SwapPayment.objects.create(
                swap_request=swap_request,
                payer=swap_request.requester,
                amount=swap_request.slot.price or 0,
                status='completed',
                paid_at=timezone.now(),
                stripe_checkout_session_id="manual_confirmation"
            )

        # Check if payment is completed (if it existed but was pending)
        if payment.status != 'completed':
            from django.utils import timezone
            payment.status = 'completed'
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at'])

        # Check if already confirmed
        if payment.receiver_confirmed:
            return Response(
                {
                    'detail': 'Payment has already been confirmed.',
                    'status': 'completed',
                    'receiver_confirmed': True,
                    'confirmed_at': payment.receiver_confirmed_at,
                }
            )

        # Confirm the payment
        from django.utils import timezone
        payment.receiver_confirmed = True
        payment.receiver_confirmed_at = timezone.now()
        payment.save(update_fields=['receiver_confirmed', 'receiver_confirmed_at'])

        # Update swap status to scheduled (payment confirmed, swap scheduled)
        if swap_request.status in ['pending', 'confirmed']:
            swap_request.status = 'scheduled'
            swap_request.save(update_fields=['status'])

        # AWARD REPUTATION POINTS
        from core.services.reputation_service import ReputationService
        ReputationService.update_confirmed_sends(swap_request.requester) # The person who paid
        ReputationService.update_confirmed_sends(swap_request.slot.user) # The person who received

        # Create notification for payer
        Notification.objects.create(
            recipient=swap_request.requester,
            title="Payment Confirmed & Swap Scheduled! ✅",
            badge="SWAP",
            message=f"{request.user.username} has confirmed receipt of your payment. The swap is now scheduled!",
            action_url=f"/dashboard/swaps/track/{swap_request.id}/"
        )

        return Response({
            'detail': 'Payment confirmed successfully.',
            'status': 'completed',
            'receiver_confirmed': True,
            'confirmed_at': payment.receiver_confirmed_at,
        })


class ChangePlanView(APIView):
    """
    POST /api/stripe/change-plan/
    Body: { "tier_id": <int> }

    Immediately swaps the price on the user's existing Stripe subscription
    (upgrade or downgrade) and updates the DB. No new checkout flow required.
    Requires an active subscription with a valid stripe_subscription_id.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        tier_id = request.data.get('tier_id')
        if not tier_id:
            return Response({"detail": "tier_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({"detail": "Invalid subscription tier."}, status=status.HTTP_404_NOT_FOUND)

        user_sub = getattr(request.user, 'subscription', None)

        # ── Auto-sync from Stripe if missing or inactive ──
        if not user_sub or not user_sub.stripe_subscription_id or not user_sub.is_active:
            user_sub = _sync_user_subscription_from_stripe(request.user)

        # If user has no subscription record at all, they must subscribe first via checkout.
        if not user_sub:
            return Response(
                {"detail": "No active subscription found. Please subscribe first via the checkout flow."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If the subscription record has no Stripe subscription ID, fall through
        # to the checkout-session path below instead of blocking.
        has_active_stripe_sub = bool(user_sub.stripe_subscription_id)

        if has_active_stripe_sub and user_sub.tier_id == tier.id:
            return Response({"detail": "You are already on this plan."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price_id = tier.stripe_price_id

            def _ensure_valid_price(t):
                product = stripe.Product.create(
                    name=f"Author Swap - {t.name}",
                    description=t.best_for or t.name,
                )
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(t.price * 100),
                    currency="usd",
                    recurring={"interval": "month"},
                )
                t.stripe_price_id = price.id
                t.save(update_fields=['stripe_price_id'])
                return price.id

            if not price_id:
                price_id = _ensure_valid_price(tier)
            else:
                try:
                    stripe.Price.retrieve(price_id)
                except stripe.error.InvalidRequestError:
                    price_id = _ensure_valid_price(tier)

            def _create_checkout_session(price_id):
                """
                Create a fresh Stripe Checkout Session with proration credit applied.
                Gets/creates a Stripe Customer, applies unused-days credit to their
                balance, then creates the session — Stripe Checkout will display and
                deduct the credit automatically so the user pays only what they owe.
                """
                cust_id = _get_or_create_stripe_customer(request.user, user_sub)

                # Apply the unused-days credit from the current plan so the user
                # isn't charged the full new-plan price on the checkout page.
                if user_sub and user_sub.is_active:
                    _apply_unused_credit(user_sub, cust_id)

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{'price': price_id, 'quantity': 1}],
                    mode='subscription',
                    client_reference_id=str(request.user.id),
                    customer=cust_id,   # balance credit auto-applied on checkout
                    success_url="http://72.61.251.114/authorswap-frontend/subscription",
                    cancel_url="http://72.61.251.114/authorswap-frontend/subscription",
                )
                return Response({'url': checkout_session.url}, status=status.HTTP_200_OK)

            # No stored subscription ID — go straight to checkout
            if not has_active_stripe_sub:
                return _create_checkout_session(price_id)

            # Retrieve current subscription and its first item.
            # If the stored ID is stale (belongs to a different Stripe account),
            # clear the bad data and automatically create a fresh Checkout Session.
            try:
                stripe_sub = stripe.Subscription.retrieve(user_sub.stripe_subscription_id)
            except stripe.error.InvalidRequestError:
                import logging
                logging.getLogger(__name__).warning(
                    f"Stale stripe_subscription_id '{user_sub.stripe_subscription_id}' "
                    f"for user {request.user.id}. Clearing and creating a new checkout session."
                )
                user_sub.stripe_subscription_id = None
                user_sub.stripe_customer_id = None
                user_sub.save(update_fields=['stripe_subscription_id', 'stripe_customer_id'])
                return _create_checkout_session(price_id)


            # ── Upgrade vs Downgrade Logic ──
            old_price = float(user_sub.tier.price) if user_sub.tier else 0
            new_price = float(tier.price)
            is_upgrade = new_price > old_price

            if is_upgrade:
                # ── Try to charge saved card directly for upgrade ──
                cust_id = user_sub.stripe_customer_id
                if cust_id:
                    try:
                        stripe_customer = stripe.Customer.retrieve(cust_id)
                        default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')
                        
                        if not default_pm_id:
                            pms = stripe.PaymentMethod.list(customer=cust_id, type='card', limit=1)
                            if pms.data:
                                default_pm_id = pms.data[0].id

                        if default_pm_id:
                            item_id = stripe_sub['items']['data'][0]['id']
                            updated_sub = stripe.Subscription.modify(
                                user_sub.stripe_subscription_id,
                                items=[{'id': item_id, 'price': price_id}],
                                proration_behavior='always_invoice',
                                default_payment_method=default_pm_id,
                                payment_behavior='error_if_incomplete',
                            )

                            period_end = _safe_period_end(updated_sub)
                            user_sub.tier = tier
                            user_sub.active_until = period_end
                            user_sub.renew_date = period_end
                            user_sub.is_active = True
                            user_sub.save(update_fields=['tier', 'active_until', 'renew_date', 'is_active'])

                            return Response({
                                "detail": f"Plan upgraded to {tier.label} successfully using your saved card.",
                                "tier": tier.name,
                                "label": tier.label,
                                "price": str(tier.price),
                                "active_until": str(period_end),
                                "url": None,
                                "is_upgrade": True,
                                "charged_directly": True
                            })
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Direct upgrade failed for user {request.user.id}: {str(e)}")
                        # Fall through to checkout session
                
                # ── Use Stripe Checkout for Upgrades (Fallback) ──
                return _create_checkout_session(price_id)

            # ── Use Background Update for Downgrades/Same-Price changes ──
            # No immediate payment is required, so we just modify it in-place.
            item_id = stripe_sub['items']['data'][0]['id']
            updated_sub = stripe.Subscription.modify(
                user_sub.stripe_subscription_id,
                items=[{'id': item_id, 'price': price_id}],
                proration_behavior='always_invoice',
            )

            # Use Stripe's real billing period end
            period_end = _safe_period_end(updated_sub)
            user_sub.tier = tier
            user_sub.active_until = period_end
            user_sub.renew_date = period_end
            user_sub.is_active = True
            user_sub.save(update_fields=['tier', 'active_until', 'renew_date', 'is_active'])

            return Response({
                "detail": f"Plan changed to {tier.label} successfully.",
                "tier": tier.name,
                "label": tier.label,
                "price": str(tier.price),
                "active_until": str(period_end),
                "url": None,
                "is_upgrade": False
            })

        except stripe.error.InvalidRequestError as e:
            import logging
            logging.getLogger(__name__).error(f"Stripe ChangePlan Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Stripe ChangePlan Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PreviewPlanChangeView(APIView):
    """
    POST /api/stripe/change-plan/preview/
    Body: { "tier_id": <int> }

    Returns the prorated amount the user will be charged (or credited) if they
    switch to the given tier RIGHT NOW — without actually making the change.

    Response:
        {
            "current_plan":  "Tier 3 - Growth ($48.99/mo)",
            "new_plan":      "Tier 2 - Starter ($28.99/mo)",
            "amount_due":    -18.67,          # negative = credit/refund
            "amount_due_display": "-$18.67",
            "billing_period_end": "2026-04-02",
            "proration_date": "2026-03-03",
            "line_items": [
                {"description": "Unused time on Growth...", "amount": -45.72},
                {"description": "Remaining time on Starter...", "amount": 27.05}
            ]
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        tier_id = request.data.get('tier_id')
        if not tier_id:
            return Response({"detail": "tier_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({"detail": "Invalid subscription tier."}, status=status.HTTP_404_NOT_FOUND)

        user_sub = getattr(request.user, 'subscription', None)
        if not user_sub or not user_sub.stripe_subscription_id or not user_sub.stripe_customer_id:
            user_sub = _sync_user_subscription_from_stripe(request.user)

        if not user_sub or not user_sub.stripe_subscription_id or not user_sub.stripe_customer_id:
            return Response(
                {"detail": "No active subscription to preview changes for."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            price_id = tier.stripe_price_id
            if not price_id:
                return Response(
                    {"detail": "This tier has no Stripe price configured yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate price ID
            try:
                stripe.Price.retrieve(price_id)
            except stripe.error.InvalidRequestError:
                return Response(
                    {"detail": "Price for this tier is invalid. Please contact support."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Retrieve the actual subscription to get the billing period
            try:
                stripe_sub = stripe.Subscription.retrieve(user_sub.stripe_subscription_id)
            except stripe.error.InvalidRequestError:
                return Response(
                    {"detail": "No valid Stripe subscription found. Please use the checkout flow."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from datetime import date as _date
            import math as _math

            # ── Manual proration calculation ────────────────────────────────────
            # More reliable than Invoice.create_preview — not affected by
            # customer balance credits or Stripe SDK version changes.
            today = _date.today()
            period_end = _safe_period_end(stripe_sub)
            remaining_days = max(0, (period_end - today).days)

            # Get the real period length from Stripe if available
            period_start_ts = None
            try:
                period_start_ts = getattr(stripe_sub, 'current_period_start', None) \
                    or stripe_sub.get('current_period_start')
            except (KeyError, TypeError, AttributeError):
                pass

            if period_start_ts:
                period_start = _date.fromtimestamp(int(period_start_ts))
                total_days = max(1, (period_end - period_start).days)
            else:
                total_days = 30

            current_price = float(user_sub.tier.price)
            new_price = float(tier.price)

            # Credit = unused portion of current plan
            credit = _math.floor((remaining_days / total_days) * current_price * 100) / 100
            # Charge = proportional cost of new plan for remaining days
            charge = _math.floor((remaining_days / total_days) * new_price * 100) / 100
            # Net = what the user actually pays (negative = refund / credit)
            net = round(charge - credit, 2)

            current_tier = user_sub.tier
            current_plan_label = f"{current_tier.name} - {current_tier.label} (${current_tier.price}/mo)"
            new_plan_label = f"{tier.name} - {tier.label} (${tier.price}/mo)"

            line_items = [
                {
                    "description": f"Unused time on {current_tier.label} ({remaining_days} of {total_days} days remaining)",
                    "amount": -credit,
                },
                {
                    "description": f"Remaining time on {tier.label} ({remaining_days} of {total_days} days)",
                    "amount": charge,
                },
            ]

            return Response({
                "current_plan": current_plan_label,
                "new_plan": new_plan_label,
                "amount_due": net,
                "amount_due_display": f"-${abs(net):.2f}" if net < 0 else f"${net:.2f}",
                "billing_period_end": str(period_end),
                "days_remaining": remaining_days,
                "days_in_period": total_days,
                "credit_from_current_plan": credit,
                "charge_for_new_plan": charge,
                "line_items": line_items,
            })



        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"PreviewPlanChange Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    POST /api/stripe/webhook/
    Listens for Stripe webhooks to update subscription status.

    """
    # Disable global auth/CSRF for webhooks as it uses Stripe signature
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        try:
            # You can find your endpoint's secret in your webhook settings
            # We recommend using the Webhook Secret from your settings.
            webhook_secret = settings.STRIPE_WEBHOOK_SECRET
            if webhook_secret:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            else:
                import json
                if not settings.STRIPE_SECRET_KEY:
                    return Response(
                        {"detail": "Stripe API key is missing. Please configure STRIPE_SECRET_KEY."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
                event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

        except ValueError:
            # Invalid payload
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type']

        # ── New subscription created via Checkout ──
        if event_type == 'checkout.session.completed':
            session = event['data']['object']

            # Check if this is a swap payment (metadata will have payment_type='swap')
            metadata = session.get('metadata', {})
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Webhook checkout.session.completed - metadata: {metadata}")
            
            if metadata.get('payment_type') == 'swap':
                # Handle swap payment completion
                swap_request_id = metadata.get('swap_request_id')
                payment_intent = session.get('payment_intent')
                
                logger.info(f"Processing swap payment for swap_request_id: {swap_request_id}")
                
                if swap_request_id:
                    try:
                        from core.models import SwapPayment
                        # Convert string ID to int if needed
                        try:
                            swap_request_id_int = int(swap_request_id)
                        except (ValueError, TypeError):
                            swap_request_id_int = swap_request_id
                            
                        swap_payment = SwapPayment.objects.filter(
                            swap_request_id=swap_request_id_int
                        ).first()
                        
                        if swap_payment:
                            logger.info(f"Found SwapPayment record, calling complete_payment()")
                            # Ensure session ID and intent ID are preserved
                            if not swap_payment.stripe_checkout_session_id:
                                swap_payment.stripe_checkout_session_id = session.get('id')
                            swap_payment.stripe_payment_intent_id = payment_intent
                            swap_payment.save(update_fields=['stripe_checkout_session_id', 'stripe_payment_intent_id'])
                            
                            # Use internal method to finalize and move money!
                            swap_payment.complete_payment()
                            logger.info(f"SwapPayment {swap_payment.id} finalized via complete_payment()")

                            # Notify the receiver (slot owner)
                            from core.models import Notification
                            swap_req = swap_payment.swap_request
                            Notification.objects.create(
                                recipient=swap_req.slot.user,
                                title="Payment Received! 💰",
                                badge="WALLET",
                                message=f"{swap_req.requester.username} has sent you ${swap_payment.amount}. Your wallet has been credited.",
                                action_url=f"/dashboard/swaps/manage/"
                            )
                        else:
                            # Create SwapPayment if it doesn't exist
                            logger.info(f"No SwapPayment found, creating new for swap_request_id: {swap_request_id}")
                            try:
                                swap_request = SwapRequest.objects.get(id=swap_request_id_int)
                                swap_payment = SwapPayment.objects.create(
                                    swap_request=swap_request,
                                    payer=swap_request.requester,
                                    amount=swap_request.slot.price or 0,
                                    currency='USD',
                                    stripe_checkout_session_id=session.get('id'),
                                    stripe_payment_intent_id=payment_intent,
                                    status='pending', # Start as pending so complete_payment works
                                )
                                # Now move the money!
                                swap_payment.complete_payment()
                                logger.info(f"Created and finalized new SwapPayment {swap_payment.id}")
                            except Exception as e:
                                logger.error(f"Failed to process new SwapPayment: {e}")
                                swap_payment = None
                            
                            # Notification
                            if swap_payment:
                                Notification.objects.create(
                                    recipient=swap_payment.swap_request.slot.user,
                                    title="Swap Payment Received",
                                    badge="SWAP",
                                    message=f"Payment received from {swap_payment.payer.username}. Wallet credited.",
                                    action_url=f"/dashboard/swaps/manage/"
                                )
                    except Exception as e:
                        logger.error(f"Webhook swap payment error: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.error("swap_request_id not found in metadata")
                
                return Response(status=status.HTTP_200_OK)

            elif metadata.get('payment_type') == 'direct_payment':
                # Handle direct payment completion
                transaction_id = metadata.get('transaction_id')
                payment_intent = session.get('payment_intent')
                
                logger.info(f"Processing direct payment for transaction_id: {transaction_id}")
                
                if transaction_id:
                    try:
                        from core.models import PaymentTransaction, UserWallet, Notification
                        transaction = PaymentTransaction.objects.get(id=transaction_id)
                        
                        if transaction.status == 'pending':
                            # Complete the transaction
                            transaction.status = 'completed'
                            transaction.stripe_payment_intent_id = payment_intent
                            transaction.completed_at = timezone.now()
                            transaction.save()
                            
                            # Add money to receiver's wallet
                            receiver_wallet, _ = UserWallet.objects.get_or_create(user=transaction.receiver)
                            receiver_wallet.add_balance(transaction.amount)
                            
                            # Notify the receiver
                            Notification.objects.create(
                                recipient=transaction.receiver,
                                title="Money Received! 💰",
                                badge="WALLET",
                                message=f"{transaction.sender.username} has sent you ${transaction.amount}. Your wallet has been credited.",
                                action_url=f"/dashboard/wallet/"
                            )
                            logger.info(f"Direct transaction {transaction.id} completed successfully via webhook")
                    except Exception as e:
                        logger.error(f"Webhook direct payment error: {e}")
                
                return Response(status=status.HTTP_200_OK)

            # ── Handle subscription checkout (original logic) ──
            # Retrieve the user ID from the client_reference_id
            user_id = session.get('client_reference_id')
            stripe_customer_id = session.get('customer')
            stripe_subscription_id = session.get('subscription')

            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    
                    # We also need to get the tier based on the price ID from the session's line items.
                    # Since session doesn't include line items directly by default, we retrieve it:
                    line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
                    if line_items and line_items.data:
                        price_id = line_items.data[0].price.id
                        tier = SubscriptionTier.objects.filter(stripe_price_id=price_id).first()
                        
                        if tier:
                            sub_start = datetime.now().date()
                            sub_end = sub_start + timedelta(days=30) # Roughly 1 month

                            # Create or update user subscription
                            UserSubscription.objects.update_or_create(
                                user=user,
                                defaults={
                                    'tier': tier,
                                    'active_until': sub_end,
                                    'renew_date': sub_end,
                                    'is_active': True,
                                    'stripe_customer_id': stripe_customer_id,
                                    'stripe_subscription_id': stripe_subscription_id
                                }
                            )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Webhook checkout.session.completed error: {e}")

        # ── Plan changed directly on Stripe subscription (upgrade/downgrade) ──
        elif event_type == 'customer.subscription.updated':
            stripe_sub = event['data']['object']
            stripe_subscription_id = stripe_sub['id']
            stripe_customer_id = stripe_sub['customer']

            try:
                # Get the new price from the first subscription item
                price_id = stripe_sub['items']['data'][0]['price']['id']
                tier = SubscriptionTier.objects.filter(stripe_price_id=price_id).first()

                user_sub = UserSubscription.objects.filter(
                    stripe_subscription_id=stripe_subscription_id
                ).first()

                if not user_sub:
                    # Try to find by customer ID
                    user_sub = UserSubscription.objects.filter(
                        stripe_customer_id=stripe_customer_id
                    ).first()

                if user_sub and tier:
                    sub_start = datetime.now().date()
                    sub_end = sub_start + timedelta(days=30)
                    user_sub.tier = tier
                    user_sub.active_until = sub_end
                    user_sub.renew_date = sub_end
                    user_sub.is_active = True
                    user_sub.stripe_subscription_id = stripe_subscription_id
                    user_sub.save(update_fields=[
                        'tier', 'active_until', 'renew_date', 'is_active', 'stripe_subscription_id'
                    ])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Webhook customer.subscription.updated error: {e}")

        # ── Subscription cancelled / expired ──
        elif event_type == 'customer.subscription.deleted':
            stripe_sub = event['data']['object']
            stripe_subscription_id = stripe_sub['id']
            try:
                user_sub = UserSubscription.objects.filter(
                    stripe_subscription_id=stripe_subscription_id
                ).first()
                if user_sub:
                    user_sub.is_active = False
                    user_sub.save(update_fields=['is_active'])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Webhook customer.subscription.deleted error: {e}")

        # ── Invoice Payment Succeeded ──
        elif event_type == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            stripe_subscription_id = invoice.get('subscription')
            if stripe_subscription_id:
                try:
                    user_sub = UserSubscription.objects.filter(
                        stripe_subscription_id=stripe_subscription_id
                    ).first()
                    if user_sub:
                        user_sub.is_active = True
                        user_sub.save(update_fields=['is_active'])
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Webhook invoice.payment_succeeded error: {e}")

        # ── Invoice Payment Failed ──
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            stripe_subscription_id = invoice.get('subscription')
            if stripe_subscription_id:
                try:
                    user_sub = UserSubscription.objects.filter(
                        stripe_subscription_id=stripe_subscription_id
                    ).first()
                    if user_sub:
                        # Optionally mark as inactive if payment fails, or handle dunning
                        user_sub.is_active = False
                        user_sub.save(update_fields=['is_active'])
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Webhook invoice.payment_failed error: {e}")

        return Response(status=status.HTTP_200_OK)


# =====================================================================
# STRIPE — CARD SAVE / PAYMENT METHOD MANAGEMENT
# =====================================================================

def _get_stripe_customer_id(user):
    """Resolve the Stripe customer ID from UserSubscription or UserProfile fallback."""
    user_sub = getattr(user, 'subscription', None)
    if user_sub and user_sub.stripe_customer_id:
        return user_sub.stripe_customer_id
    try:
        return user.profile.stripe_customer_id or None
    except Exception:
        return None

class SetupIntentView(APIView):
    """
    POST /api/stripe/setup-intent/

    Creates (or reuses) a Stripe Customer for the authenticated user,
    then creates a SetupIntent so the frontend can securely collect and
    save the user's card using Stripe.js / Stripe Elements.

    Response:
        {
            "client_secret": "seti_xxx_secret_xxx",
            "customer_id":   "cus_xxx"
        }

    Frontend usage (Stripe.js):
        const { error, setupIntent } = await stripe.confirmCardSetup(client_secret, {
            payment_method: { card: cardElement }
        });
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        try:
            user = request.user
            user_sub = getattr(user, 'subscription', None)

            # ── Resolve existing Stripe Customer ID from any source ──
            stripe_customer_id = None
            if user_sub and user_sub.stripe_customer_id:
                stripe_customer_id = user_sub.stripe_customer_id
            else:
                # Fallback: check authentication.UserProfile
                try:
                    auth_profile = user.profile
                    stripe_customer_id = getattr(auth_profile, 'stripe_customer_id', None) or None
                except Exception:
                    pass

            # ── Validate the stored customer ID is still valid in Stripe ──
            if stripe_customer_id:
                try:
                    stripe.Customer.retrieve(stripe_customer_id)
                except stripe.error.InvalidRequestError:
                    # Stale customer from a different Stripe account → create a new one
                    stripe_customer_id = None

            # ── Create a new Stripe Customer if needed ──
            if not stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.get_full_name() or user.username,
                    metadata={'user_id': str(user.id)},
                )
                stripe_customer_id = customer.id

                # Persist to subscription if it exists
                if user_sub:
                    user_sub.stripe_customer_id = stripe_customer_id
                    user_sub.save(update_fields=['stripe_customer_id'])
                else:
                    # Persist to authentication.UserProfile as fallback
                    try:
                        auth_profile = user.profile
                        if hasattr(auth_profile, 'stripe_customer_id'):
                            auth_profile.stripe_customer_id = stripe_customer_id
                            auth_profile.save(update_fields=['stripe_customer_id'])
                    except Exception:
                        pass

            # ── Always create a fresh SetupIntent ──
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],
                usage='off_session',   # card can be charged later without the user present
            )

            return Response({
                'client_secret': setup_intent.client_secret,
                'customer_id': stripe_customer_id,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
            })

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SetupIntent Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SavedPaymentMethodsView(APIView):
    """
    GET /api/stripe/payment-methods/

    Returns the list of saved cards for the authenticated user.

    Response:
        [
            {
                "id":       "pm_xxx",
                "brand":    "visa",
                "last4":    "4242",
                "exp_month": 12,
                "exp_year":  2027,
                "is_default": true
            },
            ...
        ]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        try:
            user = request.user
            stripe_customer_id = _get_stripe_customer_id(user)

            # ── Fallback: search Stripe by email to find orphaned customer ──
            if not stripe_customer_id:
                customers = stripe.Customer.list(email=user.email, limit=5)
                if customers.data:
                    # Pick the most recently created one
                    stripe_customer_id = customers.data[0].id
                    # Persist so we don't have to search again
                    user_sub = getattr(user, 'subscription', None)
                    if user_sub:
                        user_sub.stripe_customer_id = stripe_customer_id
                        user_sub.save(update_fields=['stripe_customer_id'])
                    else:
                        try:
                            user.profile.stripe_customer_id = stripe_customer_id
                            user.profile.save(update_fields=['stripe_customer_id'])
                        except Exception:
                            pass

            if not stripe_customer_id:
                return Response([])

            # Validate the customer ID is still valid
            try:
                customer = stripe.Customer.retrieve(stripe_customer_id)
                if customer.get('deleted'):
                    return Response([])
            except stripe.error.InvalidRequestError:
                return Response([])

            # Fetch all saved card payment methods
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id,
                type='card',
            )

            # Determine the default payment method
            default_pm_id = None
            if customer.get('invoice_settings'):
                default_pm_id = customer['invoice_settings'].get('default_payment_method')

            # Fetch the user's wallet balance to show alongside cards if needed by UI
            from core.models import UserWallet
            wallet, _ = UserWallet.objects.get_or_create(user=user)
            current_balance = str(wallet.balance)

            result = []
            for pm in payment_methods.data:
                card = pm.get('card', {})
                result.append({
                    'id':        pm.id,
                    'brand':     card.get('brand', ''),
                    'last4':     card.get('last4', ''),
                    'exp_month': card.get('exp_month'),
                    'exp_year':  card.get('exp_year'),
                    'is_default': pm.id == default_pm_id,
                    'balance':   current_balance,  # Added balance field
                })

            return Response(result)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SavedPaymentMethods Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DeletePaymentMethodView(APIView):
    """
    DELETE /api/stripe/payment-methods/<pm_id>/

    Detaches (removes) a saved card from the user's Stripe Customer.
    Only the owner of the payment method can delete it.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pm_id):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        try:
            stripe_customer_id = _get_stripe_customer_id(request.user)

            if not stripe_customer_id:
                return Response(
                    {'detail': 'No Stripe customer found for this account.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Verify the payment method belongs to this customer before detaching
            try:
                pm = stripe.PaymentMethod.retrieve(pm_id)
            except stripe.error.InvalidRequestError:
                return Response(
                    {'detail': 'Payment method not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if pm.get('customer') != stripe_customer_id:
                return Response(
                    {'detail': 'You do not own this payment method.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            stripe.PaymentMethod.detach(pm_id)
            return Response({'detail': 'Card removed successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"DeletePaymentMethod Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetDefaultPaymentMethodView(APIView):
    """
    POST /api/stripe/payment-methods/<pm_id>/set-default/

    Sets the specified payment method as the default for the user's
    Stripe Customer (used for future subscription renewals).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pm_id):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        try:
            user_sub = getattr(request.user, 'subscription', None)
            stripe_customer_id = _get_stripe_customer_id(request.user)

            if not stripe_customer_id:
                return Response(
                    {'detail': 'No Stripe customer found for this account.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Verify ownership
            try:
                pm = stripe.PaymentMethod.retrieve(pm_id)
            except stripe.error.InvalidRequestError:
                return Response(
                    {'detail': 'Payment method not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if pm.get('customer') != stripe_customer_id:
                return Response(
                    {'detail': 'You do not own this payment method.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Set as default on the Customer
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={'default_payment_method': pm_id},
            )

            # Also update the subscription's default payment method if one exists
            if user_sub and user_sub.stripe_subscription_id:
                try:
                    stripe.Subscription.modify(
                        user_sub.stripe_subscription_id,
                        default_payment_method=pm_id,
                    )
                except stripe.error.InvalidRequestError:
                    pass  # Stale subscription — ignore

            return Response({'detail': 'Default card updated successfully.'})

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SetDefaultPaymentMethod Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncSubscriptionView(APIView):
    """
    POST /api/stripe/sync-subscription/

    Queries Stripe directly for the authenticated user's active subscriptions
    and creates or updates the local UserSubscription record.

    Call this endpoint right after the user returns from Stripe's checkout
    success URL so the DB is updated even if the webhook hasn't fired yet.

    Optionally accepts a Stripe Checkout Session ID to use as a hint:
        { "session_id": "cs_test_xxx" }   ← pass this if you have it

    Response (success):
        {
            "detail": "Subscription synced.",
            "tier": "Tier 2",
            "label": "Starter",
            "price": "28.99",
            "active_until": "2026-04-02",
            "is_active": true
        }

    Response (nothing found yet):
        { "detail": "No active Stripe subscription found yet. Try again in a moment." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        user = request.user
        user_sub = getattr(user, 'subscription', None)
        session_id = request.data.get('session_id')

        try:
            stripe_customer_id = None
            stripe_subscription_id = None
            stripe_price_id = None

            # ── Path 1: We have a session_id from the success URL ──
            if session_id:
                try:
                    session = stripe.checkout.Session.retrieve(
                        session_id,
                        expand=['line_items', 'subscription'],
                    )
                    stripe_customer_id = session.get('customer')
                    stripe_subscription_id = session.get('subscription')

                    # Extract the price ID from line items
                    line_items = session.get('line_items')
                    if line_items and line_items.get('data'):
                        stripe_price_id = line_items['data'][0]['price']['id']

                    # If subscription is an object (expanded), get its details directly
                    if isinstance(stripe_subscription_id, dict):
                        sub_obj = stripe_subscription_id
                        stripe_subscription_id = sub_obj['id']
                        if not stripe_price_id:
                            stripe_price_id = sub_obj['items']['data'][0]['price']['id']

                except stripe.error.InvalidRequestError:
                    pass  # Bad session ID — fall through to customer search

            # ── Path 2: Look up by existing customer ID in our DB ──
            if not stripe_subscription_id and user_sub and user_sub.stripe_customer_id:
                try:
                    stripe.Customer.retrieve(user_sub.stripe_customer_id)
                    stripe_customer_id = user_sub.stripe_customer_id
                except stripe.error.InvalidRequestError:
                    stripe_customer_id = None

            # ── Path 3: Search Stripe for a customer by email ──
            if not stripe_customer_id:
                customers = stripe.Customer.list(email=user.email, limit=5)
                for c in customers.data:
                    # Pick the customer that has active subscriptions
                    subs = stripe.Subscription.list(customer=c.id, status='active', limit=1)
                    if subs.data:
                        stripe_customer_id = c.id
                        break

            if not stripe_customer_id:
                return Response(
                    {'detail': 'No active Stripe subscription found yet. Try again in a moment.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # ── Fetch the latest active subscription for this customer ──
            if not stripe_subscription_id:
                subs = stripe.Subscription.list(
                    customer=stripe_customer_id,
                    status='active',
                    limit=1,
                )
                if not subs.data:
                    return Response(
                        {'detail': 'No active Stripe subscription found yet. Try again in a moment.'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                active_sub = subs.data[0]
                stripe_subscription_id = active_sub.get('id') or active_sub['id']
                stripe_price_id = active_sub['items']['data'][0]['price']['id']
                period_end_ts = _safe_period_end(active_sub)
            else:
                # Retrieve the subscription to get current_period_end
                active_sub = stripe.Subscription.retrieve(stripe_subscription_id)
                if not stripe_price_id:
                    stripe_price_id = active_sub['items']['data'][0]['price']['id']
                period_end_ts = _safe_period_end(active_sub)

            # ── Match price to a SubscriptionTier in our DB ──
            tier = SubscriptionTier.objects.filter(stripe_price_id=stripe_price_id).first()

            if not tier:
                # The price might be from a different account — try to match by amount
                import logging
                logging.getLogger(__name__).warning(
                    f"SyncSubscription: price_id '{stripe_price_id}' not found in DB for user {user.id}. "
                    f"Attempting to match by amount."
                )
                price_obj = stripe.Price.retrieve(stripe_price_id)
                amount_cents = price_obj.get('unit_amount', 0)
                # Match to the tier with the closest price
                tier = SubscriptionTier.objects.filter(
                    price=round(amount_cents / 100, 2)
                ).first()

            if not tier:
                return Response(
                    {'detail': f'Could not match Stripe price {stripe_price_id} to any subscription tier.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Create or update the UserSubscription record ──
            # period_end_ts is already a date object returned by _safe_period_end()
            period_end = period_end_ts

            obj, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'tier': tier,
                    'active_until': period_end,
                    'renew_date': period_end,
                    'is_active': True,
                    'stripe_customer_id': stripe_customer_id,
                    'stripe_subscription_id': stripe_subscription_id,
                }
            )

            import logging
            logging.getLogger(__name__).info(
                f"SyncSubscription: {'created' if created else 'updated'} subscription "
                f"for user {user.id} → {tier.label} until {period_end}"
            )

            return Response({
                'detail': 'Subscription synced.',
                'tier': tier.name,
                'label': tier.label,
                'price': str(tier.price),
                'active_until': str(period_end),
                'is_active': True,
            })

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SyncSubscription Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletView(APIView):
    """
    GET /api/wallet/
    Returns user's wallet balance and basic info
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet, created = UserWallet.objects.get_or_create(user=user)
        
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class WalletTransactionHistoryView(APIView):
    """
    GET /api/wallet/transactions/
    Returns user's transaction history (both sent and received)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Clean up pending wallet funding transactions
        from datetime import timedelta
        expiry_time = timezone.now() - timedelta(minutes=30)  # 30 minutes instead of 1 hour
        
        # Clean up all pending wallet funding transactions older than 30 minutes
        expired_transactions = PaymentTransaction.objects.filter(
            sender=user,
            transaction_type='bonus',
            status='pending',
            created_at__lt=expiry_time
        )
        if expired_transactions.exists():
            expired_transactions.update(status='cancelled')
        
        # Clean up pending direct_payment transactions older than 30 minutes
        expired_direct_payments = PaymentTransaction.objects.filter(
            sender=user,
            transaction_type='direct_payment',
            status='pending',
            stripe_payment_intent_id__startswith='cs_',
            created_at__lt=expiry_time
        )
        if expired_direct_payments.exists():
            expired_direct_payments.update(status='cancelled')
        
        # Also clean up transactions with checkout session IDs that are still pending
        checkout_expired_transactions = PaymentTransaction.objects.filter(
            sender=user,
            transaction_type='bonus',
            status='pending',
            stripe_payment_intent_id__startswith='cs_'
        )
        if checkout_expired_transactions.exists():
            # Verify with Stripe if these sessions are actually completed
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
            
            for transaction in checkout_expired_transactions:
                try:
                    session = stripe.checkout.Session.retrieve(transaction.stripe_payment_intent_id)
                    if session.payment_status == 'paid':
                        # Complete the transaction
                        transaction.status = 'completed'
                        transaction.completed_at = timezone.now()
                        transaction.save()
                        
                        # Add funds to wallet
                        wallet, _ = UserWallet.objects.get_or_create(user=user)
                        wallet.add_balance(transaction.amount)
                        
                        # Create notification
                        from core.models import Notification
                        Notification.objects.create(
                            recipient=user,
                            title="💵 Wallet Funded!",
                            badge="WALLET",
                            message=f"${transaction.amount} has been added to your wallet. New balance: ${wallet.balance}",
                            action_url="/wallet"
                        )
                    else:
                        # Cancel the transaction
                        transaction.status = 'cancelled'
                        transaction.save()
                except Exception:
                    # If we can't verify, cancel it
                    transaction.status = 'cancelled'
                    transaction.save()
        
        # Get all transactions involving this user using Q objects for efficiency and SQLite compatibility
        # Filter to show only wallet-related transactions (bonus/add_funds, withdrawal)
        from django.db.models import Q
        wallet_transaction_types = ['bonus', 'withdrawal', 'add_funds']
        all_transactions = PaymentTransaction.objects.filter(
            Q(sender=user) | Q(receiver=user),
            transaction_type__in=wallet_transaction_types
        ).order_by('-created_at')
        
        # Apply filters
        transaction_type = request.query_params.get('type', None)
        if transaction_type:
            all_transactions = all_transactions.filter(transaction_type=transaction_type)
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            all_transactions = all_transactions.filter(status=status_filter)
        
        # By default, exclude cancelled and pending wallet funding transactions unless explicitly requested
        # Also exclude pending direct_payment transactions with checkout session IDs (user hasn't paid yet)
        if not status_filter:
            all_transactions = all_transactions.exclude(
                Q(status='cancelled') | 
                Q(transaction_type='bonus', status='pending') |
                Q(transaction_type='direct_payment', status='pending', stripe_payment_intent_id__startswith='cs_')
            )
        
        serializer = PaymentTransactionSerializer(all_transactions, many=True, context={'request': request})
        return Response(serializer.data)


class DirectPaymentView(APIView):
    """
    POST /api/payments/direct/
    Send direct payment from current user to another user
    Body: {
        "receiver_id": 123,
        "amount": "10.00",
        "description": "Payment for collaboration"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender = request.user
        receiver_id = request.data.get('receiver_id')
        swap_id = request.data.get('swap_id')
        amount = request.data.get('amount')
        description = request.data.get('description', '')
        
        receiver = None
        swap_request = None

        # 1. Try to resolve via explicit swap_id
        if swap_id:
            try:
                swap_request = SwapRequest.objects.get(id=swap_id)
                receiver = swap_request.slot.user if sender == swap_request.requester else swap_request.requester
            except SwapRequest.DoesNotExist:
                return Response({'detail': f'SwapRequest with ID {swap_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Try to resolve via receiver_id (User or Profile), with SwapRequest fallback
        if not receiver and receiver_id:
            try:
                # Try User ID
                receiver = User.objects.get(id=receiver_id)
            except (User.DoesNotExist, ValueError, TypeError):
                try:
                    # Try Profile ID
                    profile = Profile.objects.get(id=receiver_id)
                    receiver = profile.user
                except (Profile.DoesNotExist, ValueError, TypeError):
                    # FALLBACK: check if they passed swap_id as receiver_id
                    try:
                        swap_request = SwapRequest.objects.get(id=receiver_id)
                        receiver = swap_request.slot.user if sender == swap_request.requester else swap_request.requester
                    except (SwapRequest.DoesNotExist, ValueError, TypeError):
                        pass

        if not receiver:
            return Response({
                'detail': f'Receiver not found (checked User, Profile, and Swap ID {receiver_id or swap_id}).'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 3. Auto-detect swap request if not already found
        # Look for pending/scheduled swap requests where receiver is the slot owner (to be paid)
        if not swap_request and receiver and sender:
            from django.db.models import Q
            try:
                # Find swap requests where:
                # - Sender is the requester (paying for the swap)
                # - Receiver is the slot owner (getting paid)
                # - Status indicates payment is expected
                # - Slot is a paid slot (either promotion_type='paid' OR price > 0)
                
                # Build the query
                base_query = SwapRequest.objects.filter(
                    status__in=['pending', 'scheduled', 'confirmed', 'accepted'],
                    slot__price__gt=0
                ).select_related('slot', 'requester')
                
                # Try to find swap where sender is requester and receiver is slot owner
                swap_candidates = base_query.filter(
                    requester=sender,
                    slot__user=receiver
                )
                
                # If not found, try the reverse (sender is slot owner, receiver is requester)
                if not swap_candidates.exists():
                    swap_candidates = base_query.filter(
                        requester=receiver,
                        slot__user=sender
                    )
                
                # Get the first matching swap
                swap_request = swap_candidates.first()
                
                if swap_request:
                    import logging
                    logging.getLogger(__name__).info(
                        f"Auto-detected swap {swap_request.id} for payment from {sender.username} to {receiver.username}"
                    )
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Swap auto-detect error: {str(e)}")
                pass  # No matching swap found, continue without linking
        
        # Validate amount
        try:
            if amount is None or str(amount).strip() == '':
                return Response({
                    'detail': 'Amount is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            amount = Decimal(str(amount))
            if amount <= 0:
                return Response({
                    'detail': 'Amount must be greater than 0.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, InvalidOperation) as e:
            return Response({
                'detail': f'Invalid amount: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check sender's wallet balance
        sender_wallet, created = UserWallet.objects.get_or_create(user=sender)
        payment_method = request.data.get('payment_method', 'wallet')

        # Scenario A: User has enough balance in their internal wallet AND didn't force stripe
        if sender_wallet.balance >= amount and payment_method != 'stripe':
            # Create transaction
            transaction = PaymentTransaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                transaction_type='direct_payment',
                description=description,
                swap_request=swap_request
            )
            
            try:
                # Deduct from sender's wallet
                sender_wallet.withdraw_balance(amount)
                # Add to receiver's wallet and complete transaction
                transaction.complete_transaction()
                
                return Response({
                    'detail': 'Payment sent successfully from your wallet!',
                    'payment_type': 'wallet',
                    'transaction': PaymentTransactionSerializer(transaction, context={'request': request}).data,
                    'new_balance': str(sender_wallet.balance)
                })
            except Exception as e:
                transaction.status = 'failed'
                transaction.save()
                return Response({
                    'detail': f'Wallet payment failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Scenario B: Wallet balance is low, try Stripe if configured
        if not settings.STRIPE_SECRET_KEY:
            return Response({
                'detail': 'Insufficient balance and Stripe is not configured.',
                'current_balance': str(sender_wallet.balance)
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
        
        try:
            # 1. Get/Create Stripe Customer
            user_sub = getattr(sender, 'subscription', None)
            cust_id = _get_or_create_stripe_customer(sender, user_sub)
            
            # 2. Check for saved default card
            stripe_customer = stripe.Customer.retrieve(cust_id)
            default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')
            
            # The User explicitly wants to use ONLY the default card.
            # No fallback to payment_methods.data[0].id here.
            
            # Metadata for tracking
            metadata = {
                'payment_type': 'direct_payment',
                'sender_id': str(sender.id),
                'receiver_id': str(receiver.id),
                'amount': str(amount),
                'description': description,
                'swap_id': str(swap_request.id) if swap_request else ''
            }

            # 3. If card exists, try direct charge
            if default_pm_id:
                try:
                    payment_intent = stripe.PaymentIntent.create(
                        amount=int(amount * 100),
                        currency='usd',
                        customer=cust_id,
                        payment_method=default_pm_id,
                        confirm=True,
                        off_session=True,
                        metadata=metadata,
                        description=f"Direct Payment to {receiver.username}: {description}"
                    )
                    
                    # Create and complete transaction immediately
                    transaction = PaymentTransaction.objects.create(
                        sender=sender,
                        receiver=receiver,
                        amount=amount,
                        transaction_type='direct_payment',
                        description=description,
                        status='completed',
                        stripe_payment_intent_id=payment_intent.id,
                        completed_at=timezone.now(),
                        swap_request=swap_request
                    )
                    
                    # Add balance to receiver
                    receiver_wallet, _ = UserWallet.objects.get_or_create(user=receiver)
                    receiver_wallet.add_balance(amount)
                    
                    # Update swap status if this is a swap payment
                    if swap_request:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Payment completed for swap {swap_request.id}, current status: {swap_request.status}")
                        
                        if swap_request.status in ['pending', 'confirmed', 'accepted']:
                            old_status = swap_request.status
                            swap_request.status = 'scheduled'
                            swap_request.save()
                            
                            logger.info(f"Swap {swap_request.id} status updated from {old_status} to scheduled")
                            
                            # Create notifications for swap completion
                            from core.models import Notification
                            Notification.objects.create(
                                recipient=swap_request.requester,
                                title="✅ Payment Confirmed!",
                                badge="SWAP",
                                message=f"Your payment for swap with {swap_request.slot.user.username} has been confirmed. The swap is now scheduled!",
                                action_url=f"/dashboard/swaps/track/{swap_request.id}/"
                            )
                            
                            Notification.objects.create(
                                recipient=swap_request.slot.user,
                                title="✅ Swap Completed!",
                                badge="SWAP",
                                message=f"Your swap with {swap_request.requester.username} has been completed successfully.",
                                action_url=f"/dashboard/swaps/track/{swap_request.id}/"
                            )
                        else:
                            logger.warning(f"Swap {swap_request.id} not updated - status {swap_request.status} not in allowed list")
                    
                    return Response({
                        'detail': 'Payment sent successfully using your saved card!',
                        'payment_type': 'card',
                        'transaction': PaymentTransactionSerializer(transaction, context={'request': request}).data,
                        'new_balance': str(sender_wallet.balance) # Balance didn't change as it was external
                    })
                except (stripe.error.CardError, stripe.error.StripeError):
                    # Card failed or needs authentication, fall through to Checkout
                    pass

            # 4. No card or direct charge failed, return Stripe Checkout URL
            # Create a pending transaction to track this
            transaction = PaymentTransaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                transaction_type='direct_payment',
                description=description,
                status='pending',
                swap_request=swap_request
            )
            metadata['transaction_id'] = str(transaction.id)

            # Create session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"Direct Payment to {receiver.username}",
                            'description': description or "Support author collaboration",
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                client_reference_id=str(sender.id),
                customer=cust_id,
                success_url=f"http://72.61.251.114/authorswap-frontend/swap-management",
                cancel_url=f"http://72.61.251.114/authorswap-frontend/swap-management",
                metadata=metadata,
                payment_intent_data={'setup_future_usage': 'off_session'}
            )
            
            # Update transaction with session ID
            transaction.stripe_payment_intent_id = checkout_session.id # Re-using this field for session ID if pending
            transaction.save()

            return Response({
                'detail': 'No sufficient balance or saved card. Please complete payment via Stripe.',
                'payment_type': 'stripe_checkout',
                'url': checkout_session.url,
                'transaction_id': transaction.id
            })

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Direct Stripe Payment Error: {str(e)}")
            return Response({
                'detail': f'External payment failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WithdrawFundsView(APIView):
    """
    POST /api/wallet/withdraw/
    Withdraw funds from wallet to bank account (requires Stripe Connect)
    Body: {
        "amount": "50.00"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data.get('amount')
        
        # Validate amount
        try:
            if amount is None or str(amount).strip() == '':
                return Response({
                    'detail': 'Amount is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            amount = Decimal(str(amount))
            if amount <= 0:
                return Response({
                    'detail': 'Amount must be greater than 0.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, InvalidOperation) as e:
            return Response({
                'detail': f'Invalid amount: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user's wallet
        wallet, created = UserWallet.objects.get_or_create(user=user)
        
        # Check if user has a default payment method set in Stripe
        # This is where the funds would theoretically be withdrawn to (Card or Bank)
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
        from core.views import _get_stripe_customer_id
        cust_id = _get_stripe_customer_id(user)
        
        if not cust_id:
            return Response({
                'detail': 'No Stripe account found. Please link a payment method first.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        stripe_customer = stripe.Customer.retrieve(cust_id)
        if not stripe_customer.get('invoice_settings', {}).get('default_payment_method'):
            return Response({
                'detail': 'No default withdrawal card set. Please set a default card in your payment settings.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if wallet.balance < amount:
            return Response({
                'detail': 'Insufficient balance.',
                'current_balance': str(wallet.balance)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has Stripe Connect account
        # For development/testing, we allow manual withdrawal processing if not connected
        if not wallet.is_stripe_connected or not wallet.stripe_connect_account_id:
            # You can either enforce the check or allow a 'manual' status
            # For now, we will allow it to proceed for development/testing
            pass
        
        # Get default payment method details
        default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')
        withdrawal_destination = "default payment method"
        
        if default_pm_id:
            try:
                pm = stripe.PaymentMethod.retrieve(default_pm_id)
                if pm.type == 'card':
                    card = pm.card
                    withdrawal_destination = f"card ending in {card.last4} ({card.brand.title()} ****{card.last4})"
                elif pm.type == 'bank_account':
                    bank = pm.bank_account
                    withdrawal_destination = f"bank account ending in {bank.last4} ({bank.bank_name})"
            except Exception:
                withdrawal_destination = "default payment method"
        
        # Create withdrawal transaction
        transaction = PaymentTransaction.objects.create(
            sender=user,
            receiver=user,  # Self-transaction for withdrawal
            amount=amount,
            transaction_type='withdrawal',
            description=f'Withdrawal of ${amount} to {withdrawal_destination}'
        )
        
        try:
            # Process withdrawal via Stripe Connect
            # This is where you'd integrate with Stripe Connect transfers
            # For now, we'll mark as completed
            wallet.withdraw_balance(amount)
            transaction.complete_transaction()
            
            return Response({
                'detail': 'Withdrawal processed successfully!',
                'transaction': PaymentTransactionSerializer(transaction, context={'request': request}).data,
                'new_balance': str(wallet.balance)
            })
            
        except Exception as e:
            transaction.status = 'failed'
            transaction.save()
            return Response({
                'detail': f'Withdrawal failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddFundsView(APIView):
    """
    POST /api/wallet/add-funds/
    Add funds to user's wallet via Stripe Checkout
    Body: {
        "amount": "50.00"
    }
    Returns: {
        "url": "https://checkout.stripe.com/..."
    }
    User is redirected to Stripe Checkout, then back to wallet page
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe API configuration is missing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
        
        user = request.user
        amount = request.data.get('amount')
        
        # Validate amount
        try:
            if amount is None or str(amount).strip() == '':
                return Response({
                    'detail': 'Amount is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            amount = Decimal(str(amount))
            if amount <= 0:
                return Response({
                    'detail': 'Amount must be greater than 0.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Max limit check (optional)
            if amount > Decimal('10000'):
                return Response({
                    'detail': 'Maximum deposit amount is $10,000.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (ValueError, TypeError, InvalidOperation) as e:
            return Response({
                'detail': f'Invalid amount: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get or create user's wallet
            wallet, created = UserWallet.objects.get_or_create(user=user)
            
            # Get or create Stripe Customer using standard helper
            user_sub = getattr(user, 'subscription', None)
            cust_id = _get_or_create_stripe_customer(user, user_sub)
            
            # Create a pending transaction record
            transaction = PaymentTransaction.objects.create(
                sender=user,
                receiver=user,  # Self-transaction for adding funds
                amount=amount,
                transaction_type='bonus',  # Using 'bonus' type for wallet funding
                status='pending',
                description=f'Wallet funding of ${amount}'
            )
            
            # Check for saved default card - use correct Stripe API field
            default_pm_id = None
            
            # Get the Stripe Customer to check for default payment method
            try:
                stripe_customer = stripe.Customer.retrieve(cust_id)
                default_pm_id = stripe_customer.get('invoice_settings', {}).get('default_payment_method')
                
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[DEBUG AddFunds] Customer {cust_id} default_pm_id from invoice_settings: {default_pm_id}")
                
                # If no default set in invoice_settings, try to get from payment methods
                if not default_pm_id:
                    customer_payment_methods = stripe.PaymentMethod.list(
                        customer=cust_id,
                        type='card'
                    )
                    logger.warning(f"[DEBUG AddFunds] Found {len(customer_payment_methods.data)} payment methods")
                    if customer_payment_methods.data:
                        default_pm_id = customer_payment_methods.data[0].id
                        logger.warning(f"[DEBUG AddFunds] Using first card as fallback: {default_pm_id}")
                    else:
                        logger.warning(f"[DEBUG AddFunds] No payment methods found for customer {cust_id}")
                        
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error retrieving customer/payment methods: {str(e)}")
            
            if default_pm_id:
                # User has a saved card, set it as default on customer for future use
                try:
                    stripe.Customer.modify(
                        cust_id,
                        invoice_settings={'default_payment_method': default_pm_id}
                    )
                    logger.warning(f"[DEBUG AddFunds] Set default payment method {default_pm_id} on customer {cust_id}")
                except Exception as e:
                    logger.warning(f"[DEBUG AddFunds] Could not set default payment method: {str(e)}")
                
                # Try direct charge
                try:
                    payment_intent = stripe.PaymentIntent.create(
                        amount=int(amount * 100),
                        currency='usd',
                        customer=cust_id,
                        payment_method=default_pm_id,
                        confirm=True,
                        off_session=True,
                        metadata={
                            'transaction_id': str(transaction.id),
                            'transaction_type': 'wallet_funding',
                            'user_id': str(user.id),
                            'amount': str(amount)
                        },
                        description=f"Wallet funding: ${amount}"
                    )
                    
                    # Payment successful, complete transaction
                    transaction.status = 'completed'
                    transaction.stripe_payment_intent_id = payment_intent.id
                    transaction.completed_at = timezone.now()
                    transaction.save()
                    
                    # Add funds to wallet
                    wallet.add_balance(amount)
                    
                    # Create notification
                    from core.models import Notification
                    Notification.objects.create(
                        recipient=user,
                        title="💵 Wallet Funded!",
                        badge="WALLET",
                        message=f"${amount} has been added to your wallet. New balance: ${wallet.balance}",
                        action_url="/wallet"
                    )
                    
                    return Response({
                        'detail': 'Funds added successfully using your saved card!',
                        'payment_type': 'card',
                        'transaction': PaymentTransactionSerializer(transaction, context={'request': request}).data,
                        'new_balance': str(wallet.balance)
                    })
                    
                except (stripe.error.CardError, stripe.error.StripeError) as e:
                    # Card failed, fall through to checkout
                    import logging
                    logging.getLogger(__name__).warning(f"Saved card charge failed for user {user.id}: {str(e)}")
            
            # No saved card or card failed - use Stripe Checkout
            # IMPORTANT: Set setup_future_usage so the card is saved for next time!
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Add Funds to Wallet',
                            'description': f'Deposit ${amount} to your Author Swap wallet',
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                client_reference_id=str(user.id),
                customer=cust_id,
                success_url=f"http://72.61.251.114/authorswap-frontend/account-settings",
                cancel_url=f"http://72.61.251.114/authorswap-frontend/account-settings",
                metadata={
                    'transaction_id': str(transaction.id),
                    'transaction_type': 'wallet_funding',
                    'user_id': str(user.id),
                    'amount': str(amount)
                },
                payment_intent_data={
                    'setup_future_usage': 'off_session'  # Save card for future wallet funding!
                }
            )
            
            # Store the checkout session ID
            transaction.stripe_payment_intent_id = checkout_session.id
            transaction.save()
            
            return Response({
                'detail': 'Redirecting to Stripe Checkout...',
                'url': checkout_session.url,
                'transaction_id': transaction.id,
                'amount': str(amount)
            })
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Add Funds Error: {str(e)}")
            return Response({
                'detail': f'Failed to create checkout session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmAddFundsView(APIView):
    """
    POST /api/wallet/confirm-funds/
    Called after Stripe payment success to complete the wallet funding
    Body: {
        "transaction_id": 123
    }
    Or this can be handled by Stripe Webhook
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        
        try:
            transaction = PaymentTransaction.objects.get(
                id=transaction_id,
                sender=request.user,
                transaction_type='bonus',
                status='pending'
            )
        except PaymentTransaction.DoesNotExist:
            return Response({
                'detail': 'Transaction not found or already processed.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Verify payment status with Stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
            session = stripe.checkout.Session.retrieve(transaction.stripe_payment_intent_id)
            
            if session.payment_status == 'paid':
                # Complete the transaction and add funds to wallet
                wallet, _ = UserWallet.objects.get_or_create(user=request.user)
                transaction.complete_transaction()
                
                # Create notification for wallet funding
                from core.models import Notification
                Notification.objects.create(
                    recipient=request.user,
                    title="💵 Wallet Funded!",
                    badge="WALLET",
                    message=f"${transaction.amount} has been added to your wallet. New balance: ${wallet.balance}",
                    action_url="/wallet"
                )
                
                return Response({
                    'detail': 'Funds added successfully!',
                    'transaction': PaymentTransactionSerializer(transaction, context={'request': request}).data,
                    'new_balance': str(wallet.balance)
                })
            else:
                return Response({
                    'detail': f'Payment not completed. Status: {session.payment_status}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Confirm Funds Error: {str(e)}")
            return Response({
                'detail': f'Failed to confirm payment: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
