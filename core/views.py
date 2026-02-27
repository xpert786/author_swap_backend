from rest_framework.views import APIView
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    NewsletterSlotSerializer, NotificationSerializer, SwapPartnerSerializer, 
    SwapRequestSerializer, SwapManagementSerializer, BookSerializer, ProfileSerializer, RecentSwapSerializer
)
from authentication.constants import GENRE_SUBGENRE_MAPPING


from .models import Book, NewsletterSlot, Profile, SwapRequest, Notification
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
        serializer = NewsletterSlotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "message": "Newsletter slot created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        slots = request.user.newsletter_slots.all()
        serializer = NewsletterSlotSerializer(slots, many=True)
        return Response({
            "message": "Newsletter slots retrieved successfully.",
            "data": serializer.data
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

    def post(self, request):
        serializer = SwapRequestSerializer(data=request.data)
        if serializer.is_valid():
            slot = serializer.validated_data['slot']
            book = serializer.validated_data.get('book')

            if slot.user == request.user:
                return Response({"detail": "You cannot request a swap for your own slot."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if a request already exists
            if SwapRequest.objects.filter(slot=slot, requester=request.user).exists():
                return Response({"detail": "You have already sent a request for this slot."}, status=status.HTTP_400_BAD_REQUEST)

            # Link validation
            if book:
                links = [book.amazon_url, book.apple_url, book.kobo_url, book.barnes_noble_url]
                for link in links:
                    if link:
                        try:
                            r = requests.head(link, timeout=3, allow_redirects=True)
                            if r.status_code >= 400:
                                return Response({"detail": f"Retailer link {link} appears broken (HTTP {r.status_code})."}, status=status.HTTP_400_BAD_REQUEST)
                        except requests.RequestException:
                            return Response({"detail": f"Failed to reach retailer link: {link}."}, status=status.HTTP_400_BAD_REQUEST)

            initial_status = 'pending'
            target_profile = slot.user.profiles.first()
            requester_profile = request.user.profiles.first()

            if target_profile and requester_profile:
                is_friend = target_profile.friends.filter(id=requester_profile.id).exists()
                meets_rep = (target_profile.auto_approve_min_reputation > 0 and 
                             requester_profile.reputation_score >= target_profile.auto_approve_min_reputation)
                
                if (target_profile.auto_approve_friends and is_friend) or meets_rep:
                    initial_status = 'confirmed'

            swap_req = serializer.save(requester=request.user, status=initial_status)
            return Response(SwapRequestSerializer(swap_req).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        # type param: 'sent' or 'received'
        request_type = request.query_params.get('type', 'sent')
        if request_type == 'sent':
            requests = SwapRequest.objects.filter(requester=request.user)
        else:
            requests = SwapRequest.objects.filter(slot__user=request.user)
        
        serializer = SwapRequestSerializer(requests, many=True)
        return Response(serializer.data)

class SwapRequestDetailView(RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating (Accept/Reject), and deleting swap requests.
    """
    queryset = SwapRequest.objects.all()
    serializer_class = SwapRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SwapRequest.objects.filter(
            Q(requester=self.request.user) | Q(slot__user=self.request.user)
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        new_status = serializer.validated_data.get('status')
        
        if new_status in ['confirmed', 'rejected'] and instance.slot.user != self.request.user:
            return Response({"detail": "Only the slot owner can confirm or reject a swap request."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer.save()

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

        # Base queryset: swaps where the current user owns the slot (received)
        qs = SwapRequest.objects.filter(slot__user=user).select_related(
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
        all_qs = SwapRequest.objects.filter(slot__user=user)
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
        return Response({
            "detail": "Swap request cancelled successfully.",
            "swap_id": swap.id,
            "status": swap.status,
        })

from django.db.models import Q
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import ChatMessage, SwapRequest
from .serializers import ChatMessageSerializer, ConversationPartnerSerializer

class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get users who have exchanged messages with current user
        message_users = User.objects.filter(
            Q(sent_messages__receiver=user) | 
            Q(received_messages__sender=user)
        ).distinct()
        
        serializer = ConversationPartnerSerializer(message_users, many=True, context={'request': request})
        return Response(serializer.data)

class ComposePartnerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. Get all swap partners (eligible to chat)
        swap_requests = SwapRequest.objects.filter(
            (Q(requester=user) | Q(slot__user=user))
        ).exclude(status='rejected')
        
        eligible_user_ids = set()
        for sr in swap_requests:
            if sr.requester == user:
                eligible_user_ids.add(sr.slot.user_id)
            else:
                eligible_user_ids.add(sr.requester_id)
        
        # 2. Get user IDs who ALREADY have a conversation
        chatted_user_ids = set(User.objects.filter(
            Q(sent_messages__receiver=user) | 
            Q(received_messages__sender=user)
        ).values_list('id', flat=True).distinct())
        
        # 3. Filter: eligible minus chatted
        compose_user_ids = eligible_user_ids - chatted_user_ids
        
        compose_users = User.objects.filter(id__in=compose_user_ids)
        
        serializer = ConversationPartnerSerializer(compose_users, many=True, context={'request': request})
        return Response(serializer.data)

class MySwapPartnersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get swap partners (any swap relationship, excluding rejected)
        swap_requests = SwapRequest.objects.filter(
            (Q(requester=user) | Q(slot__user=user))
        ).exclude(status='rejected')
        
        partner_users = []
        for sr in swap_requests:
            if sr.requester == user:
                partner_users.append(sr.slot.user)
            else:
                partner_users.append(sr.requester)
        
        # Unique
        partner_users = list(set(partner_users))
        
        serializer = ConversationPartnerSerializer(partner_users, many=True, context={'request': request})
        return Response(serializer.data)

class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, receiver_id):
        user = request.user
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            
        messages = ChatMessage.objects.filter(
            (Q(sender=user) & Q(receiver=receiver)) |
            (Q(sender=receiver) & Q(receiver=user))
        ).order_by('created_at')
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)