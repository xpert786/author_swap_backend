from django.urls import path
from .views import (
    CreateNewsletterSlotView, NewsletterSlotDetailView, GenreSubgenreMappingView, 
    AddBookView, BookDetailView, ProfileDetailView, BookManagementStatsView, 
    NewsletterStatsView, NotificationListView, TestWebSocketNotificationView, 
    NewsletterSlotExportView, SwapPartnerDiscoveryView, SwapRequestListView, SwapRequestDetailView,
    MyPotentialBooksView, SwapPartnerDetailView, RecentSwapHistoryView,
    SwapManagementListView, AcceptSwapView, RejectSwapView, RestoreSwapView,
    SwapHistoryDetailView, TrackMySwapView, CancelSwapView, AuthorReputationView,
    SubscriberVerificationView, ConnectMailerLiteView, SubscriberAnalyticsView
)
from .ui_views import SlotExploreView, SlotDetailsView, SwapArrangementView




urlpatterns = [
    path('newsletter-slot/', CreateNewsletterSlotView.as_view(), name='create-newsletter-slot'),
    path('newsletter-slot/<int:pk>/', NewsletterSlotDetailView.as_view(), name='newsletter-slot-detail'),
    path('genre-mapping/', GenreSubgenreMappingView.as_view(), name='genre-subgenre-mapping'),
    path('add-book/', AddBookView.as_view(), name='add-book'),
    path('book/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('profile/', ProfileDetailView.as_view(), name='profile-detail'),
    path('book-management-stats/', BookManagementStatsView.as_view(), name='book-management-stats'),
    path('newsletter-dashboard/', NewsletterStatsView.as_view(), name='newsletter-dashboard'),
    path('newsletter-stats/', NewsletterStatsView.as_view(), name='newsletter-stats'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('test-notification/', TestWebSocketNotificationView.as_view(), name='test-notification'),
    path('newsletter-slot/<int:pk>/export/', NewsletterSlotExportView.as_view(), name='newsletter-slot-export'),
    path('swap-requests/', SwapRequestListView.as_view(), name='swap-request-list'),
    path('swap-requests/<int:pk>/', SwapRequestDetailView.as_view(), name='swap-request-detail'),
    path('my-books/', MyPotentialBooksView.as_view(), name='my-potential-books'),
    
    # --- Swap Management Page (Figma) ---
    path('swaps/', SwapManagementListView.as_view(), name='swap-management-list'),
    path('accept-swap/<int:pk>/', AcceptSwapView.as_view(), name='accept-swap'),
    path('reject-swap/<int:pk>/', RejectSwapView.as_view(), name='reject-swap'),
    path('restore-swap/<int:pk>/', RestoreSwapView.as_view(), name='restore-swap'),
    path('swap-history/<int:pk>/', SwapHistoryDetailView.as_view(), name='swap-history-detail'),
    path('track-swap/<int:pk>/', TrackMySwapView.as_view(), name='track-my-swap'),
    path('cancel-swap/<int:pk>/', CancelSwapView.as_view(), name='cancel-swap'),

    # --- Figma UI Specific APIs ---
    path('slots/explore/', SlotExploreView.as_view(), name='slots-explore'),
    path('slots/<int:pk>/details/', SlotDetailsView.as_view(), name='slots-details'),
    path('swaps/<int:pk>/arrangement/', SwapArrangementView.as_view(), name='swaps-arrangement'),
    
    path('author-reputation/', AuthorReputationView.as_view(), name='author-reputation'),
    path('subscriber-verification/', SubscriberVerificationView.as_view(), name='subscriber-verification'),
    path('connect-mailerlite/', ConnectMailerLiteView.as_view(), name='connect-mailerlite'),
    path('subscriber-analytics/', SubscriberAnalyticsView.as_view(), name='subscriber-analytics'),
]