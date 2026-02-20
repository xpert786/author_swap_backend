from django.urls import path
from .views import (
    CreateNewsletterSlotView, NewsletterSlotDetailView, GenreSubgenreMappingView, 
    AddBookView, BookDetailView, ProfileDetailView, BookManagementStatsView, 
    NewsletterStatsView, NotificationListView, TestWebSocketNotificationView, 
    NewsletterSlotExportView, SwapPartnerDiscoveryView, SwapRequestListView, SwapRequestDetailView,
    MyPotentialBooksView, SwapPartnerDetailView, RecentSwapHistoryView
)




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
    path('swap-partners/discovery/', SwapPartnerDiscoveryView.as_view(), name='swap-partner-discovery'),
    path('swap-partners/discovery/<int:pk>/', SwapPartnerDetailView.as_view(), name='swap-partner-detail'),
    path('swap-partners/discovery/<int:author_id>/history/', RecentSwapHistoryView.as_view(), name='author-swap-history'),
    path('swap-requests/', SwapRequestListView.as_view(), name='swap-request-list'),
    path('swap-requests/<int:pk>/', SwapRequestDetailView.as_view(), name='swap-request-detail'),
    path('my-books/', MyPotentialBooksView.as_view(), name='my-potential-books'),
]



