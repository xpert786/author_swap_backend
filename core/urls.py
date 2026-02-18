from django.urls import path
from .views import CreateNewsletterSlotView, NewsletterSlotDetailView, GenreSubgenreMappingView, AddBookView, BookDetailView

urlpatterns = [
    path('newsletter-slot/', CreateNewsletterSlotView.as_view(), name='create-newsletter-slot'),
    path('newsletter-slot/<int:pk>/', NewsletterSlotDetailView.as_view(), name='newsletter-slot-detail'),
    path('genre-mapping/', GenreSubgenreMappingView.as_view(), name='genre-subgenre-mapping'),
    path('add-book/', AddBookView.as_view(), name='add-book'),
    path('book/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
]
