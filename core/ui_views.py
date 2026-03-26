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
        
        # Get list of users the current user has completed swaps with (Friends)
        # Search in both sent and received requests
        past_partners = SwapRequest.objects.filter(
            Q(requester=user) | Q(slot__user=user),
            status__in=['completed', 'verified']
        ).values_list('requester', 'slot__user')
        
        # Flatten and unique the user ID list
        partner_ids = set()
        for p1, p2 in past_partners:
            partner_ids.add(p1)
            partner_ids.add(p2)
        
        if user.id in partner_ids:
            partner_ids.remove(user.id)

        # Show public slots OR friend_only slots from past partners
        return NewsletterSlot.objects.filter(
            Q(visibility='public') | 
            Q(visibility='friend_only', user_id__in=list(partner_ids))
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
