from django.db import models
from django.contrib.auth import get_user_model
from authentication.constants import PRIMARY_GENRE_CHOICES

User = get_user_model()

class NewsletterSlot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='newsletter_slots')
    send_date = models.DateField()
    send_time = models.TimeField()  
    status = models.CharField(max_length=20, choices=[('available', 'Available'), ('booked', 'Booked'),('pending', 'Pending')], default='available')    
    @property
    def time_period(self):
        hour = self.send_time.hour
        if 0 <= hour < 12:
            return "Morning"    
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"
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
    
    # Advanced Discovery Fields
    PLACEMENT_CHOICES = [('top', 'Top'), ('mid', 'Mid'), ('bottom', 'Bottom'), ('any', 'Any')]
    placement_style = models.CharField(max_length=20, choices=PLACEMENT_CHOICES, default='any')
    
    PROMOTION_CHOICES = [('free', 'Free'), ('paid', 'Paid'), ('genre_specific', 'Genre-Specific')]
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_CHOICES, default='genre_specific')
    
    # Added price for paid promotions based on UI mockups
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Set price if promotion_type is Paid")
    
    partner_requirements = models.TextField(blank=True, null=True)
    
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
    primary_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    reputation_score = models.FloatField(default=5.0) # 0 to 5
    
    # Analytics Breakdown (Mockup Details)
    avg_open_rate = models.FloatField(default=0.0)
    avg_click_rate = models.FloatField(default=0.0)
    monthly_growth = models.PositiveIntegerField(default=0)
    send_reliability_percent = models.FloatField(default=0.0)
    
    # Reputation Score Breakdown
    confirmed_sends_score = models.PositiveIntegerField(default=0)
    timeliness_score = models.PositiveIntegerField(default=0)
    missed_sends_penalty = models.IntegerField(default=0)
    communication_score = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Auto-Approve logic and friends
    auto_approve_friends = models.BooleanField(default=False)
    auto_approve_min_reputation = models.FloatField(default=0.0)
    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    @property
    def swaps_completed(self):
        from .models import SwapRequest
        # Count confirmed/verified requests where this profile's user is either the requester or the slot owner
        sent_confirmed = self.user.sent_swap_requests.filter(status__in=['confirmed', 'verified']).count()
        received_confirmed = SwapRequest.objects.filter(slot__user=self.user, status__in=['confirmed', 'verified']).count()
        return sent_confirmed + received_confirmed

    def __str__(self):
        return self.name

class SwapRequest(models.Model):
    # The slot being requested (owned by *another* user)
    slot = models.ForeignKey(NewsletterSlot, on_delete=models.CASCADE, related_name='swap_requests')
    
    # The user making the request
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_swap_requests')
    
    # The book being promoted in this swap ("You Send" book)
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='swap_requests', null=True)

    # The slot the requester is offering in return ("You Send" slot)
    offered_slot = models.ForeignKey(NewsletterSlot, on_delete=models.SET_NULL, related_name='offered_swap_requests', null=True, blank=True)
    
    # The book the requester wants the partner to promote ("Partner Sends" book)
    requested_book = models.ForeignKey('Book', on_delete=models.SET_NULL, related_name='requested_in_swaps', null=True, blank=True)

    
    # The status of the request
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('sending', 'Sending'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # UI Modal Fields
    message = models.TextField(max_length=250, blank=True, null=True)
    PLACEMENT_CHOICES = [('top', 'Top'), ('middle', 'Middle'), ('bottom', 'Bottom')]
    preferred_placement = models.CharField(max_length=10, choices=PLACEMENT_CHOICES, default='middle')
    max_partners_acknowledged = models.PositiveIntegerField(default=5)

    # Rejection
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    # Scheduling
    scheduled_date = models.DateField(blank=True, null=True)
    
    # Completion
    completed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Request by {self.requester} for slot {self.slot}"


class SwapLinkClick(models.Model):
    """
    Tracks link-level CTR analysis for completed swaps.
    Each row = one tracked link in the swap partner's newsletter.
    Shown on the 'View Swap History' detail page (Figma).
    """
    swap = models.ForeignKey(SwapRequest, on_delete=models.CASCADE, related_name='link_clicks')
    link_name = models.CharField(max_length=255, help_text="e.g. 'The Midnight Garden'")
    destination_url = models.URLField(help_text="e.g. https://amazon.com/dp/B0C123456")
    clicks = models.PositiveIntegerField(default=0)
    ctr = models.FloatField(default=0.0, help_text="Click-through rate as percentage, e.g. 4.1")
    ctr_label = models.CharField(max_length=20, blank=True, default='', help_text="e.g. 'Excellent', 'Good', 'Low'")
    conversions = models.PositiveIntegerField(default=0, help_text="Number of sales/conversions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.link_name} → {self.clicks} clicks ({self.ctr}%)"


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