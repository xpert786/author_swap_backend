from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size,
                'results': data
            
            
        })

from .models import NewsletterSlot, SwapRequest
from .ui_serializers import SlotExploreSerializer, SlotDetailsSerializer, SwapArrangementSerializer
from .views import NewsletterSlotFilter

class SlotExploreView(ListAPIView):
    """
    Figma Screen 3: Swap Partner Explorer Page
    Endpoint: /api/slots/explore/
    Returns paginated list of available newsletter slots for swapping.
    Pagination: 9 items per page
    """
    serializer_class = SlotExploreSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = NewsletterSlotFilter
    search_fields = ['user__profiles__name', 'preferred_genre']

    def get_queryset(self):
        user = self.request.user
        
        # Identify "Friends" as authors with whom a swap has been confirmed, scheduled, or completed
        past_partners = SwapRequest.objects.filter(
            Q(requester=user) | Q(slot__user=user),
            status__in=['confirmed', 'scheduled', 'sending', 'completed', 'verified']
        ).values_list('requester', 'slot__user')
        
        # Flatten and unique the user ID list
        partner_ids = set()
        for p1, p2 in past_partners:
            partner_ids.add(p1)
            partner_ids.add(p2)
        
        if user.id in partner_ids:
            partner_ids.remove(user.id)

        from django.db.models import Count, F
        
        # Show public slots OR friend_only slots from past partners
        # ALSO: Filter out slots that have already reached their max_partners limit
        return NewsletterSlot.objects.annotate(
            active_partners_count=Count(
                'swap_requests',
                filter=Q(swap_requests__status__in=['confirmed', 'verified', 'completed', 'sending', 'scheduled'])
            )
        ).filter(
            Q(visibility='public') | 
            Q(visibility='friend_only', user_id__in=list(partner_ids))
        ).filter(
            active_partners_count__lt=F('max_partners'),
            status='available'
        ).exclude(user=user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        # Get the paginated response first
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        # Get campaign analytics for the logged-in user
        from core.models import CampaignAnalytic
        from core.serializers import CampaignAnalyticSerializer
        
        campaigns = CampaignAnalytic.objects.filter(user=request.user).order_by('-date')[:5]
        campaign_data = CampaignAnalyticSerializer(campaigns, many=True).data
        
        # Return paginated response with campaign analytics
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        
        # Add campaign_analytics to the response data
        response.data['campaign_analytics'] = campaign_data
        
        return response

class SlotDetailsView(RetrieveUpdateAPIView):
    """
    Figma Screen 1: Slot Details Modal
    Endpoint: /api/slots/<id>/details/
    """
    serializer_class = SlotDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allowing viewing of all slots for data retrieval
        # Restrict update to author only
        if self.request.method in ['PUT', 'PATCH']:
            return NewsletterSlot.objects.filter(user=self.request.user)
        return NewsletterSlot.objects.all()

class SwapArrangementView(RetrieveAPIView):
    """
    Figma Screen 2: Swap Arrangement Modal (Two-Way)
    Endpoint: /api/swaps/<id>/arrangement/
    """
    serializer_class = SwapArrangementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Either the requester or the slot owner can view the arrangement details
        return SwapRequest.objects.filter(
            Q(requester=self.request.user) | Q(slot__user=self.request.user)
        )


class SharedSlotView(RetrieveAPIView):
    """
    Endpoint: /api/slots/shared/<token>/
    Allows access to a private/hidden slot via its unique share_token.
    Only someone with the exact token can view the slot details.
    """
    serializer_class = SlotDetailsSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'share_token'
    lookup_url_kwarg = 'token'

    def get_queryset(self):
        return NewsletterSlot.objects.all()

    def retrieve(self, request, *args, **kwargs):
        try:
            slot = NewsletterSlot.objects.get(share_token=kwargs['token'])
        except NewsletterSlot.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired share link."},
                status=404
            )

        serializer = self.get_serializer(slot)
        response_data = dict(serializer.data)

        # Add share_url for reference
        response_data['share_url'] = f"http://72.61.251.114/authorswap/api/slots/shared/{slot.share_token}/"

        # Add user's books so they can pick one to send a request
        from core.models import Book
        from core.serializers import BookSerializer
        user_books = Book.objects.filter(user=request.user)
        response_data['my_books'] = list(BookSerializer(user_books, many=True, context={'request': request}).data)

        # Check if user already sent a request for this slot
        sent_request = SwapRequest.objects.filter(slot=slot, requester=request.user).exists()
        response_data['sent_request'] = sent_request

        return Response(response_data)
