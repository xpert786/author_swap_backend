from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import NewsletterSlot, SwapRequest
from .ui_serializers import SlotExploreSerializer, SlotDetailsSerializer, SwapArrangementSerializer
from .views import NewsletterSlotFilter

class SlotExploreView(ListAPIView):
    """
    Figma Screen 3: Swap Partner Explorer Page
    Endpoint: /api/slots/explore/
    """
    serializer_class = SlotExploreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = NewsletterSlotFilter
    search_fields = ['user__profiles__name', 'preferred_genre']

    def get_queryset(self):
        # Showing all slots so you can get the data as requested
        return NewsletterSlot.objects.all().order_by('send_date')

class SlotDetailsView(RetrieveAPIView):
    """
    Figma Screen 1: Slot Details Modal
    Endpoint: /api/slots/<id>/details/
    """
    serializer_class = SlotDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allowing viewing of all slots for data retrieval
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
