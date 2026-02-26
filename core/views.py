from rest_framework.views import APIView
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    NewsletterSlotSerializer, NotificationSerializer, SwapPartnerSerializer, 
    SwapRequestSerializer, SwapManagementSerializer, BookSerializer, ProfileSerializer, RecentSwapSerializer,
    SubscriptionTierSerializer, UserSubscriptionSerializer, SubscriberVerificationSerializer,
    SubscriberGrowthSerializer, CampaignAnalyticSerializer
)
from .ui_serializers import SlotExploreSerializer, SlotDetailsSerializer
from authentication.constants import GENRE_SUBGENRE_MAPPING


from .models import (
    Book, NewsletterSlot, Profile, SwapRequest, Notification, 
    SubscriptionTier, UserSubscription, SubscriberVerification,
    SubscriberGrowth, CampaignAnalytic
)
import calendar
from datetime import datetime, date, timedelta
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.db.models import Count, Q

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

            serializer.save(user=request.user, audience_size=audience_size)
            return Response({
                "message": "Newsletter slot created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get(self, request):
        slots = request.user.newsletter_slots.all()
        serializer = NewsletterSlotSerializer(slots, many=True, context={'request': request})
        return Response({
            "message": "Newsletter slots retrieved successfully.",
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
            "audience_size": verification.audience_size,
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

        # --- 1. TOP STATS CARDS DATA ---
        all_slots = NewsletterSlot.objects.filter(user=user)
        stats = {
            "total": all_slots.count(),
            "published_slots": all_slots.filter(visibility='public').count(),
            "pending_swaps": SwapRequest.objects.filter(slot__user=user, status='pending').count(),
            "confirmed_swaps": SwapRequest.objects.filter(slot__user=user, status='confirmed').count(),
            "verified_sent": SwapRequest.objects.filter(slot__user=user, status='verified').count()
        }

        # --- 2. CALENDAR DATA ---
        calendar_data = []
        num_days = calendar.monthrange(year, month)[1]

        # Use 'swap_requests' instead of 'swaps'
        slots_in_month = NewsletterSlot.objects.filter(
            user=user, 
            send_date__year=year, 
            send_date__month=month
        ).values('send_date', 'visibility').annotate(
            total=Count('id'),
            pending=Count('swap_requests', filter=Q(swap_requests__status='pending')),
            confirmed=Count('swap_requests', filter=Q(swap_requests__status='confirmed')),
            verified=Count('swap_requests', filter=Q(swap_requests__status='verified'))
        )

        # Map the DB results by date for easy lookup
        date_map = {s['send_date']: s for s in slots_in_month}

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            day_stats = date_map.get(current_date, {})
            
            calendar_data.append({
                "date": current_date.isoformat(),
                "day": day,
                "has_published": day_stats.get('total', 0) > 0 and day_stats.get('visibility') == 'public',
                "has_confirmed": day_stats.get('confirmed', 0) > 0,
                "has_pending": day_stats.get('pending', 0) > 0,
                "has_verified": day_stats.get('verified', 0) > 0,
            })

        return Response({
            "stats_cards": stats,
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
            
            # If no book provided, auto-pick the requester's primary promotional book
            if not book:
                primary_book = Book.objects.filter(user=request.user, is_primary_promo=True).first()
                if primary_book:
                    book = primary_book
                else:
                    # Fallback to the latest active book
                    book = Book.objects.filter(user=request.user, is_active=True).order_by('-created_at').first()
            
            # if not book:
            #     return Response({"detail": "You must have at least one active book to request a swap."}, status=status.HTTP_400_BAD_REQUEST)

            #if slot.user == request.user:
            #    return Response({"detail": "You cannot request a swap for your own slot."}, status=status.HTTP_400_BAD_REQUEST)
            
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

            swap_req = serializer.save(requester=request.user, status=initial_status, book=book)
            response_data = SwapRequestSerializer(swap_req).data
            response_data['detail'] = f"Swap request sent successfully! {request.user.username} has requested the {slot.send_date} slot."
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
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
            status__in=['confirmed', 'verified']
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
        'scheduled': ['scheduled'],
        'completed': ['completed', 'verified'],
    }

    def get(self, request):
        user = request.user
        tab = request.query_params.get('tab', 'all').lower()
        search = request.query_params.get('search', '').strip()

        # Base queryset: swaps where the current user is either the requester (sent) or owns the slot (received)
        qs = SwapRequest.objects.filter(
            Q(slot__user=user) | Q(requester=user)
        ).select_related(
            'requester', 'slot', 'book'
        ).order_by('-created_at')

        # Tab filtering
        statuses = self.TAB_STATUS_MAP.get(tab)
        if statuses:
            qs = qs.filter(status__in=statuses)

        # Search by author name, book title, or date
        if search:
            qs = qs.filter(
                Q(requester__profiles__name__icontains=search) |
                Q(requester__username__icontains=search) |
                Q(book__title__icontains=search) |
                Q(slot__send_date__icontains=search)
            ).distinct()

        # Sync audience from MailerLite for each unique requester (non-blocking)
        try:
            for swap in qs[:20]:  # Limit to avoid overloading
                profile = swap.requester.profiles.first()
                if profile:
                    sync_profile_audience(profile)
        except Exception:
            pass  # MailerLite may not be configured; silently continue

        serializer = SwapManagementSerializer(qs, many=True, context={'request': request})

        # Tab counts for the badge numbers on each tab
        all_qs = SwapRequest.objects.filter(Q(slot__user=user) | Q(requester=user))
        tab_counts = {
            'all': all_qs.count(),
            'pending': all_qs.filter(status='pending').count(),
            'sending': all_qs.filter(status='sending').count(),
            'rejected': all_qs.filter(status='rejected').count(),
            'scheduled': all_qs.filter(status='scheduled').count(),
            'completed': all_qs.filter(status__in=['completed', 'verified']).count(),
        }

        return Response({
            'tab': tab,
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

        swap.status = 'confirmed'
        swap.save()

        # MailerLite: move from Pending → Approved group
        requester_email = swap.requester.email
        try:
            approve_swap_notification(requester_email)
        except Exception:
            pass  # Non-critical; log internally

        # Notification for requester
        Notification.objects.create(
            recipient=swap.requester,
            title="Swap Request Accepted! ✅",
            badge="SWAP",
            message=f"Good news! {request.user.username} has accepted your swap request for their {swap.slot.get_preferred_genre_display()} slot.",
            action_url=f"/dashboard/swaps/track/{swap.id}/"
        )

        return Response({
            "detail": "Swap request accepted.",
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
        swap.rejection_reason = request.data.get('reason', '')
        swap.rejected_at = tz.now()
        swap.save()

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

        # Notification for slot owner
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
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        verification, _ = SubscriberVerification.objects.get_or_create(user=request.user)
        subscription = UserSubscription.objects.filter(user=request.user, is_active=True).first()
        tiers = SubscriptionTier.objects.all().order_by('price')
        
        return Response({
            "verification": SubscriberVerificationSerializer(verification).data,
            "subscription": UserSubscriptionSerializer(subscription).data if subscription else None,
            "available_tiers": SubscriptionTierSerializer(tiers, many=True).data,
        })


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
        from core.services.mailerlite_service import sync_subscriber_analytics
        
        # Trigger real-time sync
        verification = sync_subscriber_analytics(request.user)
        
        growth_data = SubscriberGrowth.objects.filter(user=request.user)
        campaigns = CampaignAnalytic.objects.filter(user=request.user)
        
        return Response({
            "summary_stats": {
                "active_subscribers": verification.audience_size,
                "avg_open_rate": f"{verification.avg_open_rate}%",
                "avg_click_rate": f"{verification.avg_click_rate}%",
                "list_health_score": f"{verification.list_health_score}/100",
            },
            "growth_chart": SubscriberGrowthSerializer(growth_data, many=True).data,
            "list_health_metrics": {
                "bounce_rate": f"{verification.bounce_rate}%",
                "unsubscribe_rate": f"{verification.unsubscribe_rate}%",
                "active_rate": f"{verification.active_rate}%",
                "avg_engagement": verification.avg_engagement,
            },
            "campaign_analytics": CampaignAnalyticSerializer(campaigns, many=True).data,
            # Link-level analysis is handled per-campaign or as a general summary here
            "link_level_ctr": [] # Placeholder for now as it depends on campaign selection in UI
        })


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
            status__in=['completed', 'verified']
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
            confirmed_swaps=Count('swap_requests', filter=Q(swap_requests__status__in=['confirmed', 'verified'])),
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
        notifications = Notification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:10]

        for notif in notifications:
            time_diff = now - notif.created_at.replace(tzinfo=None)
            if time_diff.days == 0:
                time_ago = "Today"
            elif time_diff.days == 1:
                time_ago = "1 day ago"
            else:
                time_ago = f"{time_diff.days} days ago"

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

                time_diff = now - swap.created_at.replace(tzinfo=None)
                if time_diff.days == 0:
                    time_ago = "Today"
                elif time_diff.days == 1:
                    time_ago = "1 day ago"
                else:
                    time_ago = f"{time_diff.days} days ago"

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

        pen_name = user_profile.pen_name if user_profile and user_profile.pen_name else user.username
        profile_photo = None
        if user_profile and user_profile.profile_photo:
            profile_photo = request.build_absolute_uri(user_profile.profile_photo.url)
        elif profile and profile.profile_picture:
            profile_photo = request.build_absolute_uri(profile.profile_picture.url)

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