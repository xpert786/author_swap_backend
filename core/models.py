from django.db import models
from django.contrib.auth import get_user_model
from authentication.models import PRIMARY_GENRE_CHOICES

User = get_user_model()

class NewsletterSlot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='newsletter_slots')
    send_date = models.DateField()
    send_time = models.TimeField()
    audience_size = models.PositiveIntegerField(default=0)
    preferred_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    
    # Store subgenres as a comma-separated string
    subgenres = models.CharField(max_length=300, blank=True, null=True)
    
    max_partners = models.PositiveIntegerField(default=5)
    visibility = models.CharField(
        max_length=30, 
        choices=[('public', 'Public'), ('friend_only', 'Friend Only'),('single_use_private_link', 'Single-use private link'),('hidden', 'Hidden')], 
        default='public'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.preferred_genre} slot on {self.send_date}"

class Book(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=255)
    primary_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    subgenres = models.CharField(max_length=300, help_text="Comma-separated keys")
    
    price_tier = models.CharField(max_length=50, blank=True, null=True, choices=[('discounted', 'Discounted'), ('free', 'Free'), ('standard', 'Standard'), ('0.99', '$0.99')], default='standard')
    book_cover = models.ImageField(upload_to='book_covers/')
    availability = models.CharField(max_length=50,choices=[('all','All'),('wide','Wide'),('kindle Unlimited','Kindle Unlimited')],default='all')
    publish_date = models.DateField()
    description = models.TextField()    
    # Retailer Links
    amazon_url = models.URLField(blank=True, null=True)
    apple_url = models.URLField(blank=True, null=True)
    kobo_url = models.URLField(blank=True, null=True)
    barnes_noble_url = models.URLField(blank=True, null=True)

    is_primary_promo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title