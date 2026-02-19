from django.urls import path
from .views import CreateNewsletterSlotView, NewsletterSlotDetailView, GenreSubgenreMappingView, AddBookView, BookDetailView, ProfileDetailView, BookManagementStatsView, NewsletterStatsView, NotificationListView

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
]
