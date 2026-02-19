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
    rating = models.FloatField(default=0.0)
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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    email = models.EmailField(blank=True, null=True)
    name = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    primary_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    bio = models.TextField()
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name   

class SwapRequest(models.Model):
    # The slot being requested (owned by *another* user)
    slot = models.ForeignKey(NewsletterSlot, on_delete=models.CASCADE, related_name='swap_requests')
    
    # The user making the request
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_swap_requests')
    
    # The status of the request
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.requester} for slot {self.slot}"
class Notification(models.Model):
    # Badge labels as seen in image
    BADGE_CHOICES = [
        ('SWAP', 'Swap'),
        ('VERIFIED', 'Verified'),
        ('REMINDER', 'Reminder'),
        ('DEADLINE', 'Deadline'),
        ('NEW', 'New'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)  # e.g., "New Swap Request"
    message = models.TextField()              # e.g., "Amanda Johnson requested a swap..."
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, blank=True)
    
    # Actionable link (URL to jump to Message/Swap Detail)
    action_url = models.CharField(max_length=255, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} for {self.recipient.username}"